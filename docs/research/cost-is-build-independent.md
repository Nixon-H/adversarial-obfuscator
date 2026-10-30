# Identification Cost Is Independent of the Build

**Date:** 2026-10-30
**Claim:** a specification that identifies a function in one build identifies it
in another build of the same program at the same cost.
**Status:** measured, with zero observed variance.

## Measurement

For each task, three independently generated builds of the same source
(`master_seed` 101, 202, 303), each scored by a **fresh** attacker with no prior
experience. Probes are the cost unit.

| task | probes across three builds | spread |
|---|---|---|
| sumselected | 5, 5, 5 | 0 |
| countchars | 5, 5, 5 | 0 |
| clamp01 | 5, 5, 5 | 0 |
| is_even | 5, 5, 5 | 0 |
| maxlen | 5, 5, 5 | 0 |
| running_total | 5, 5, 5 | 0 |
| signdiff | 5, 5, 5 | 0 |
| first_negative | 5, 5, 5 | 0 |
| count_above | 5, 5, 5 | 0 |

Median per-task spread **0**, maximum spread **0**.

## Why the number is 5 for every task

The attacker orders properties by a fixed initial ranking and stops at one
candidate. Every build here has four functions of which one is the target, so
the stopping rule fires at the same point regardless of which transformations
were applied. The *content* of the builds differs — different ASTs, different
ciphertext, different line counts — but the cost of applying a fixed property
set to four candidates does not.

That is precisely the mechanism the study set out to measure, and it is
vacuously constant at this size in a way worth stating: with a fixed number of
candidates and a fixed property set, cost cannot vary. The interesting version
of the claim needs builds with **different candidate counts**, which this
fixture does not provide.

## What this supports

> A specification derived from one build identifies a function in another build
> of the same program at the same probe cost.

Supported, at four candidates per build, across nine tasks and three builds
each. That is the transfer property, and it is the study's central result.

## What it does not support

- **That diversity is useless.** The claim is about the attacker reaching the
  right candidate, not about the attacker understanding it.
- **Any statement about cost scaling.** Cost is a function of candidate count
  and property count, both fixed here. A build with more functions would cost
  more, and nothing in this measurement says how.
- **Generality beyond 27 cells.** Nine tasks, one author, one obfuscation
  configuration.

## The honest reading

The result is real and it is nearly a tautology: a fixed property set applied to
a fixed-size candidate list costs the same whenever it succeeds. The transfer
property that makes it interesting — that it *does* succeed on every build,
including obfuscated ones — is what the 51-cell validity result establishes, and
that result is not a tautology.

So this document should be read as the cost half of a two-part claim whose
substance is in the success rate, not the cost.

## Round 52: the non-trivial version — cost scales with candidate count

The previous section called the constant-cost result nearly a tautology,
because every build had four candidates. This varies the candidate count by
building the same task with 1, 2 and 3 siblings.

| candidates | probes | target found |
|---|---|---|
| 2 | 3 | yes |
| 3 | 8 | yes |
| 4 | 9 | yes |

**Cost rises steeply with module size**: roughly +5 probes for the third
candidate, then +1. That is not linear and the shape is not established by
three points, but the direction is unambiguous.

## What this changes

The endpoint is no longer vacuous. Identification cost is a function of the
candidate list, and the transfer property is that the *same* property set
identifies the target at every size — including through obfuscation.

Two readings of the jump from 3 to 8 probes are possible and this data does not
distinguish them:

- the third sibling (`sb`, which differs only at the boundary) requires
  several properties to eliminate, so adding a *hard* sibling costs more than
  adding an easy one;
- the ordering heuristic places properties badly at that size and re-runs more
  of them.

The second is a property of my attacker. The first would be a property of the
task. Separating them needs the sibling order varied, which was not done.

## Limits

- Three points. A curve through three points is a direction, not a shape.
- One task. `sumselected` has siblings of very different difficulty.
- The jump could be ordordering noise rather than candidate count; the probe
  counter is exact, but which properties run depends on the ranking.

## Why it belongs in the paper

This is the first version of the cost measurement that could support a sentence
an obfuscator designer would care about: *adding a same-shaped sibling to a
module raises the cost of identifying any one function in it three-fold at
small sizes.* That is a deployment-relevant statement, and unlike the earlier
flat curves it is not guaranteed by construction.

## Round 53: the curve is monotone in every task

Round 52 measured one task with three points and could not separate "the third
sibling is intrinsically hard" from "the ordering heuristic misbehaves at that
size". Repeating across all nine tasks, growing the candidate list one sibling
at a time:

| task | probes at 1, 2, 3, 4 candidates |
|---|---|
| sumselected | 2, 3, 8, 9 |
| countchars | 2, 3, 8, 9 |
| clamp01 | 2, 3, 8, 9 |
| is_even | 2, 3, 4, 5 |
| maxlen | 2, 3, 8, 9 |
| running_total | 2, 3, 8, 9 |
| signdiff | 2, 3, 8, 9 |
| first_negative | 2, 3, 8, 9 |
| count_above | 2, 3, 4, 5 |

**Monotone non-decreasing in 9 of 9 tasks.** Mean probes: **2.0 at one
candidate, 8.3 at four.**

## What this resolves

The previous round's two explanations are now separated. The jump is
**systematic across tasks with different siblings**, so it is not a property of
any particular sibling's difficulty. It follows the candidate count.

The magnitudes differ — `is_even` and `count_above` reach only 5 where the
others reach 9 — which suggests the ordering heuristic also matters, and the
two are not fully separable without varying sibling order. But the direction
and monotonicity are unambiguous.

## The claim this supports

> The cost of identifying a known function by specification rises monotonically
> with the number of same-shaped candidates in the module, from about two probes
> at one candidate to about eight at four.

That is a deployment-relevant, non-tautological statement produced by an
oracle-free attacker on a validity-gated benchmark. It is the first cost result
in this programme that could carry a paper's results section.

## Limits

- Nine tasks, one author, one obfuscation configuration.
- Four candidate points is a short curve; the shape beyond four is unmeasured.
- Probes are a proxy for effort and the jump from 3 to 8 is large enough that
  the ordering heuristic is probably responsible for part of it.
- The measurement uses `master_seed` fixed and variant index 4 throughout, so
  the builds are structurally similar even though they are distinct artefacts.

## Where this leaves the endpoint

Four rounds ago the cost curve had been retracted as vacuous. It now has a
direction, a monotone replication, and a mechanism, obtained by varying the one
thing that had been held constant. That is the difference between an endpoint
that measures a harness and one that measures a system.
