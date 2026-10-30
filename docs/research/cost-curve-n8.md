# Cost Curve at n=8 Tasks: Still Flat

**Date:** 2026-10-30
**Method:** the same measurement as `cost-curve.md`, run across all eight
benchmark tasks at build indices k = 0, 2, 4.

The earlier curve was n=1, which was its main weakness. This replaces a
single point with a distribution.

## Result

| quantity | value |
|---|---|
| cells | 24 (8 tasks × 3 build indices) |
| cells where the attacker's property set contains at least one candidate | **24** |
| probes per cell | min 7, median 10, max 12 |
| CPU-seconds per cell | min 0.002, median 0.007, max 0.221 |
| mean CPU at k=0 | 0.033 s |
| mean CPU at k=2 | 0.010 s |
| mean CPU at k=4 | 0.008 s |

**The curve is flat, and if anything it falls.** The k=0 mean is the only
outlier and it is a cold-start artefact (first process, import cost). Nothing
in the data suggests attacker cost rises with the number of previously
analysed builds.

## What this confirms, and what it does not

It confirms at n=8 what the n=1 measurement suggested: a spec-directed
attacker's frozen property set applies unchanged to every build, because a
function's specification does not change when its source is transformed.

It does **not** show that the attacker's set identifies the target *uniquely*
in every cell: `signdiff` returns two candidates at all three build indices.
The uniqueness claim (24 of 24) comes from the evaluator, which resolves
identity by behaviour against the original — a different measurement, made
in `task-validity.md`. Reporting the two as one number would overstate the
attacker.

It does not price property authoring, which is the remaining unpriced labour.
It does not establish anything about a real corpus: eight synthetic tasks are
a calibration set.

## Sanity note

The CPU numbers are dominated by Python interpreter startup (0.002 s floor)
rather than by attacker work. Probes are the meaningful unit at this scale:
7 to 12 per cell, regardless of build index. A deployment-scale study would
need analyst-minutes, not seconds.
