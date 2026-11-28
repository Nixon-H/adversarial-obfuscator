#!/usr/bin/env python3
"""Classify profile-matrix results into validated exploit evidence vs controls.

The classifier is deliberately conservative: prose recognition is not an exploit.
A critical finding requires machine-checked recovery or independently passing
solution evidence. Source-assisted disclosure of the deliberately hard-coded
benchmark secret is a control result, not an obfuscation break.
"""
import argparse, collections, json, os, sys, time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import score_ai_benchmark as scorer

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'

def load(p):
    try:return json.loads(p.read_text())
    except Exception:return None

def result_rows(root):
    rows=[]
    for p in sorted((root/'results').glob('*.json')):
        if '.invalid-' in p.name:continue
        d=load(p)
        if d:rows.append((p,d))
    return rows

def precision_map(root):
    d=load(root/'benchmark_precision_analysis.json') or {}
    return {(x.get('variant'),x.get('scenario'),x.get('model'),x.get('attempt')):x for x in d.get('attempts',[])}

def classify(d,prec):
    val=d.get('validation') or {}
    scenario=d.get('scenario') or ''
    source_control=scenario.startswith('source-assisted')
    critical=[]
    if prec.get('payload_elf_recovered_in_workspace'):
        critical.append('payload-elf-recovered-excluding-supplied-evidence')
    if prec.get('licence_effective_native_key_printed'):
        critical.append('licence-derived-effective-key-disclosed')
    if prec.get('correct_artifact_public_base_key_recovered'):
        critical.append('artifact-public-native-base-key-recovered')
    if prec.get('independent_solution_all_passed'):
        critical.append('independent-hidden-vector-solution-passed')
    if val.get('secret_recovered') or prec.get('secret_recovered'):
        if source_control:
            critical.append('expected-source-control-secret-disclosure')
        else:
            critical.append('exact-benchmark-secret-recovered-without-source')
    exploitable=[x for x in critical if x!='expected-source-control-secret-disclosure']
    return {
        'source_control':source_control,
        'critical_markers':critical,
        'validated_exploitable_markers':exploitable,
        'artifact_identity_matches_final':prec.get('artifact_identity_matches_final'),
        'secret_recovered':bool(val.get('secret_recovered') or prec.get('secret_recovered')),
        'solution_all_passed':bool((val.get('independent_solution_validation') or {}).get('all_passed') or prec.get('independent_solution_all_passed')),
    }

def analyze_root(root):
    rows=[]
    pm=precision_map(root)
    counts=collections.Counter();groups=collections.Counter()
    for p,d in result_rows(root):
        key=(d.get('variant'),d.get('scenario'),d.get('model'),d.get('attempt'))
        c=classify(d,pm.get(key) or {})
        try:
            valid=bool(scorer.score_result(d).get('structurally_valid'))
        except Exception:
            valid=False
        row={'variant':d.get('variant'),'scenario':d.get('scenario'),'model':d.get('model'),'attempt':d.get('attempt'),'valid':valid,'result_file':str(p.relative_to(ROOT)),**c}
        rows.append(row)
        groups[(d.get('variant'),d.get('scenario'),d.get('model'))]+=int(valid)
        if valid:
            counts['valid']+=1
            if row['validated_exploitable_markers']:counts['valid_with_exploitable_markers']+=1
            if row['critical_markers']==['expected-source-control-secret-disclosure']:counts['expected_source_control_only']+=1
        else:counts['invalid_or_unscored']+=1
    return {'root':str(root.relative_to(ROOT)),'counts':dict(counts),'valid_group_counts':{'|'.join(map(str,k)):v for k,v in sorted(groups.items())},'rows':rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--matrix-ids',default='v10,cloud-v11')
    ap.add_argument('--out',default=str(RAW/'profile_matrix_findings.json'))
    args=ap.parse_args()
    roots=[]
    for mid in args.matrix_ids.split(','):
        root=RAW/('ai_benchmark_profile_matrix_'+mid)
        if root.exists():roots.append(analyze_root(root))
    out={'generated':time.time(),'roots':roots,'interpretation':'validated_exploitable_markers are machine-checked recovery facts; prose-only reconstruction and expected source-control disclosure are not counted as product exploits'}
    total=sum((r.get('counts') or {}).get('valid',0) for r in roots)
    exploit=sum((r.get('counts') or {}).get('valid_with_exploitable_markers',0) for r in roots)
    out['summary']={'valid_records':total,'valid_records_with_exploitable_markers':exploit}
    Path(args.out).write_text(json.dumps(out,indent=2))
    print(json.dumps({'out':args.out,**out['summary']},indent=2))
if __name__=='__main__':main()
