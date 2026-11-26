#!/usr/bin/env python3
"""Exact-match redaction of host/provider credential environment values from benchmark evidence.

Never prints secret values. Writes machine-readable counts and file paths only.
"""
import ast, base64, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AI=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark'
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
 Path('/home/nixon/absmax-ai-workspaces-deepseek-smoke-v1'),
 Path('/home/nixon/absmax-ai-workspaces-deepseek-smoke-v2'),
 Path('/home/nixon/absmax-ai-workspaces-deepseek-smoke-v3'),
 Path('/home/nixon/absmax-ai-workspaces-deepseek-smoke-v4'),
 Path('/home/nixon/absmax-opencode-state-deepseek-smoke-v1'),
 Path('/home/nixon/absmax-opencode-state-deepseek-smoke-v2'),
 Path('/home/nixon/absmax-opencode-state-deepseek-smoke-v3'),
 Path('/home/nixon/absmax-opencode-state-deepseek-smoke-v4'),
 Path('/home/nixon/absmax-ai-workspaces-profile-matrix-deepseek-local-v12'),
 Path('/home/nixon/absmax-opencode-state-profile-matrix-deepseek-local-v12'),
 Path('/home/nixon/absmax-ai-workspaces-profile-matrix-deepseek-cloud-v13'),
 Path('/home/nixon/absmax-opencode-state-profile-matrix-deepseek-cloud-v13'),
]
SENSITIVE_NAME_PARTS=('API_KEY','AUTH_TOKEN','ACCESS_TOKEN','SECRET','PASSWORD','CREDENTIAL','PRIVATE_KEY')
EXTRA_NAMES={'TOKENHARBOR_API_KEY','OPENCODE_API_KEY','ANTHROPIC_AUTH_TOKEN','BRIDGE_AUTH_TOKEN','SCRAPLING_MCP_AUTH_TOKEN','COPILOT_PROVIDER_API_KEY','SSH_AUTH_SOCK'}


def expand_secret_representations(value, label):
    """Return exact secret representations likely to appear in JSONL/tool output.

    Raw multiline licence files do not appear byte-for-byte inside JSON event
    payloads: newlines and quotes are JSON-escaped. Redacting only the raw file
    therefore leaves a partial licence in evidence or provider-bound traffic.
    This helper expands exact literal, JSON-escaped, hexadecimal, and base64
    representations without ever printing the underlying value.
    """
    if not isinstance(value,str) or len(value)<8:
        return []
    out=[(value,label)]
    try:
        js=json.dumps(value)
        # The escaped inner form is sufficient for JSON strings and preserves
        # the surrounding quotes/structure when redacted.
        out.append((js[1:-1],label+'-json-escaped'))
    except Exception:
        pass
    try:
        b=value.encode()
        out.extend([(base64.b64encode(b).decode(),label+'-base64'),(b.hex(),label+'-hex-encoded'),(b.hex().upper(),label+'-hex-encoded')])
    except Exception:
        pass
    v=value.strip()
    if len(v)>=16 and len(v)%2==0 and all(c in '0123456789abcdefABCDEF' for c in v):
        out.append((v.lower(),label+'-hex-lower'))
        out.append((v.upper(),label+'-hex-upper'))
        try:
            raw=bytes.fromhex(v)
            out.append((base64.b64encode(raw).decode(),label+'-hex-base64'))
        except Exception:
            pass
    uniq=[];seen=set()
    for val,lab in sorted(out,key=lambda x:len(x[0]),reverse=True):
        if val and val not in seen:
            seen.add(val);uniq.append((val,lab))
    return uniq


def collect_env_secrets():
    out=[]
    for k,v in os.environ.items():
        if not isinstance(v,str) or len(v)<8:
            continue
        if k in EXTRA_NAMES or any(x in k.upper() for x in SENSITIVE_NAME_PARTS):
            # Exclude values that are obviously ordinary public paths unless the
            # variable name itself is an explicit auth/token/key variable.
            out.append((k,v))
    return sorted(set(out))


def collect_opencode_config_secrets(config_paths=None):
    """Collect literal credential-like values from copied OpenCode configs.

    Exact environment matching alone misses stale provider keys that are no
    longer present in the operator's shell. Copied benchmark OpenCode configs
    are evidence, not active operator configuration, so literal apiKey/token /
    org-id fields must be redacted structurally. Environment-variable
    expressions are references rather than secrets and are preserved.
    """
    if config_paths is None:
        config_paths=[Path('/home/nixon/absmax-opencode-home/.config/opencode/opencode.json')]
    sensitive_names={'apikey','api_key','authorization','auth_token','auth-token','access_token','access-token','token','secret','password','x-opencode-org-id'}
    out=[]
    def env_expression(value):
        return bool(re.fullmatch(r'\{env:[A-Z0-9_]+\}|\$\{[A-Z0-9_]+\}|\$[A-Z0-9_]+',value))
    def walk(obj,path=''):
        if isinstance(obj,dict):
            for key,val in obj.items():
                child=f'{path}.{key}' if path else str(key)
                if isinstance(val,str) and str(key).lower() in sensitive_names:
                    if len(val)>=8 and not val.startswith('<redacted-') and not env_expression(val):
                        label='opencode-config-'+(child.replace(' ','_')[-90:] or 'value')
                        out.append((label,val))
                walk(val,child)
        elif isinstance(obj,list):
            for idx,val in enumerate(obj):
                walk(val,f'{path}[{idx}]')
    for cp in config_paths:
        try:
            data=json.loads(Path(cp).read_text())
        except Exception:
            continue
        walk(data)
    return sorted(set(out),key=lambda x:len(x[0]),reverse=True)


def collect_license_derived_secrets():
    """Collect exact licence-derived native-key material without logging values.

    Returns (value, label) pairs. Artifact-public XOR shares are deliberately not
    included; only licence values, customer masks, and effective keys are redacted.
    """
    out=[]
    builds=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds'
    # Cloud-final4 secrets belong to the validated replacement artifacts in the
    # additive cloud-final4 subdirectory, not to the older degraded cloud
    # artifacts at the authoritative base path. Include both root/artifact
    # pairings explicitly so provider-bound redaction covers every matrix lane.
    secret_root_configs=[
        (ROOT/'re-bench/secrets',''),
        (Path('/home/nixon/absmax-scratch/cloud-final4-secrets'),'cloud-final4'),
    ]
    for root,artifact_subdir in secret_root_configs:
      for sec in sorted(root.glob('*/cipher')):
        variant=sec.parent.name
        try:
            lic_text=(sec/'runtime.licence').read_text().strip()
            out.append((lic_text,'licence-runtime-token'))
            lic=json.loads(lic_text); payload=lic.get('payload') or {}
            km=payload.get('key_material')
            for key in ('key_material','nonce','hwid'):
                val=payload.get(key)
                if isinstance(val,str) and val:
                    out.append((val,f'licence-{key}'))
            sig=lic.get('sig')
            if isinstance(sig,str) and sig:
                out.append((sig,'licence-sig'))
        except Exception:
            km=None
        try:
            shard=(sec/'nx_seal_shard.hex').read_text().strip()
            if shard: out.append((shard,'nx-seal-shard'))
        except Exception:
            pass
        try:
            honey=(sec/'honey.secret.hex').read_text().strip()
            if honey: out.append((honey,'nx-honey-secret'))
        except Exception:
            pass
        try:
            artifact=(builds/variant/'cipher'/artifact_subdir/'artifact.py') if artifact_subdir else (builds/variant/'cipher/artifact.py')
            tree=ast.parse(artifact.read_text(encoding='utf-8',errors='surrogateescape'))
            lit={}
            for node in tree.body:
                if isinstance(node,ast.Assign):
                    for tgt in node.targets:
                        if isinstance(tgt,ast.Name):
                            try: lit[tgt.id]=ast.literal_eval(node.value)
                            except Exception: pass
            s0=base64.b64decode(lit['_BLOB_S0']); s1=base64.b64decode(lit['_BLOB_S1'])
            raw=bytes(a^b for a,b in zip(s0,s1))
            bm=hashlib.sha256(str(lit['_NX_BUILD_ID']).encode()).digest()
            basekey=bytes(b^bm[i%len(bm)] for i,b in enumerate(raw))
            cm=hashlib.sha256(b'nx-customer:'+str(km).encode()).digest()
            eff=bytes(b^cm[i%len(cm)] for i,b in enumerate(basekey))
            derived_pairs=[('licence-customer-mask',cm),('licence-effective-native-key',eff)]
            # Operator-bound builds apply a second mask over the customer-masked
            # key. The benchmark deliberately supplies NX_SEAL_SHARD in
            # legitimate-secrets workspaces, so the fully composed key is
            # licence-derived sensitive material even though each input is
            # intentionally attacker-available in that scenario.
            try:
                seal=(sec/'nx_seal_shard.hex').read_text().strip().encode()
            except Exception:
                seal=b''
            table=(os.environ.get('NX_TABLE_SHARD','') or '').encode()
            if seal or table:
                material=(b'nx-operator-blob:'+str(len(seal)).encode('ascii')+b':'+seal+b'|'+str(len(table)).encode('ascii')+b':'+table)
                om=hashlib.sha256(material).digest()
                effop=bytes(b^om[i%len(om)] for i,b in enumerate(eff))
                derived_pairs.extend([('licence-operator-mask',om),('licence-effective-native-key-operator',effop)])
            for label,val in derived_pairs:
                out.extend([(val.hex(),label),(val.hex().upper(),label),(base64.b64encode(val).decode(),label)])
        except Exception:
            pass
    return sorted(set(out),key=lambda x:len(x[0]),reverse=True)


def secret_candidate_files(root, secrets):
    """Return files containing any fixed secret representation, using ripgrep.

    Secret values are supplied on stdin and never written to a pattern file or
    printed. `-l` emits only file paths. If ripgrep is unavailable or rejects a
    pattern, callers fall back to the slower in-process scanner.
    """
    if shutil.which('rg') is None:
        return None
    vals=[];seen=set()
    for _label,val in secrets:
        if not isinstance(val,str) or len(val)<8:
            continue
        candidate=val
        if '\n' in val or '\r' in val:
            # ripgrep's default fixed-string prefilter is line-oriented and
            # cannot match a multiline private key/licence value as one pattern.
            # Use its longest line as a coarse prefilter; the compiled bytes
            # regex still requires the complete multiline value before any
            # replacement or hit is recorded.
            lines=[x for x in re.split(r'[\r\n]+',val) if x]
            candidate=max(lines,key=len) if lines else ''
        if len(candidate)<8:
            continue
        if candidate not in seen:
            seen.add(candidate);vals.append(candidate)
    if not vals:
        return set()
    try:
        cp=subprocess.run(['rg','--hidden','--no-ignore','--text','--fixed-strings','-l','-f','-',str(root)],input='\n'.join(vals)+'\n',text=True,capture_output=True,timeout=180)
    except Exception:
        return None
    if cp.returncode not in (0,1):
        return None
    try:
        root_resolved=str(root.resolve())
    except Exception:
        root_resolved=str(root)
    out=set()
    for line in cp.stdout.splitlines():
        if not line:continue
        # rg preserves the root path form supplied on the command line. Resolve
        # relative output against the current working directory when necessary.
        pp=Path(line)
        if not pp.is_absolute(): pp=(Path.cwd()/pp)
        try: out.add(str(pp.resolve()))
        except Exception: out.add(str(pp))
    return out


def compile_secret_matcher(secrets):
    """Compile a bytes regex for exact secret presence.

    Naively testing every expanded representation against hundreds of megabytes
    of event logs is quadratic and too slow for post-processing. One compiled
    alternation scans each file in C; only representations observed in that file
    are then replaced with exact bytes replacements.
    """
    mapping={}
    for label,val in secrets:
        if not isinstance(val,str) or len(val)<8:
            continue
        try:b=val.encode()
        except Exception:continue
        # Keep the first/longest label for duplicate representations.
        mapping.setdefault(b,label)
    patterns=sorted(mapping,key=len,reverse=True)
    if not patterns:
        return None,{}
    rx=re.compile(b'|'.join(re.escape(x) for x in patterns))
    return rx,mapping


def redact_tree(root, secrets, skip_labels=frozenset()):
    stats={'root':str(root),'files_scanned':0,'files_changed':0,'replacements':{},'changed_files':[],'skipped_labels':sorted(skip_labels)}
    if not root.exists(): return stats
    rx,mapping=compile_secret_matcher(secrets)
    if rx is None:return stats
    candidates=secret_candidate_files(root,secrets)
    stats['candidate_files']=None if candidates is None else len(candidates)
    stats['prefilter']='ripgrep-fixed-strings' if candidates is not None else 'in-process-regex-all-files'
    for p in root.rglob('*'):
        if not p.is_file() or p.name=='artifact.py':
            continue
        try:
            if p.stat().st_size>80*1024*1024: continue
        except Exception:
            continue
        stats['files_scanned']+=1
        if candidates is not None:
            try: rp=str(p.resolve())
            except Exception: rp=str(p)
            if rp not in candidates:
                continue
        try:
            data=p.read_bytes()
        except Exception:
            continue
        stats['files_inspected_for_replacement']=stats.get('files_inspected_for_replacement',0)+1
        try:
            found=sorted(set(rx.findall(data)),key=len,reverse=True)
        except Exception:
            found=[]
        if not found:
            continue
        new=data; labels=[]
        for b in found:
            name=mapping.get(b,'unknown')
            if name in skip_labels:
                stats['skipped_replacements']=stats.get('skipped_replacements',{})
                stats['skipped_replacements'][name]=stats['skipped_replacements'].get(name,0)+new.count(b)
                continue
            count=new.count(b)
            if not count:
                continue
            label=name if name.startswith(('licence-','nx-')) else 'env-'+name
            new=new.replace(b,f'<redacted-{label}>'.encode())
            stats['replacements'][name]=stats['replacements'].get(name,0)+count
            labels.append(name)
        if new!=data:
            try:
                p.write_bytes(new); stats['files_changed']+=1; stats['changed_files'].append({'path':str(p),'variables':sorted(set(labels))})
            except Exception:
                pass
    return stats


def main():
    env_pairs=collect_env_secrets()
    config_pairs=collect_opencode_config_secrets()
    derived=collect_license_derived_secrets()
    # Normalize to (redaction_label, secret_value). Environment labels retain the
    # variable name; licence-derived labels are semantic and never contain values.
    base_secrets=[(k,v) for k,v in env_pairs]+[(label,val) for label,val in config_pairs]+[(label,val) for val,label in derived]
    secrets=[]
    for label,val in base_secrets:
        secrets.extend((label,rep_val) for rep_val,_rep_label in expand_secret_representations(val,label))
    raw_root=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
    matrix_roots=sorted(raw_root.glob('ai_benchmark*')) if raw_root.exists() else []
    roots=[AI,LIVE,STATE,*EXTRA_EVIDENCE_ROOTS]
    roots.extend(x for x in matrix_roots if x not in roots)
    reports=[redact_tree(r,secrets,skip_labels={'licence-hwid'} if r in EXTRA_EVIDENCE_ROOTS else frozenset()) for r in roots]
    report={'secret_variable_names':[k for k,_ in env_pairs],'opencode_config_secret_labels':[k for k,_ in config_pairs],'licence_derived_redaction_labels':sorted(set(label for _,label in derived)),'expanded_secret_representation_count':len(secrets),'redaction':'exact-match environment credential and licence-derived key redaction; artifact.py files skipped to preserve byte-identical evidence','reports':reports}
    dest=AI/'credential_redaction_report.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2))
    print(json.dumps({'variables':len(secrets),'files_changed':sum(r['files_changed'] for r in reports),'files_scanned':sum(r['files_scanned'] for r in reports)},indent=2))

if __name__=='__main__': main()
