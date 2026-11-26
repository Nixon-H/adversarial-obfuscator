#!/usr/bin/env python3
"""Scan preserved raw evidence for exact runtime-secret values without printing them."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import redact_benchmark_credentials as rbc
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
LIVE=Path('/home/nixon/absmax-ai-workspaces')
STATE=Path('/home/nixon/absmax-opencode-state')
EXTRA_EVIDENCE_ROOTS=[
 Path('/home/nixon/absmax-ai-workspaces-invalid-nonstandalone'),
 Path('/home/nixon/absmax-ai-workspaces-invalid_nonstandalone_round2'),
 Path('/home/nixon/absmax-ai-workspaces-invalid-pre-bwrap'),
 Path('/home/nixon/absmax-ai-smoke-git'),
 Path('/home/nixon/absmax-ai-smoke-outside'),
 Path('/home/nixon/absmax-ai-standalone'),
 Path('/home/nixon/absmax-opencode-home'),
 Path('/home/nixon/absmax-action-verify'),
 Path('/home/nixon/absmax-scratch'),
 Path('/home/nixon/absmax-tokenharbor-proxy'),
 Path('/home/nixon/absmax-ai-workspaces-profile-matrix-v10'),
 Path('/home/nixon/absmax-opencode-state-profile-matrix-v10'),
 Path('/home/nixon/absmax-ai-workspaces-opencode-go-smoke'),
 Path('/home/nixon/absmax-opencode-state-opencode-go-smoke'),
 Path('/home/nixon/absmax-ai-workspaces-profile-matrix-go-v12'),
 Path('/home/nixon/absmax-opencode-state-profile-matrix-go-v12'),
]

def main():
 raw_secrets=[]
 for sec in sorted((ROOT/'re-bench/secrets').glob('*/cipher')):
  try:
   lic_text=(sec/'runtime.licence').read_text().strip();raw_secrets.append(('runtime.licence',lic_text))
   lic=json.loads(lic_text);payload=lic.get('payload') or {}
   for k in ('key_material','hwid','nonce'):
    v=payload.get(k)
    if isinstance(v,str) and v:raw_secrets.append((f'licence-{k}',v))
   sig=lic.get('sig')
   if isinstance(sig,str) and sig:raw_secrets.append(('licence-sig',sig))
  except Exception:pass
  try:
   shard=(sec/'nx_seal_shard.hex').read_text().strip()
   if shard:raw_secrets.append(('nx_seal_shard',shard))
  except Exception:pass
  try:
   honey=(sec/'honey.secret.hex').read_text().strip()
   if honey:raw_secrets.append(('nx_honey_secret',honey))
  except Exception:pass
 for val,label in rbc.collect_license_derived_secrets():
  if val and label in {'licence-customer-mask','licence-effective-native-key','licence-operator-mask','licence-effective-native-key-operator'}:
   raw_secrets.append((label,val))
 # The scanner must audit the same host/provider credential values that the
 # redactor handles. Earlier exact-only scans did not independently verify these
 # environment values or their JSON/base64/hex representations.
 for name,value in rbc.collect_env_secrets():
  raw_secrets.append(('env-'+name,value))
 for label,value in rbc.collect_opencode_config_secrets():
  raw_secrets.append((label,value))

 expanded=[]
 for label,value in raw_secrets:
  for representation,_rep_label in rbc.expand_secret_representations(value,label):
   expanded.append((label,representation))
 rx,mapping=rbc.compile_secret_matcher(expanded)
 representation_count=len(mapping)

 hits=[];files=0;bytes_scanned=0;content_cache={};cache_hits=0
 scan_roots=[root for root in (RAW,LIVE,STATE,*EXTRA_EVIDENCE_ROOTS) if root.exists()]
 candidates=set()
 prefilter='ripgrep-fixed-strings'
 for scan_root in scan_roots:
  root_candidates=rbc.secret_candidate_files(scan_root,expanded)
  if root_candidates is None:
   candidates=None;prefilter='in-process-regex-all-files';break
  candidates.update(root_candidates)
 else:
  if not scan_roots:
   candidates=set()
 for scan_root in scan_roots:
  for p in scan_root.rglob('*'):
   if not p.is_file():continue
   try:
    size=p.stat().st_size
    if size>80*1024*1024:continue
   except Exception:continue
   files+=1;bytes_scanned+=size
   if candidates is not None:
    try:rp=str(p.resolve())
    except Exception:rp=str(p)
    if rp not in candidates:
     continue
   try:
    data=p.read_bytes()
   except Exception:continue
   # Hundreds of workspaces contain byte-identical copies of the two fixed
   # artifacts. Scan unique content once while still reporting every matching
   # path; this preserves evidence coverage without repeatedly running the
   # representation regex over duplicate bytes.
   digest=hashlib.sha256(data).hexdigest()
   if digest in content_cache:
    labels=content_cache[digest];cache_hits+=1
   else:
    labels=[]
    if rx is not None:
     try:labels=sorted(set(mapping.get(m,'unknown') for m in rx.findall(data)))
     except Exception:labels=[]
    content_cache[digest]=labels
   if labels:hits.append({'path':str(p),'labels':labels,'sha256':digest})
 def classify(path):
  name=path.rsplit('/',1)[-1]
  artifact_names={'artifact.py','artifact_tampered.py','absolute-tampered.py','absolute-native-only-tampered.py'}
  if name in artifact_names or name.endswith('_protected.py') or name.endswith('_protected_dbg.py'):
   return 'artifact-or-tampered-artifact-copy'
  if name in {'opencode.events.jsonl','opencode.stderr.txt','opencode.log','opencode.db'} or '/.local/share/opencode/' in path:
   return 'benchmark-opencode-state-evidence'
  if name.endswith('.licence') or '/runtime/' in path or '/secrets/' in path:
   return 'runtime-licence-fixture-metadata'
  if name=='build_command.json':
   return 'build-command-metadata'
  if 'manifest' in name.lower():
   return 'build-manifest-metadata'
  return 'other-nonartifact-evidence'
 categories={}
 for h in hits:
  cat=classify(h['path']);h['category']=cat;categories[cat]=categories.get(cat,0)+1
 def sensitive_hit(hit):
  for label in hit['labels']:
   if label=='licence-hwid':
    continue
   # The preserved forged-licence fixtures intentionally reuse the valid
   # signature while changing key_material and nonce. They are negative-test
   # inputs, cannot authorise execution by themselves, and signatures are not
   # key material; retain them as evidence but do not count that expected
   # fixture category as a credential leak. Any licence signature outside this
   # fixture category remains sensitive.
   if label=='licence-sig' and hit.get('category')=='runtime-licence-fixture-metadata':
    continue
   return True
  return False
 signature_fixture_files=sum(1 for h in hits if 'licence-sig' in h['labels'] and h.get('category')=='runtime-licence-fixture-metadata')
 credential_hits=sum(1 for h in hits if sensitive_hit(h))
 summary={'scan_roots':[str(x) for x in scan_roots],'files_scanned':files,'prefilter':prefilter,'bytes_scanned':bytes_scanned,'unique_content_scanned':len(content_cache),'duplicate_content_cache_hits':cache_hits,'exact_match_files':len(hits),'secret_representation_match_files':len(hits),'secret_representations_scanned':representation_count,'hit_category_counts':categories,'expected_signature_fixture_files':signature_fixture_files,'credential_hits':credential_hits,'hits':hits,'interpretation':'licence-hwid may appear inside artifact copies and derived agent evidence because host-binding metadata is embedded by design; it is not a licence key, shard, signing secret, or credential. The two runtime forged-licence fixtures intentionally contain the invalid test token signature while their key_material and nonce differ from the valid licence; signatures are public verification artifacts, not key material, and those fixtures cannot authorise execution alone. No exact or common JSON/base64/hex representation of key_material/nonce/full-licence/seal-shard/honey-secret/customer-mask/effective-native-key/provider-or-host credential values should appear outside transient pre-redaction processing. hit_category_counts explains where otherwise expected licence-hwid strings remain. The scan inventory includes current host environment credentials and literal credential-like values still detectable in copied OpenCode configs; values already redacted before a scan cannot be re-derived by that scan, so AM-031 post-redaction assurance also relies on the same-process broad redaction report and the structural config-field audit.'}
 (RAW/'secret_redaction_scan.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps({'files_scanned':files,'unique_content_scanned':len(content_cache),'exact_match_files':len(hits),'secret_representation_match_files':len(hits),'secret_representations_scanned':representation_count,'expected_signature_fixture_files':signature_fixture_files,'credential_hits':credential_hits}))
if __name__=='__main__':main()
