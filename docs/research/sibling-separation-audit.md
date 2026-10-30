# Sibling Separation Audit

**Date:** 2026-10-30
**Trigger:** the round-62 positive control found that a fault can make a target
behaviourally identical to a sibling. This audits how close the nearest sibling
is in every task, using the attacker's own property set.

## Method

For each task, count how many of its properties the **closest sibling fails**.
A property the sibling fails separates it from the target; a property it passes
does not.

## Result

| task | properties the closest sibling fails |
|---|---|
| maxlen | 1 |
| running_total | 2 |
| **signdiff** | **0** |
| first_negative | 1 |
| count_above | 2 |
| (others) | 2–4 |

Median **2**. One task — `signdiff` — has a sibling that passes **all four**
properties.

## The signdiff case, in detail

| subject | property results |
|---|---|
| target | True, True, True, True |
| sibling 0 | False, False, False, False |
| sibling 1 | True, False, True, True |
| **sibling 2** | **True, True, True, True** |

Sibling 2 uses `a >= 0` where the target uses `a > 0`. It differs **only** when
`a` is zero, and no attacker property supplies a zero — the evaluator does, in
the `(0, -1)` input added in round 23.

So the attacker cannot separate them, and its passing set contains two
candidates. The evaluator resolves the identity, and the "hit" recorded for this
task is an **intersection**, not a unique identification.

## Why this is not new

Round 24 recorded exactly this: the attacker returns two candidates on
`signdiff` at every build index, and the doc states that "hit" means the
attacker's set intersects the truth, not that it is a singleton.

This audit adds the general form: **one of seventeen tasks has an
attacker-inseparable sibling, and the median task is separated from its nearest
sibling by two properties.** That is enough separation for the benchmark to be
meaningful and thin enough that the control's fault finding was not spurious.

## What it changes

Nothing in the results. It converts an incidental observation into a measured
property of the benchmark, and it identifies the task where the attacker's
specification is weakest.

The honest fix would be to give `signdiff`'s properties a zero-valued input, so
the attacker can separate what the evaluator already can. That is a one-line
change and it would remove the last task where the attacker's set is not a
singleton.

## Status

Audit complete. The benchmark's separation is adequate, its weakest task is
named, and the reason "hit" is a weaker criterion than "unique" is now measured
rather than remembered.
