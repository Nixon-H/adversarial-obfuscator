#!/usr/bin/env python3
"""Finite first-pass protection-profile benchmark matrix.

This runner is deliberately sequential because the Kern endpoint enforces a low
per-IP request rate. It writes a separate suffixed evidence root so harness-version
smoke/invalid records are not overwritten or mixed into the profile comparison.
"""
import argparse, json, os, sys, time
from pathlib import Path

PROFILE_MATRIX_ID=os.environ.get('ABSMAX_PROFILE_MATRIX_ID','v10')
os.environ.setdefault('ABSMAX_BENCHMARK_SUFFIX','_profile_matrix_'+PROFILE_MATRIX_ID)
os.environ.setdefault('ABSMAX_LIVE_WORKSPACE_ROOT','/home/nixon/absmax-ai-workspaces-profile-matrix-'+PROFILE_MATRIX_ID)
os.environ.setdefault('ABSMAX_OPENCODE_STATE_ROOT','/home/nixon/absmax-opencode-state-profile-matrix-'+PROFILE_MATRIX_ID)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ai_bench

CORE_SCENARIOS=[
 'legitimate-runtime-secrets',
 'runtime-secrets-withheld',
 'source-assisted-runtime-secrets',
 'source-assisted-secrets-withheld',
]
LOCAL_VARIANTS=['maximum-packed','maximum-local','absolute','absolute-native-only']
CLOUD_VARIANTS=['maximum-cloud','absolute-cloud']
ALL_VARIANTS=LOCAL_VARIANTS+CLOUD_VARIANTS
STATUS=Path('/home/nixon/absmax-scratch/profile-matrix-'+PROFILE_MATRIX_ID+'-status.json')


def result_path(variant,scenario,model,attempt):
    safe=model.replace('/','_').replace(':','_')
    return ai_bench.OUT/'results'/f'{variant}__{scenario}__{safe}__a{attempt}.json'


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model',default='kern/inkling-2-mini')
    ap.add_argument('--variants',default=','.join(ALL_VARIANTS))
    ap.add_argument('--scenarios',default=','.join(CORE_SCENARIOS))
    ap.add_argument('--attempts',type=int,default=1)
    args=ap.parse_args()
    variants=args.variants.split(',')
    scenarios=args.scenarios.split(',')
    jobs=[]
    missing=[]
    for variant in variants:
        try:
            artifact=ai_bench.artifact_for(variant)
            if not artifact.exists():
                missing.append({'variant':variant,'reason':'artifact-missing','path':str(artifact)})
                continue
        except Exception as e:
            missing.append({'variant':variant,'reason':type(e).__name__,'path':str(ai_bench.artifact_for(variant))})
            continue
        for scenario in scenarios:
            for attempt in range(1,args.attempts+1):
                jobs.append((variant,scenario,args.model,attempt))
    STATUS.parent.mkdir(parents=True,exist_ok=True)
    state={'started':time.time(),'model':args.model,'jobs_planned':len(jobs),'completed':0,'missing_variants':missing,'complete':False,'results':[]}
    STATUS.write_text(json.dumps(state,indent=2))
    for job in jobs:
        variant,scenario,model,attempt=job
        rp=result_path(variant,scenario,model,attempt)
        if rp.exists():
            try:
                r=json.loads(rp.read_text())
                rec={'job':job,'skipped_existing':True,'returncode':r.get('returncode'),'answer_json_exists':(r.get('validation') or {}).get('answer_json_exists')}
            except Exception:
                rec={'job':job,'skipped_existing':True}
        else:
            try:
                r=ai_bench.one(job)
                rec={'job':job,'returncode':r.get('returncode'),'timeout':r.get('timeout'),'tool_event_count':r.get('tool_event_count'),'answer_json_exists':(r.get('validation') or {}).get('answer_json_exists'),'answer_json_valid':(r.get('validation') or {}).get('answer_json_valid'),'secret_recovered':(r.get('validation') or {}).get('secret_recovered'),'solution_py_exists':(r.get('validation') or {}).get('solution_py_exists')}
            except Exception as e:
                rec={'job':job,'executor_error':type(e).__name__,'error':str(e)[:200]}
        state['results'].append(rec)
        state['completed']=len(state['results'])
        state['updated']=time.time()
        STATUS.write_text(json.dumps(state,indent=2))
    state['complete']=True
    state['finished']=time.time()
    STATUS.write_text(json.dumps(state,indent=2))
    print(json.dumps({'complete':True,'jobs':len(jobs),'missing_variants':missing,'status':str(STATUS)},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
