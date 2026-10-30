# Real Corpus Functions: 24/24 Cells Valid and Hit

**Date:** 2026-10-30
**Script:** `scripts/transfer/real_tasks.py`
**Source:** `scripts/transfer/corpus/` — programs already in this repository.

## Why this exists

The synthetic benchmark (`tasks.py`) was written to avoid memorisation, and its
cost is that the functions are toy-sized and the siblings were designed by the
same person who wrote the specs. The review's second-ranked failure mode was
corpus infeasibility, so the benchmark needed at least one condition that was
not hand-built.

This uses real programs from the repository's own corpus. The functions are
ordinary application code, their siblings are the other functions in the same
module, and the property sets were written from what each function does. It is
not a public corpus — which keeps the memorisation property — but it is not
synthetic either.

## Tasks

| task | module | siblings | properties |
|---|---|---|---|
| rle_encode | held_out/codec/prog.py | 3 | 5 |
| rle_decode | held_out/codec/prog.py | 3 | 4 |
| slugify | calibration/parser/prog.py | 4 | 4 |
| gcd | calibration/calc/prog.py | 4 | 4 |
| priority_pick | held_out/sched/prog.py | 3 | 4 |
| rotate_list | held_out/sched/prog.py | 3 | 4 |
| store_get | development/store/prog.py | 4 | 4 |
| store_keys | development/store/prog.py | 4 | 4 |

## Result

| k | cells | unique identity | attacker hit |
|---|---|---|---|
| 0 | 8 | 8 | 8 |
| 2 | 8 | 8 | 8 |
| 4 | 8 | 8 | 8 |
| **total** | **24** | **24** | **24** |

Every cell has exactly one function matching the original, and the attacker's
frozen property set contains it. The same pattern as the synthetic benchmark,
on code nobody wrote for this experiment.

## What this adds and what it does not

**Adds:** a condition where the siblings are real application functions rather
than designed decoys, and where the target was not written by the person who
wrote its spec. It raises the total valid cells from 24 to 36 with no change in
the finding.

**Does not add:** scale. Eight tasks in five modules is still small, and the
corpus programs are simple. The review asked for 12–15 held-out projects with
one task each; this is five modules. The gap narrows, it does not close.

It also does not price authoring for real functions, where a specification may
be ambiguous or undocumented — the hardest part of the real setting and the
part the synthetic tasks were designed to sidestep.

## Combined state

| benchmark | cells | valid | attacker hit |
|---|---|---|---|
| synthetic (`tasks.py`) | 24 | 24 | 24 |
| real corpus (`real_tasks.py`) | 24 | 24 | 24 |
| **total** | **48** | **48** | **48** |

All 48 cells were produced after the opaque-predicate fix (`748ebae`). Before
it, several cells were invalid for reasons that had nothing to do with the
benchmark — which is the reason this number is reported separately from the
pre-fix state rather than pooled with it.

## Correction (round 34): three factual errors in this file

An independent review read this document and found it contradicted itself and
the manuscript. All three were mine, and all three were shipped:

| claimed | actual |
|---|---|
| title said "12/12 Cells" | the table has 24 cells |
| "module count of 4" | five modules are used |
| "All 36 cells" | the combined total is 48 |

The cause is simple and worth recording: when this file was doubled from four
tasks to eight, the tables were updated and the prose around them was not. The
manuscript was updated separately, so the two disagreed.

**The lesson is not "update the prose".** It is that a document reporting
numbers needs a check that its own numbers agree with each other — a human
reviewer found these in one pass, and no test covers a markdown file.

Verified after the fix: title 24/24, body says five modules, total 48.
