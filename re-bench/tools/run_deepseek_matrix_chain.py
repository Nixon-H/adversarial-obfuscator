#!/usr/bin/env python3
"""Run the cache-aware OpenCode Go DeepSeek local then cloud profile matrices."""
import json,os,subprocess,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUNNER=ROOT/'re-bench/tools/run_profile_matrix.py'
ARCHIVER=ROOT/'re-bench/tools/archive_invalid_matrix_results.py'
MODEL='opencode-go/deepseek-v4.1-flash'
SCENARIOS='legitimate-runtime-secrets,runtime-secrets-withheld,source-assisted-runtime-secrets,source-assisted-secrets-withheld'
STATUS=Path('/home/nixon/absmax-scratch/deepseek-matrix-chain-status.json')
LOCK=Path('/home/nixon/absmax-scratch/deepseek-matrix-chain.lock')


def run_one_matrix(matrix_id,variants,cloud=False,max_provider_retries=2):
    env=dict(os.environ)
    env['ABSMAX_PROFILE_MATRIX_ID']=matrix_id
    if cloud:
        env['ABSMAX_ARTIFACT_SUBDIR']='cloud-final4'
        env['ABSMAX_SECRETS_ROOT']='/home/nixon/absmax-scratch/cloud-final4-secrets'
    results_dir=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'/('ai_benchmark_profile_matrix_'+matrix_id)/'results'
    passes=[]
    for pass_no in range(max_provider_retries+1):
        logbase=Path('/home/nixon/absmax-scratch/profile-matrix-'+matrix_id+'-pass'+str(pass_no+1))
        with open(str(logbase)+'.out','ab') as out, open(str(logbase)+'.err','ab') as err:
            cp=subprocess.run([sys.executable,str(RUNNER),'--variants',variants,'--scenarios',SCENARIOS,'--attempts','1','--model',MODEL],cwd=str(ROOT),env=env,stdout=out,stderr=err)
        archived=0
        if results_dir.exists():
            ap=subprocess.run([sys.executable,str(ARCHIVER),'--results-dir',str(results_dir),'--provider-only'],text=True,capture_output=True,timeout=30)
            try: archived=json.loads(ap.stdout).get('archived',0)
            except Exception: archived=0
        passes.append({'pass':pass_no+1,'runner_returncode':cp.returncode,'provider_invalid_archived':archived})
        if cp.returncode!=0 or archived==0:
            break
    status_path=Path('/home/nixon/absmax-scratch/profile-matrix-'+matrix_id+'-status.json')
    try: status=json.loads(status_path.read_text())
    except Exception: status={}
    return {'matrix_id':matrix_id,'variants':variants,'cloud':cloud,'passes':passes,'status_path':str(status_path),'complete':bool(status.get('complete')),'jobs_planned':status.get('jobs_planned'),'jobs_completed':status.get('completed')}


def main():
    import fcntl
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    fh=open(LOCK,'a+')
    try:fcntl.flock(fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({'started':False,'reason':'another deepseek matrix chain is active'}));return 0
    state={'started':time.time(),'model':MODEL,'phase':'local','complete':False,'matrices':[]}
    STATUS.write_text(json.dumps(state,indent=2))
    local=run_one_matrix('deepseek-local-v12','maximum-packed,maximum-local,absolute,absolute-native-only',cloud=False)
    state['matrices'].append(local);state['phase']='cloud';STATUS.write_text(json.dumps(state,indent=2))
    cloud=run_one_matrix('deepseek-cloud-v13','maximum-cloud,absolute-cloud',cloud=True)
    state['matrices'].append(cloud);state['phase']='done';state['complete']=True;state['finished']=time.time();STATUS.write_text(json.dumps(state,indent=2))
    print(json.dumps(state,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
