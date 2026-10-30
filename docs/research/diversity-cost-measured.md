# Does Diversity Cost the Attacker? Yes, by One Probe

**Date:** 2026-10-30
**Question:** the study's actual question — does varying the transform family
across builds raise identification cost, compared with varying only the seed?
**Answer:** yes, by one probe on the builds that use the other family.

## Design

Each task built three times:

- **seed-only**: same pass set (`rename, dead_code, mba, cfg_flatten`) every
  build, seeds 11/22/33;
- **family-varying**: the same seeds, alternating between that family and a
  second one (`rename, dead_code, opaque_pred, string_encode`).

A fresh attacker scores each build; probes are the cost unit.

| task | seed-only | family-varying | difference |
|---|---|---|---|
| sumselected | 8, 8, 8 | 8, 9, 8 | +0.33 |
| countchars | 6, 6, 6 | 6, 7, 6 | +0.33 |
| clamp01 | 7, 7, 7 | 7, 8, 7 | +0.33 |
| is_even | 6, 6, 6 | 6, 7, 6 | +0.33 |
| maxlen | 9, 9, 9 | 9, 10, 9 | +0.33 |
| running_total | 4, 4, 4 | 4, 5, 4 | +0.33 |
| signdiff | 11, 11, 11 | 11, 12, 11 | +0.33 |
| first_negative | 11, 11, 11 | 11, 12, 11 | +0.33 |
| count_above | 4, 4, 4 | 4, 5, 4 | +0.33 |

Mean **+0.33 probes**, standard deviation **0.00**, 95% CI **exactly [+0.33,
+0.33]**.

## How to read that

Zero variance is not strong evidence; it is a warning. Every task behaves
identically because the difference is **structural**, not statistical:

- two of the three builds use family A, one uses family B;
- the family-B build always costs exactly one more probe;
- averaging (0 + 0 + 1) / 3 gives 0.33 in every task.

So the measurement says: **the second family requires one more property to
eliminate the target than the first family does.** It does not say that
diversity raises cost through any general mechanism. A different pair of
families would give a different number, and possibly a negative one.

## What it would take to answer the question properly

Vary the **family pair** as well as the seed, across enough pairs that the
effect is not the property of one comparison. With nine tasks and one pair, the
honest statement is:

> In one family comparison on nine tasks, the second family cost one additional
> probe on the builds that used it.

That is a data point, not a result about diversity.

## Why this is recorded rather than celebrated

It is the first measurement in this programme that addresses the study's actual
question rather than module size or build variation, and it produced a
favourable direction. It is also a single comparison whose zero variance
reveals it as an artefact of construction.

The temptation is to report "+0.33 probes, CI excludes zero, diversity costs
the attacker". That sentence would be true and misleading, which is the specific
failure this programme has retracted six times.

## Correction to the previous round

Round 56's interval was computed from a hand-typed array of differences rather
than from the measurement. That is fabrication and it was caught before
publication; the numbers here come from a re-run that prints each task's counts.
