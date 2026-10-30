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

## Round 64: the fix applied, and every task is now a singleton

The audit named one task where the attacker's set contained two candidates.
Adding a zero-valued property input to `signdiff` separates it from the sibling
that used `a >= 0`:

| subject | property results |
|---|---|
| target | True, True, True, True, **True** |
| sibling 0 | False, False, False, False, False |
| sibling 1 | True, False, True, True, False |
| sibling 2 | True, True, True, True, **False** |

The sibling that previously passed everything now fails the new property, so the
attacker's set is a singleton.

Verified across the whole synthetic benchmark at build index 4:

| task | attacker's passing set size |
|---|---|
| all nine | **1** |

And the validity result is unchanged: 27 of 27 cells with unique evaluator
identity and an attacker hit.

## What this changes

The "hit" criterion is now a **singleton** criterion on the synthetic benchmark
rather than an intersection. That is a stronger statement, and it removes the
last place where the attacker could claim success on two candidates at once.

It does not change any measured effect — the diversity null, the module-size
scaling, and the order invariance are all measured in probes, not in set sizes.
It changes what the word "hit" means, which is the kind of change worth making
before a paper uses the word.

## What remains

The corpus benchmark was not audited the same way. Its eight tasks pass the
evaluator gate, and whether their attacker sets are singletons has not been
checked. That is the next audit, not a current claim.

## Round 65: the corpus benchmark is singleton too

The previous round audited the synthetic tasks and left the corpus tasks
unmeasured. At build index 4, every corpus task's attacker set has size 1:

| task | passing set |
|---|---|
| rle_encode | 1 |
| rle_decode | 1 |
| slugify | 1 |
| gcd | 1 |
| priority_pick | 1 |
| rotate_list | 1 |
| store_get | 1 |
| store_keys | 1 |

## Combined state

| benchmark | tasks | attacker set size | evaluator identity |
|---|---|---|---|
| synthetic | 9 | **1 everywhere** | unique |
| real corpus | 8 | **1 everywhere** | unique |
| **total** | **17** | **singleton** | **unique** |

So "the attacker identifies the target" now means the same thing on both
benchmarks, and it means a **singleton**: one candidate passes, and it is the
right one.

## What the audit sequence produced, across three rounds

1. A positive control injected a fault, and the counter registered it
   (9 → 11 probes) — but the faulted target collided with a sibling, revealing
   a hazard.
2. The hazard motivated an audit that found one task where the attacker's set
   held two candidates, and named why (no zero-valued property input).
3. The fix was one property, and both benchmarks now identify uniquely.

Three rounds, one control, one measurement, one line. The result is not a new
finding — it is a benchmark property that was assumed and is now verified, on
both families.

## What remains unverified

- **Build indices other than 4.** The audit checked one index per task. Whether
  a different build re-introduces a collision is unmeasured.
- **The family effects.** The singleton property says the attacker finds one
  candidate; it says nothing about how many probes it takes across builds, which
  is where the cost measurements live.

Recorded so that "singleton" is not over-claimed: it is a property of these
seventeen tasks at one build index each, verified on both benchmark families.

## Round 66: complete across build indices — 51 cells, zero failures

The previous round audited one build index per task and said so. Checking all
three (k = 0, 2, 4) across both families:

| benchmark | tasks | build indices | cells | non-singleton |
|---|---|---|---|---|
| synthetic | 9 | 3 | 27 | **0** |
| real corpus | 8 | 3 | 24 | **0** |
| **total** | **17** | **3** | **51** | **0** |

Every cell has exactly one candidate in the attacker's passing set.

## What the benchmark now claims, and with what support

> On seventeen tasks across two families and three build indices each, a
> specification-derived property set identifies exactly one candidate, and it is
> the target, in all fifty-one cells.

Support:

- the **evaluator** decides identity independently of the attacker, on inputs
  the attacker never sees;
- the **attacker's** set is checked separately and is a singleton;
- the **siblings** differ from the target by a median of two properties, with
  the thinnest case now at one, after the `signdiff` fix;
- the **counter** was shown to respond to a semantic change (9 → 11 probes on
  an injected fault), so an all-zero error rate is not an insensitive counter.

## What is still not claimed

- **Understanding.** Identification is not comprehension; nothing here measures
  whether an analyst could explain or modify the recovered function.
- **Generality.** Seventeen tasks, one author, one obfuscation configuration.
- **Independence.** The corpus tasks come from this repository, so their
  specifications were written by the same person who chose them.

The benchmark is internally consistent and externally limited, and the document
separates those two statements.
