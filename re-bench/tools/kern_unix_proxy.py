#!/usr/bin/env python3
"""Credential-holding Kern proxy on a loopback-only Unix socket.

The proxy exists so benchmark sandboxes can use the operator-authorised Kern
model without inheriting or reading the real API credential. It logs metadata
only: no prompts, completions, headers, or credential material.
"""
import ast, base64, hashlib, json, os, socketserver, sys, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler
from pathlib import Path

UPSTREAM='https://api.kern-llm.org/v1'
MODEL='thinkingmachines/inkling-2-mini'
LOCAL_MODEL='inkling-2-mini'
AUTHORIZED_MODELS=frozenset((MODEL,LOCAL_MODEL))
MAX_BODY=32*1024*1024
SOCKET_PATH=Path(os.environ.get('KERN_PROXY_SOCKET','/home/nixon/absmax-tokenharbor-proxy/kern.sock'))
LOG_PATH=Path('/home/nixon/absmax-tokenharbor-proxy/kern-proxy.log')
READY_PATH=Path(os.environ.get('KERN_PROXY_READY','/home/nixon/absmax-tokenharbor-proxy/kern-proxy.ready'))
KEY=os.environ.get('KERN_API_KEY','')


def load_redactions():
    """Exact benchmark-runtime secret redaction for provider-bound traffic.

    The legitimate-runtime-secrets attacker is intentionally given test secrets,
    but the remote model provider is not an authorized recipient of those values.
    Redact them from both requests and responses while preserving shape labels.
    """
    root=Path('/home/nixon/Projects/adversarial-obfuscator/re-bench/secrets')
    out=[]
    for sec in sorted(root.glob('*/cipher')):
        variant=sec.parent.name
        try:
            lic_text=(sec/'runtime.licence').read_text().strip()
            out.append((lic_text.encode(),b'<redacted-runtime-licence>'))
            lic=json.loads(lic_text); payload=lic.get('payload') or {}
            for key in ('key_material','nonce','hwid'):
                val=payload.get(key)
                if isinstance(val,str) and val:
                    out.append((val.encode(),f'<redacted-licence-{key}>'.encode()))
        except Exception:
            pass
        try:
            shard=(sec/'nx_seal_shard.hex').read_text().strip()
            if shard: out.append((shard.encode(),b'<redacted-nx-seal-shard>'))
        except Exception:
            pass
        # Licence-derived masks/effective native keys are sensitive even though
        # the raw artifact shares are attacker-visible. Compute them locally so
        # a legitimate-secrets agent cannot exfiltrate them merely by deriving
        # and printing the result. Never log the values themselves.
        try:
            artifact=Path('/home/nixon/Projects/adversarial-obfuscator/re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds')/variant/'cipher/artifact.py'
            tree=ast.parse(artifact.read_text(encoding='utf-8',errors='surrogateescape'))
            lit={}
            for node in tree.body:
                if isinstance(node,ast.Assign):
                    for tgt in node.targets:
                        if isinstance(tgt,ast.Name):
                            try: lit[tgt.id]=ast.literal_eval(node.value)
                            except Exception: pass
            s0=base64.b64decode(lit['_BLOB_S0']); s1=base64.b64decode(lit['_BLOB_S1'])
            raw=bytes(a^b for a,b in zip(s0,s1))
            bm=hashlib.sha256(str(lit['_NX_BUILD_ID']).encode()).digest()
            basekey=bytes(b^bm[i%len(bm)] for i,b in enumerate(raw))
            lic=json.loads((sec/'runtime.licence').read_text())
            km=(lic.get('payload') or {}).get('key_material')
            cm=hashlib.sha256(b'nx-customer:'+str(km).encode()).digest()
            eff=bytes(b^cm[i%len(cm)] for i,b in enumerate(basekey))
            for label,val in [('licence-customer-mask',cm),('licence-effective-native-key',eff)]:
                for encoded in (val.hex().encode(),val.hex().upper().encode(),base64.b64encode(val)):
                    out.append((encoded,f'<redacted-{label}>'.encode()))
        except Exception:
            pass
    # Expand exact values into JSON-escaped, hexadecimal, and base64 forms before
    # matching. OpenCode serialises tool output into JSON request bodies, so raw
    # multiline licence text usually does not appear byte-for-byte even when the
    # model is relaying that exact file content back to the provider.
    try:
        import redact_benchmark_credentials as rbc
        for val,label in rbc.collect_license_derived_secrets():
            if not val:
                continue
            for rep_val,rep_label in rbc.expand_secret_representations(val,label):
                if rep_val:
                    out.append((rep_val.encode(),f'<redacted-{rep_label}>'.encode()))
        for env_name,val in rbc.collect_env_secrets():
            if not val:
                continue
            for rep_val,rep_label in rbc.expand_secret_representations(val,'env-'+env_name):
                if rep_val:
                    out.append((rep_val.encode(),f'<redacted-{rep_label}>'.encode()))
    except Exception:
        pass
    # Longest first avoids partial replacement when one value is a prefix/substring.
    return sorted(set(out),key=lambda x:len(x[0]),reverse=True)

REDACTIONS=load_redactions()

def redact_bytes_detailed(data):
    count=0
    labels={}
    for secret,label in REDACTIONS:
        if secret:
            n=data.count(secret)
            if n:
                count+=n
                data=data.replace(secret,label)
                key=label.decode('utf-8',errors='replace')
                labels[key]=labels.get(key,0)+n
    return data,count,labels


def redact_bytes(data):
    data,count,_labels=redact_bytes_detailed(data)
    return data,count

class ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads=True
    allow_reuse_address=True

def log(obj):
    obj=dict(obj); obj['ts']=time.time()
    LOG_PATH.parent.mkdir(parents=True,exist_ok=True)
    with open(LOG_PATH,'a') as f: f.write(json.dumps(obj)+'\n')

class Handler(BaseHTTPRequestHandler):
    server_version='absmax-kern-proxy/1.0'
    def log_message(self,fmt,*args):
        return

    def _json(self,status,obj):
        body=json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if self.path.split('?',1)[0]=='/v1/models':
            self._json(200,{'object':'list','data':[{'id':m,'object':'model','created':0,'owned_by':'kern'} for m in sorted(AUTHORIZED_MODELS)]})
        else:
            self._json(404,{'error':'endpoint not permitted'})

    def do_POST(self):
        path=self.path.split('?',1)[0]
        if path!='/v1/chat/completions':
            self._json(404,{'error':'endpoint not permitted'}); return
        try: n=int(self.headers.get('Content-Length','0'))
        except Exception: n=0
        if n<=0 or n>MAX_BODY:
            self._json(413,{'error':'invalid or oversized request body'}); return
        body=self.rfile.read(n)
        body,request_redactions,request_redaction_labels=redact_bytes_detailed(body)
        try:
            obj=json.loads(body)
        except Exception:
            self._json(400,{'error':'request body must be JSON'}); return
        model=obj.get('model')
        if model not in AUTHORIZED_MODELS:
            self._json(403,{'error':'model not permitted in benchmark proxy','allowed_models':sorted(AUTHORIZED_MODELS)}); return
        if model==LOCAL_MODEL:
            obj['model']=MODEL
            body=json.dumps(obj,separators=(',',':')).encode()
        if not KEY:
            self._json(500,{'error':'proxy upstream credential unavailable'}); return
        req=urllib.request.Request(UPSTREAM+'/chat/completions',data=body,method='POST')
        req.add_header('Authorization','Bearer '+KEY)
        req.add_header('Content-Type',self.headers.get('Content-Type','application/json'))
        req.add_header('Accept',self.headers.get('Accept','application/json'))
        req.add_header('User-Agent','absmax-benchmark-credential-proxy')
        t0=time.time(); sent=0; status=None; response_redactions=0; response_redaction_labels={}
        try:
            resp=urllib.request.urlopen(req,timeout=345)
            status=resp.status
            self.send_response(status)
            # Forward semantic response headers but not connection/framing headers.
            for k,v in resp.headers.items():
                if k.lower() in {'connection','transfer-encoding','content-length','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','upgrade'}:
                    continue
                self.send_header(k,v)
            self.send_header('Connection','close')
            self.end_headers()
            # Buffer before forwarding so exact runtime-secret redaction cannot be
            # defeated by chunk boundaries. Responses in this benchmark are small
            # enough for memory buffering; metadata logging still excludes content.
            raw_response=resp.read()
            redacted_response,response_redactions,response_redaction_labels=redact_bytes_detailed(raw_response)
            self.wfile.write(redacted_response); self.wfile.flush(); sent=len(redacted_response)
        except urllib.error.HTTPError as e:
            status=e.code
            try: errbody=e.read()
            except Exception: errbody=b'{"error":"upstream error"}'
            self.send_response(status)
            self.send_header('Content-Type',e.headers.get('Content-Type','application/json'))
            self.send_header('Content-Length',str(len(errbody)))
            self.send_header('Connection','close')
            self.end_headers(); self.wfile.write(errbody); sent=len(errbody)
        except Exception as e:
            status='proxy-error'
            try: self._json(502,{'error':'upstream proxy failure','detail':type(e).__name__})
            except Exception: pass
        log({'endpoint':path,'model':model,'status':status,'response_bytes':sent,'elapsed':round(time.time()-t0,3),'request_redactions':request_redactions,'response_redactions':response_redactions,'request_redaction_labels':request_redaction_labels,'response_redaction_labels':response_redaction_labels})

def main():
    if not KEY:
        print('KERN_API_KEY missing',file=sys.stderr); return 2
    SOCKET_PATH.parent.mkdir(parents=True,exist_ok=True)
    try: SOCKET_PATH.unlink()
    except FileNotFoundError: pass
    srv=ThreadingUnixServer(str(SOCKET_PATH),Handler)
    os.chmod(SOCKET_PATH,0o600)
    READY_PATH.write_text(json.dumps({'ready':True,'pid':os.getpid(),'socket':str(SOCKET_PATH),'model':MODEL,'local_model':LOCAL_MODEL,'redaction_count':len(REDACTIONS)}))
    print(json.dumps({'listening':str(SOCKET_PATH),'model':MODEL,'local_model':LOCAL_MODEL}),flush=True)
    try: srv.serve_forever()
    finally:
        srv.server_close()
        try: SOCKET_PATH.unlink()
        except FileNotFoundError: pass
        try: READY_PATH.unlink()
        except FileNotFoundError: pass

if __name__=='__main__': sys.exit(main())
