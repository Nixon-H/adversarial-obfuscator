#!/usr/bin/env python3
"""Finite first-pass protection-profile benchmark matrix.

This runner is deliberately capped at two concurrent attempts to protect provider quota and cache locality. It writes a
separate suffixed evidence root so harness-version smoke/invalid records are not
overwritten or mixed into the profile comparison.
"""
import argparse, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROFILE_MATRIX_ID=os.environ.get('ABSMAX_PROFILE_MATRIX_ID','v10')
os.environ.setdefault('ABSMAX_BENCHMARK_SUFFIX','_profile_matrix_'+PROFILE_MATRIX_ID)
os.environ.setdefault('ABSMAX_LIVE_WORKSPACE_ROOT','/home/nixon/absmax-ai-workspaces-profile-matrix-'+PROFILE_MATRIX_ID)
os.environ.setdefault('ABSMAX_OPENCODE_STATE_ROOT','/home/nixon/absmax-opencode-state-profile-matrix-'+PROFILE_MATRIX_ID)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ai_bench

CORE_SCENARIOS=list(ai_bench.SCENARIOS)
LOCAL_VARIANTS=['maximum-packed','maximum-local','absolute','absolute-native-only']
CLOUD_VARIANTS=['maximum-cloud','absolute-cloud']
ALL_VARIANTS=LOCAL_VARIANTS+CLOUD_VARIANTS
STATUS=Path('/home/nixon/absmax-scratch/profile-matrix-'+PROFILE_MATRIX_ID+'-status.json')


def result_path(variant,scenario,model,attempt):
    safe=model.replace('/','_').replace(':','_')
    return ai_bench.OUT/'results'/f'{variant}__{scenario}__{safe}__a{attempt}.json'


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model',default='opencode-go/deepseek-v4.1-flash')
    ap.add_argument('--matrix-id',default=PROFILE_MATRIX_ID,help='visible matrix identifier; must match ABSMAX_PROFILE_MATRIX_ID when both are supplied')
    ap.add_argument('--variants',default=','.join(ALL_VARIANTS))
    ap.add_argument('--scenarios',default=','.join(CORE_SCENARIOS))
    ap.add_argument('--attempts',type=int,default=1)
    ap.add_argument('--parallel',type=int,default=2,help='concurrent attempts; clamped to 2 to protect provider quota and cache locality')
    args=ap.parse_args()
    args.parallel=max(1,min(2,args.parallel))
    if args.matrix_id!=PROFILE_MATRIX_ID:
        raise SystemExit('matrix id mismatch: pass ABSMAX_PROFILE_MATRIX_ID or matching --matrix-id')
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
    def execute_job(job):
        variant,scenario,model,attempt=job
        rp=result_path(variant,scenario,model,attempt)
        if rp.exists():
            try:
                r=json.loads(rp.read_text())
                return {'job':job,'skipped_existing':True,'returncode':r.get('returncode'),'answer_json_exists':(r.get('validation') or {}).get('answer_json_exists')}
            except Exception:
                return {'job':job,'skipped_existing':True}
        try:
            r=ai_bench.one(job)
            return {'job':job,'returncode':r.get('returncode'),'timeout':r.get('timeout'),'tool_event_count':r.get('tool_event_count'),'answer_json_exists':(r.get('validation') or {}).get('answer_json_exists'),'answer_json_valid':(r.get('validation') or {}).get('answer_json_valid'),'secret_recovered':(r.get('validation') or {}).get('secret_recovered'),'solution_py_exists':(r.get('validation') or {}).get('solution_py_exists')}
        except Exception as e:
            return {'job':job,'executor_error':type(e).__name__,'error':str(e)[:200]}

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures={pool.submit(execute_job,job):job for job in jobs}
        for fut in as_completed(futures):
            try:
                rec=fut.result()
            except Exception as e:
                rec={'job':futures[fut],'executor_error':type(e).__name__,'error':str(e)[:200]}
            state['results'].append(rec)
            state['completed']=len(state['results'])
            state['updated']=time.time()
            state['parallel']=args.parallel
            STATUS.write_text(json.dumps(state,indent=2))
    state['complete']=True
    state['finished']=time.time()
    STATUS.write_text(json.dumps(state,indent=2))
    try:
        subprocess.run([sys.executable,str(Path(__file__).with_name('analyze_benchmark_precision.py'))],cwd=str(ROOT),env=dict(os.environ),timeout=120,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception:
        pass
    print(json.dumps({'complete':True,'jobs':len(jobs),'missing_variants':missing,'status':str(STATUS)},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
