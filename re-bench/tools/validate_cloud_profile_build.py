#!/usr/bin/env python3
"""Validate cloud-profile build artifacts without printing secrets."""
import argparse,ast,base64,hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path

EXPECTED_STDOUT_SHA256='d9d34b5c820045756b0bd7eb21a72540e6575744efd01a3dd307a72df1f0c623'

def sha256_bytes(b):return hashlib.sha256(b).hexdigest()
def sha256_file(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def artifact_native_lengths(path):
    text=path.read_text(errors='replace')
    out={'natives_present':False,'lengths':{},'decoded_sizes':{},'decoded_sha256':{},'magic':{}}
    try:
        tree=ast.parse(text);lit={}
        for node in tree.body:
            if isinstance(node,ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt,ast.Name):
                        try:lit[tgt.id]=ast.literal_eval(node.value)
                        except Exception:pass
        nb=lit.get('NATIVE_BLOBS')
        if isinstance(nb,dict):
            out['natives_present']=True
            for osname in ['windows','linux','darwin','android']:
                val=nb.get(osname) or ''
                out['lengths'][osname]=len(val)
                if val:
                    raw=base64.b64decode(val)
                    out['decoded_sizes'][osname]=len(raw)
                    out['decoded_sha256'][osname]=sha256_bytes(raw)
                    if raw[:4]==b'NXS1':magic='nxs1-container'
                    elif raw[:4]==b'\x7fELF':magic='elf'
                    elif raw[:2]==b'MZ':magic='pe'
                    elif raw[:4] in (bytes((0xcf,0xfa,0xed,0xfe)),bytes((0xce,0xfa,0xed,0xfe)),bytes((0xca,0xfe,0xba,0xbe))):magic='macho'
                    else:magic='unknown'
                    out['magic'][osname]=magic
    except Exception as e:out['parse_error']=type(e).__name__
    return out

def runtime_control(artifact,secrets_dir):
    res={}
    env=os.environ.copy()
    env.update({
        'NIXON_LOG_REDIRECT':'0',
        'NX_SEAL_SHARD':(secrets_dir/'nx_seal_shard.hex').read_text().strip(),
        'NIXON_PROVENANCE_PUBKEY':(secrets_dir/'provenance.public.hex').read_text().strip(),
        'NIXON_LICENCE':str((secrets_dir/'runtime.licence').resolve()),
    })
    without=dict(os.environ)
    for key in ('NX_SEAL_SHARD','NX_TABLE_SHARD','NIXON_LICENCE','NIXON_PROVENANCE_PUBKEY'):
        without.pop(key,None)
    for label,useenv in [('with_secrets',env),('without_secrets',without)]:
        try:
            p=subprocess.run([sys.executable,str(artifact.resolve())],env=useenv,text=True,capture_output=True,timeout=30,cwd=tempfile.mkdtemp(prefix='cloud-profile-control-'))
            res[label]={'returncode':p.returncode,'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest(),'stdout_len':len(p.stdout),'stderr_len':len(p.stderr),'timeout':False}
        except subprocess.TimeoutExpired:res[label]={'timeout':True}
    res['positive_ok']=res.get('with_secrets',{}).get('returncode')==0 and res.get('with_secrets',{}).get('stdout_sha256')==EXPECTED_STDOUT_SHA256
    res['negative_fail_closed']=res.get('without_secrets',{}).get('returncode') not in (0,None) and res.get('without_secrets',{}).get('stdout_len')==0
    return res

def attestation_summary(blob_dir):
    out={}
    if not blob_dir.exists():return out
    for p in sorted(blob_dir.glob('runner-attestation-payload*.json')):
        try:
            d=json.loads(p.read_text())
            verdict=d.get('hardening_verdict') or {}
            out[p.name]={'payload_sha256':d.get('payload_sha256'),'artifacts':d.get('artifacts'),'hardening_ok':verdict.get('ok'),'missing':verdict.get('missing'),'wrong':verdict.get('wrong'),'inert':verdict.get('inert'),'partial':verdict.get('partial'),'unavailable':verdict.get('unavailable'),'smoke_test':d.get('smoke_test')}
        except Exception as e:out[p.name]={'parse_error':type(e).__name__}
    return out

def validate_variant(variant,raw_root,secrets_root,build_root):
    rdir=Path(raw_root)/'builds'/variant/'cipher'
    sdir=Path(secrets_root)/variant/'cipher'
    bdir=Path(build_root)/variant/'cipher'
    result_path=rdir/'build_result.json'
    artifact=rdir/'artifact.py'
    out={'variant':variant,'build_result_exists':result_path.exists(),'artifact_exists':artifact.exists()}
    if result_path.exists():
        br=json.loads(result_path.read_text());out['build']={k:br.get(k) for k in ['returncode','artifact_sha256','artifact_size','artifact_selected_form','elapsed_seconds']}
    if artifact.exists():
        out['artifact']={'sha256':sha256_file(artifact),'size':artifact.stat().st_size,'native':artifact_native_lengths(artifact)}
        out['artifact_matches_build_manifest']=bool((out.get('build') or {}).get('artifact_sha256') and out['artifact']['sha256']==(out.get('build') or {}).get('artifact_sha256'))
        if sdir.exists():out['runtime_control']=runtime_control(artifact,sdir)
    out['attestations']=attestation_summary(bdir/'.native_blobs')
    natives=(out.get('artifact') or {}).get('native') or {}
    magic=natives.get('magic') or {}
    out['cross_platform_blob_presence']={k:bool((natives.get('decoded_sizes') or {}).get(k)) for k in ['windows','linux','darwin']}
    out['cross_platform_magic_ok']=(magic.get('windows')=='nxs1-container' and magic.get('linux')=='nxs1-container' and magic.get('darwin')=='nxs1-container')
    att=out['attestations']
    out['attestation_count']=len(att)
    out['attestation_all_hardening_ok']=bool(att) and all((x.get('hardening_ok') is True) for x in att.values())
    out['valid_cloud_candidate']=bool(out['artifact_exists'] and out.get('artifact_matches_build_manifest') and (out.get('build') or {}).get('returncode')==0 and out['cross_platform_magic_ok'] and (out.get('runtime_control') or {}).get('positive_ok') and (out.get('runtime_control') or {}).get('negative_fail_closed') and out['attestation_all_hardening_ok'])
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--variants',default='maximum-cloud,absolute-cloud')
    ap.add_argument('--raw-root',required=True)
    ap.add_argument('--secrets-root',required=True)
    ap.add_argument('--build-root',required=True)
    ap.add_argument('--out')
    args=ap.parse_args()
    result={'generated':time.time(),'variants':{}}
    for v in args.variants.split(','):
        result['variants'][v]=validate_variant(v,args.raw_root,args.secrets_root,args.build_root)
    result['all_valid']=bool(result['variants']) and all(x['valid_cloud_candidate'] for x in result['variants'].values())
    text=json.dumps(result,indent=2)
    if args.out:Path(args.out).write_text(text)
    print(text)
    return 0 if result['all_valid'] else 2
if __name__=='__main__':raise SystemExit(main())
