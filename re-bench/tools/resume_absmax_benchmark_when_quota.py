#!/usr/bin/env python3
"""Resume the authoritative ABSOLUTE MAXIMUM benchmark only when authorised quota is available.

Outer mode probes the credential-isolated TokenHarbor Unix proxy with a tiny
non-sensitive request. It never reads or prints the API key. Worker mode scans
preserved results, counts structurally valid attempts with the real scorer, and
runs only enough new attempts to move each variant/scenario group toward five
valid attempts. Invalid provider/harness/timeout records remain evidence but do
not consume a valid-attempt slot.
"""
import argparse, concurrent.futures, datetime, json, os, re, socket, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
AI=RAW/'ai_benchmark'
ORCH=AI/'orchestrator'
HY4_MODEL='opencode/hy4-flash-free'
KERN_MODEL='kern/inkling-2-mini'
TOKEN_FREE_MODEL='tokenharbor/deepseek-v4.1-flash:free'
TOKEN_PAID_MODEL='tokenharbor/deepseek-v4.1-flash-1017'
MODEL=os.environ.get('ABSMAX_BENCH_MODEL',KERN_MODEL)
# Authorised lanes only. Do not substitute unauthorized models here: the
# operator-authorised lanes are the built-in OpenCode Hy4 free lane, the
# TokenHarbor free lane, and the TokenHarbor 1017 fallback.
LANES=[KERN_MODEL,TOKEN_FREE_MODEL,TOKEN_PAID_MODEL]
PROXY_SOCKET=Path('/home/nixon/absmax-tokenharbor-proxy/tokenharbor.sock')
KERN_PROXY_SOCKET=Path('/home/nixon/absmax-tokenharbor-proxy/kern.sock')
STOP=ORCH/'STOP_RESUME'
WATCHDOG_PIDFILE=ORCH/'resume_quota_watchdog.pid'
WATCHDOG_CMDLINE_TOKEN='resume_absmax_benchmark_when_quota'

def _model_slug(model):
    return model.replace('/','_').replace(':','_')

def status_paths(model):
    if model==TOKEN_PAID_MODEL:
        return ORCH/'resume_post_status.json',ORCH/'resume_prefix_status.json'
    slug=_model_slug(model)
    return ORCH/f'resume_post_status_{slug}.json',ORCH/f'resume_prefix_status_{slug}.json'

POST_STATUS,PREFIX_STATUS=status_paths(MODEL)
COMPLETION=ORCH/'resume_completion_report.json'
LOG=ORCH/'resume_quota_watchdog.log'
ALL_SCENARIOS=[
 'binary-only-external','static-analysis-only','ghidra-static','ghidra-dynamic',
 'unprivileged-local','privileged-debugger','native-module-extraction','loader-initialization-order',
 'pack-layout-sections','crypto-construction','provenance-signatures','host-runtime-gates',
 'chain-licence-path','semantics-hidden-vectors','legitimate-runtime-secrets','runtime-secrets-withheld']
# User-directed priority: essential zero-valid groups first, then remaining groups.
PRIORITY=[
 'legitimate-runtime-secrets','runtime-secrets-withheld','crypto-construction','chain-licence-path',
 'semantics-hidden-vectors','loader-initialization-order','pack-layout-sections','provenance-signatures',
 'host-runtime-gates']
PREFIX_SCENARIOS=['native-module-extraction','crypto-construction']


def log(obj):
    ORCH.mkdir(parents=True,exist_ok=True)
    obj=dict(obj);obj['ts']=time.time()
    with LOG.open('a') as f:f.write(json.dumps(obj)+'\n')


def _pid_cmdline(pid):
    """Best-effort live-process cmdline read; empty string when unreadable."""
    try:
        return Path('/proc/'+str(int(pid))+'/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
    except Exception:
        return ''


def cmdline_is_outer_watchdog(cmdline):
    """True only for an outer-mode watchdog cmdline, never a --worker child."""
    raw=str(cmdline or '')
    return WATCHDOG_CMDLINE_TOKEN in raw and '--worker' not in raw


def live_outer_watchdog_pid(pid):
    """True when pid belongs to a live outer-mode watchdog process.

    Stale pid files, pid reuse by unrelated processes, and short-lived worker
    children (which carry --worker in their cmdline) are all treated as not
    conflicting so a new watchdog can safely take over.
    """
    try:
        pid=int(pid)
    except (TypeError,ValueError):
        return False
    if pid<=0 or pid==os.getpid():
        return False
    return cmdline_is_outer_watchdog(_pid_cmdline(pid))


def acquire_watchdog_fence(pidfile=WATCHDOG_PIDFILE):
    """Claim the single outer-watchdog instance slot.

    Exactly one multi-lane resume watchdog may be active. The fence combines an
    exclusive non-blocking flock on the pid file (held for the process lifetime,
    which closes simultaneous-start races) with live cmdline validation of any
    pid already recorded there (which detects pre-flock legacy watchdogs that
    hold no lock). On any conflict the caller must exit safely without starting
    scans, probes, or jobs.
    """
    pidfile=Path(pidfile)
    pidfile.parent.mkdir(parents=True,exist_ok=True)
    me=os.getpid()
    try:
        fh=pidfile.open('a+')
    except OSError as e:
        return {'acquired':False,'error':'pidfile-unavailable','detail':str(e)[:200]}
    lock_mechanism='unavailable'
    lock_held_by_other=False
    try:
        import fcntl
        try:
            fcntl.flock(fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            lock_mechanism='flock'
        except OSError:
            lock_held_by_other=True
            lock_mechanism='flock-conflict'
    except ImportError:
        lock_mechanism='cmdline-only'
    existing=None
    try:
        fh.seek(0)
        existing=int((fh.read() or '').strip() or '0')
    except Exception:
        existing=None
    if lock_held_by_other or (existing and existing!=me and live_outer_watchdog_pid(existing)):
        try:fh.close()
        except Exception:pass
        return {'acquired':False,'conflict_pid':existing,'mechanism':lock_mechanism,'pid':me}
    try:
        fh.seek(0);fh.truncate();fh.write(str(me));fh.flush()
        try:os.fsync(fh.fileno())
        except Exception:pass
    except OSError as e:
        try:fh.close()
        except Exception:pass
        return {'acquired':False,'error':'pidfile-unwritable','detail':str(e)[:200]}
    # The handle must stay open for the process lifetime: closing it releases
    # the flock. The caller keeps the returned dict alive in outer().
    return {'acquired':True,'pid':me,'pidfile':str(pidfile),'mechanism':lock_mechanism,'handle':fh}


def probe_opencode_config():
    """Minimal credential-free OpenCode provider config mirroring benchmark state.

    Benchmark attempts run with only the credential-isolated TokenHarbor provider
    defined. The dummy apiKey is not a credential: the host-side Unix proxy
    replaces authorization outside the sandbox. Only authorised lanes are
    represented here.
    """
    return {
     '$schema':'https://opencode.ai/config.json',
     'provider':{
      'tokenharbor':{
       'npm':'@ai-sdk/openai-compatible',
       'name':'Token Harbor',
       'options':{'baseURL':'http://127.0.0.1:8976/v1','apiKey':'credential-isolated-local-proxy'},
       'models':{
        'deepseek-v4.1-flash-1017':{'name':'DeepSeek V4.1 Flash 1017'},
        'deepseek-v4.1-flash:free':{'name':'DeepSeek V4.1 Flash (Free)'},
       },
      },
     },
    }


def assess_hy4_probe_output(stdout,stderr,returncode):
    """Pure assessment of one Hy4 probe run.

    Availability requires a zero return code, no free-limit/quota error, and
    evidence of assistant text or token usage in the JSON event stream. An exact
    'ok' reply is not required: any non-empty assistant text or positive token
    usage proves the model lane actually served a completion, while rc0 alone
    cannot distinguish a real response from an early harness/client failure.
    """
    out=stdout or '';err=stderr or ''
    err_tail=err[-240:];out_tail=out[-500:]
    combined=(out_tail+'\n'+err_tail).lower()
    quota=('free-limit' in combined or 'free usage limit' in combined or 'freeusagelimiterror' in combined or 'provider.free-limit' in combined)
    retry_ms=0;assistant_text=False;token_usage=False
    for line in out.splitlines():
        try:
            ev=json.loads(line)
        except Exception:
            continue
        if not isinstance(ev,dict):
            continue
        e=ev.get('error') or {}
        if isinstance(e,dict):
            try:retry_ms=max(retry_ms,int(e.get('retryAfterMs') or 0))
            except Exception:pass
            typ=str(e.get('type') or '').lower();msg=str(e.get('message') or '').lower()
            if 'free-limit' in typ or 'free usage limit' in msg or 'freeusagelimiterror' in typ:
                quota=True
        part=ev.get('part') or {}
        if isinstance(part,dict):
            if ev.get('type')=='text' and str(part.get('text') or '').strip():
                assistant_text=True
            tok=part.get('tokens')
            if isinstance(tok,dict):
                total=0
                for key in ('total','input','output','reasoning'):
                    try:total+=int(tok.get(key) or 0)
                    except Exception:pass
                if total>0:
                    token_usage=True
    compact=out.replace(' ','')
    ok_text='"text":"ok"' in compact or '\nok' in out or out.strip().endswith('ok')
    available=(returncode==0 and not quota and (assistant_text or token_usage))
    return {'available':available,'returncode':returncode,'quota_limited':quota,'retry_after_ms':retry_ms,
            'error_message':err_tail,'assistant_text_evidence':assistant_text,'token_usage_evidence':token_usage,'ok_text':ok_text}


def probe_hy4(model=HY4_MODEL):
    """Tiny non-sensitive availability probe for the built-in OpenCode free lane.

    The probe mirrors the minimal benchmark OpenCode environment as closely as
    practical for a host-side check: fresh per-probe config/data state with the
    same credential-free provider config benchmark attempts use, the same
    invocation flags, a scrubbed minimal environment with no inherited host
    credentials, and the same redacting-MITM egress path. In-sandbox attempts
    reach that MITM through the bridge on 127.0.0.1:8976; the host-side probe
    uses the same MITM directly on 127.0.0.1:9898, so TLS interception,
    redaction, and upstream validation match the benchmark lane.
    """
    import tempfile
    tmp_root=Path(os.environ.get('ABSMAX_PROBE_TMP_ROOT','/home/nixon/absmax-tmp'))
    try:
        tmp_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='absmax-hy4-probe-',dir=tmp_root) as td:
            probe_home=Path(td)/'home'
            cfg_dir=probe_home/'.config/opencode'
            data_dir=probe_home/'.local/share/opencode'
            cfg_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)
            (cfg_dir/'opencode.json').write_text(json.dumps(probe_opencode_config(),indent=2))
            (data_dir/'opencode.db').touch()
            env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(probe_home),'USER':'nixon','LOGNAME':'nixon',
                 'LANG':'C.UTF-8','LC_ALL':'C.UTF-8','TMPDIR':str(tmp_root),'PYTHONUNBUFFERED':'1','OPENCODE_DISABLE_AUTOUPDATE':'1',
                 'HTTPS_PROXY':'http://127.0.0.1:9898','https_proxy':'http://127.0.0.1:9898','HTTP_PROXY':'http://127.0.0.1:9898','http_proxy':'http://127.0.0.1:9898',
                 'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost',
                 'SSL_CERT_FILE':'/home/nixon/absmax-tokenharbor-proxy/opencode-mitm-ca-bundle.pem','NODE_EXTRA_CA_CERTS':'/home/nixon/absmax-tokenharbor-proxy/opencode-mitm-ca-bundle.pem'}
            cmd=['/home/nixon/.opencode/bin/opencode','run','--standalone','--format','json','--auto','--archived','--title','absmax-hy4-availability-probe','--model',model,'Reply with exactly: ok']
            p=subprocess.run(cmd,cwd=td,text=True,capture_output=True,timeout=45,env=env)
        assessment=assess_hy4_probe_output(p.stdout or '',p.stderr or '',p.returncode)
        assessment['model']=model
        return assessment
    except Exception as e:
        return {'available':False,'error':type(e).__name__,'model':model}


def _unix_http_json(sock_path, method, path, obj=None, timeout=20):
    """Minimal HTTP/JSON client for the credential-isolated Unix proxy."""
    body=b'' if obj is None else json.dumps(obj).encode()
    s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(timeout)
    s.connect(str(sock_path))
    req=(f'{method} {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n').encode()+body
    s.sendall(req)
    data=b''
    while True:
        try:chunk=s.recv(65536)
        except socket.timeout:break
        if not chunk:break
        data+=chunk
    try:s.close()
    except Exception:pass
    head,_,resp_body=data.partition(b'\r\n\r\n')
    try:status=int(head.split(None,2)[1])
    except Exception:status=None
    try:parsed=json.loads(resp_body.decode() or '{}')
    except Exception:parsed={}
    return status,parsed


def provider_reset_epoch(message):
    m=re.search(r'comes back on\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+at\s+\d{1,2}:\d{2}\s+UTC)',str(message or ''))
    if not m:
        return 0.0
    try:
        dt=datetime.datetime.strptime(m.group(1),'%d %b %Y at %H:%M UTC').replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def probe_model(model=MODEL):
    """Probe the selected model lane without exposing credentials."""
    if model.startswith('opencode/'):
        return probe_hy4(model)
    upstream_model=model.split('/',1)[1] if '/' in model else model
    payload={'model':upstream_model,'messages':[{'role':'user','content':'Reply with exactly: ok'}],'max_tokens':1,'temperature':0}
    try:
        sock=KERN_PROXY_SOCKET if model.startswith('kern/') else PROXY_SOCKET
        status,obj=_unix_http_json(sock,'POST','/v1/chat/completions',payload,timeout=30)
        err=obj.get('error') if isinstance(obj,dict) else None
        if isinstance(err,dict):
            msg=err.get('message') or err.get('type') or ''
        elif isinstance(err,str):
            msg=err
        else:
            msg=''
        return {'available':status==200,'status':status,'error_message':msg,'model':model}
    except Exception as e:
        return {'available':False,'error':type(e).__name__,'model':model}


def hy4_free_limit_cooldown(ai_out):
    """Return the cooldown implied by the freshest Hy4 free-limit record.

    OpenCode includes retryAfterMs in provider.free-limit result records. Only
    the freshest such record (by local completion mtime) is authoritative:
    taking the maximum historical file_mtime+retryAfterMs across all records
    lets one stale long-cooldown record block the lane long after the provider
    has reset quota, because newer records with shorter or expired windows are
    ignored. File mtime is the local completion time; the provider-specified
    retryAfterMs extends from that point.
    """
    now=time.time();freshest=None
    rdir=ai_out/'results'
    if not rdir.exists():
        return {'active':False,'until':0.0,'remaining_seconds':0}
    for p in rdir.glob('*opencode_hy4-flash-free*.json'):
        try:d=json.loads(p.read_text())
        except Exception:continue
        err=d.get('provider_error') or {}
        if not isinstance(err,dict):continue
        typ=str(err.get('type') or '').lower();msg=str(err.get('message') or '').lower()
        if 'free-limit' not in typ and 'free usage limit' not in msg:
            continue
        try:ms=int(err.get('retryAfterMs') or 0)
        except Exception:ms=0
        if ms<=0:ms=3600000
        try:mtime=p.stat().st_mtime
        except Exception:continue
        if freshest is None or mtime>freshest['record_mtime']:
            freshest={'result_file':p.name,'retry_after_ms':ms,'record_mtime':mtime}
    if freshest is None:
        return {'active':False,'until':0.0,'remaining_seconds':0}
    until=freshest['record_mtime']+freshest['retry_after_ms']/1000.0
    freshest['cooldown_until']=until
    return {'active':until>now,'until':until,'remaining_seconds':max(0,int(until-now)),'latest_free_limit':freshest}


def advisory_capped_until(cooldown_until,now,advisory_seconds):
    """Cap how long a recorded cooldown may suppress inexpensive probing.

    Long provider cooldowns are advisory, not proof the lane stays unavailable:
    the watchdog still re-probes every advisory window (30-60 minutes of cheap
    single-request probes) so it resumes promptly when quota resets early,
    while never probing more often than the advisory window. A shorter
    cooldown is honoured exactly.
    """
    try:until=float(cooldown_until or 0)
    except Exception:return 0.0
    if until<=0:
        return 0.0
    try:cap=float(advisory_seconds)
    except Exception:cap=2700.0
    return min(until,float(now)+max(0.0,cap))


def scan_groups(ai_out,variants,scenarios,target_valid):
    """Count valid attempts using the real scorer inside worker mode."""
    import score_ai_benchmark
    groups={(v,s):{'valid':0,'used_attempts':set(),'records':0} for v in variants for s in scenarios}
    rdir=ai_out/'results'
    if rdir.exists():
        for p in sorted(rdir.glob('*.json')):
            try:d=json.loads(p.read_text())
            except Exception:continue
            key=(d.get('variant'),d.get('scenario'))
            if key not in groups or d.get('model')!=MODEL:continue
            g=groups[key];g['records']+=1
            try:g['used_attempts'].add(int(d.get('attempt') or 0))
            except Exception:pass
            try:valid=bool(score_ai_benchmark.score_result(d).get('structurally_valid'))
            except Exception:valid=False
            if valid:g['valid']+=1
    out={}
    for key,g in groups.items():
        out[key]={'valid':g['valid'],'needed':max(0,target_valid-g['valid']),'used_attempts':g['used_attempts'],'records':g['records']}
    return out


def next_attempt(used):
    n=1
    while n in used:n+=1
    return n


def choose_jobs(groups,variants,scenarios,batch_size,target_valid):
    def order(item):
        (variant,scenario),g=item
        pri=PRIORITY.index(scenario) if scenario in PRIORITY else len(PRIORITY)+scenarios.index(scenario)
        return (0 if g['valid']==0 else 1,pri,variant)
    ordered=sorted(groups.items(),key=order)
    jobs=[]
    # Round-robin through deficient groups so one difficult scenario cannot starve the rest.
    while len(jobs)<batch_size:
        added=False
        for (variant,scenario),g in ordered:
            if len(jobs)>=batch_size:break
            planned=sum(1 for j in jobs if j[0]==variant and j[1]==scenario)
            if g['needed']-planned<=0:continue
            used=set(g['used_attempts'])|{j[3] for j in jobs if j[0]==variant and j[1]==scenario}
            jobs.append((variant,scenario,MODEL,next_attempt(used)));added=True
        if not added:break
    return jobs


def worker(args):
    if args.suffix:
        os.environ['ABSMAX_BENCHMARK_SUFFIX']=args.suffix
    if args.artifact_subdir:
        os.environ['ABSMAX_ARTIFACT_SUBDIR']=args.artifact_subdir
    if args.live_workspace_root:
        os.environ['ABSMAX_LIVE_WORKSPACE_ROOT']=args.live_workspace_root
    if args.opencode_state_root:
        os.environ['ABSMAX_OPENCODE_STATE_ROOT']=args.opencode_state_root
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import ai_bench
    variants=args.variants.split(',')
    scenarios=args.scenarios.split(',')
    groups=scan_groups(ai_bench.OUT,variants,scenarios,args.target_valid)
    complete=all(g['needed']==0 for g in groups.values())
    jobs=[];batch=[]
    if not complete and not args.scan_only:
        jobs=choose_jobs(groups,variants,scenarios,args.batch_size,args.target_valid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.batch_size) as ex:
            futs={ex.submit(ai_bench.one,j):j for j in jobs}
            for fut in concurrent.futures.as_completed(futs):
                j=futs[fut]
                try:
                    r=fut.result();batch.append({'job':j,'returncode':r.get('returncode'),'timeout':r.get('timeout'),'provider_error_type':(r.get('provider_error') or {}).get('type'),'fallback_reason':r.get('fallback_reason'),'result_model':r.get('model')})
                except Exception as e:
                    batch.append({'job':j,'executor_error':repr(e)})
        groups=scan_groups(ai_bench.OUT,variants,scenarios,args.target_valid)
        complete=all(g['needed']==0 for g in groups.values())
    status={
      'complete':complete,'target_valid_per_group':args.target_valid,'model':MODEL,
      'groups_total':len(groups),'groups_complete':sum(1 for g in groups.values() if g['needed']==0),
      'valid_total':sum(g['valid'] for g in groups.values()),'records_total':sum(g['records'] for g in groups.values()),
      'deficient':{'/'.join(k):g for k,g in groups.items() if g['needed']},
      'last_batch':batch,'scan_only':bool(args.scan_only),'updated':time.time(),
      'results_root':str(ai_bench.OUT.relative_to(ROOT)),
    }
    # JSON cannot serialize sets; they are only internal above.
    for g in status['deficient'].values():g['used_attempts']=sorted(g['used_attempts'])
    Path(args.status_file).parent.mkdir(parents=True,exist_ok=True)
    Path(args.status_file).write_text(json.dumps(status,indent=2))
    print(json.dumps({'complete':complete,'groups_complete':status['groups_complete'],'groups_total':len(groups),'valid_total':status['valid_total'],'batch':len(batch),'scan_only':bool(args.scan_only)}),flush=True)
    return 0


def load_status(path):
    try:return json.loads(path.read_text())
    except Exception:return {'complete':False}


def run_worker(mode,scan_only=False,model=MODEL):
    post_status,prefix_status=status_paths(model)
    if mode=='post':
        cmd=[sys.executable,str(Path(__file__).resolve()),'--worker','--status-file',str(post_status),'--variants','absolute-native-only,absolute','--scenarios',','.join(ALL_SCENARIOS),'--batch-size','1','--target-valid','5']
    else:
        cmd=[sys.executable,str(Path(__file__).resolve()),'--worker','--status-file',str(prefix_status),'--variants','absolute-native-only,absolute','--scenarios',','.join(PREFIX_SCENARIOS),'--batch-size','1','--target-valid','5','--suffix','_prefix_xor_comparison','--artifact-subdir','pre_fix','--live-workspace-root','/home/nixon/absmax-ai-workspaces-prefix-xor-comparison','--opencode-state-root','/home/nixon/absmax-opencode-state-prefix-xor-comparison']
    if scan_only:cmd.append('--scan-only')
    env=dict(os.environ);env['ABSMAX_BENCH_MODEL']=model
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env)
    rec={'mode':mode,'scan_only':scan_only,'model':model,'returncode':p.returncode,'stdout':p.stdout[-1000:],'stderr':p.stderr[-2000:]}
    log({'worker_finished':rec})
    return rec


def run_step(cmd,env=None):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env)
    return {'cmd':cmd,'returncode':p.returncode,'stdout':p.stdout[-1000:],'stderr':p.stderr[-2000:]}


def final_processing(model=MODEL):
    steps=[]
    post_scripts=['repair_copied_artifacts.py','analyze_benchmark_precision.py','score_ai_benchmark.py','render_benchmark_report.py','redact_benchmark_credentials.py','scan_secret_redaction.py']
    for name in post_scripts:
        steps.append(run_step([sys.executable,'re-bench/tools/'+name]))
    pre_env=dict(os.environ)
    pre_env['ABSMAX_BENCHMARK_SUFFIX']='_prefix_xor_comparison'
    pre_env['ABSMAX_ARTIFACT_SUBDIR']='pre_fix'
    pre_env['ABSMAX_LIVE_WORKSPACE_ROOT']='/home/nixon/absmax-ai-workspaces-prefix-xor-comparison'
    pre_env['ABSMAX_OPENCODE_STATE_ROOT']='/home/nixon/absmax-opencode-state-prefix-xor-comparison'
    for name in ['score_ai_benchmark.py','analyze_benchmark_precision.py']:
        steps.append(run_step([sys.executable,'re-bench/tools/'+name],env=pre_env))
    steps.append(run_step([sys.executable,'re-bench/tools/compare_prefix_postfix_crypto.py']))
    steps.append(run_step([sys.executable,'re-bench/tools/final_verification_summary.py']))
    post_status,prefix_status=status_paths(model)
    report={'finished':time.time(),'completed_model':model,'post_status':load_status(post_status),'prefix_status':load_status(prefix_status),'steps':steps}
    COMPLETION.write_text(json.dumps(report,indent=2))
    log({'resume_complete':True,'step_count':len(steps)})
    return report


def outer(args):
    ORCH.mkdir(parents=True,exist_ok=True)
    # Exactly one multi-lane resume watchdog may be active. Validate the pid
    # file against live process cmdlines (and hold an exclusive flock) before
    # writing our own pid; never scan, probe, or start jobs when another outer
    # watchdog is active.
    fence=acquire_watchdog_fence(WATCHDOG_PIDFILE)
    if not fence.get('acquired'):
        conflict={'watchdog_fence_conflict':{'pid':os.getpid(),'conflict_pid':fence.get('conflict_pid'),'mechanism':fence.get('mechanism'),'error':fence.get('error'),'pidfile':str(WATCHDOG_PIDFILE)}}
        try:log(conflict)
        except Exception:pass
        print(json.dumps({'error':'another outer watchdog is already active; exiting safely without scanning or probing','conflict_pid':fence.get('conflict_pid'),'pidfile':str(WATCHDOG_PIDFILE)}),flush=True)
        return 3
    log({'watchdog_start':True,'pid':os.getpid(),'probe_interval_seconds':args.probe_interval,'advisory_probe_interval_seconds':args.advisory_probe_interval,'lanes':LANES,'fence':{'pidfile':str(WATCHDOG_PIDFILE),'mechanism':fence.get('mechanism')}})
    # Scan every authorised lane once without invoking jobs so restarts do not
    # depend on provider state and no evidence label is overwritten.
    for lane in LANES:
        run_worker('post',scan_only=True,model=lane)
        run_worker('prefix',scan_only=True,model=lane)
    current_lane=None
    blocked_until={lane:0.0 for lane in LANES}
    while not STOP.exists():
        statuses={}
        for lane in LANES:
            post_status,prefix_status=status_paths(lane)
            statuses[lane]=(load_status(post_status),load_status(prefix_status))
        completed=[lane for lane,(post,prefix) in statuses.items() if post.get('complete') and prefix.get('complete')]
        if completed:
            report=final_processing(completed[0])
            print(json.dumps({'complete':True,'completed_model':completed[0],'report':str(COMPLETION),'steps':len(report['steps'])}),flush=True)
            return 0
        now=time.time()
        if current_lane:
            post,prefix=statuses[current_lane]
            if post.get('complete') and prefix.get('complete'):
                current_lane=None
                continue
            mode='post' if not post.get('complete') else 'prefix'
            rec=run_worker(mode,model=current_lane)
            post_status,prefix_status=status_paths(current_lane)
            status=load_status(post_status if mode=='post' else prefix_status)
            last=status.get('last_batch') or []
            provider_error=any('free-limit' in str(x.get('provider_error_type') or '').lower()
                               or 'free usage limit' in str(x.get('provider_error_type') or '').lower()
                               for x in last)
            fallback=any(x.get('fallback_reason') for x in last)
            if fallback and current_lane==TOKEN_FREE_MODEL:
                blocked_until[current_lane]=time.time()+max(args.probe_interval,300)
                log({'lane_fallback_exhausted':{'lane':current_lane,'fallback_model':TOKEN_PAID_MODEL,'last_batch':last}})
                current_lane=None
                continue
            if rec.get('returncode')!=0 or provider_error:
                if current_lane==HY4_MODEL:
                    cooldown=hy4_free_limit_cooldown(AI)
                    blocked_now=time.time()
                    if cooldown.get('active'):
                        until=advisory_capped_until(float(cooldown.get('until') or 0),blocked_now,args.advisory_probe_interval)
                    else:
                        until=blocked_now+args.probe_interval
                    blocked_until[current_lane]=until
                    log({'lane_provider_blocked':{'lane':current_lane,'until':until,'cooldown':cooldown,'advisory_probe_capped_until':until,'last_batch':last,'returncode':rec.get('returncode')}})
                else:
                    blocked_until[current_lane]=time.time()+args.probe_interval
                    log({'lane_provider_blocked':{'lane':current_lane,'until':blocked_until[current_lane],'last_batch':last,'returncode':rec.get('returncode')}})
                current_lane=None
            continue

        for lane in LANES:
            now=time.time()
            if now<float(blocked_until.get(lane) or 0):
                continue
            # Historical Hy4 free-limit records carry retryAfterMs, but they
            # are not proof the lane is still unavailable now. Probe first;
            # only use the recorded cooldown after a fresh quota failure.
            probe=probe_model(lane)
            log({'provider_probe':probe,'lane_selection':'multi-lane-watchdog'})
            if lane==HY4_MODEL and not probe.get('available'):
                cooldown=hy4_free_limit_cooldown(AI)
                if cooldown.get('active'):
                    capped=advisory_capped_until(float(cooldown.get('until') or 0),now,args.advisory_probe_interval)
                    blocked_until[lane]=capped
                    log({'hy4_free_limit_cooldown':cooldown,'advisory_probe_capped_until':capped})
                    continue
            if probe.get('available'):
                current_lane=lane
                log({'lane_selected':{'lane':lane,'reason':'first available authorised lane in watchdog priority order'}})
                break
            retry_ms=int(probe.get('retry_after_ms') or 0)
            reset_at=provider_reset_epoch(probe.get('error_message'))
            if reset_at>now:
                blocked_until[lane]=reset_at
            else:
                blocked_until[lane]=now+max(args.probe_interval,retry_ms/1000.0)
            if lane==HY4_MODEL:
                # The fresh probe's own retryAfterMs can span many hours. Like
                # the record-derived cooldown it is advisory only: inexpensive
                # probes still re-check the lane every advisory window.
                capped=advisory_capped_until(float(blocked_until[lane] or 0),now,args.advisory_probe_interval)
                if capped!=blocked_until[lane]:
                    log({'hy4_advisory_probe_cap':{'lane':lane,'uncapped_until':blocked_until[lane],'capped_until':capped,'retry_after_ms':retry_ms}})
                blocked_until[lane]=capped
        if not current_lane:
            time.sleep(args.probe_interval)
    log({'stopped_by_file':str(STOP)})
    print(json.dumps({'stopped':True,'stop_file':str(STOP)}),flush=True)
    return 0


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--worker',action='store_true')
    ap.add_argument('--scan-only',action='store_true')
    ap.add_argument('--status-file',default='/tmp/absmax-resume-status.json')
    ap.add_argument('--variants',default='absolute-native-only,absolute')
    ap.add_argument('--scenarios',default=','.join(ALL_SCENARIOS))
    ap.add_argument('--batch-size',type=int,default=6)
    ap.add_argument('--target-valid',type=int,default=5)
    ap.add_argument('--suffix',default='')
    ap.add_argument('--artifact-subdir',default='')
    ap.add_argument('--live-workspace-root',default='')
    ap.add_argument('--opencode-state-root',default='')
    ap.add_argument('--probe-interval',type=int,default=1800)
    # Long Hy4 free-limit cooldowns are advisory: inexpensive availability
    # probes still re-check the lane at most this often (default 45 minutes,
    # inside the operator-directed 30-60 minute window) instead of trusting a
    # multi-hour historical cooldown blindly.
    ap.add_argument('--advisory-probe-interval',type=int,default=2700)
    args=ap.parse_args()
    if args.worker:return worker(args)
    return outer(args)

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        try:
            import traceback
            log({'watchdog_fatal':{'error_type':type(exc).__name__,'error':str(exc)[:300],'traceback_tail':traceback.format_exc()[-2000:]}})
        finally:
            raise
