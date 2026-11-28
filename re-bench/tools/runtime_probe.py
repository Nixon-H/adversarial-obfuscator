#!/usr/bin/env python3
"""Controlled runtime probes for built ABSOLUTE artefacts; no secret values logged."""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def redact_sensitive_text(text, values):
    for value in values:
        if value:
            text=text.replace(value,'<redacted-runtime-secret>')
    return text


def runtime_secret_values(sec):
    values=[]
    try:
        shard=(sec/'nx_seal_shard.hex').read_text().strip()
        if shard:values.append(shard)
    except Exception:pass
    try:
        raw=(sec/'runtime.licence').read_text().strip()
        if raw:values.append(raw)
        doc=json.loads(raw);payload=doc.get('payload') or {}
        for key in ('key_material','nonce','hwid'):
            val=payload.get(key)
            if isinstance(val,str) and val:values.append(val)
        sig=doc.get('sig')
        if isinstance(sig,str) and sig:values.append(sig)
    except Exception:pass
    return sorted(set(values),key=len,reverse=True)


def run_case(artifact, cwd, env, timeout=20):
    e=dict(os.environ); e.update(env)
    # Never log secret env values. Ensure traceback diagnostics remain as built.
    t0=time.perf_counter()
    try:
        p=subprocess.run([sys.executable,str(artifact)],cwd=str(cwd),env=e,text=True,capture_output=True,timeout=timeout)
        return {'returncode':p.returncode,'stdout':p.stdout[-2000:],'stderr':p.stderr[-2000:],'elapsed_seconds':round(time.perf_counter()-t0,4),'timeout':False}
    except subprocess.TimeoutExpired as x:
        return {'returncode':None,'stdout':(x.stdout or '')[-2000:] if isinstance(x.stdout,str) else '', 'stderr':(x.stderr or '')[-2000:] if isinstance(x.stderr,str) else '', 'elapsed_seconds':round(time.perf_counter()-t0,4),'timeout':True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--variant',required=True)
    ap.add_argument('--target',default='cipher')
    ap.add_argument('--artifact',required=True)
    ap.add_argument('--secrets-root',help='override benchmark secrets root for continuation/non-authoritative builds')
    ap.add_argument('--output-root',help='override runtime evidence root for continuation/non-authoritative builds')
    args=ap.parse_args()
    sec=(Path(args.secrets_root).resolve() if args.secrets_root else ROOT/'re-bench/secrets')/args.variant/args.target
    shard=(sec/'nx_seal_shard.hex').read_text().strip()
    licence=str(sec/'runtime.licence')
    outdir=(Path(args.output_root).resolve() if args.output_root else ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/runtime')/args.variant/args.target
    outdir.mkdir(parents=True,exist_ok=True)
    artifact=Path(args.artifact).resolve()
    prov_pub=(sec/'provenance.public.hex').read_text().strip() if (sec/'provenance.public.hex').exists() else ''
    base={'NIXON_LOG_REDIRECT':'0','NX_SEAL_SHARD':shard,'NIXON_LICENCE':licence,'NIXON_TRACEBACKS':'1'}
    if prov_pub:
        base['NIXON_PROVENANCE_PUBKEY']=prov_pub
    cases={}
    cases['valid_runtime_secrets']=run_case(artifact,artifact.parent,base)
    x=dict(base); x.pop('NIXON_LICENCE',None)
    cases['missing_licence']=run_case(artifact,artifact.parent,x)
    x=dict(base); x.pop('NX_SEAL_SHARD',None)
    cases['missing_seal_shard']=run_case(artifact,artifact.parent,x)
    x=dict(base); x['NX_SEAL_SHARD']='00'*32
    cases['wrong_seal_shard']=run_case(artifact,artifact.parent,x)
    x=dict(base); x.pop('NIXON_LICENCE',None); x.pop('NX_SEAL_SHARD',None)
    cases['missing_all_runtime_secrets']=run_case(artifact,artifact.parent,x)
    # Tampered artifact: alter one ASCII byte in a comment-safe area near the head (not a semantic patch tool;
    # it tests whether integrity/provenance detects any file mutation).
    tampered=outdir/'artifact_tampered.py'
    data=bytearray(artifact.read_bytes())
    pos=min(2048,len(data)-1)
    data[pos]=ord('X') if data[pos]!=ord('X') else ord('Y')
    tampered.write_bytes(bytes(data))
    cases['tampered_one_byte']=run_case(tampered,tampered.parent,base)
    # Forge token by flipping a payload character without updating signature/pin.
    forged=outdir/'forged.licence'
    tok=json.loads((sec/'runtime.licence').read_text())
    tok['payload']['customer']='attacker-forged'
    forged.write_text(json.dumps(tok,separators=(',',':')))
    x=dict(base); x['NIXON_LICENCE']=str(forged)
    cases['forged_licence_payload']=run_case(artifact,artifact.parent,x)
    # Wrong file as token.
    wrong=outdir/'wrong.licence'; wrong.write_text('{"payload":{"key_material":"00"},"sig":"00"}')
    x=dict(base); x['NIXON_LICENCE']=str(wrong)
    cases['wrong_licence_token']=run_case(artifact,artifact.parent,x)
    sensitive=runtime_secret_values(sec)
    for row in cases.values():
        row['stdout']=redact_sensitive_text(row.get('stdout') or '',sensitive)
        row['stderr']=redact_sensitive_text(row.get('stderr') or '',sensitive)
    summary={'artifact':str(artifact),'cases':cases,'secret_values_logged':False}
    (outdir/'runtime_cases.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:{'rc':v['returncode'],'timeout':v['timeout'],'stdout_tail':v['stdout'][-120:],'stderr_tail':v['stderr'][-160:]} for k,v in cases.items()},indent=2))
if __name__=='__main__': main()
