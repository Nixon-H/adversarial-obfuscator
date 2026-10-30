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

## Round 35: a first step toward the redesign, and why it is not enough

`scripts/transfer/accumulating_attack.py` now carries state across builds:
it records a per-build transform fingerprint and which properties were
informative, and it exposes `observe()` and `apply()` as separate steps so the
state exists between builds.

It does **not** yet close the retraction. Measured on six builds it discovers
that all four properties are "useful" and therefore skips none, so the cost
remains what it was: a frozen set applied repeatedly. The mechanism that would
make cost depend on k — skipping properties that carry no information —
exists in code but has nothing to skip on this task.

So the endpoint stays withdrawn. What now exists is the scaffold the real
design needs: persistent state, a separate observation phase, and a place for
utilisation to be measured once the state actually discriminates.

## What the next attempt must show

1. State that **discriminates**: an attacker that, after build k, runs fewer
   probes on build k+1 than a from-scratch attacker at k=0, with both reaching
   the same identification.
2. Cost measured in a currency with no startup floor, because interpreter
   startup (0.002 s) dominates at this scale.
3. A pre-registered equivalence bound, so a null is a result rather than a
   failure to detect.

Until all three hold, no claim about diversity and attacker cost is supported.

## Round 36: the endpoint is now falsifiable, and the sign is mixed

The attacker now orders properties by elimination power learned on earlier
builds and stops when one candidate remains. That makes cost a function of k,
which the previous design could not be.

Probes per build, six builds per task, eight tasks:

| task | k=0..5 |
|---|---|
| sumselected | 8 7 7 6 7 7 |
| countchars | 6 7 7 6 7 7 |
| is_even | 6 7 7 6 7 7 |
| maxlen | 9 10 10 9 10 10 |
| running_total | 4 5 5 4 5 5 |
| signdiff | 11 12 12 11 12 12 |
| first_negative | 11 10 10 9 10 10 |

**Probes fall in 2 tasks, rise in 2, and stay flat in 4.** The endpoint can now
yield either sign — the reviewer's central objection is addressed — but the
sign is not a consistent reduction.

The rise is informative: learned ordering can be *worse* than a fixed order,
because a property that was powerful on build k may be weak on build k+1 and
the attacker has no way to know before running it. That is a real property of
accumulating analysis, not a bug, and it is the kind of result the old
endpoint could not have produced.

## What this does and does not support

**Supports:** cost is k-dependent; learned ordering transfers unevenly; the
mechanism can help or hurt. Each of those is now measurable.

**Does not support:** any claim that accumulation reduces cost, or that
per-build diversity helps or hurts. Two tasks down, two up, four flat is not a
result at n=8 with no equivalence bound.

**Still required:** the currency problem (probes are now the unit, which avoids
the interpreter-startup floor that dominated seconds), a pre-registered
equivalence bound, and a corpus large enough that 2-of-8 is not the whole
sample.
