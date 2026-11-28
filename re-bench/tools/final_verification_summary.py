#!/usr/bin/env python3
"""Collect final audit verification facts without printing secrets."""
import hashlib, json, re, subprocess, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
AI=RAW/'ai_benchmark'
EXPECTED_ARTIFACT_SHA256={
 'absolute-native-only':'28630cc945e883151761b4752db1d9a7e59a7dbb29bc9e93b381e75ba2898032',
 'absolute':'5382e72af5cce267fa2ec0379b6c3910b0bc33f7ac645a5ad2c88bc011ce0fbe',
}
EXPECTED_NATIVE_SHA256={
 'absolute-native-only':'ebd1f04def3f422a27dcaa7e9d223432454f270bd8af28371cdf9323a3a71515',
 'absolute':'4b0b297aefb138c78944eb59adf90ac681fd5708cab9413bfa434a771dfa5cf6',
}

def sh(cmd):
 p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
 return {'cmd':' '.join(cmd),'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}

def sha(p):
 h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()

def text(p):
 try:return p.read_text(errors='replace')
 except:return ''

def last_count_line(path):
 t=text(path)
 lines=[x.strip() for x in t.splitlines() if re.search(r'\b(?:passed|failed|xfailed|skipped)\b',x)]
 return lines[-1] if lines else None

def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def rc_file(path):
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def result_identity_check(rows, artifacts):
    expected={v:x['sha256'] for v,x in artifacts.items()}
    mismatches=[]; counts={}; model_counts={}
    for d in rows:
        v=d.get('variant'); counts[v]=counts.get(v,0)+1
        m=str(d.get('model')); model_counts[m]=model_counts.get(m,0)+1
        if expected.get(v) and d.get('artifact_sha256')!=expected[v]:
            mismatches.append({'variant':v,'scenario':d.get('scenario'),'model':d.get('model'),'attempt':d.get('attempt'),'artifact_sha256':d.get('artifact_sha256')})
    return {'result_counts_by_variant':counts,'result_counts_by_model':model_counts,'mismatch_count':len(mismatches),'mismatches':mismatches[:20]}


def precision_counts():
    p=AI/'benchmark_precision_analysis.json'
    x=load_json(p)
    if not x:return {'available':False}
    rows=x.get('attempts',[])
    # Raw precision analysis includes malformed/invalid attempts because their
    # workspace evidence can still be security-relevant. Valid-only counts come
    # from score_summary.json and are the counts used for benchmark conclusions.
    sr=load_json(AI/'score_summary.json') or {}
    srows=sr.get('attempts',[])
    valid=[r for r in srows if r.get('structurally_valid')]
    valid_keys={(r.get('variant'),r.get('scenario'),r.get('model'),r.get('attempt')) for r in valid}
    precision_valid=[x for x in rows if (x.get('variant'),x.get('scenario'),x.get('model'),x.get('attempt')) in valid_keys]
    return {'available':True,'attempts':len(rows),
            'valid_only':{
             'attempts':len(valid),
             'correct_public_base_key':sum(1 for r in valid if r.get('correct_artifact_public_base_key_recovered')),
             'correct_nxs1_nonce':sum(1 for r in valid if r.get('correct_nxs1_nonce_reported')),
             'payload_plaintext_or_semantic_recovery':sum(1 for r in valid if r.get('payload_plaintext_recovered')),
             'payload_elf_recovered_excluding_supplied':sum(1 for x in precision_valid if x.get('payload_elf_recovered_in_workspace')),
             'raw_payload_elf_hits_including_supplied':sum(1 for x in precision_valid if x.get('raw_payload_elf_hits_including_supplied')),
             'independent_solution_passed':sum(1 for r in valid if r.get('independent_solution_all_passed')),
             'secret_recovered':sum(1 for r in valid if r.get('secret_recovered'))},
            'all_records_including_invalid':{
             'correct_public_base_key':sum(1 for r in rows if r.get('correct_artifact_public_base_key_recovered')),
             'correct_nxs1_nonce':sum(1 for r in rows if r.get('correct_nxs1_nonce_reported')),
             'payload_elf_recovered':sum(1 for r in rows if r.get('payload_elf_recovered_in_workspace')),
             'independent_solution_passed':sum(1 for r in rows if r.get('independent_solution_all_passed')),
             'secret_recovered':sum(1 for r in rows if r.get('secret_recovered'))},
            'interpretation':'use valid_only for scored benchmark conclusions; payload_plaintext_or_semantic_recovery includes exact secret or fully passing solution evidence, while payload_elf_recovered_excluding_supplied is the stricter native-object recovery count after excluding scenario-supplied evidence; all_records includes invalid attempts as security-relevant raw evidence, not valid benchmark performance'}


def main():
 status=sh(['git','status','--short','--branch'])
 head=sh(['git','rev-parse','HEAD'])
 diff_docs=sh(['git','diff','--name-only','--','docs/MAXIMUM_SECURITY.md'])
 artifacts={}
 native_objects={}
 for v in ['absolute-native-only','absolute']:
  p=RAW/'builds'/v/'cipher/artifact.py'
  digest=sha(p)
  artifacts[v]={'path':str(p.relative_to(ROOT)),'sha256':digest,'size':p.stat().st_size,'authoritative_sha256':EXPECTED_ARTIFACT_SHA256[v],'matches_authoritative_sha256':digest==EXPECTED_ARTIFACT_SHA256[v]}
  np=RAW/'native_final_lowering'/v/'linux.so'
  if np.exists():
   nd=sha(np)
   native_objects[v]={'path':str(np.relative_to(ROOT)),'sha256':nd,'size':np.stat().st_size,'authoritative_sha256':EXPECTED_NATIVE_SHA256[v],'matches_authoritative_sha256':nd==EXPECTED_NATIVE_SHA256[v]}
  else:
   native_objects[v]={'path':str(np.relative_to(ROOT)),'exists':False,'matches_authoritative_sha256':False}
 test_files={
  'native_build_regression':'final_native_build_regression.txt',
  'ai_findings_regression':'ai_findings_current_source_rerun.log',
  'ai_findings_historical_pre_hardening':'final_ai_findings_regression.txt',
  'focused_security':'final_focused_security.txt',
  'chain':'final_chain_tests.txt',
  'lowering':'final_lowering_suite.txt',
  'native_core_abi':'native_core_abi_after_rebuild.txt',
  'lowering_perf_harness':'lowering_perf_test.txt',
  'operator_shard_masking_later_source':'operator_shard_masking_tests.txt',
  'benchmark_harness_regression':'benchmark_harness_regression.txt',
  'evidence_completeness_perf_fix':'pytest-evidence-completeness-perf-fix.log',
  'cfi_loader_test_fixes':'pytest-cfi-loader-test-fixes.log',
  'tmp_path_hardcoded_test_fixes':'pytest-tmp-path-hardcoded-fixes.log',
  'hybrid_loader_fragment_fix':'pytest-hybrid-loader-fragment-fix.log',
  'full_pytest_incomplete':'full_pytest_postfix_incomplete.txt',
 }
 tests={k:{'file':str((RAW/'test_outputs'/f).relative_to(ROOT)),'summary_line':last_count_line(RAW/'test_outputs'/f),'returncode':rc_file(RAW/'test_outputs'/(f[:-4]+'.rc'))} for k,f in test_files.items()}
 partition_runs={}
 for part_dir in sorted((RAW/'test_outputs').glob('full_pytest*')):
  if not part_dir.is_dir():
   continue
  data=load_json(part_dir/'results.json')
  if not data:
   continue
  partition_runs[part_dir.name]={
   'results_file':str((part_dir/'results.json').relative_to(ROOT)),
   'all_partitions_passed':data.get('all_partitions_passed'),
   'failed_partitions':data.get('failed_partitions'),
   'partitions':{p.get('name'):{'returncode':p.get('returncode'),'timed_out':p.get('timed_out'),'duration_seconds':p.get('duration_seconds'),'counts':p.get('counts')} for p in data.get('partitions',[])},
  }
 if partition_runs:
  tests['partitioned_full_suite_runs']=partition_runs
 score={}
 strict_rows=[]
 strict_group_rows=[]
 sp=AI/'score_summary.json'
 if sp.exists():
  s=json.loads(sp.read_text())
  strict_rows=s.get('attempts',[])
  model_counts={}
  for model in sorted({str(r.get('model')) for r in strict_rows}):
   mr=[r for r in strict_rows if str(r.get('model'))==model]
   model_counts[model]={
    'records':len(mr),
    'strict_valid':sum(1 for r in mr if r.get('structurally_valid')),
    'failure_categories':dict(Counter(r.get('failure_category','valid') for r in mr)),
   }
  groups=defaultdict(list)
  for r in strict_rows:
   groups[(r.get('variant'),r.get('scenario'),str(r.get('model')))].append(r)
  for (variant,scenario,model),rs in sorted(groups.items()):
   valid=sum(1 for r in rs if r.get('structurally_valid'))
   strict_group_rows.append({'variant':variant,'scenario':scenario,'model':model,'valid_total':valid,'total':len(rs),'meets_five_valid':valid>=5})
  valid_group_size_distribution=dict(Counter(str(g['valid_total']) for g in strict_group_rows if g['valid_total']))
 score={'completed_records':s.get('completed_records'),'structurally_valid':s.get('structurally_valid'),'valid_scored_group_count':len(s.get('group_stats',[])),'valid_scored_group_count_note':'group_stats contains groups with at least one strict valid attempt, not groups meeting the five-valid target','model_counts':model_counts,'groups_meeting_five_valid':sum(1 for g in strict_group_rows if g['meets_five_valid']),'groups_total':len(strict_group_rows),'valid_group_size_distribution':valid_group_size_distribution,'max_valid_attempts_in_any_group':max((g['valid_total'] for g in strict_group_rows),default=0),'model_separated_groups_with_valid':sum(1 for g in strict_group_rows if g['valid_total']),'model_separated_groups_zero_valid':sum(1 for g in strict_group_rows if not g['valid_total'])}
 completion={}
 cp=AI/'final_completion_report.json'
 if cp.exists():
  c=json.loads(cp.read_text());completion={'benchmark_status':c.get('benchmark_status'),'supplementation_rounds':c.get('supplementation_rounds'),'scorer_returncode':c.get('scorer_returncode'),'render_returncode':c.get('render_returncode'),'completed_records':c.get('completed_records'),'structurally_valid':c.get('structurally_valid'),'valid_initial_records':c.get('valid_initial_records'),'valid_supplemental_records':c.get('valid_supplemental_records'),'failure_category_reconciliation':c.get('failure_category_reconciliation'),'matrix_group_count':len(c.get('groups',[])),'groups_meeting_five_valid':c.get('groups_meeting_five_valid'),'groups_with_any_valid':c.get('groups_with_any_valid')}
  score['matrix_group_count']=len(c.get('groups',[]))
 secret_scan={}
 ss=RAW/'secret_redaction_scan.json'
 if ss.exists():
  x=json.loads(ss.read_text());secret_scan={'scan_roots':x.get('scan_roots'),'prefilter':x.get('prefilter'),'files_scanned':x.get('files_scanned'),'exact_match_files':x.get('exact_match_files'),'secret_representation_match_files':x.get('secret_representation_match_files'),'secret_representations_scanned':x.get('secret_representations_scanned'),'hit_category_counts':x.get('hit_category_counts'),'expected_signature_fixture_files':x.get('expected_signature_fixture_files'),'credential_hits':x.get('credential_hits')}
 opencode_config_audit=load_json(AI/'opencode_config_secret_field_audit.json') or {}
 credscan={}
 cr=AI/'credential_redaction_report.json'
 if cr.exists():
  x=json.loads(cr.read_text());credscan={'source_environment_variable_count':len(x.get('secret_variable_names',[])),'licence_derived_redaction_label_count':len(x.get('licence_derived_redaction_labels',[])),'opencode_config_secret_label_count':len(x.get('opencode_config_secret_labels',[])),'expanded_secret_representation_count':x.get('expanded_secret_representation_count'),'files_changed':sum(r.get('files_changed',0) for r in x.get('reports',[])),'files_scanned':sum(r.get('files_scanned',0) for r in x.get('reports',[]))}
 result_rows=[]
 rdir=AI/'results'
 if rdir.exists():
  for rp in sorted(rdir.glob('*.json')):
   d=load_json(rp)
   if d: result_rows.append(d)
 artifact_identity=result_identity_check(result_rows,artifacts)
 deficient=[g for g in strict_group_rows if not g.get('meets_five_valid')]
 if completion:
  completion['scope']='historical TokenHarbor completion-orchestrator report before Hy4 continuation and before AM-027 strict 20-tool-call enforcement; use benchmark_score/model_counts for current strict counts'
 repair={}
 rp=RAW/'copied_artifact_repair_report.json'
 if rp.exists():
  x=load_json(rp) or {}
  reps=x.get('reports') or []
  repair={'copies_checked':sum(r.get('copies',0) for r in reps),'copies_repaired':sum(r.get('changed',0) for r in reps),'mismatches_after_repair':sum(len(r.get('mismatches') or []) for r in reps),'errors':sum(len(r.get('errors') or []) for r in reps),'skipped_fail_closed_no_workspace':sum(len(r.get('skipped_no_workspace') or []) for r in reps),'roots':len(reps)}
 prefix={}
 pp=RAW/'prefix_postfix_crypto_comparison.json'
 if pp.exists():
  x=load_json(pp) or {};prefix={'available':True,'pre_rows':len(x.get('pre_fix_rows',[])),'post_rows':len(x.get('post_fix_rows',[])),'markdown':'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/prefix_postfix_crypto_comparison.md'}
 else:
  prefix={'available':False}
 postproc={}
 pc=AI/'post_completion_processing.json'
 if pc.exists():
  x=load_json(pc) or {};postproc={'available':True,'steps':len(x.get('steps',[])),'failed_steps':[{'cmd':st.get('cmd'),'returncode':st.get('returncode')} for st in x.get('steps',[]) if st.get('returncode') not in (0,None)]}
 exact_crypto=load_json(RAW/'crypto_validation'/'prefix_postfix_exact_artifact_known_plaintext.json') or {}
 honey_crypto=load_json(RAW/'crypto_validation'/'authoritative_artifact_honey_key_derivation_check.json') or {}
 partition_completion=load_json(RAW/'test_outputs'/'partitioned_full_suite_completion_summary.json') or {}
 xfail_inventory=load_json(RAW/'xfail_inventory.json') or {}
 exact_rows=exact_crypto.get('rows') or []
 exact_summary={'available':bool(exact_crypto),'path':'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/crypto_validation/prefix_postfix_exact_artifact_known_plaintext.json','pre_fix_marker_bearing_elf_recoveries':sum(1 for r in exact_rows if r.get('label')=='pre_fix' for a in r.get('attacks',[]) if a.get('recovered_path')),'post_fix_matching_plaintext_recoveries':sum(1 for c in exact_crypto.get('comparisons',[]) if c.get('label')=='post_fix_final' and c.get('matches_final_extracted_plaintext'))}
 resume_statuses={p.name:load_json(p) for p in sorted((AI/'orchestrator').glob('resume_*_status*.json'))} if (AI/'orchestrator').exists() else {}
 resume={'statuses':resume_statuses,'post_status':load_json(AI/'orchestrator'/'resume_post_status.json'),'prefix_status':load_json(AI/'orchestrator'/'resume_prefix_status.json'),'completion_report':load_json(AI/'orchestrator'/'resume_completion_report.json'),'watchdog_pid_file':'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/resume_quota_watchdog.pid','hy4_watchdog_pid_file':'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/hy4-watchdog.pid','watchdog_log':'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/resume_quota_watchdog.log'}
 endpoint_src=Path('/home/nixon/absmax-tokenharbor-proxy')
 endpoint_dir=Path('/home/nixon/absmax-sandbox-endpoints')
 endpoint_rows=[]
 endpoint_family_rows={}
 for family,names in {'opencode':['evm.sock','opencode-mitm.sock','opencode-connect.sock'],'opencode-go':['evm.sock','opencode-go.sock'],'tokenharbor':['evm.sock','tokenharbor.sock'],'kern':['evm.sock','kern.sock']}.items():
  family_dir=endpoint_dir/family
  rows=[]
  for name in names:
   try:
    a=(endpoint_src/name).stat();b=(family_dir/name).stat()
    rows.append({'name':name,'source_exists':True,'link_exists':True,'inode_match':(a.st_dev,a.st_ino)==(b.st_dev,b.st_ino)})
   except FileNotFoundError:
    rows.append({'name':name,'source_exists':(endpoint_src/name).exists(),'link_exists':(family_dir/name).exists(),'inode_match':False})
  entries=sorted(x.name for x in family_dir.iterdir()) if family_dir.exists() else []
  forbidden={
   'opencode':{'opencode-go.sock','tokenharbor.sock','kern.sock'},
   'opencode-go':{'opencode-mitm.sock','opencode-connect.sock','tokenharbor.sock','kern.sock'},
   'tokenharbor':{'opencode-mitm.sock','opencode-connect.sock','opencode-go.sock','kern.sock'},
   'kern':{'opencode-mitm.sock','opencode-connect.sock','opencode-go.sock','tokenharbor.sock'},
  }[family]
  endpoint_family_rows[family]={
   'entries':entries,
   'expected_entries':sorted(names),
   'socket_links':rows,
   'all_required_socket_links_match':all(x['inode_match'] for x in rows),
   'no_cross_model_socket_exposed':not bool(set(entries)&forbidden) if family_dir.exists() else False,
  }
  endpoint_rows.extend(rows)
 endpoint_hardening={
  'endpoint_root':str(endpoint_dir),
  'families':endpoint_family_rows,
  'socket_links':endpoint_rows,
  'all_required_socket_links_match':bool(endpoint_rows) and all(x['inode_match'] for x in endpoint_rows),
  'model_separation_validation':load_json(AI/'orchestrator/model_endpoint_separation_validation.json'),
  'runtime_smoke':load_json(RAW/'evm/per_model_endpoint_runtime_smoke.json'),
  'metadata_assessment':load_json(AI/'orchestrator/proxy_operational_log_metadata_assessment.json'),
 }
 evm_readonly_proxy={
  'validation':load_json(RAW/'evm/evm_readonly_unix_proxy_validation.json'),
  'owner_state':load_json(RAW/'evm/evm_owner_state_after_readonly_proxy.json'),
  'runtime_smoke':load_json(RAW/'evm/per_model_endpoint_runtime_smoke.json'),
 }
 invalid_evidence={}
 for root in sorted(AI.glob('results_invalid*'))+sorted(AI.glob('results_archived*'))+sorted(AI.glob('results_final_aborted*')):
  if not root.is_dir():
   continue
  rows=[]
  for rp in sorted(root.glob('*.json')):
   row=load_json(rp)
   if row:
    rows.append(row)
  invalid_evidence[root.name]={
   'records':len(rows),
   'models':dict(Counter(str(r.get('model')) for r in rows)),
   'returncodes':dict(Counter(str(r.get('returncode')) for r in rows)),
   'excluded_from_authoritative_scoring':True,
  }
 out={'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'head':head['stdout'],'git_status_branch':status['stdout'].splitlines()[0] if status['stdout'] else '', 'git_status_entries':max(0,len(status['stdout'].splitlines())-1),'docs_maximum_security_worktree_diff_present':bool(diff_docs['stdout']),'docs_maximum_security_current_sha256':sha(ROOT/'docs/MAXIMUM_SECURITY.md') if (ROOT/'docs/MAXIMUM_SECURITY.md').exists() else None,'docs_maximum_security_preservation_note':'audit deliverable generation does not write this file; any worktree diff is pre-existing or external and is reported rather than reverted','artifacts':artifacts,'artifact_hash_pins_match':all(x.get('matches_authoritative_sha256') for x in artifacts.values()),'native_objects':native_objects,'native_hash_pins_match':all(x.get('matches_authoritative_sha256') for x in native_objects.values()),'tests':tests,'benchmark_score':score,'benchmark_completion':completion,'benchmark_result_artifact_identity':artifact_identity,'invalid_or_archived_evidence_inventory':invalid_evidence,'benchmark_groups_not_meeting_five_valid':deficient,'benchmark_precision_counts':precision_counts(),'copied_artifact_repair':repair,'prefix_postfix_comparison':prefix,'exact_prefix_postfix_crypto_validation':exact_summary,'authoritative_honey_key_derivation_validation':honey_crypto,'partitioned_full_suite_completion':partition_completion,'xfail_inventory':xfail_inventory,'benchmark_resume_watchdog':resume,'post_completion_processing':postproc,'evm_readonly_proxy':evm_readonly_proxy,'endpoint_hardening':endpoint_hardening,'secret_redaction_scan':secret_scan,'opencode_config_secret_field_audit':{'files_with_sensitive_fields':opencode_config_audit.get('files_with_sensitive_fields'),'state_counts':opencode_config_audit.get('state_counts'),'literal_sensitive_field_count':opencode_config_audit.get('literal_sensitive_field_count')},'credential_redaction':credscan}
 dest=RAW/'final_verification_summary.json';dest.write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
