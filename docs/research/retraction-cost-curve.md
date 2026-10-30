# Retraction: the Cost Curve Measured a Memoryless Attacker

**Date:** 2026-10-30
**Retracts:** the interpretation of `cost-curve.md`, `cost-curve-n8.md`, and
the primary endpoint as written in `protocol-v3.md` §6.
**Found by:** an independent reviewer (round 34), reading the protocol and the
attacker interface together.

## What was claimed

> Attacker cost per target as a function of *k* previously analysed builds is
> flat, therefore per-build diversity does not raise identification cost.

## Why that claim is vacuous

The attacker's `develop()` takes **one build** and returns an artefact. The
five oracle-free guards enforce that it never carries evaluator information.
There is no path by which analysing build 1 could make analysing build 2
cheaper or dearer: the property set is frozen, and the same frozen set is
applied to each build independently.

So *k* is not a treatment. It is a label recording which build was served.
A memoryless attacker applied twenty-four times must cost the same each time,
and measuring that it does is measuring the harness, not the defence.

The reviewer's phrasing is exact: the endpoint "cannot fail". A tautology was
reported as a measurement.

## What is still true

The measurements themselves are correct — the numbers in `cost-curve-n8.md`
were produced by the code they describe. What is wrong is the **causal
attribution**. "We attribute this to the specification being invariant" is an
assertion over an instrument that could not have detected the opposite.

Two further problems the same reading exposes:

1. **The currency is dominated by setup.** CPU per cell is 0.002–0.221 s with a
   median of 0.007; the 0.033 → 0.010 → 0.008 sequence is a *decreasing*
   estimate explained as cold start and then cited as "if anything it falls".
   That is setup noise being narrated as a trend.
2. **A null claim needs an equivalence test.** Three *k* values, no pairing,
   no intervals, no pre-registered minimum detectable effect. Failing to see a
   rise in noise-dominated seconds with n=8 is not evidence of absence.

## What the endpoint requires

The reviewer's proposed replacement, which I accept:

> An **accumulating** attacker holding persistent per-program state — property
> set, feature weights, transform-fire fingerprints — updated after each build
> and scored on build *k+1* using only accumulated state, under matched
> cumulative CPU, against a from-scratch attacker at k=0, with a pre-registered
> equivalence bound.

That design can yield either sign. The current one cannot.

## What is not retracted

- The **benchmark validity** work (`task-validity.md`): 48 cells across two
  families, each with a unique evaluator-decided identity. That is a property
  of the tasks and the builds, not of the attacker's memory.
- The **oracle-free attacker** and its guards. They are the reason the design
  is honest about what the attacker can see; the flaw is in what the attacker
  is allowed to *remember*, not in what it may read.
- The **correctness defect and its fix**. Post-fix, 40 seeds with
  `dead_code + opaque_pred` all preserve the target, against about one in
  twelve before.

## Status

The primary endpoint is **withdrawn pending redesign**. Any claim of the form
"diversity does not raise attacker cost" is unsupported until the accumulating
attacker exists and the equivalence bound is pre-registered.

This is the fourth conclusion in this programme retracted after re-reading the
instrument rather than the result, and the largest: three of the earlier
retractions were harness bugs, this one is a design error in the endpoint
itself.
