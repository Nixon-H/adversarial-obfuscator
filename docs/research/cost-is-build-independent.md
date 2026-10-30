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
