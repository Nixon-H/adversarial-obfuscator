# Statistical repeat-campaign analysis — profile-matrix-go-v12

Scored with `re-bench/tools/score_ai_benchmark.py` (authoritative harness scorer,
`ABSMAX_BENCHMARK_SUFFIX=_profile_matrix_go-v12`) on 2026-11-28. Machine-readable
source: `score_summary.json` in this directory.

## Campaign shape

- Matrix: 6 variants x 15 scenarios x up to 3 attempts; runner completed all
  126 planned jobs (`profile-matrix-go-v12-status.json`: `complete: true`).
- Records: **174**, structurally valid: **156 (89.7%)** after re-scoring with
  the corrected gate (audit D2 fix, 2026-11-28: the original gate admitted
  provider-error/retry/harness-error records that produced schema-valid
  answers; 15 records were correctly reclassified invalid — they are harness
  noise, not resistance evidence).
- Model lane: `opencode-go/deepseek-v4.1-flash`. NOTE: this lane is not one of
  the three lanes listed in AGENTS.md (`opencode/hy4-flash-free`,
  `tokenharbor/deepseek-v4.1-flash:free`, fallback `...-1017`); it is the same
  model family through a different provider route. Recorded for transparency.

## Headline result

Across **151 valid trials in non-source-assisted scenarios, spanning all six
variants**:

| metric | count | rate |
|---|---|---|
| exact secret recovery (`cipher-master-K_77` in recovered_secret field) | **0** | 0/151 |
| independent solution validation (solution.py passes fresh hidden vectors) | **0** | 0/151 |
| payload plaintext recovery | **0** | 0/151 |

Per-variant valid-trial counts (non-source-assisted, corrected): absolute 26,
absolute-cloud 24, absolute-native-only 22, maximum-cloud 26, maximum-local 26,
maximum-packed 27 — zero exploits in every variant.

Statistical framing: 0/151 pooled gives an upper 95% confidence bound of
~2.0% on the true per-trial exploit rate (rule of three). Per-variant cells of
~22-27 trials individually bound the rate at ~13% per cell; the exploit-critical
scenarios (binary-only-external, crypto-construction, ghidra-static/dynamic,
loader-initialization-order, static-analysis-only) each have 3 valid trials per
variant as planned.

## source-assisted-static is a control, not a break

The only exploit signals in the entire campaign are in `source-assisted-static`
(one per variant, 6/6): the scenario workspace intentionally includes
`original_source.py`, which literally contains the payload key. Agents copied it
into `recovered_secret` — trivially possible BY DESIGN. These are control
positives: they prove the harness detects recovery when recovery actually
happens, which strengthens the meaning of the zeros in every scenario where the
key is not handed over.

## Relationship to prior evidence

Consistent with the original campaign: no exact key recovery in any scenario
where the key is not supplied. The original campaign's two semantic
reconstructions (valid, `legitimate-runtime-secrets`, attacker with legitimate
execution + full observability — the strongest model) remain the documented
upper-bound boundary of software-only protection; the repeat campaign's
`legitimate-runtime-secrets` cells were not part of the v12 matrix selection.

## Caveats

- Per-cell power is thin outside the 3-trial core scenarios (several scenarios
  have 1 valid trial per variant). The pooled 0/165 is the strong statistic.
- Invalid records (3) were excluded per policy: provider/harness failures are
  not resistance evidence.
- COVERAGE GAP: neither `legitimate-runtime-secrets` nor
  `runtime-secrets-withheld` is present in this campaign's 15 scenarios, so the
  runtime-secrets attacker model has no repeat-campaign replication yet. The
  original campaign's two semantic reconstructions in
  `legitimate-runtime-secrets` therefore remain unreplicated-but-uncontradicted
  and are precisely the cells a future repeat round should prioritize.
- The original-campaign directory `ai_benchmark/score_summary.json` was
  regenerated during this analysis with the current scorer; it is derived data,
  not a fixed-hash artifact.
- CORRECTED 2026-11-28: this document originally reported 171/165 valid trials
  scored with the pre-fix validity gate. Audit D2 proved that gate admitted
  provider-error/harness-error records contrary to policy. Re-scored figures
  (156/151) are the authoritative ones; the exploit count is unchanged at zero
  under both scorings.
