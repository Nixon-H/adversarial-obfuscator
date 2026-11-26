#!/usr/bin/env python3
"""Render final machine-scored benchmark results into ABSOLUTE_MAXIMUM_BENCHMARK.md."""
import json, collections, statistics, datetime, os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark'
DOC=ROOT/'re-bench/ABSOLUTE_MAXIMUM_BENCHMARK.md'


def fmt(x):
    if x is None: return 'n/a'
    return f'{x:.2f}' if isinstance(x,float) else str(x)


def main():
    score=json.loads((OUT/'score_summary.json').read_text())
    completion={}
    fp=OUT/'final_completion_report.json'
    if fp.exists(): completion=json.loads(fp.read_text())
    rows=score['attempts']
    groups=collections.defaultdict(list)
    for r in rows:
        groups[(r['variant'],r['scenario'],r['model'])].append(r)
    lines=[]
    lines.append('## Final strict execution results')
    lines.append('')
    lines.append(f"Rendered: `{datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace('+00:00','Z')}` from `score_summary.json`, `final_completion_report.json`, and current resume-status files.")
    lines.append('')
    lines.append(f"* Raw attempt records: **{score['completed_records']}**")
    lines.append(f"* Structurally valid scored attempts: **{score['structurally_valid']}**")
    lines.append(f"* Invalid/unscored attempts: **{score['completed_records']-score['structurally_valid']}**")
    lines.append("* Planned initial matrix: **160 jobs**; supplemental attempts were used only to replace invalid attempts where needed, without overwriting their evidence.")
    if completion:
        lines.append(f"* Supplementation rounds run by the completion orchestrator: **{completion.get('supplementation_rounds',0)}**")
        if completion.get('benchmark_status'):
            lines.append(f"* Benchmark completion status: **{completion.get('benchmark_status')}**")
        if completion.get('status_note'):
            lines.append(f"* Historical initial-campaign status note: {completion.get('status_note')}")
    orch=OUT/'orchestrator'
    if orch.exists():
        status_lines=[]
        for sp in sorted(orch.glob('resume_*_status*.json')):
            try:
                st=json.loads(sp.read_text())
            except Exception:
                continue
            scope='post-fix' if 'post' in sp.name else 'pre-fix comparison'
            status_lines.append(f"{scope} `{sp.name}`: model `{st.get('model')}`, strict-valid {st.get('valid_total')}, groups complete {st.get('groups_complete')}/{st.get('groups_total')}, records {st.get('records_total')}, complete={st.get('complete')}")
        if status_lines:
            lines.append('* Current resume-worker scan (supersedes stale historical completion wording): '+ '; '.join(status_lines)+'.')
        pidfile=orch/'resume_quota_watchdog.pid'
        try:
            pid=int(pidfile.read_text().strip())
            try:
                os.kill(pid,0); alive=True
            except OSError:
                alive=False
            lines.append(f"* Resume watchdog PID `{pid}` alive={alive}; worker log: `ai_benchmark/orchestrator/resume_quota_watchdog.log`.")
        except Exception:
            pass
    authorised_models={
        'kern/inkling-2-mini',
        'tokenharbor/deepseek-v4.1-flash:free',
        'tokenharbor/deepseek-v4.1-flash-1017',
    }
    models=sorted({str(r.get('model')) for r in rows} | authorised_models)
    lines.append('* Model lanes: '+', '.join(f'`{m}`' for m in models)+'. Kern and TokenHarbor lanes are reported separately by model; no lane is complete unless explicitly stated. A lane with zero records is still listed when authorised but quota-blocked before execution.')
    per_model=[]
    for model in models:
        mr=[r for r in rows if str(r.get('model'))==model]
        mv=[r for r in mr if r.get('structurally_valid')]
        per_model.append(f'`{model}` {len(mv)}/{len(mr)} strict valid')
    lines.append('* Strict-validity correction (AM-027): the pre-registered maximum of 20 tool invocations is now enforced. Security-relevant over-limit attempts are preserved as raw evidence but excluded from valid means. Current lane counts: '+ '; '.join(per_model)+'.')
    lines.append('')
    lines.append('These scores measure how much the agents reconstruct under the rubric. They are **not** resistance percentages: invalid attempts are excluded, and a low score does not prove that a different attacker cannot recover more.')
    lines.append('')
    lines.append('### Per-variant/per-scenario results')
    lines.append('')
    lines.append('| variant | scenario | model | valid/total | mean | median | max | variance | secret hits | hidden-vector passes | invalid categories |')
    lines.append('|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|')
    allvals=collections.defaultdict(list)
    for (variant,scenario,model),rs in sorted(groups.items()):
        valid=[r for r in rs if r['structurally_valid']]
        vals=[r['total'] for r in valid]
        cats=collections.Counter(r.get('failure_category','invalid') for r in rs if not r['structurally_valid'])
        secret=sum(1 for r in valid if r.get('secret_recovered'))
        hp=sum(1 for r in valid if r.get('independent_solution_all_passed'))
        if vals:
            mean=statistics.mean(vals); med=statistics.median(vals); mx=max(vals); var=statistics.pvariance(vals) if len(vals)>1 else 0.0
            allvals[(variant,model)].extend(vals)
        else:
            mean=med=mx=var=None
        catstr='none' if not cats else ', '.join(f'{k}:{v}' for k,v in sorted(cats.items()))
        lines.append(f"| `{variant}` | `{scenario}` | `{model}` | {len(valid)}/{len(rs)} | {fmt(mean)} | {fmt(med)} | {fmt(mx)} | {fmt(var)} | {secret} | {hp} | {catstr} |")
    lines.append('')
    lines.append('### Variant-level aggregate over valid scored attempts')
    lines.append('')
    lines.append('| variant | model | valid scored attempts | mean | median | maximum | variance |')
    lines.append('|---|---|---:|---:|---:|---:|---:|')
    for (variant,model),vals in sorted(allvals.items()):
        lines.append(f"| `{variant}` | `{model}` | {len(vals)} | {statistics.mean(vals):.2f} | {statistics.median(vals):.2f} | {max(vals):.2f} | {(statistics.pvariance(vals) if len(vals)>1 else 0.0):.2f} |")
    lines.append('')
    lines.append('### Failure categories across all raw attempts')
    lines.append('')
    cats=collections.Counter(r.get('failure_category','valid') for r in rows)
    lines.append('| category | count | interpretation |')
    lines.append('|---|---:|---|')
    for cat,n in sorted(cats.items()):
        interp={
         'valid':'structurally valid and scored',
         'timeout':'model/tool invocation reached 360-second limit; not resistance evidence',
         'static-scenario-execution-policy-violation':'agent executed the artifact despite a static-only attacker boundary',
         'tool-call-limit-exceeded':'agent exceeded the pre-registered 20-tool-call limit; security-relevant but not a valid scored attempt',
         'provider-quota-exhausted':'TokenHarbor 1017 pass allowance exhausted before model invocation; not resistance evidence',
         'provider-free-usage-limit':'OpenCode Hy4 free usage limit or cooldown reached before/during model invocation; not resistance evidence',
         'harness-bridge-syntax-error':'benchmark harness bridge syntax regression before model invocation; invalid infrastructure record, not resistance evidence',
         'harness-blocked-before-workspace':'fail-closed harness decision before copying secrets or invoking a model; invalid infrastructure record, not resistance evidence',
         'nonzero-missing-malformed-answer-or-isolation':'missing/malformed schema, nonzero/provider interruption, or filesystem isolation violation',
        }.get(cat,'invalid or unscored')
        lines.append(f'| `{cat}` | {n} | {interp} |')
    lines.append('')
    lines.append('### Dimension means over valid scored attempts')
    lines.append('')
    lines.append('These means use the final calibrated scorer. Answer keys themselves are not treated as evidence; only answer values are scored. Payload/crypto recognition is capped unless exact artifact-public key recovery and independently observed plaintext recovery are present.')
    lines.append('')
    lines.append('| variant | model | loader/15 | payload-crypto/15 | provenance-chain/15 | semantics-hidden/25 | dynamic-platform/15 | evidence/10 | unsupported penalty |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|')
    dims=['loader_initialisation','payload_crypto','provenance_rollback_chain','semantic_hidden_vectors','dynamic_platform','evidence_quality','unsupported_claims_penalty']
    for variant,model in sorted({(r['variant'],r['model']) for r in rows}):
        valid=[r for r in rows if r['variant']==variant and r['model']==model and r['structurally_valid']]
        if not valid: continue
        vals=[]
        for dim in dims:
            vals.append(statistics.mean([r['scores'][dim] for r in valid]))
        lines.append(f"| `{variant}` | `{model}` | {vals[0]:.2f} | {vals[1]:.2f} | {vals[2]:.2f} | {vals[3]:.2f} | {vals[4]:.2f} | {vals[5]:.2f} | {vals[6]:.2f} |")
    lines.append('')
    lines.append('### Independent precision checks')
    lines.append('')
    lines.append('These are machine-checked recovery facts, not prose credit. `Correct public base key` means the exact artifact-public Shamir/build-ID-derived key appeared in the answer; it is not the licence-derived effective key. `Plaintext recovery` means a payload ELF with expected markers, exact hidden secret recovery, or a fully passing independent `solution.py` was observed; merely observing the valid output vector is not plaintext recovery.')
    lines.append('')
    lines.append('| variant | scenario | model | valid/total | correct public base key | correct NXS1 nonce | plaintext recovery |')
    lines.append('|---|---|---|---:|---:|---:|---:|')
    for (variant,scenario,model),rs in sorted(groups.items()):
        valid=[r for r in rs if r['structurally_valid']]
        bk=sum(1 for r in valid if r.get('correct_artifact_public_base_key_recovered'))
        nn=sum(1 for r in valid if r.get('correct_nxs1_nonce_reported'))
        pr=sum(1 for r in valid if r.get('payload_plaintext_recovered'))
        lines.append(f"| `{variant}` | `{scenario}` | `{model}` | {len(valid)}/{len(rs)} | {bk} | {nn} | {pr} |")
    lines.append('')
    lines.append('### Dynamic-evidence scoring control')
    lines.append('')
    lines.append('Dynamic-platform credit is not awarded for prose alone. The scorer parses the observable `opencode.events.jsonl` shell log and requires an actual artifact execution/tracing command plus output consistent with either valid sealed execution or fail-closed behaviour. Static-only scenarios are structurally invalid if the agent executes the artifact despite instructions. Static scenarios can still receive limited credit for identifying platform protections statically, subject to the pre-registered cap.')
    lines.append('')
    lines.append('### Semantic recovery outcome')
    lines.append('')
    valid_rows=[r for r in rows if r.get('structurally_valid')]
    secret=sum(1 for r in valid_rows if r.get('secret_recovered'))
    hp=sum(1 for r in valid_rows if r.get('independent_solution_all_passed'))
    bk=sum(1 for r in valid_rows if r.get('correct_artifact_public_base_key_recovered'))
    nn=sum(1 for r in valid_rows if r.get('correct_nxs1_nonce_reported'))
    pr=sum(1 for r in valid_rows if r.get('payload_plaintext_recovered'))
    prec_path=OUT/'benchmark_precision_analysis.json'
    prec=None
    if prec_path.exists():
        try: prec=json.loads(prec_path.read_text())
        except Exception: prec=None
    valid_keyset={(r.get('variant'),r.get('scenario'),r.get('model'),r.get('attempt')) for r in valid_rows}
    valid_prec=[]
    if prec:
        valid_prec=[x for x in prec.get('attempts',[]) if (x.get('variant'),x.get('scenario'),x.get('model'),x.get('attempt')) in valid_keyset]
    elf_excluding_supplied=sum(1 for x in valid_prec if x.get('payload_elf_recovered_in_workspace'))
    raw_elf_including_supplied=sum(1 for x in valid_prec if x.get('raw_payload_elf_hits_including_supplied'))
    lines.append(f'* Exact artifact-public base-key reports in valid attempts: **{bk}/{len(valid_rows)}**. This key is public-structure recovery and is not the licence-derived effective key.')
    lines.append(f'* Correct NXS1 nonce reports in valid attempts: **{nn}/{len(valid_rows)}**.')
    lines.append(f'* Payload plaintext/semantic recovery in valid attempts: **{pr}/{len(valid_rows)}**. This count includes exact secret recovery or a fully passing independent solution; it does not necessarily mean the agent extracted a new payload ELF.')
    lines.append(f'* Payload ELF recovery excluding scenario-supplied native evidence in valid attempts: **{elf_excluding_supplied}/{len(valid_rows)}**.')
    lines.append(f'* Raw payload ELF hits including scenario-supplied evidence in valid attempts: **{raw_elf_including_supplied}/{len(valid_rows)}**.')
    lines.append(f'* Exact `cipher-master-K_77` recovery appearances in valid attempts: **{secret}**.')
    lines.append(f'* Independently passing `solution.py` hidden-vector validations: **{hp}**.')
    lines.append('* Recognition of SHA-256/HMAC/XOR/counter terms is reported separately from recovery of the protected implementation and secret inputs.')
    lines.append('')
    lines.append('### Security-relevant over-limit evidence (unscored)')
    lines.append('')
    prec_path=OUT/'benchmark_precision_analysis.json'
    prec=None
    if prec_path.exists():
        try: prec=json.loads(prec_path.read_text())
        except Exception: prec=None
    over_rows=[r for r in rows if r.get('failure_category')=='tool-call-limit-exceeded']
    if prec and over_rows:
        prec_map={(x.get('variant'),x.get('scenario'),x.get('model'),x.get('attempt')):x for x in prec.get('attempts',[])}
        lines.append('These attempts exceeded the pre-registered 20-tool-call limit and therefore have no valid score. Their machine-checked recovery facts are still security-relevant attacker evidence. `ELF excluding supplied` is zero when the only native objects observed were pre-supplied in legitimate-runtime workspaces.')
        lines.append('')
        lines.append('| model | over-limit attempts | correct public base key | correct NXS1 nonce | raw ELF incl. supplied | ELF excluding supplied | exact secret | output vector | independent solution |')
        lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
        for model in sorted({r['model'] for r in over_rows}):
            mr=[r for r in over_rows if r['model']==model]
            pr=[]
            for r in mr:
                x=prec_map.get((r['variant'],r['scenario'],r['model'],r['attempt']))
                if x: pr.append((r,x))
            def cnt(pred): return sum(1 for _r,x in pr if pred(x))
            lines.append(f"| `{model}` | {len(mr)} | {cnt(lambda x: x.get('correct_artifact_public_base_key_recovered'))} | {cnt(lambda x: x.get('correct_nxs1_nonce_reported'))} | {cnt(lambda x: x.get('raw_payload_elf_hits_including_supplied'))} | {cnt(lambda x: x.get('payload_elf_recovered_in_workspace'))} | {cnt(lambda x: x.get('secret_recovered'))} | {cnt(lambda x: x.get('output_vector_recovered'))} | {cnt(lambda x: x.get('independent_solution_all_passed'))} |")
        lines.append('')
        notable=[]
        for r in over_rows:
            x=prec_map.get((r['variant'],r['scenario'],r['model'],r['attempt']))
            if x and (x.get('secret_recovered') or x.get('independent_solution_all_passed') or x.get('raw_payload_elf_hits_including_supplied')):
                notable.append((r,x))
        if notable:
            lines.append('Notable over-limit rows:')
            lines.append('')
            for r,x in sorted(notable,key=lambda z:(z[0]['model'],z[0]['variant'],z[0]['scenario'],z[0]['attempt'])):
                lines.append(f"* `{r['model']}` `{r['variant']}/{r['scenario']}` attempt {r['attempt']}: tool invocations {r.get('tool_invocations','n/a')}; exact secret `{bool(x.get('secret_recovered'))}`; independent solution all-passed `{bool(x.get('independent_solution_all_passed'))}`; raw ELF hits `{len(x.get('raw_payload_elf_hits_including_supplied') or [])}`; pre-supplied evidence excluded `{bool(x.get('pre_supplied_native_evidence_excluded_from_recovery_credit'))}`.")
            lines.append('')
    lines.append('### Pre-fix versus post-fix comparison')
    lines.append('')
    cmp_path=ROOT/'re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/prefix_postfix_crypto_comparison.json'
    cmp=None
    if cmp_path.exists():
        try: cmp=json.loads(cmp_path.read_text())
        except Exception: cmp=None
    if cmp:
        lines.append('The targeted comparison covers only `native-module-extraction` and `crypto-construction` because those are the scenarios affected by the confirmed repeating-XOR native-blob weakness. It uses separate pre-fix result/workspace roots and is excluded from the authoritative post-fix matrix. Payload-ELF hits are independent raw-workspace evidence; invalid attempts are excluded from means but retained for security impact.')
        lines.append('')
        lines.append('| variant | scenario | model | pre valid/total | pre payload-ELF attempts | post valid/total | post payload-ELF attempts | pre mean | post mean |')
        lines.append('|---|---|---|---:|---:|---:|---:|---:|---:|')
        pre_groups=cmp.get('pre_fix_groups',{}); post_groups=cmp.get('post_fix_groups',{})
        for key in sorted(set(pre_groups)|set(post_groups)):
            if '|' in key:
                variant,scenario,model=key.split('|',2)
            else:
                variant,scenario=key.split('/',1); model='tokenharbor/deepseek-v4.1-flash-1017'
            pre=pre_groups.get(key,{}); post=post_groups.get(key,{})
            def fnum(x): return 'n/a' if x is None else f'{x:.2f}'
            lines.append(f"| `{variant}` | `{scenario}` | `{model}` | {pre.get('valid_scored',0)}/{pre.get('attempts',0)} | {pre.get('payload_elf_attempts',0)} | {post.get('valid_scored',0)}/{post.get('attempts',0)} | {post.get('payload_elf_attempts',0)} | {fnum(pre.get('mean_score'))} | {fnum(post.get('mean_score'))} |")
        lines.append('')
        if not cmp.get('pre_fix_rows'):
            lines.append('**Pre-fix AI comparison status:** blocked before execution by provider quota exhaustion. The zero pre-fix rows are missing evidence, not a successful pre-fix resistance result. The mechanical known-plaintext reproduction remains the isolated causal pre/post crypto evidence.')
            lines.append('')
        lines.append('The pre-fix artifacts are not build-identical to the post-fix artifacts because the post-fix builds also include strict dependency locking and corrected native lowering. The comparison therefore measures product evolution plus the crypto fix. The isolated causal crypto evidence remains the mechanical known-plaintext validation in `native_final_lowering/old_attack_validation.json`. Full machine-readable comparison: `ABSOLUTE_MAXIMUM_RAW_RESULTS/prefix_postfix_crypto_comparison.json` and `.md`.')
    else:
        lines.append('The targeted pre-fix comparison for `native-module-extraction` and `crypto-construction` is pending or still running in the separate `ai_benchmark_prefix_xor_comparison` root. Earlier full campaigns are preserved but invalid/mixed-version and are not statistically comparable. The already-established mechanistic result is that the pre-fix repeating-key XOR artifact-only attack reconstructed the native ELF exactly, while the same procedure against strict post-fix `NXS1` artifacts does not reconstruct the ELF.')
    lines.append('')
    new='\n'.join(lines)+'\n'
    doc=DOC.read_text()
    start_marker='## Current strict execution status' if '## Current strict execution status' in doc else '## Final strict execution results'
    start=doc.index(start_marker)
    end=doc.index('## Independent non-AI validation relevant to interpretation')
    doc=doc[:start]+new+'\n'+doc[end:]
    DOC.write_text(doc)
    (OUT/'final_benchmark_tables.md').write_text(new)
    print(json.dumps({'rendered':True,'records':score['completed_records'],'valid':score['structurally_valid']}))

if __name__=='__main__': main()
