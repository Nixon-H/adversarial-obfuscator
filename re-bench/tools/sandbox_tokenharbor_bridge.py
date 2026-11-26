#!/usr/bin/env python3
"""In-sandbox TCP-loopback -> Unix-socket bridge, then wrapper for OpenCode.

No credentials are used or accepted here. The only network endpoints reachable
inside the benchmark network namespace are loopback bridges; their Unix sockets
are handled outside the sandbox. Port 8976 is the credential-isolated model
proxy. Port 8545 is the local py-evm relay required by the licence-chain path.
"""
import json, os, socket, subprocess, sys, threading

HOST='127.0.0.1'
MAPPINGS=(
    (int(os.environ.get('ABSMAX_LOCAL_LLM_PORT','8976')), os.environ.get('ABSMAX_TOKENHARBOR_SOCK','/run/absmax-tokenharbor/tokenharbor.sock')),
    (int(os.environ.get('ABSMAX_LOCAL_EVM_PORT','8545')), os.environ.get('ABSMAX_EVM_SOCK','/run/absmax-tokenharbor/evm.sock')),
)

# The benchmark chain is shared across concurrent attempts. State-changing RPCs
# are blocked inside agent sandboxes; contract mutation/revocation behaviour is
# covered by the independent local-EVM test harness, not by letting agents
# interfere with each other's chain state.
EVM_READ_ONLY_METHODS={
    'web3_clientVersion','net_version','eth_chainId','eth_blockNumber',
    'eth_call','eth_getCode','eth_getBlockByNumber','eth_getBlockByHash',
    'eth_getBalance','eth_getTransactionCount','eth_getTransactionReceipt',
    'eth_getTransactionByHash','eth_estimateGas','eth_gasPrice','eth_syncing',
}


def relay(a,b):
    try:
        while True:
            try: data=a.recv(65536)
            except (ConnectionResetError,BrokenPipeError): break
            if not data: break
            b.sendall(data)
    except Exception:
        pass
    for s in (a,b):
        try: s.shutdown(socket.SHUT_RDWR)
        except Exception: pass


def _read_connect_target(conn):
    data=b''
    marker=b'\r\n\r\n'
    while marker not in data and len(data)<16384:
        chunk=conn.recv(4096)
        if not chunk:
            raise ValueError('eof before CONNECT headers')
        data+=chunk
    first=data.split(b'\r\n',1)[0].decode('ascii','strict')
    parts=first.split()
    if len(parts)<2 or parts[0].upper()!='CONNECT':
        raise ValueError('not CONNECT')
    host,port_s=parts[1].rsplit(':',1)
    return host,int(port_s),data


def pipe_unix_client(conn,sock_path):
    """Pipe the untouched CONNECT stream to the host-side redacting MITM proxy."""
    try:
        upstream=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        upstream.connect(sock_path)
    except Exception:
        try: conn.close()
        except Exception: pass
        return
    t1=threading.Thread(target=relay,args=(conn,upstream),daemon=True)
    t2=threading.Thread(target=relay,args=(upstream,conn),daemon=True)
    t1.start(); t2.start()


def connect_client(conn,relay_sock):
    """Handle HTTPS_PROXY CONNECT through the allowlisted host-side relay.

    The tunnel is opaque TLS, but only exact OpenCode service hosts are
    reachable. This preserves the no-general-egress boundary while allowing
    the operator-authorised hy4 lane to function without provider credentials.
    """
    upstream=None
    try:
        host,port,_headers=_read_connect_target(conn)
        upstream=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        upstream.connect(relay_sock)
        upstream.sendall((host+' '+str(port)+'\n').encode('ascii'))
        status=b''
        while not status.endswith(b'\n') and len(status)<128:
            x=upstream.recv(1)
            if not x:raise ValueError('relay closed before status')
            status+=x
        if not status.startswith(b'OK'):
            conn.sendall(b'HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n')
            return
        conn.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
        t1=threading.Thread(target=relay,args=(conn,upstream),daemon=True)
        t2=threading.Thread(target=relay,args=(upstream,conn),daemon=True)
        t1.start(); t2.start()
    except Exception:
        try:conn.close()
        except Exception:pass
        try:
            if upstream is not None:upstream.close()
        except Exception:pass


def client(conn,sock_path):
    try:
        try:
            peek=conn.recv(2048,socket.MSG_PEEK)
        except Exception:
            peek=b''
        if peek.upper().startswith(b'CONNECT '):
            mitm_sock='/run/absmax-tokenharbor/opencode-mitm.sock'
            if os.path.exists(mitm_sock):
                pipe_unix_client(conn,mitm_sock)
            else:
                connect_client(conn,'/run/absmax-tokenharbor/opencode-connect.sock')
            return
        upstream=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        upstream.connect(sock_path)
    except Exception:
        try: conn.close()
        except Exception: pass
        return
    t1=threading.Thread(target=relay,args=(conn,upstream),daemon=True)
    t2=threading.Thread(target=relay,args=(upstream,conn),daemon=True)
    t1.start(); t2.start()


def _http_json_response(request_id, code, obj):
    body=json.dumps(obj).encode()
    head=(f'HTTP/1.1 {code}\r\n'
          'Content-Type: application/json\r\n'
          f'Content-Length: {len(body)}\r\n'
          'Connection: close\r\n\r\n')
    return head.encode()+body


def _read_http_request(conn):
    data=b''
    marker=b'\r\n\r\n'
    while marker not in data and len(data)<65536:
        chunk=conn.recv(4096)
        if not chunk:
            raise ValueError('eof before headers')
        data+=chunk
    head,rest=data.split(marker,1)
    lines=head.decode('iso-8859-1',errors='replace').split('\r\n')
    headers={}
    for line in lines[1:]:
        if ':' in line:
            k,v=line.split(':',1);headers[k.strip().lower()]=v.strip()
    length=int(headers.get('content-length','0') or '0')
    body=rest
    while len(body)<length:
        chunk=conn.recv(min(65536,length-len(body)))
        if not chunk:
            raise ValueError('eof before body')
        body+=chunk
    return head+marker+body[:length],body[:length]


def _read_http_response(upstream):
    data=b''
    marker=b'\r\n\r\n'
    while marker not in data and len(data)<1048576:
        chunk=upstream.recv(65536)
        if not chunk:
            return data
        data+=chunk
    if marker not in data:
        return data
    head,rest=data.split(marker,1)
    headers={}
    for line in head.decode('iso-8859-1',errors='replace').split('\r\n')[1:]:
        if ':' in line:
            k,v=line.split(':',1);headers[k.strip().lower()]=v.strip()
    if 'content-length' not in headers:
        return data
    try:
        length=int(headers['content-length'])
    except Exception:
        return data
    while len(rest)<length:
        chunk=upstream.recv(min(65536,length-len(rest)))
        if not chunk: break
        rest+=chunk
    return head+marker+rest[:length]


def _rpc_methods(body):
    try:
        req=json.loads(body.decode())
    except Exception:
        return None,None
    if isinstance(req,list):
        return [str(x.get('method','')) for x in req if isinstance(x,dict)],req
    if isinstance(req,dict):
        return [str(req.get('method',''))],req
    return [],req


def evm_client(conn,sock_path):
    """Forward one read-only JSON-RPC HTTP request to the local EVM relay."""
    try:
        raw,body=_read_http_request(conn)
        methods,req=_rpc_methods(body)
        if not methods or any(m not in EVM_READ_ONLY_METHODS for m in methods):
            rid=req.get('id') if isinstance(req,dict) else None
            conn.sendall(_http_json_response(rid,'403 Forbidden',{
                'jsonrpc':'2.0','id':rid,
                'error':{'code':-32601,'message':'benchmark chain endpoint is read-only in agent sandboxes'}}))
            return
        upstream=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        upstream.connect(sock_path)
        upstream.sendall(raw)
        response=_read_http_response(upstream)
        if response:
            conn.sendall(response)
        try: upstream.close()
        except Exception: pass
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass


def server(srv,port,sock_path):
    evm_port=int(os.environ.get('ABSMAX_LOCAL_EVM_PORT','8545'))
    while True:
        conn,_=srv.accept()
        handler=evm_client if port==evm_port else client
        threading.Thread(target=handler,args=(conn,sock_path),daemon=True).start()


def listen(port):
    srv=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    srv.bind((HOST,port)); srv.listen(64)
    return srv


def main():
    if len(sys.argv)<2:
        print('usage: sandbox_tokenharbor_bridge.py COMMAND...',file=sys.stderr); return 2
    for port,sock_path in MAPPINGS:
        srv=listen(port)
        threading.Thread(target=server,args=(srv,port,sock_path),daemon=True).start()
    return subprocess.call(sys.argv[1:])

if __name__=='__main__': sys.exit(main())
