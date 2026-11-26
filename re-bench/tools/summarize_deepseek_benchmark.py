#!/usr/bin/env python3
"""Aggregate OpenCode Go DeepSeek benchmark evidence across complementary roots."""
import json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS'
sys.path.insert(0,str(ROOT/'re-bench/tools'))
import score_ai_benchmark

CORE_SUFFIXES=['_profile_matrix_deepseek-local-v12','_profile_matrix_deepseek-cloud-v13','_profile_matrix_go-v12']
SOURCE_CONTROLS={'source-assisted-runtime-secrets','source-assisted-secrets-withheld','source-assisted-static'}

def iter_rows():
    for suffix in CORE_SUFFIXES:
        root=RAW/('ai_benchmark'+suffix)
        for f in sorted((root/'results').glob('*.json')) if (root/'results').exists() else []:
            try:d=json.loads(f.read_text())
            except Exception:continue
            sc=score_ai_benchmark.score_result(d)
            yield {'root':root.name,'file':str(f.relative_to(ROOT)),'variant':d.get('variant'),'scenario':d.get('scenario'),'model':d.get('model'),'attempt':d.get('attempt'),'result':d,'score':sc}

def main():
    rows=list(iter_rows())
    valid=[r for r in rows if r['score'].get('structurally_valid')]
    invalid=[r for r in rows if not r['score'].get('structurally_valid')]
    markers=[]
    for r in valid:
        sc=r['score'];scenario=r['scenario']
        payload=bool(sc.get('payload_plaintext_recovered'))
        secret=bool(sc.get('secret_recovered'))
        solution=bool(sc.get('independent_solution_all_passed'))
        if not (payload or secret or solution):
            continue
        expected_control=scenario in SOURCE_CONTROLS
        customer_boundary=scenario in {'legitimate-runtime-secrets','source-assisted-runtime-secrets'}
        markers.append({'variant':r['variant'],'scenario':scenario,'root':r['root'],'file':r['file'],'payload_plaintext_recovered':payload,'secret_recovered':secret,'independent_solution_all_passed':solution,'expected_source_control':expected_control,'customer_machine_boundary':customer_boundary,'requires_product_fix':bool(payload and not expected_control and not customer_boundary)})
    combos={(r['variant'],r['scenario']) for r in valid}
    variants=['maximum-packed','maximum-local','absolute','absolute-native-only','maximum-cloud','absolute-cloud']
    scenarios=list(score_ai_benchmark.__dict__.get('SCENARIOS',{})) or []
    # The scorer does not own the scenario registry; derive the canonical count from ai_bench.
    try:
        import ai_bench
        scenarios=list(ai_bench.SCENARIOS)
    except Exception:
        scenarios=sorted({s for v,s in combos})
    planned=[(v,s) for v in variants for s in scenarios]
    covered={(r['variant'],r['scenario']) for r in rows}
    valid_covered=combos
    out={'generated':time.time(),'model':'opencode-go/deepseek-v4.1-flash','roots':['ai_benchmark'+x for x in CORE_SUFFIXES],'records':len(rows),'valid_records':len(valid),'invalid_records':len(invalid),'valid_scenario_variant_pairs':len(valid_covered),'planned_pairs':len(planned),'coverage_ratio':round(len(valid_covered)/len(planned),6) if planned else 0,'markers':markers,'fix_requiring_markers':[m for m in markers if m['requires_product_fix']],'invalid_by_category':{},'scores':[{'variant':r['variant'],'scenario':r['scenario'],'root':r['root'],'total':r['score'].get('total'),'valid':r['score'].get('structurally_valid'),'failure_category':r['score'].get('failure_category'),'secret_recovered':r['score'].get('secret_recovered'),'independent_solution_all_passed':r['score'].get('independent_solution_all_passed'),'payload_plaintext_recovered':r['score'].get('payload_plaintext_recovered')} for r in rows]}
    for r in invalid:
        cat=r['score'].get('failure_category') or 'unknown';out['invalid_by_category'][cat]=out['invalid_by_category'].get(cat,0)+1
    path=RAW/'deepseek_benchmark_aggregate.json'
    path.write_text(json.dumps(out,indent=2))
    print(json.dumps({k:out[k] for k in ['records','valid_records','invalid_records','valid_scenario_variant_pairs','planned_pairs','coverage_ratio']},indent=2))
    print('output',path)
if __name__=='__main__':main()
