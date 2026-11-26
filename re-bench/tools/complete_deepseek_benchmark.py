#!/usr/bin/env python3
"""Complete the OpenCode Go DeepSeek benchmark after the core chain.

Ordering is deliberate: wait for the existing core chain to finish, run the
remaining 15-scenario slice, archive/retry invalid core records, then redact,
scan, and aggregate. Only one matrix runner is launched at a time.
"""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
STATUS=Path('/home/nixon/absmax-scratch/deepseek-full-completion-status.json')
LOCK=Path('/home/nixon/absmax-scratch/deepseek-full-completion.lock')
CORE_SCENARIOS='legitimate-runtime-secrets,runtime-secrets-withheld,source-assisted-runtime-secrets,source-assisted-secrets-withheld'
MODEL='opencode-go/deepseek-v4.1-flash'


def write_state(**kw):
    state={}
    try:state=json.loads(STATUS.read_text())
    except Exception:pass
    state.update(kw);state['updated']=time.time();STATUS.write_text(json.dumps(state,indent=2))


def process_alive(pattern):
    try:
        out=subprocess.run(['pgrep','-f',pattern],text=True,capture_output=True,timeout=5).stdout.split()
    except Exception:
        return []
    live=[]
    for x in out:
        try:
            cmd=Path('/proc/'+x+'/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if pattern in cmd:live.append(int(x))
        except Exception:pass
    return live


def run(cmd,env=None,logname='completion'):
    write_state(last_command=' '.join(str(x) for x in cmd),last_log=logname)
    with open('/home/nixon/absmax-scratch/'+logname+'.out','ab') as out,open('/home/nixon/absmax-scratch/'+logname+'.err','ab') as err:
        cp=subprocess.run([str(x) for x in cmd],cwd=str(ROOT),env=env or dict(os.environ),stdout=out,stderr=err)
    return cp.returncode


def matrix_env(matrix_id,cloud=False):
    env=dict(os.environ);env['ABSMAX_PROFILE_MATRIX_ID']=matrix_id
    if cloud:
        env['ABSMAX_ARTIFACT_SUBDIR']='cloud-final4'
        env['ABSMAX_SECRETS_ROOT']='/home/nixon/absmax-scratch/cloud-final4-secrets'
    return env


def run_matrix(matrix_id,variants,scenarios,cloud=False,logname='matrix'):
    cmd=[sys.executable,ROOT/'re-bench/tools/run_profile_matrix.py','--model',MODEL,'--matrix-id',matrix_id,'--variants',variants,'--scenarios',scenarios,'--attempts','1','--parallel','2']
    return run(cmd,matrix_env(matrix_id,cloud),logname)


def archive_invalid(matrix_id):
    results=RAW/('ai_benchmark_profile_matrix_'+matrix_id)/'results'
    if not results.exists():return 0
    cp=subprocess.run([sys.executable,str(ROOT/'re-bench/tools/archive_invalid_matrix_results.py'),'--results-dir',str(results)],cwd=str(ROOT),text=True,capture_output=True,timeout=60)
    try:return int(json.loads(cp.stdout).get('archived',0))
    except Exception:return 0


def chain_finished():
    if process_alive('run_deepseek_matrix_chain.py'):return False
    try:return bool(json.loads(Path('/home/nixon/absmax-scratch/deepseek-matrix-chain-status.json').read_text()).get('complete'))
    except Exception:return True


def main():
    import fcntl
    fh=open(LOCK,'a+')
    try:fcntl.flock(fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return 0
    write_state(phase='waiting-for-core-chain',complete=False)
    deadline=time.time()+8*3600
    while process_alive('run_deepseek_matrix_chain.py') and time.time()<deadline:
        write_state(phase='waiting-for-core-chain',chain_pids=process_alive('run_deepseek_matrix_chain.py'))
        time.sleep(60)
    if process_alive('run_profile_matrix.py'):
        write_state(phase='blocked-unexpected-runner',error='another matrix runner remained active after core chain completion')
        return 2

    # Ensure the cloud core matrix with the corrected cloud-final4 secret root.
    # Earlier attempts prepared while that root contained redaction placeholders
    # are archived as harness-invalid and are rerun here.
    write_state(phase='core-cloud')
    run_matrix('deepseek-cloud-v13','maximum-cloud,absolute-cloud',CORE_SCENARIOS,True,'profile-matrix-deepseek-cloud-v13-completion')

    # Complete the non-core 15 scenario families into go-v12. Existing static/binary
    # go-v12 results are skipped by the runner.
    write_state(phase='remaining-15-scenarios')
    rc=run([sys.executable,ROOT/'re-bench/tools/run_deepseek_remaining_scenarios.py'],logname='deepseek-remaining-scenarios')

    # Bounded retry of invalid core records. Archive preserves original bytes;
    # rerunning the same matrix skips valid files and retries only archived gaps.
    retry_notes=[]
    for round_no in range(2):
        any_archived=False
        for matrix_id,variants,cloud in [
            ('deepseek-local-v12','maximum-packed,maximum-local,absolute,absolute-native-only',False),
            ('deepseek-cloud-v13','maximum-cloud,absolute-cloud',True),
        ]:
            archived=archive_invalid(matrix_id)
            retry_notes.append({'round':round_no+1,'matrix_id':matrix_id,'archived':archived})
            if archived:
                any_archived=True
                write_state(phase='core-invalid-retry-round-'+str(round_no+1),retry_notes=retry_notes)
                run_matrix(matrix_id,variants,CORE_SCENARIOS,cloud,'profile-matrix-'+matrix_id+'-completion-retry-r'+str(round_no+1))
        if not any_archived:break

    # Aggregate before redaction so scores are independent of redaction labels.
    write_state(phase='aggregate',retry_notes=retry_notes)
    run([sys.executable,ROOT/'re-bench/tools/summarize_deepseek_benchmark.py'],logname='deepseek-aggregate')
    run([sys.executable,ROOT/'re-bench/tools/summarize_opencode_go_cache.py','--since','1795705047','--out',str(RAW/'opencode_go_cache_summary.json')],logname='deepseek-cache-summary')

    # Redact only after all benchmark jobs have stopped; otherwise legitimate
    # live workspaces intentionally contain runtime secrets.
    write_state(phase='redaction-scan')
    run([sys.executable,ROOT/'re-bench/tools/redact_benchmark_credentials.py'],logname='deepseek-final-redact')
    scan=run([sys.executable,ROOT/'re-bench/tools/scan_secret_redaction.py'],logname='deepseek-final-scan')
    write_state(phase='done',complete=True,remaining_runner_rc=rc,scan_rc=scan,finished=time.time())
    return 0 if scan==0 else 3

if __name__=='__main__':raise SystemExit(main())
