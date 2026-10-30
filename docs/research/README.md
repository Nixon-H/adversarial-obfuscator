# Research Programme: Index and Current State

**Last updated:** round 112 (2026-10-30)

This directory holds a research programme that produced **seven product defects
and one negative result**. This file is the entry point: what exists, what it
claims, and what it does not.

---

## Start here

| If you want to | read |
|---|---|
| the paper | `paper-draft.md` — instrument-validity note with a seven-defect section |
| whether the artefact runs | `python3 scripts/transfer/artefact_gate.py` — 69 artefacts, 0 failures |
| the defects | `paper-draft.md` §6, or the individual files below |
| the benchmark | `task-validity.md`, `real-corpus-tasks.md`, `external-tasks-evaluated.md` |
| what went wrong | `retraction-cost-curve.md`, `fourth-review-reframing.md`, and the eight retractions |

---

## The research question and its answer

**Question.** Does per-build diversification of Python source obfuscation raise
the cost for an attacker to identify a function?

**Answer (withdrawn three times, now a methods note).** A specification-derived
property set is semantic, and a semantics-preserving transformation has no
channel to it. Any null it produces is predicted by the construction, so the
instrument cannot measure the question.

That claim survived three independent reviews that each broke a larger one:

| round | claim before review | after |
|---|---|---|
| 34 | flat cost curve | withdrawn: attacker was memoryless |
| 71 | negative result, bounded | withdrawn: bound measured the wrong quantity |
| 79 | bounded null at 2 probes | withdrawn: bound is a non-sequitur |

---

## The defects

Nine, of which six could not have been found by the project's own tests.

| # | defect | symptom | document |
|---|---|---|---|
| 1 | 30-day expiry | artefact stops decrypting after a month | `paper-draft.md` §6.2 |
| 2 | false opaque predicates | functions silently return `None` | `paper-draft.md` §6.2 |
| 3 | emptied dataclass | does not compile | `dataclass-body-strip.md` |
| 4 | unbound import/kwarg names | fails at import | `dataclass-body-strip.md` |
| 5 | string `match` patterns | does not compile | `match-pattern-rename-defect.md` |
| 6 | plain-import bindings | fails at import | `artefact-gate.md` |
| 7 | `from __future__` hoisting | does not compile | `future-import-defect.md` |
| 8 | builtin names in the function table | fails at import | `table-key-folding-defect.md` |
| 9 | an `except` that returns the input | silently returns unobfuscated source | `swallowed-exception-returns-original.md` |

All nine are fixed and guarded. The guards live in `tests/test_*` and are named
in `artefact-gate.md`.

---

## The benchmark

| family | tasks | cells | source |
|---|---|---|---|
| hand-written | 9 | 27 | `scripts/transfer/tasks.py` |
| repository corpus | 8 | 24 | `scripts/transfer/real_tasks.py` |
| external: more_itertools | 3 | 12 | `corpus/external/recipes.py` (MIT) |
| external: cpython statistics | 1 | 3 | `corpus/external2/statistics.py` (PSF) |
| external: boltons | 0 gated | — | `corpus/external3/strutils.py` (BSD-3), gate only |
| stress fixture | — | — | `corpus/fixtures/stress.py` |

Validity: every gated cell has a unique evaluator-decided identity and a
singleton attacker set. `sibling-separation-audit.md` records the audit.

---

## Instruments

| instrument | what it answers | how to run |
|---|---|---|
| artefact gate | does the output compile, import and run | `python3 scripts/transfer/artefact_gate.py` |
| reproduction | are the paper's numbers still true | `python3 scripts/transfer/reproduce.py` |
| validity | is the task scoreable | `python3 scripts/transfer/evaluate_tasks.py` |
| external validity | do third-party tasks pass | `python3 scripts/transfer/evaluate_external.py` |

All are deterministic: explicit seeds, no network, repository inputs.

---

## What is not done

| gap | why it is open |
|---|---|
| **external corpus at scale** | `corpus-acquisition-plan.md` has the protocol; 4 sources acquired, 12–15 needed. The binding constraint is specification, not fetching — `external-fetch-attempt.md` measured 0 usable tasks from 38 KB of plumbing, and `in-repo-corpus-yield.md` measured 37% docstring coverage in-repo |
| **analyst-minutes** | `authoring-cost-proxy.md` prices the specification work in assertions; turning that into human time needs a study |
| **systematic review** | `novelty-search-log.md` is a documented screen (eight queries, fifteen sources), not a PRISMA review; OFCI is the closest prior and the paper says so |
| **the study itself** | blocked by the first two |

---

## Retractions, because they are the evidence

Eight claims were withdrawn after checking. Each is recorded next to what it
corrected rather than deleted:

1. round 3 — reproducibility by seeding derivation inputs
2. round 39 — a shifted-timestamp experiment that tripped the self-check
3. round 51 — a diff of two nonexistent files
4. round 52 — a pre-pin copy of the session key
5. round 56 — a hand-typed interval instead of a measured one
6. round 71 — the flat cost curve
7. round 79 — the two-probe bound
8. round 102 — a "seventh defect" that was an invalid fixture

Five of the eight were my own instrument failing, not the system under test.
That is the ratio this programme should be judged on: **the checks caught the
checker more often than they caught the product**, and the product still yielded
seven defects.

---

## Sealed reports

`../research-reports/adversarial-obfuscator-research-readiness/` holds 40 sealed
reports. Each claim is bound to a content-addressed evidence snapshot and
re-hashed on read, so a claim that no longer matches its evidence is marked
rather than trusted.
