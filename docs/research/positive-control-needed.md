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

## Round 62: the positive control, run

The review's charge was that the probe counter cannot register a difference it
was not built to see, so a B-vs-C null cannot distinguish "equally hard" from
"insensitive". The way to test that is to inject a difference the counter *must*
see if it can see anything.

Injected fault: the target's bound changed from `lo <= v < hi` to
`lo <= v <= hi`, applied before obfuscation:

| build | probes | passing |
|---|---|---|
| correct | **9** | 1 |
| boundary fault | **11** | 1 |

**The counter registers the fault: 9 → 11 probes.** It is not blind, so the
null in the diversity comparison is not automatic insensitivity. That part of
the review's objection is answered.

## And the control found something worse

The attacker still reports **one passing candidate** on the faulted build — and
it is the wrong one. The sibling `sb` is written `lo < v <= hi`; the faulted
target became behaviourally identical to `sb`, so the property set accepted the
sibling in place of the target.

So the counter is sensitive but the **identities are not**:

> A specification that pins the boundary catches the fault as a candidate-level
> change but cannot tell the faulted target from the sibling that always had
> that behaviour.

That is a real limitation of the benchmark, not of the fault: `sb` and a
boundary-faulted target are the same function, and no specification can
separate two identical functions. The right reading is that the fault control
needs a target with **no behaviourally identical sibling** — which this task
does not have.

## What the control establishes

1. **The counter is not blind.** It moved by two probes on a known semantic
   change. The review's strongest charge — that seventeen tasks were seventeen
   replications of an insensitive harness — does not hold for the counter.
2. **The diversity null is still weak for a different reason.** Sensitivity of
   the *counter* is not sensitivity of the *comparison*: a deterministic counter
   that responds to semantics can still produce zero for two families that
   happen to cost the same. The null needs families chosen to differ, which is
   the family-space limitation already recorded.
3. **The benchmark has a sibling-collision hazard.** A fault can make the target
   indistinguishable from a sibling, and then identification is undefined. That
   is a task-design constraint worth stating: siblings must differ from the
   target on **any** plausible fault, not merely on the tested inputs.

## Status

The control is run and its result is mixed: it rescues the counter from the
insensitivity charge and adds a new limitation to the benchmark. Both are now
written down. The claim in the manuscript should say "the counter responds to
semantic change (9 → 11 probes on a fault control)" alongside the null, and
should not claim the null demonstrates equal difficulty.
