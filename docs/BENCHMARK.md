# Benchmarking Methodology

**Status:** current description of the measurement programme. The authoritative
protocols are the dated documents in [`research/`](research/); this document
explains the design and points to them. It does not replace them.

Related: [`RESULTS.md`](RESULTS.md) for what was measured,
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) for commands.

---

## 1. What the benchmark is for

The benchmark exists to answer one question:

> Does per-build transform-family diversification raise the cost for an attacker
> to identify a function in Python source?

It is deliberately narrow. It does not measure comprehension, exploit
development, licence bypass, or resistance to a human analyst with unlimited
time. It measures **identification** — narrowing a candidate set to the one
function that matches a specification — and it uses **probe evaluations** as
its cost unit.

The narrowness is the point. A broad claim ("obfuscation works") is not
falsifiable at this scale. A narrow one ("this instrument observes no effect
once callable counts are matched") is.

---

## 2. Task corpus

### 2.1 Internal tasks

| Family | Tasks | Cells (3 build indices) | Source |
|---|---|---|---|
| Hand-written | 9 | 27 | `scripts/transfer/tasks.py` |
| Repository corpus | 8 | 24 | `scripts/transfer/real_tasks.py` |
| **Total** | **17** | **51** | |

Each task is a target function among siblings in the same module. The
hand-written tasks are designed so siblings differ at one boundary each (an
off-by-one comparison, a different accumulation order, and so on). The corpus
tasks come from real modules in this repository, where the siblings are the
module's other functions.

The task design has one hard requirement: the evaluator must be able to name a
unique target. This failed twice and was repaired; the failures are recorded in
[`research/task-validity.md`](research/task-validity.md). Nine of 24 cells in
an early run were ambiguous by construction, and a zero there said nothing
about the attacker.

### 2.2 External tasks and gated sources

| Source | Licence | Use | Tasks / artefacts |
|---|---|---|---|
| `more_itertools.recipes` | MIT | Tasks + gate | 3 tasks, 12 cells |
| CPython `statistics.py` | PSF | Task + gate | 1 task, 3 cells |
| `boltons/strutils.py` | BSD-3 | Gate only | — |
| `boltons/iterutils.py` (bulk) | BSD-3 | Gate only | — |
| `more_itertools` package | MIT | Gate only | — |

The artefact gate covers **38 artefacts at one index**, of which 20 are
external. The gate validates that emitted artefacts compile, import, and run;
it does not supply an independent specification. That distinction matters: a
gated artefact is evidence about execution, not about identification.

Two larger packages (`urllib3`, `requests`) remain un-gated. They are blocked
by the cross-module export question in
[`research/paper-draft.md`](research/paper-draft.md) §6.4, not by packaging.

### 2.3 Blind specification

Six tasks were specified by an author who had **not** read the paper, the
programme, or the defect documents — only the data shape of
`external_tasks.py`. The specification file is
`scripts/transfer/blind_tasks.py`, SHA-256
`3cb7f06a22806f2f2ddab4a475f022819b064a03425201bde65d579516387489`, sealed
before any obfuscated output was generated.

The blind tasks are the only independent specification in the programme. They
cover six of twenty-three tasks, and **two of them (`is_prime`, `median_high`)
are load-bearing**. The rest of the specifications are the author's own. This is
the paper's primary limitation, and no amount of re-analysis removes it.

Why the others are not load-bearing: under the attacker's actual candidate base
(the module's own callables), the first property eliminates every sibling for
four blind tasks. Their equality is arithmetic, not evidence. The informative
external tasks are `is_prime` and `median_high` (blind) and `all_equal` and
`median_low` (prior); the load-bearing base is 11 tasks — 7 hand-written, 2
blind, 2 prior.

---

## 3. Attacker

### 3.1 What it is

A **specification-derived property set**: three to five executable assertions
per task, written from the documentation of what the function does, not from
its body. The set is applied **frozen** to every build. It does not learn from
the build it is analysing.

Measured authoring cost: **38 properties across nine hand-written tasks**, of
which one or two per task actually separate the target from its nearest
sibling. The work is paid once per task, not per build.

### 3.2 What it may see

| Sees | Does not see |
|---|---|
| One emitted artefact | Clean source |
| Its executability | Evaluator vectors |
| The task specification | Labels |
| | Any other build |

`tests/test_artifact_only_attack.py` asserts that `develop()` takes only a
build and a workdir and references no ground truth, vectors, or original
source.

### 3.3 Identity versus conclusion

This separation resolved three rounds of unattributable numbers:

- **Identity** — decided by the evaluator, which alone holds the original
  function, by running candidates on inputs the attacker never sees.
- **Conclusion** — decided by the attacker's property set.
- **Score** — whether the attacker's passing set intersects the evaluator's
  identity set.

A cell where the evaluator cannot name a unique target is **invalid**, not a
zero. Reporting it as a zero would attribute a task-design failure to the
defence.

### 3.4 What the attacker is not

It is not a decompiler, not an LLM, not a symbolic executor, and not a human.
It is a probe counter. The result is about what that instrument can observe.
The programme's own readiness audit says this explicitly: a frozen property
set is a valid *known-source, specification-driven* attacker, not a general
reverse-engineering model.

---

## 4. Cost unit

The unit is a **specification-derived probe evaluation**: one assertion applied
to one candidate. CPU seconds are recorded in the source documents but are not
used for inference, because at this scale they are dominated by interpreter
startup (median 0.007 s).

The unit has a known ceiling: it is a resolution unit, not analyst time. No
probe-to-minutes mapping is claimed. A result in probes says nothing about how
long a human would take.

---

## 5. Builds

Builds are produced by the research generator
(`scripts/diversity/generator.py`) with pinned transform selection:

```python
generate_variant(src, 4, {"master_seed": s, "pass_sets": [family]})
```

Builds are **not byte-reproducible**. Eight builds of
`urllib3/_collections.py` (17,762 bytes of source) produced outputs of
30,424 / 30,514 / 30,771 / 33,515 / 31,661 / 28,612 / 30,605 / 34,208 bytes —
a **5,596-byte spread, 17.9% of the mean** — and eight distinct ASTs (SHA-256
of `ast.dump`). The same measurement on a small synthetic task gives 1,018
bytes, also about 18%.

An earlier draft claimed a 314-byte spread (0.08%); that figure could not be
reproduced and is withdrawn. See
[`research/build-nondeterminism.md`](research/build-nondeterminism.md).

The cost endpoint nevertheless appeared stable on the task measured: probe
count was identical (9,9,9,9,9,9,9,9) across the same eight seeds. That is an
empirical observation on one task, not a consequence of the variation being
small, and it is the only reason the unpaired design is defensible.

**Important scope note.** These builds are the research generator's output, not
the shipped `scripts/build.py` or the packed loader. The paper studies the
source-level research path. Extrapolating its result to the full protection
stack is not supported.

---

## 6. Gates

A task or artefact enters the benchmark only if it passes all applicable gates.

| Gate | What it rejects | Where |
|---|---|---|
| Evaluator distinguishability | Tasks whose target cannot be uniquely identified from siblings on evaluator inputs | `evaluate_tasks.py` |
| Behavioural equivalence | Builds that do not reproduce the original's behaviour | `evaluate_tasks.py` |
| Compile / import / run | Artefacts that do not execute | `artefact_gate.py` |
| Singleton | Cells where the attacker's passing set has more than one candidate | `reproduce.py` / `measure.py` |
| Semantic gate (const-split) | Variants that change observable behaviour | `run_const_split.py` |

The behavioural-equivalence gate is what caught the false opaque predicates:
functions compiled, imported, and returned `None`. The compile/import/run gate
is what caught ten of the thirteen defects. Neither check subsumes the other;
the programme demonstrated that in both directions.

---

## 7. Protocols

The programme wrote its protocols down before running the confirmatory
measurements, and preserved the amendments.

| Protocol | Scope | Status |
|---|---|---|
| [`protocol-v2.md`](research/protocol-v2.md) | H0–H5 arms, endpoints, gates | Superseded by the readiness audit's findings; preserved |
| [`protocol-v3.md`](research/protocol-v3.md) | Cost-curve endpoint | Primary endpoint **withdrawn**; see the retraction |
| Const-split protocol | Pre-registered arms C0–C3, semantic gate, amendments 1–2 | Complete; results in `research/const-split-results/RESULTS.md` |
| 2026-10-29 plan | Frozen vs adaptive transfer, project-held-out corpus, power analysis | **Designed, not run** |

The const-split experiment is the best example of the intended discipline: the
config freeze hash is recorded, both amendments were written before the number
they govern, and the pre-amendment instrument is disclosed alongside the
primary table.

---

## 8. Statistics

The primary comparison is a paired difference in probe counts:

```
seed_only = [probes(f1, s1), probes(f1, s2), probes(f1, s3)]
varying   = [probes(f1, s1), probes(f2, s2), probes(f1, s3)]
diff      = mean(varying) - mean(seed_only)
```

Only the middle seed crosses families, so a one-probe difference appears as
+0.33. The comparison is replicated across 17 tasks.

Known statistical limits:

- **51 cells** at three build indices; other indices are unmeasured.
- **The sd of 0.00 is a fingerprint, not a null.** All 17 tasks give exactly
  +1/3 probes uncontrolled. A constant difference in every task is the
  signature of a systematic cause — here, the one-callable gap.
- **Pairs reuse builds.** The H0–H5 pilot's 36 ordered pairs reused six builds
  and included six self-pairs fixed at T=1; the readiness audit flagged the
  resulting dependence. The current 17-task comparison does not use that
  design.
- **No equivalence test was pre-registered for the original null.** That is one
  reason the original "flat cost curve" claim was withdrawn.

---

## 9. Validity threats

Stated in the paper (§7) and the readiness audit. The ones that bound the
result most tightly:

| Threat | Effect |
|---|---|
| **Single author** | All 38 properties and most specifications are the author's. Two blind tasks mitigate; they do not remove it. |
| **Small corpus** | 17 tasks, mostly 37–51 lines with 3–4 functions. Not a Python corpus in the sense a general claim needs. |
| **Finite properties** | Three to five assertions per task; passing them is a semantic smoke gate, not proof of equivalence. |
| **Probes ≠ effort** | No human has been timed; the unit may not track analyst cost. |
| **Three families** | Two shown equally hard; unequal families differ for reasons of strength, a confound intrinsic to any cross-strength comparison. |
| **Order invariance** | Established on one task's permutations, not all. |
| **Build indices** | Singleton audit covers three indices per task. |
| **Instrument validity** | The property set is blind to semantic transformation but sensitive to structure. That is the finding, and it also means the instrument cannot answer the original question as posed. |

---

## 10. Reproduction

```bash
# The paper's ten tables
python3 scripts/transfer/reproduce.py

# The artefact gate (38 artefacts at one index, 0 failures)
python3 scripts/transfer/artefact_gate.py --variants 1 --seeds 4242

# Task validity
python3 scripts/transfer/evaluate_tasks.py

# External validity
python3 scripts/transfer/evaluate_external.py
```

All are deterministic: explicit seeds, no network, repository inputs. The
reproduction script prints its values beside the documents' claims; it does
not assert equality itself, so a human must compare. That limitation is
recorded in [`research/final-verdict.md`](research/final-verdict.md).

---

## 11. What the benchmark cannot answer

- Whether an adaptive attacker recovers what a frozen one misses.
- Whether a human analyst finds the task harder.
- Whether the result generalises to real packages at scale.
- Whether the full product (packed loader, counter-REA, native backends) is
  harder than the research path.
- Whether symbol stripping, MBA, or packing stop a capable analyst.

Those are the open questions. [`LIMITATIONS.md`](LIMITATIONS.md) lists what
would be needed to answer each.
