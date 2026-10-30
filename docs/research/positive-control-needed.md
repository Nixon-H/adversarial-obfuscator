# The Negative Result Needs a Positive Control

**Date:** 2026-10-30
**Source:** an independent review of the result documents (round 61).

The review's decisive objection, which I accept:

> Probing is a deterministic function of candidate count, property ranking and
> family strength. Family *variation* is not an argument to that function. The
> null was entailed by the attacker interface — the round-34 "cannot fail"
> defect relocated into a new counter.

## Why the tables show it

Every table in the result documents has **sd = 0.00**:

| measurement | values |
|---|---|
| seed-only across builds | 5, 5, 5 |
| experience on a fixed build | 9, 9, 9, 9, 9 |
| B vs C | 0.00, sd 0.00 |
| A vs B | +0.33, sd 0.00 |

Variance appears **only** when the candidate count varies. That is not a
statistical result about diversity; it is arithmetic. `(0 + 0 + 1) / 3 = 0.33`
for every task, and zero spread across nine tasks is what that expression
produces, not evidence of equivalence.

## What the review says is missing

> A **positive control in the diversity direction**: a family effect the
> endpoint can register. Without it, seventeen tasks are seventeen replications
> of a harness.

This is the sharpest criticism in the programme so far, because it is correct
and it is the same shape as the defect that caused the round-34 retraction: an
endpoint whose answer cannot vary.

## What would count as a positive control

The endpoint must show a **non-zero** diversity effect when one is engineered to
exist. Candidate constructions:

1. **A family that perturbs a boundary the specification does not pin.** If a
   transform changes `lo <= v < hi` to `lo < v <= hi` only on builds of one
   family, a specification that does not test the boundary should identify the
   wrong function on those builds. That is the mechanism gap the manuscript
   already lists as open, and it is the natural positive control.
2. **Per-family property derivation.** A specification written specifically for
   each family's transforms should cost less than one written blind. If the
   endpoint cannot see that, it cannot see any family effect.
3. **Injected known difference.** Give one family a transform that provably
   adds a candidate the property set cannot eliminate, and check the counter
   rises by the expected amount.

Option 1 is the most faithful to the threat model and connects to the
specification-completeness question the manuscript leaves open.

## What this means for the current claim

The negative result should be **weakened** to what the data supports:

> On seventeen tasks, with a specification written once and applied to every
> build, the probe count did not differ between two families. Because the
> counter's only source of variance is candidate count, this cannot distinguish
> "the families are equally hard" from "the counter cannot see a difference."

The bound that **is** supported is the review's own reading of the power
analysis: a null that excludes only effects of roughly one probe on a base of
five to nine, i.e. about 15% relative. That number belongs in the abstract; it
currently is not there.

## Status

Open. The positive control is the next experiment and it should be run before
any submission. Until then the null is a measurement limitation presented as a
result, which is the specific failure this programme has retracted seven times.
