#!/usr/bin/env python3
"""Credential-holding OpenCode Go proxy on a loopback-only Unix socket.

The proxy exists so benchmark sandboxes can use the operator-authorised
DeepSeek V4.1 Flash model without inheriting or reading the real API credential.
It logs metadata only: no prompts, completions, headers, or credential material.
"""
import ast, base64, hashlib, json, os, socket, socketserver, sys, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler
from pathlib import Path

UPSTREAM='https://opencode.ai/zen/go/v1'
MODEL='deepseek-v4.1-flash'
AUTHORIZED_MODELS=frozenset((MODEL,))
MAX_BODY=32*1024*1024
SOCKET_PATH=Path(os.environ.get('OPENCODE_GO_PROXY_SOCKET','/home/nixon/absmax-tokenharbor-proxy/opencode-go.sock'))
LOG_PATH=Path('/home/nixon/absmax-tokenharbor-proxy/opencode-go-proxy.log')
KEY_PATH=Path('/home/nixon/absmax-tokenharbor-proxy/opencode-go.key')
READY_PATH=Path(os.environ.get('OPENCODE_GO_PROXY_READY','/home/nixon/absmax-tokenharbor-proxy/opencode-go-proxy.ready'))
KEY=os.environ.get('OPENCODE_API_KEY','')
if not KEY and KEY_PATH.exists():
    try: KEY=KEY_PATH.read_text().strip()
    except Exception: KEY=''


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
            derived_pairs=[('licence-customer-mask',cm),('licence-effective-native-key',eff)]
            try:
                seal=(sec/'nx_seal_shard.hex').read_text().strip().encode()
            except Exception:
                seal=b''
            table=(os.environ.get('NX_TABLE_SHARD','') or '').encode()
            if seal or table:
                material=(b'nx-operator-blob:'+str(len(seal)).encode('ascii')+b':'+seal+b'|'+str(len(table)).encode('ascii')+b':'+table)
                om=hashlib.sha256(material).digest()
                effop=bytes(b^om[i%len(om)] for i,b in enumerate(eff))
                derived_pairs.extend([('licence-operator-mask',om),('licence-effective-native-key-operator',effop)])
            for label,val in derived_pairs:
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

def redact_bytes(data):
    count=0
    for secret,label in REDACTIONS:
        if secret:
            n=data.count(secret)
            if n:
                count+=n; data=data.replace(secret,label)
    return data,count

class ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads=True
    allow_reuse_address=True

def _numeric_usage(value):
    """Return only numeric usage metadata; never prompt or completion content."""
    if isinstance(value,bool):
        return None
    if isinstance(value,(int,float)):
        return value
    if isinstance(value,dict):
        return {str(k):v for k,v in ((kk,_numeric_usage(vv)) for kk,vv in value.items()) if v is not None}
    return None


def usage_metrics(raw_response):
    """Extract token/cache metadata from JSON or SSE responses.

    DeepSeek-compatible upstreams may expose cache accounting as
    prompt_cache_hit_tokens/prompt_cache_miss_tokens or nested
    prompt_tokens_details.cached_tokens. Keep the schema flexible but numeric-only.
    """
    usage=None
    try:
        obj=json.loads(raw_response.decode('utf-8',errors='replace'))
        usage=obj.get('usage') if isinstance(obj,dict) else None
    except Exception:
        usage=None
    if usage is None:
        # OpenCode commonly uses SSE. Usage often appears only in the terminal
        # chunk; scan data lines and keep the last usage object.
        try:
            for line in raw_response.decode('utf-8',errors='replace').splitlines():
                if not line.startswith('data:') or line.startswith('data: [DONE]'):
                    continue
                try:
                    obj=json.loads(line[5:].strip())
                except Exception:
                    continue
                if isinstance(obj,dict) and isinstance(obj.get('usage'),dict):
                    usage=obj.get('usage')
        except Exception:
            pass
    clean=_numeric_usage(usage or {}) or {}
    details=usage.get('prompt_tokens_details') if isinstance(usage,dict) else {}
    if not isinstance(details,dict): details={}
    oc_tokens=(usage.get('opencode') or {}).get('tokens') if isinstance(usage,dict) else {}
    if not isinstance(oc_tokens,dict): oc_tokens={}
    hit=(usage.get('prompt_cache_hit_tokens') if isinstance(usage,dict) else None)
    if hit is None: hit=usage.get('cache_hit_tokens') if isinstance(usage,dict) else None
    if hit is None: hit=details.get('cached_tokens')
    if not hit: hit=oc_tokens.get('cache_read')
    miss=(usage.get('prompt_cache_miss_tokens') if isinstance(usage,dict) else None)
    if miss is None: miss=usage.get('cache_miss_tokens') if isinstance(usage,dict) else None
    prompt=(usage.get('prompt_tokens') if isinstance(usage,dict) else None)
    try: hit=int(hit or 0)
    except Exception: hit=0
    try: miss=int(miss or 0)
    except Exception: miss=0
    try: prompt=int(prompt or 0)
    except Exception: prompt=0
    cache={'prompt_cache_hit_tokens':hit,'prompt_cache_miss_tokens':miss,'cache_write_5m_tokens':int(oc_tokens.get('cache_write_5m') or 0),'cache_write_1h_tokens':int(oc_tokens.get('cache_write_1h') or 0),'cache_hit_present':bool(hit),'cache_accounting_present':bool(hit or miss or details.get('cached_tokens') is not None or oc_tokens)}
    if prompt:
        cache['cache_hit_rate']=round(hit/float(prompt),6)
    return clean,cache


_SENSITIVE_FIELDS=('authorization','api_key','apikey','secret','password','credential','x-api-key','cookie')
def _redact(k,v):
    lk=str(k).lower()
    if any(s in lk for s in _SENSITIVE_FIELDS):
        return True
    # token-named fields are redacted only when the value is credential-
    # shaped; numeric usage counters (prompt_tokens etc.) must survive
    # because the cache summarizer does arithmetic on them.
    return 'token' in lk and isinstance(v,str) and len(v)>=16
def _scrub(o):
    if isinstance(o,dict):
        return {k:('[redacted]' if _redact(k,v) else _scrub(v)) for k,v in o.items()}
    if isinstance(o,list):
        return [_scrub(v) for v in o]
    return o
def log(obj):
    obj=_scrub(dict(obj)); obj['ts']=time.time()
    LOG_PATH.parent.mkdir(parents=True,exist_ok=True)
    with open(LOG_PATH,'a') as f: f.write(json.dumps(obj)+'\n')

class Handler(BaseHTTPRequestHandler):
    server_version='absmax-opencode-go-proxy/1.0'
    protocol_version='HTTP/1.1'
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
            self._json(200,{'object':'list','data':[{'id':m,'object':'model','created':0,'owned_by':'opencode-go'} for m in sorted(AUTHORIZED_MODELS)]})
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
        body,request_redactions=redact_bytes(body)
        try:
            obj=json.loads(body)
        except Exception:
            self._json(400,{'error':'request body must be JSON'}); return
        model=obj.get('model')
        if model not in AUTHORIZED_MODELS:
            self._json(403,{'error':'model not permitted in benchmark proxy','allowed_models':sorted(AUTHORIZED_MODELS)}); return
        # Pin optional cache/routing metadata to stable values. These fields do
        # not change the analysis prompt; they prevent avoidable cache-domain
        # churn when the client omits them or varies incidental retry metadata.
        # DeepSeek/OpenCode cache use remains best-effort and is measured from
        # provider usage accounting rather than assumed.
        obj.setdefault('prompt_cache_key','absmax-benchmark-deepseek-v1')
        if isinstance(obj.get('stream_options'),dict):
            obj['stream_options'].setdefault('include_usage',True)
        elif obj.get('stream'):
            obj['stream_options']={'include_usage':True}
        body=json.dumps(obj,separators=(',',':')).encode()
        if not KEY:
            self._json(500,{'error':'proxy upstream credential unavailable'}); return
        req=urllib.request.Request(UPSTREAM+'/chat/completions',data=body,method='POST')
        req.add_header('Authorization','Bearer '+KEY)
        # OpenCode Go uses these headers for client identification and cache-aware
        # routing. Preserve a client-supplied conversation session; otherwise use
        # a stable benchmark-session label. This is metadata, not a credential.
        session=(self.headers.get('x-opencode-session') or os.environ.get('OPENCODE_GO_SESSION') or 'absmax-benchmark-deepseek-v1')
        req.add_header('x-opencode-session',session)
        req.add_header('x-opencode-client','absmax-benchmark/1.0')
        req.add_header('Content-Type',self.headers.get('Content-Type','application/json'))
        req.add_header('Accept',self.headers.get('Accept','application/json'))
        req.add_header('User-Agent','absmax-benchmark/1.0')
        t0=time.time(); sent=0; status=None; response_redactions=0; usage={}; cache_metrics={}
        try:
            resp=urllib.request.urlopen(req,timeout=345)
            status=resp.status
            # Stream the upstream response while retaining enough trailing bytes
            # to catch exact secrets that span chunk boundaries. Chunked transfer
            # gives the client a well-formed end-of-stream marker while preserving
            # first-byte progress during long model generations; buffering the
            # whole response caused OpenCode fetch timeouts/ECONNRESET retries.
            self.send_response(status)
            for k,v in resp.headers.items():
                if k.lower() in {'connection','transfer-encoding','content-length','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','upgrade'}:
                    continue
                self.send_header(k,v)
            self.send_header('Transfer-Encoding','chunked')
            self.end_headers()
            max_secret=max((len(x) for x,_ in REDACTIONS),default=1)
            carry=max(1,max_secret-1)
            pending=b''; raw_response=b''; sent=0
            def emit(data,final=False):
                nonlocal pending,raw_response,sent,response_redactions
                raw_response+=data
                pending+=data
                if final:
                    out=pending;pending=b''
                elif len(pending)>carry:
                    cut=len(pending)-carry
                    out=pending[:cut];pending=pending[cut:]
                else:
                    return
                redacted,n=redact_bytes(out)
                response_redactions+=n
                if redacted:
                    frame=(hex(len(redacted))[2:]+'\r\n').encode()+redacted+b'\r\n'
                    self.wfile.write(frame);self.wfile.flush();sent+=len(redacted)
            while True:
                chunk=(resp.read1(16384) if hasattr(resp,"read1") else resp.read(16384))
                if not chunk:break
                emit(chunk)
            emit(b'',final=True)
            self.wfile.write(b'0\r\n\r\n');self.wfile.flush()
            usage,cache_metrics=usage_metrics(raw_response)
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
        log({'endpoint':path,'model':model,'session':session,'status':status,'response_bytes':sent,'elapsed':round(time.time()-t0,3),'request_redactions':request_redactions,'response_redactions':response_redactions,'usage':usage,'cache':cache_metrics})

def main():
    if not KEY:
        print('OPENCODE_API_KEY missing',file=sys.stderr); return 2
    SOCKET_PATH.parent.mkdir(parents=True,exist_ok=True)
    try: SOCKET_PATH.unlink()
    except FileNotFoundError: pass
    srv=ThreadingUnixServer(str(SOCKET_PATH),Handler)
    os.chmod(SOCKET_PATH,0o600)
    READY_PATH.write_text(json.dumps({'ready':True,'pid':os.getpid(),'socket':str(SOCKET_PATH),'model':MODEL,'redaction_count':len(REDACTIONS)}))
    print(json.dumps({'listening':str(SOCKET_PATH),'model':MODEL,'redaction_count':len(REDACTIONS)}),flush=True)
    try: srv.serve_forever()
    finally:
        srv.server_close()
        try: SOCKET_PATH.unlink()
        except FileNotFoundError: pass
        try: READY_PATH.unlink()
        except FileNotFoundError: pass

if __name__=='__main__': sys.exit(main())
