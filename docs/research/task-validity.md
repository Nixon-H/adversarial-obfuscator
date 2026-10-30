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
