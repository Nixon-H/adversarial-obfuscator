# External Tasks Through the Gates: 12 of 12 Cells Valid

> **Updated in round 171.** The original run below reported 8 of 9; the corpus
> has since grown to 12 cells and two evaluator bugs (classes and private
> aliases counted as candidates) were fixed. The historical section is kept
> because it records what was true when measured.

**Date:** 2026-10-30
**Source:** `more_itertools.recipes` (MIT), vendored at
`scripts/transfer/corpus/external/recipes.py` with its licence retained.
**Runner:** `scripts/transfer/evaluate_external.py`

## Result

| task | k=0 | k=2 | k=4 |
|---|---|---|---|
| all_equal | unique, singleton | unique, singleton | unique, singleton |
| dotproduct | **not unique**, singleton | unique, singleton | unique, singleton |
| take | unique, singleton | unique, singleton | unique, singleton |

**9 cells, 8 evaluator-unique, 9 attacker-singleton.**

## The failing cell

`dotproduct` at k=0 has **two** candidates matching the original on the
evaluator inputs. That is the same task-validity defect the internal benchmark
hit twice — an evaluator input set that does not separate the target from a
sibling — and it is reported rather than pooled, because a cell where the
evaluator cannot name a unique answer cannot be scored.

The fix would be a separating input, as it was internally. It is not applied
here because the point of this run is the gate, not the score.

## What this establishes

**Third-party code passes the same gates as the internal corpus**, at 8 of 9
cells in the original run and 12 of 12 after the round 171 evaluator fix. Three functions from a real library, with the library's own 70 functions
as siblings, are identified by a specification-derived property set — and the
audit machinery from the internal benchmark transfers without modification.

That is the first evidence in this programme that the benchmark is not
self-referential. The internal tasks were built to a template; these were not.

## What it does not establish

- **Scale.** Three functions from one module is not a corpus. The acquisition
  plan asks for twelve to fifteen projects; this is one.
- **Independence of specification.** The properties were still written by the
  same author as the benchmark, from the library's docstrings. That is the
  remaining gap and the external code does not close it.
- **That the finding generalises.** Two tasks here are trivial
  (`all_equal`, `take`), and one has an invalid cell.

## Why it belongs in the paper

The paper's §4.1 says the benchmark is 17 hand-built tasks. It can now say that
a third-party module passes the same gates at 12 of 12 cells, which is the
difference between "a benchmark we built" and "a benchmark that has been
exercised on code we did not write".

## Round 171: 12 of 12, and the evaluator bug that was hiding behind the one bad cell

`dotproduct` at build index 0 had failed the uniqueness gate since round 91. It is
now unique, and the fix was **not** a separating input.

**Two evaluator defects, found by looking at the candidate list:**

1. **Classes counted as candidates.** `IndexError([1, 2], [3, 4])` constructs
   successfully and returns an exception instance — it does not raise, so every
   exception class in the obfuscated module "matched" the target's inputs.
2. **Private aliases counted as candidates.** `_sumprod` is bound to the *same
   implementation* as the public `dotproduct`, so it matched exactly. The gate was
   right to report a duplicate and wrong to be asked the question: a task cannot be
   unique while an underscore alias is a candidate a caller could pick.

Excluding classes and underscore-prefixed names:

```
cells 12  evaluator-unique 12  attacker-singleton 12
```

## What this says about the gate

The uniqueness gate was doing its job for twelve rounds: it reported a cell it could
not score, and every attempt to "fix" it by widening the evaluator inputs was
treating a **measurement** bug as a **task** bug. The output was wrong, not the
inputs.

The lesson is the programme's own: **when a check reports a problem, inspect the
check's own assumptions before changing the thing it is measuring.** Round 135's
invalid reducer, round 141's deleted `def`, and this round's class candidates are
three instances of the instrument being wrong rather than the object.
