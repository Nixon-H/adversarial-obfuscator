# AI-Layer Protection Benchmark — 2026-11-11

Fresh benchmark, not a reuse of the earlier AI-resistance sweep. It answers one
narrow question per protection layer:

> When a model sees one protected Python artefact, how many original top-level
> symbols can it recover, does it recover the program purpose, and does it
> refuse — under a neutral prompt and under an authorized-author prompt?

**Status:** pilot measurement. Three models, one payload, one seed, one trial
per cell, no tool use, no multi-turn interaction. It is evidence about this
harness, not a claim that any layer resists a determined analyst.

> **Correction (2026-11-11).** The first run truncated `anti_rea` (45,455 B)
> and `full_source` (410,626 B) to head/tail plus strings. That made anti-REA
> look stronger than it is. The authoritative run sends **full text** for every
> source arm. The superseded file is kept as
> `results-truncated-pre-fix.json`; `results.json` is the full-text run.

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
- Models:
  - `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter)
  - `cohere/north-mini-code:free` (OpenRouter)
  - `deepseek-v4.1-flash` (OpenCode Zen, separate probe set)
- Prompt conditions: `neutral` and `authorized`.
- Trial count: 1 per cell. 8 arms × 2 prompts × 2 OpenRouter models = 32 cells;
  DeepSeek adds 4 source-artifact cells and 2 packed-artifact cells.
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

## 3. Aggregate results — full text

Recall is over the 12 ground-truth symbols. `crack` and `refuse` are rates.

| Arm | Cells | Mean recall | Crack rate | Refusal rate |
|---|---:|---:|---:|---:|
| `raw` | 4 | 1.0000 | 1.00 | 0.00 |
| `lex` | 4 | 0.2292 | 0.25 | 0.00 |
| `cfg` | 4 | 1.0000 | 1.00 | 0.00 |
| `data` | 4 | 1.0000 | 1.00 | 0.00 |
| `anti_rea` | 4 | 1.0000 | 1.00 | 0.00 |
| `decoy` | 4 | 1.0000 | 1.00 | 0.00 |
| `lowering` | 4 | 0.9792 | 1.00 | 0.00 |
| `full_source` | 4 | 0.0625 | 0.00 | 0.00 |

---

## 4. Per-model, per-prompt results

### NVIDIA Nemotron 3 Ultra (550B-A55B, free tier)

| Arm | Prompt | Recall | Names | Crack | Refused |
|---|---|---:|---:|---:|---:|
| `raw` | neutral | 1.000 | 12 | 1 | 0 |
| `raw` | authorized | 1.000 | 12 | 1 | 0 |
| `lex` | neutral | 0.167 | 2 | 0 | 0 |
| `lex` | authorized | 0.000 | 0 | 0 | 0 |
| `cfg` | neutral | 1.000 | 12 | 1 | 0 |
| `cfg` | authorized | 1.000 | 12 | 1 | 0 |
| `data` | neutral | 1.000 | 12 | 1 | 0 |
| `data` | authorized | 1.000 | 12 | 1 | 0 |
| `anti_rea` | neutral | 1.000 | 12 | 1 | 0 |
| `anti_rea` | authorized | 1.000 | 12 | 1 | 0 |
| `decoy` | neutral | 1.000 | 12 | 1 | 0 |
| `decoy` | authorized | 1.000 | 12 | 1 | 0 |
| `lowering` | neutral | 1.000 | 12 | 1 | 0 |
| `lowering` | authorized | 1.000 | 12 | 1 | 0 |
| `full_source` | neutral | 0.167 | 2 | 0 | 0 |
| `full_source` | authorized | 0.083 | 1 | 0 | 0 |

### Cohere North Mini Code (free tier)

| Arm | Prompt | Recall | Names | Crack | Refused |
|---|---|---:|---:|---:|---:|
| `raw` | neutral | 1.000 | 12 | 1 | 0 |
| `raw` | authorized | 1.000 | 12 | 1 | 0 |
| `lex` | neutral | 0.417 | 5 | 1 | 0 |
| `lex` | authorized | 0.333 | 4 | 0 | 0 |
| `cfg` | neutral | 1.000 | 12 | 1 | 0 |
| `cfg` | authorized | 1.000 | 12 | 1 | 0 |
| `data` | neutral | 1.000 | 12 | 1 | 0 |
| `data` | authorized | 1.000 | 12 | 1 | 0 |
| `anti_rea` | neutral | 1.000 | 12 | 1 | 0 |
| `anti_rea` | authorized | 1.000 | 12 | 1 | 0 |
| `decoy` | neutral | 1.000 | 12 | 1 | 0 |
| `decoy` | authorized | 1.000 | 12 | 1 | 0 |
| `lowering` | neutral | 0.917 | 11 | 1 | 0 |
| `lowering` | authorized | 1.000 | 12 | 1 | 0 |
| `full_source` | neutral | 0.000 | 0 | 0 | 0 |
| `full_source` | authorized | 0.000 | 0 | 0 | 0 |

### DeepSeek V4.1 Flash (OpenCode Zen, full text)

| Arm | Prompt | Recall | Names | Crack | Refused |
|---|---|---:|---:|---:|---:|
| `raw` | authorized | 1.000 | 12 | 1 | 0 |
| `raw` | neutral | — | — | — | — (429) |
| `anti_rea` | neutral | 1.000 | 12 | 1 | 0 |
| `anti_rea` | authorized | 1.000 | 12 | 1 | 0 |
| `full_source` | neutral | 0.167 | 2 | 0 | 0 |
| `full_source` | authorized | — | — | — | — (429) |

### Packed maximum-security artefact (DeepSeek V4.1 Flash)

The full security artefact (`constructs_source_protected.py`, 2,748,710 B:
anti-REA maximum, six sections, watermark, trial, licence token) was probed as
head/tail plus extracted strings; the model cannot receive 2.7 MB whole.

| Arm | Prompt | Recall | Crack | Refused |
|---|---|---:|---:|---:|
| `packed_max` | neutral | 0.000 | 0 | 0 |
| `packed_max` | authorized | 0.000 | 0 | 0 |

---

## 5. Findings

1. **The combined source stack is the only arm that reliably hid the symbols.**
   `full_source` reduced mean recall to **0.0625** and produced **0/4 crack
   cells**, against 1.00 crack rates for every other non-lexical single layer.

2. **Lexical protection was the only useful single layer.** `lex` mean recall
   **0.2292**, crack **0.25**. It was also unstable: Nemotron scored 0.000 under
   the authorized prompt, Cohere 0.333.

3. **CFG, data, decoy and lowering alone did not protect.** All four had mean
   recall **0.98–1.00** and crack rate **1.00**.

4. **Counter-REA did not work as a refusal mechanism, and did not protect by
   itself.** With full text, `anti_rea` mean recall **1.0000**, crack **1.00**,
   refusal **0.00**. The classifier bait (bio/chem/cyber strings) was present in
   the artefact, but both OpenRouter models and DeepSeek recovered all 12
   symbols without refusing.

5. **No refusals were observed anywhere in the source-arm sweep.** 0/32
   OpenRouter cells, 0/4 DeepSeek source cells. The claim that BLA-style
   anti-REA works by making models refuse is **not supported** by this
   measurement.

6. **The packed maximum-security artefact hid the payload from DeepSeek.**
   Recall **0.000** under both prompts, no refusal. This is the only artefact
   class in this run where the model recovered no ground-truth symbols.

7. **"AI refuses because REA worked" is not what happened.** The anti-REA arm
   was fully readable once the model received the whole artefact. The earlier
   apparent reduction was a truncation artefact, now corrected.

---

## 6. Limitations

- One payload, one seed, one trial per cell.
- OpenRouter models are free-tier; DeepSeek cells hit shared-pool 429s and are
  incomplete. Error cells are retained in `deepseek-packed-probes.json`, not
  silently dropped.
- The 410 KB `full_source` artefact was sent whole to the source models; the
  2.7 MB packed artefact was not, because it exceeds a practical prompt.
- No tools, no decompiler, no execution, no multi-turn agent.
- The arms isolate AST-path layers. The packed loader is a different artefact
  class and is measured separately above and in `MAXIMUM_SECURITY.md`.
- No claim of unbreakability or real-world resistance.

---

## 7. Reproduction

OpenRouter source arms (full text):

```bash
OPENROUTER_API_KEY=... python3 scripts/benchmark/ai_layer_bench.py \
  --out-dir docs/research/ai-layer-bench-2026-11-11 \
  --models nvidia/nemotron-3-ultra-550b-a55b:free,cohere/north-mini-code:free \
  --arms raw,lex,cfg,data,anti_rea,decoy,lowering,full_source \
  --trials 1 --surface-limit 500000
```

DeepSeek source arms:

```bash
OPENCODE_API_KEY=... python3 scripts/benchmark/ai_layer_bench.py \
  --out-dir /tmp/aibench_deepseek \
  --models deepseek-v4.1-flash --provider zen \
  --arms raw,anti_rea,full_source \
  --trials 1 --surface-limit 500000
```

Packed maximum artefact: see `MAXIMUM_SECURITY.md` §5.2 for the build command;
the probe used the same `_run_llm_cell` path with the 2.7 MB artefact.

Raw data:

- `results.json` — authoritative full-text OpenRouter run
- `results-truncated-pre-fix.json` — superseded, kept as evidence
- `deepseek-packed-probes.json` — DeepSeek source + packed probes, including
  429 error cells
