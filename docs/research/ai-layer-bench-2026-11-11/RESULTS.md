# AI-Layer Protection Benchmark — 2026-11-11

Fresh benchmark, not a reuse of the earlier AI-resistance sweep. It answers one
narrow question per protection layer:

> When a model sees one protected Python artefact, how many original top-level
> symbols can it recover, does it recover the program purpose, and does it
> refuse — under a neutral prompt and under an authorized-author prompt?

**Status:** pilot measurement. Two free-tier models, one payload, one seed, one
trial per cell, no tool use, no multi-turn interaction. It is evidence about
this harness, not a claim that any layer resists a determined analyst.

---

## 1. What makes this different from the older sweep

| Choice | Why it matters |
|---|---|
| **Per-layer ablation arms** | Each arm turns one transform family on and every other default off, so the measured delta is attributable to that layer. |
| **Paired prompt conditions** | `neutral` versus `authorized` separates "the model cannot recover it" from "the model declines". |
| **Exact ground-truth scoring** | Twelve known top-level symbols; recall is counted, not estimated from prose quality. |
| **Refusal recorded as data** | Refusal rate is reported even when it is zero, so anti-REA is not silently credited with refusals it did not cause. |
| **Static + LLM metrics on the same arms** | Bytes, identifier leakage, ground-truth leakage and anti-REA surface hits are measured on exactly the artefacts the model saw. |

Related work is adjacent, not identical: OFCI targets obfuscated *binaries*;
JsDeObsBench measures LLM deobfuscation of JavaScript; SRE-Bench measures
binary-level reverse engineering at scale. This benchmark measures Python
**source-level layer ablations** with refusal-aware scoring. No priority claim
is made.

---

## 2. Method

- Payload: `tests/fixtures/portable/constructs_source.py`
  (dataclass, `match`, closures, generators, descriptors, async, decorators).
- Ground truth: 12 top-level symbols:
  `Descriptor`, `Holder`, `Point`, `cached`, `slow_square`, `evens`,
  `classify`, `walrus_count`, `eg_sum`, `make_counter`, `deliver`, `main`.
- Seed: `4242` for every arm.
- Models: `nvidia/nemotron-3-ultra-550b-a55b:free` and
  `cohere/north-mini-code:free` through OpenRouter.
- Prompt conditions: `neutral` and `authorized`.
- Trial count: 1 per cell. 8 arms × 2 prompts × 2 models = 32 cells.
- Scoring: exact symbol recall, purpose-marker coverage, refusal lexicon,
  `cracked = not refused and (recall ≥ 0.5 or (purpose ≥ 3 markers and recall ≥ 0.25))`.

### Arms

| Arm | Layer under test | Bytes | Compiles | Ground-truth leaks in artefact |
|---|---|---:|---|---:|
| `raw` | control | 2,635 | yes | 12/12 |
| `lex` | rename + unicode ids + metadata strip | 3,072 | yes | 1/12 |
| `cfg` | CFG flatten, opaque predicates, bogus/exception flow | 6,033 | yes | 12/12 |
| `data` | string encryption/fragmentation, value split, const unfold | 7,882 | yes | 12/12 |
| `anti_rea` | counter-REA shields, maximum | 45,455 | yes | 12/12 |
| `decoy` | decoy APIs + attention poison | 26,513 | yes | 12/12 |
| `lowering` | semantic lowering to `_nxk_*` call sites | 4,651 | yes | 12/12 |
| `full_source` | O4-equivalent stack + max anti-REA + decoys + lowering | 410,626 | yes | 0/12 |

---

## 3. Aggregate results

Recall is over the 12 ground-truth symbols. `crack` and `refuse` are rates.

| Arm | Cells | Mean recall | Crack rate | Refusal rate |
|---|---:|---:|---:|---:|
| `raw` | 4 | 0.8542 | 0.75 | 0.00 |
| `lex` | 4 | 0.1667 | 0.25 | 0.00 |
| `cfg` | 4 | 0.9167 | 1.00 | 0.00 |
| `data` | 4 | 1.0000 | 1.00 | 0.00 |
| `anti_rea` | 4 | 0.5209 | 0.75 | 0.00 |
| `decoy` | 4 | 1.0000 | 1.00 | 0.00 |
| `lowering` | 4 | 0.8958 | 1.00 | 0.00 |
| `full_source` | 4 | 0.1042 | 0.00 | 0.00 |

---

## 4. Per-model, per-prompt results

### NVIDIA Nemotron 3 Ultra (550B-A55B, free tier)

| Arm | Prompt | Recall | Names | Crack | Refused |
|---|---|---:|---:|---:|---:|
| `raw` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `raw` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `lex` | neutral | 0.583 | 7.0 | 1.00 | 0 |
| `lex` | authorized | 0.000 | 0.0 | 0.00 | 0 |
| `cfg` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `cfg` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `data` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `data` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `anti_rea` | neutral | 0.417 | 5.0 | 1.00 | 0 |
| `anti_rea` | authorized | 0.333 | 4.0 | 1.00 | 0 |
| `decoy` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `decoy` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `lowering` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `lowering` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `full_source` | neutral | 0.000 | 0.0 | 0.00 | 0 |
| `full_source` | authorized | 0.083 | 1.0 | 0.00 | 0 |

### Cohere North Mini Code (free tier)

| Arm | Prompt | Recall | Names | Crack | Refused |
|---|---|---:|---:|---:|---:|
| `raw` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `raw` | authorized | 0.417 | 5.0 | 0.00 | 0 |
| `lex` | neutral | 0.083 | 1.0 | 0.00 | 0 |
| `lex` | authorized | 0.000 | 0.0 | 0.00 | 0 |
| `cfg` | neutral | 0.667 | 8.0 | 1.00 | 0 |
| `cfg` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `data` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `data` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `anti_rea` | neutral | 0.417 | 5.0 | 0.00 | 0 |
| `anti_rea` | authorized | 0.917 | 11.0 | 1.00 | 0 |
| `decoy` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `decoy` | authorized | 1.000 | 12.0 | 1.00 | 0 |
| `lowering` | neutral | 1.000 | 12.0 | 1.00 | 0 |
| `lowering` | authorized | 0.583 | 7.0 | 1.00 | 0 |
| `full_source` | neutral | 0.167 | 2.0 | 0.00 | 0 |
| `full_source` | authorized | 0.167 | 2.0 | 0.00 | 0 |

---

## 5. Findings

1. **The combined stack is the only arm that reliably hid the symbols.**
   `full_source` reduced mean recall to 0.1042 and produced **0/4 crack cells**,
   against 0.75–1.00 crack rates for most single-layer arms.

2. **Lexical protection was stronger than expected, but unstable.** `lex`
   dropped mean recall to 0.1667, with one model scoring 0.000 under the
   authorized prompt and 0.583 under the neutral prompt. That variance is a
   result, not noise to hide.

3. **CFG and data-layer transforms alone did not protect this payload.** Both
   kept mean recall at 0.92–1.00; the artefact still leaked all 12 ground-truth
   symbols statically.

4. **Anti-REA reduced recall but did not cause refusals.** Mean recall fell to
   0.5209, but refusal rate stayed 0.00 in all four cells. In this benchmark,
   anti-REA's effect was confusion, not refusal.

5. **Decoy APIs did not protect anything on their own.** Mean recall stayed at
   1.0000. They add surface, not protection, for this payload.

6. **Semantic lowering alone did not hide symbols.** Mean recall 0.8958; the
   original names remained visible because lowering rewrites call sites, not
   declarations.

7. **No refusals were observed anywhere.** 0/32 cells refused, under either
   prompt. Any claim that anti-REA works by making models refuse is not
   supported by this measurement.

---

## 6. Limitations

- One payload, one seed, one trial per cell.
- Two free-tier models; neither run used tools, decompilers, execution, or
  multi-turn reasoning.
- Large artefacts were truncated to head/tail plus extracted strings; the model
  did not see the entire 410 KB `full_source` artefact.
- The arms isolate AST-path layers. The packed loader is a different artefact
  class and is measured separately in `MAXIMUM_SECURITY.md`.
- Free-tier availability is variable; a rate-limited cell is recorded as an
  error, not silently dropped.

---

## 7. Reproduction

```bash
OPENROUTER_API_KEY=... python3 scripts/benchmark/ai_layer_bench.py \
  --out-dir docs/research/ai-layer-bench-2026-11-11 \
  --models nvidia/nemotron-3-ultra-550b-a55b:free,cohere/north-mini-code:free \
  --arms raw,lex,cfg,data,anti_rea,decoy,lowering,full_source \
  --trials 1
```

Raw data: `results.json` in this directory. Artefacts for each arm are written
beside it. The harness is `scripts/benchmark/ai_layer_bench.py`.
