#!/usr/bin/env python3
"""Validate strict artifact execution through per-model minimal endpoint directories.

Runtime licence material is copied only into a temporary isolated workspace and
deleted afterwards. The JSON report records hashes/status, never secret values.
"""
import hashlib, json, shutil, subprocess, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
TMPROOT=Path('/home/nixon/absmax-tmp')
ENDPOINT_ROOT=Path('/home/nixon/absmax-sandbox-endpoints')
EXPECTED='SEALED 8771940273853809a401795ec7699cdc'


def smoke(variant,family):
    TMPROOT.mkdir(parents=True,exist_ok=True)
    ws=Path(tempfile.mkdtemp(prefix=f'endpoint-{family}-smoke-',dir=TMPROOT))
    try:
        state=ws/'state';state.mkdir()
        work=ws/'work';work.mkdir()
        shutil.copy2(RAW/'builds'/variant/'cipher/artifact.py',work/'artifact.py')
        sec=ROOT/'re-bench/secrets'/variant/'cipher'
        for fn in ['runtime.licence','nx_seal_shard.hex','provenance.public.hex']:
            shutil.copy2(sec/fn,work/fn)
        runner=work/'run_valid.sh'
        runner.write_text('#!/bin/sh\nset -eu\nexport NIXON_LOG_REDIRECT=0\nexport NIXON_TRACEBACKS=1\nexport NX_SEAL_SHARD=$(cat nx_seal_shard.hex)\nexport NIXON_PROVENANCE_PUBKEY=$(cat provenance.public.hex)\nexport NIXON_LICENCE=$PWD/runtime.licence\nexec python3 artifact.py\n')
        runner.chmod(0o700)
        bridge=state/'sandbox_tokenharbor_bridge.py'
        shutil.copy2(ROOT/'re-bench/tools/sandbox_tokenharbor_bridge.py',bridge)
        hosts=state/'hosts';hosts.write_text('127.0.0.1 localhost\n::1 localhost ip6-localhost ip6-loopback\n')
        endpoint=ENDPOINT_ROOT/family
        cmd=['bwrap','--die-with-parent','--new-session','--unshare-net','--unshare-pid',
             '--ro-bind','/usr','/usr','--ro-bind','/bin','/bin','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64',
             '--ro-bind','/etc/resolv.conf','/etc/resolv.conf','--ro-bind','/etc/ssl','/etc/ssl',
             '--ro-bind','/etc/passwd','/etc/passwd','--ro-bind','/etc/group','/etc/group','--ro-bind','/etc/nsswitch.conf','/etc/nsswitch.conf','--ro-bind',str(hosts),'/etc/hosts',
             '--ro-bind',str(bridge),'/opt/sandbox_tokenharbor_bridge.py','--ro-bind',str(endpoint),'/run/absmax-tokenharbor',
             '--dir','/home/nixon','--bind',str(work),str(work),'--chdir',str(work),'--proc','/proc','--dev','/dev','--dir','/tmp','--setenv','HOME','/home/nixon',
             '/usr/bin/python3','/opt/sandbox_tokenharbor_bridge.py','/bin/sh','./run_valid.sh']
        env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/home/nixon','USER':'nixon','LOGNAME':'nixon','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','TMPDIR':'/tmp','PYTHONUNBUFFERED':'1'}
        p=subprocess.run(cmd,cwd=work,text=True,capture_output=True,timeout=45,env=env)
        return {'variant':variant,'endpoint_family':family,'endpoint_directory':str(endpoint),'returncode':p.returncode,'expected_output_present':EXPECTED in p.stdout,'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest(),'stderr_tail':p.stderr[-300:],'secrets_preserved':False}
    finally:
        shutil.rmtree(ws,ignore_errors=True)


def main():
    rows=[]
    for family in ['opencode','opencode-go','tokenharbor','kern']:
        for variant in ['absolute-native-only','absolute']:
            rows.append(smoke(variant,family))
    out={'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'endpoint_root':str(ENDPOINT_ROOT),'reports':rows,'all_valid':all(r['returncode']==0 and r['expected_output_present'] for r in rows),'secret_values_recorded':False}
    dest=RAW/'evm/per_model_endpoint_runtime_smoke.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2))
    print(json.dumps({'all_valid':out['all_valid'],'reports':len(rows),'output':str(dest)}))
    return 0 if out['all_valid'] else 1

if __name__=='__main__':
    raise SystemExit(main())
