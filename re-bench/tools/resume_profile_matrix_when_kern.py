#!/usr/bin/env python3
"""Resume local/cloud profile matrices only when the Kern lane is healthy."""
import json,os,subprocess,sys,time,socket
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STATUS=Path('/home/nixon/absmax-scratch/profile-matrix-kern-watchdog-status.json')
PIDFILE=Path('/home/nixon/absmax-scratch/profile-matrix-kern-watchdog.pid')
LOCK=Path('/home/nixon/absmax-scratch/profile-matrix-kern-watchdog.lock')
RESULTS=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark_profile_matrix_v10/results'
RUNNER=ROOT/'re-bench/tools/run_profile_matrix.py'
ARCHIVER=ROOT/'re-bench/tools/archive_invalid_matrix_results.py'
LOCAL_VARIANTS='maximum-packed,maximum-local,absolute,absolute-native-only'
CLOUD_VARIANTS='maximum-cloud,absolute-cloud'

def probe():
    try:
        sock=socket.socket(socket.AF_UNIX);sock.settimeout(12);sock.connect('/home/nixon/absmax-sandbox-endpoints/kern/kern.sock')
        body=json.dumps({'model':'inkling-2-mini','messages':[{'role':'user','content':'Reply OK'}],'max_tokens':8}).encode()
        req=(b'POST /v1/chat/completions HTTP/1.1\r\nHost: kern.local\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body)).encode()+b'\r\nConnection: close\r\n\r\n'+body)
        sock.sendall(req);data=sock.recv(300);sock.close()
        line=data.split(b'\r\n',1)[0].decode(errors='replace')
        return line.startswith('HTTP/') and ' 200' in line,line
    except Exception as e:return False,type(e).__name__

def matching_runners(variants):
    needle='--variants '+variants;live=[]
    try:
        out=subprocess.run(['pgrep','-f','run_profile_matrix.py'],text=True,capture_output=True,timeout=5).stdout.split()
        for x in out:
            try:cmd=Path('/proc/'+x+'/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            except Exception:continue
            if 'run_profile_matrix.py' in cmd and needle in cmd:live.append(int(x))
    except Exception:pass
    return live

def complete(matrix_id):
    p=Path('/home/nixon/absmax-scratch/profile-matrix-'+matrix_id+'-status.json')
    try:return bool(json.loads(p.read_text()).get('complete'))
    except Exception:return False

def start_matrix(matrix_id,variants,cloud=False):
    env=dict(os.environ);env['ABSMAX_PROFILE_MATRIX_ID']=matrix_id
    if cloud:
        env['ABSMAX_ARTIFACT_SUBDIR']='cloud-final4'
        env['ABSMAX_SECRETS_ROOT']='/home/nixon/absmax-scratch/cloud-final4-secrets'
    out=open('/home/nixon/absmax-scratch/profile-matrix-'+matrix_id+'-retry.out','ab')
    err=open('/home/nixon/absmax-scratch/profile-matrix-'+matrix_id+'-retry.err','ab')
    subprocess.Popen([sys.executable,str(RUNNER),'--variants',variants,'--attempts','1'],cwd=str(ROOT),env=env,stdout=out,stderr=err,start_new_session=True)

def main():
    import fcntl
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    fh=open(LOCK,'a+')
    try:fcntl.flock(fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return 0
    PIDFILE.write_text(str(os.getpid()))
    deadline=time.time()+12*3600
    while time.time()<deadline:
        ok,line=probe();live=matching_runners(LOCAL_VARIANTS);cloud_live=matching_runners(CLOUD_VARIANTS)
        local_done=complete('v10');cloud_done=complete('cloud-v11')
        state={'time':time.time(),'kern_probe_ok':ok,'kern_probe_status':line,'runner_pids':live,'cloud_runner_pids':cloud_live,'matrix_complete':local_done,'cloud_matrix_complete':cloud_done}
        STATUS.write_text(json.dumps(state,indent=2))
        if local_done and cloud_done:return 0
        if ok and not live and not cloud_live:
            if not local_done:
                subprocess.run([sys.executable,str(ARCHIVER),'--results-dir',str(RESULTS),'--provider-only'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
                start_matrix('v10',LOCAL_VARIANTS,cloud=False)
            elif not cloud_done:
                start_matrix('cloud-v11',CLOUD_VARIANTS,cloud=True)
        time.sleep(300)
    return 2
if __name__=='__main__':raise SystemExit(main())
