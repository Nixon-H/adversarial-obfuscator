# Task Validity: Nine of 24 Cells Are Ambiguous by Construction

**Date:** 2026-10-30
**Script:** `scripts/transfer/evaluate_tasks.py`

## The separation that resolved it

Rounds 14–15 could not attribute nine zero-hit cells because a single number
conflated two questions. Splitting them:

- **identity** — decided by the evaluator, which alone holds the original
  function: run each candidate of the obfuscated build on evaluator inputs
  (different from the attacker's) and keep those matching the original;
- **conclusion** — decided by the attacker's frozen property set;
- **score** — does the attacker's passing set intersect the evaluator's
  identity set?

## Result

| quantity | value |
|---|---|
| cells | 24 (8 tasks × 3 builds) |
| evaluator-unique identity | **15** |
| attacker hit (intersects truth) | **20** |
| **cells where the evaluator cannot name a unique target** | **9** |

The nine ambiguous cells are exactly the nine that read zero in round 14.

## What that means

In those nine cells the evaluator itself cannot say which function is the
target: a sibling is behaviourally identical to it **on the evaluator's
inputs**. The task, as written, has no unique answer. No attacker can be
scored on it, and a zero there says nothing about the attacker or the
protection.

The cause is task design: siblings were chosen to be near-duplicates, and
for several of these tasks the evaluator input set does not separate them.
`first_negative` is representative — `fn3` uses `x <= 0` where the target
uses `x < 0`, and none of the three evaluator inputs contains a zero.

## What this fixes

1. Rounds 14–15's "zero-hit cells" are explained: they are **invalid tasks,
   not failures**. The correct reporting is to exclude them and say why.
2. It also shows the attacker is stronger than round 14 suggested: 20 of 24
   cells intersect the truth, and among the 15 valid ones the property set
   finds the target.
3. It gives the task set a **validity gate**: every task must be checked for
   evaluator-distinguishability before it is used, and a task that fails is
   repaired by adding a separating input, not by hoping.

## Limits

- The evaluator inputs remain finite. "Unique" means unique **on these
  inputs**, which is the same caveat the study must carry everywhere.
- The seven repaired-or-ambiguous tasks have not been fixed yet; the count
  above is the honest current state, not a target.
- Attacker hit rate on valid cells only: 15 of 15 by construction of the
  intersection test, which is why the meaningful measure is the *validity*
  rate (15/24) rather than the hit rate.

## Round 17: the k=4 cells are not ambiguous tasks — they are an open defect

Repairing the ambiguous tasks required looking at why four cells have
**zero** candidates matching the original. The answer is not ambiguity:

`sumselected`, k=4, seed 5505, evaluator inputs
`[([1,2,3,4],1,4), ([2],2,3), ([9,9],9,10)]`:

| | values |
|---|---|
| original | `[6, 2, 18]` |
| candidates | `[None, None, None]`, `TypeError`, `[9, 0, 0]`, `[None, None, None]`, **`[7, 3, 19]`** |

No candidate matches. The closest, `[7, 3, 19]`, is the original plus one in
every position — which is exactly `sibling_c`, the sibling that starts its
accumulator at `1` instead of `0`. So the module contains the siblings and
**nothing that behaves like the target**.

Two explanations remain, and the evidence does not choose between them:

1. the target function is dropped from the build at this seed; or
2. the target is present but its behaviour changed.

Both are serious. Neither is established: a textual search cannot settle it
because the transformation rewrites the comparison expression, so the
target's body does not survive verbatim for a grep to find.

**Status: open defect, needs investigation before any k=4 number is used.**
The correct action is to name every candidate by behaviour against the
original and check whether a function with the target's behaviour exists at
all in the module — not to score the cell.

This is recorded rather than fixed because a wrong answer here would be a
false claim about the product in either direction: "obfuscation drops
functions" if it does not, or "tasks are merely ambiguous" if it does.
