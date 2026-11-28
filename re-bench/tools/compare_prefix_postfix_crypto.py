#!/usr/bin/env python3
"""Compare targeted pre-fix and post-fix crypto/extraction benchmark evidence.

The scorer supplies rubric totals. This comparator adds an independent raw-workspace
payload-extraction detector: an ELF file is counted as a recovered protected native
payload only when it contains both payload-specific dynamic-symbol strings. That is
not proof of byte-exact recovery by itself, so hashes/sizes are preserved for manual
verification. Invalid attempts are reported separately; extraction in an invalid
attempt is still security-relevant evidence even though it is not scored.
"""
import base64, hashlib, json, re, statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
POST=RAW/'ai_benchmark'
PRE=RAW/'ai_benchmark_prefix_xor_comparison'
OUTJSON=RAW/'prefix_postfix_crypto_comparison.json'
OUTMD=RAW/'prefix_postfix_crypto_comparison.md'
SCENARIOS=['native-module-extraction','crypto-construction']


def model_safe(model):
    return str(model or '').replace('/','_').replace(':','_')


def load_json(p):
    try:return json.loads(p.read_text())
    except Exception:return None


def flatten(x):
    if isinstance(x,dict):return '\n'.join(flatten(k)+'\n'+flatten(v) for k,v in x.items())
    if isinstance(x,(list,tuple)):return '\n'.join(flatten(v) for v in x)
    return str(x)


def copied_ws(outroot,d):
    return outroot/'workspaces'/d['variant']/d['scenario']/model_safe(d.get('model'))/f"attempt{d['attempt']}"


def _payload_hit(ws, p, data, encoding):
    rec={'path':str(p.relative_to(ws)),'size':len(data),'encoding':encoding}
    try:
        rec['sha256']=hashlib.sha256(data).hexdigest()
    except Exception:
        pass
    if b'PyInit_payload' in data and b'nx_apply_protections' in data:
        rec['payload_marker_strings']=['PyInit_payload','nx_apply_protections']
        return rec, True
    return rec, False


def scan_payload_elfs(ws):
    hits=[]; elfs=[]
    if not ws.exists():return {'payload_elf_hits':[],'other_elf_files':[]}
    for p in sorted(ws.rglob('*')):
        if not p.is_file() or p.name=='artifact.py':
            continue
        try:
            data=p.read_bytes()
        except Exception:
            continue
        candidates=[]
        if data.startswith(b'\x7fELF'):
            candidates.append((data,'raw-file'))
        if p.suffix == '.py':
            try:
                text=data.decode('ascii',errors='ignore')
            except Exception:
                text=''
            for lit in re.findall(r'(?<![A-Za-z0-9+/=])([A-Za-z0-9+/=]{200,})(?![A-Za-z0-9+/=])', text):
                if len(lit) > 2_000_000:
                    continue
                try:
                    dec=base64.b64decode(lit + '='*((4-len(lit)%4)%4), validate=True)
                except Exception:
                    continue
                if dec.startswith(b'\x7fELF'):
                    candidates.append((dec,'python-base64-string'))
                    break
        for dec,encoding in candidates:
            rec,is_hit=_payload_hit(ws,p,dec,encoding)
            elfs.append(rec)
            if is_hit:
                hits.append(dict(rec))
    hit_keys={(x.get('path'),x.get('encoding'),x.get('size')) for x in hits}
    return {'payload_elf_hits':hits,'other_elf_files':[x for x in elfs if (x.get('path'),x.get('encoding'),x.get('size')) not in hit_keys]}


def result_rows(outroot):
    rows=[]
    rdir=outroot/'results'
    if not rdir.exists():return rows
    for p in sorted(rdir.glob('*.json')):
        d=load_json(p)
        if not d or d.get('scenario') not in SCENARIOS:continue
        ws=copied_ws(outroot,d)
        scan=scan_payload_elfs(ws)
        ans=load_json(ws/'answer.json') if ws.exists() else None
        text=flatten(ans or {}).lower()
        rows.append({
            'variant':d.get('variant'),'scenario':d.get('scenario'),'model':d.get('model'),'attempt':d.get('attempt'),
            'artifact_sha256':d.get('artifact_sha256'),'artifact_size':d.get('artifact_size'),
            'returncode':d.get('returncode'),'timeout':d.get('timeout'),
            'workspace':str(ws.relative_to(ROOT)) if ws.exists() else None,
            'payload_elf_hit_count':len(scan['payload_elf_hits']),
            'payload_elf_hits':scan['payload_elf_hits'],
            'other_elf_count':len(scan['other_elf_files']),
            'mentions_repeating_xor':bool(re.search(r'repeating.{0,20}xor|xor.{0,20}repeat',text)),
            'mentions_nxs1':'nxs1' in text,
            'mentions_counter_mode':bool(re.search(r'counter.{0,30}sha256|sha256.{0,30}counter',text)),
            'mentions_customer_mask':bool(re.search(r'customer.{0,30}mask|key_material',text)),
            'result_file':str(p.relative_to(ROOT)),
        })
    return rows


def scored_index(outroot):
    s=load_json(outroot/'score_summary.json') or {}
    idx={}
    for r in s.get('attempts',[]):
        idx[(r.get('variant'),r.get('scenario'),r.get('model'),r.get('attempt'))]=r
    return idx


def aggregate(rows,scoreidx):
    groups={}
    for r in rows:
        key=(r['variant'],r['scenario'],r.get('model'))
        g=groups.setdefault(key,{'attempts':0,'valid_scored':0,'scores':[],'payload_elf_attempts':0,'payload_elf_hits':0,'timeouts':0,'mentions_repeating_xor':0,'mentions_nxs1':0})
        g['attempts']+=1
        sr=scoreidx.get((r['variant'],r['scenario'],r.get('model'),r['attempt']))
        if sr and sr.get('structurally_valid'):
            g['valid_scored']+=1;g['scores'].append(sr.get('total'))
        if r['payload_elf_hit_count']:
            g['payload_elf_attempts']+=1;g['payload_elf_hits']+=r['payload_elf_hit_count']
        if r['timeout']:g['timeouts']+=1
        g['mentions_repeating_xor']+=int(r['mentions_repeating_xor'])
        g['mentions_nxs1']+=int(r['mentions_nxs1'])
    for g in groups.values():
        vals=[x for x in g['scores'] if isinstance(x,(int,float))]
        g['mean_score']=statistics.mean(vals) if vals else None
        g['median_score']=statistics.median(vals) if vals else None
        g['max_score']=max(vals) if vals else None
    return groups


def main():
    pre_rows=result_rows(PRE);post_rows=result_rows(POST)
    pre_idx=scored_index(PRE);post_idx=scored_index(POST)
    pre_groups=aggregate(pre_rows,pre_idx);post_groups=aggregate(post_rows,post_idx)
    artifacts={'pre_fix':{},'post_fix':{}}
    for label,rows in [('pre_fix',pre_rows),('post_fix',post_rows)]:
        for r in rows:
            artifacts[label].setdefault(r['variant'],{'sha256':r['artifact_sha256'],'size':r['artifact_size']})
    # Exact mechanical validation covers the preserved pre-fix artifacts and the
    # final post-fix artifacts even when the AI pre-fix lane is blocked. It uses
    # artifact bytes only and no runtime secrets.
    exact_validation=load_json(RAW/'crypto_validation'/'prefix_postfix_exact_artifact_known_plaintext.json')
    out={'pre_fix_rows':pre_rows,'post_fix_rows':post_rows,'pre_fix_groups':{'|'.join(str(x) for x in k):v for k,v in pre_groups.items()},'post_fix_groups':{'|'.join(str(x) for x in k):v for k,v in post_groups.items()},'artifacts':artifacts,'mechanical_exact_artifact_validation':exact_validation,'interpretation_note':'payload ELF hits are raw-workspace evidence, not rubric points; invalid attempts are excluded from means but retained for security impact'}
    OUTJSON.write_text(json.dumps(out,indent=2))
    lines=['# Targeted pre-fix versus post-fix crypto/extraction comparison','']
    lines.append('This comparison covers only the confirmed native-blob packing weakness scenarios: `native-module-extraction` and `crypto-construction`. It is not a full second 160-job matrix. Payload-ELF hits are independent raw-workspace evidence; invalid attempts are not included in score means but remain security-relevant.')
    if not pre_rows:
        lines.append('')
        lines.append('**Pre-fix AI comparison status:** blocked or incomplete. Zero pre-fix rows for a lane means that lane did not produce usable pre-fix evidence; it does not mean the pre-fix artifacts resisted attack. The mechanical artifact-only validation remains the causal crypto evidence.')
    lines.append('')
    lines.append('| variant | scenario | model | pre valid/total | pre payload-ELF attempts | post valid/total | post payload-ELF attempts | pre mean | post mean |')
    lines.append('|---|---|---|---:|---:|---:|---:|---:|---:|')
    for key in sorted(set(pre_groups)|set(post_groups)):
        pre=pre_groups.get(key,{});post=post_groups.get(key,{})
        fmt=lambda x:'n/a' if x is None else f'{x:.2f}'
        lines.append(f"| `{key[0]}` | `{key[1]}` | `{key[2]}` | {pre.get('valid_scored',0)}/{pre.get('attempts',0)} | {pre.get('payload_elf_attempts',0)} | {post.get('valid_scored',0)}/{post.get('attempts',0)} | {post.get('payload_elf_attempts',0)} | {fmt(pre.get('mean_score'))} | {fmt(post.get('mean_score'))} |")
    lines.append('')
    lines.append('Artifact identities are recorded in the JSON sidecar. The pre-fix artifacts are not build-identical to the post-fix artifacts because the post-fix builds also include strict dependency locking and corrected native lowering; consequently AI comparison measures product evolution plus the crypto fix. The isolated causal crypto evidence is the artifact-only mechanical validation in `crypto_validation/prefix_postfix_exact_artifact_known_plaintext.json`: it recovered valid marker-bearing pre-fix ELFs for both variants without runtime secrets, while the same attack did not recover the final post-fix plaintexts. Older supporting validation remains in `native_final_lowering/old_attack_validation.json`.')
    OUTMD.write_text('\n'.join(lines)+'\n')
    print(json.dumps({'pre_rows':len(pre_rows),'post_rows':len(post_rows),'json':str(OUTJSON),'markdown':str(OUTMD)}))
if __name__=='__main__':main()
