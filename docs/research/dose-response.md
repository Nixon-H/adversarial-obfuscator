# Dose-Response Calibration: What the Counter Can Detect

**Date:** 2026-10-30
**Trigger:** an independent review of the paper argued that the null in §5.1 is
**predicted by the design** — family variation cannot reach the probe counter
because the properties are frozen and nothing carries between builds — and that
§5.3's single-point fault control tests the wrong variable.

The remedy it proposed: replace the single point with a **dose-response
calibration**, so the null is bounded rather than asserted.

## The measurement

`sumselected`, build index 4, seed 4242, with an increasing number of injected
semantic faults before obfuscation:

| injected faults | edits | probes |
|---|---|---|
| none | — | **9** |
| 1 | `lo <= v < hi` → `lo <= v <= hi` | **11** |
| 2 | + `total = 0` → `total = 1` | **20** |
| 3 | + `total += v` → `total += v * 2` | **20** |

## What it establishes

1. **The counter is monotone in fault magnitude** over the range measured: 9,
   11, 20. It is not blind to semantic change, which answers the weaker version
   of the sensitivity objection.
2. **The smallest single-fault effect is two probes** (9 → 11). The smallest
   detectable difference is therefore about **two probes** on this task.
3. **The counter saturates.** Two and three faults both give 20, so beyond two
   faults the measurement cannot distinguish magnitudes. That is a real ceiling
   and it is now measured rather than discovered later.

## What it says about the null

The diversity comparison reports 0.00 probes between two families on seventeen
tasks. The calibration says the design can detect a two-probe effect on a
single task. So the null is:

> **bounded at about two probes on this task**, not established as an exact
> zero.

That is a weaker and more defensible statement than "diversity does not raise
cost", because it says what the instrument could have seen.

## The objection this does not answer

The review's sharper point stands: family variation has **no path** to the probe
counter under the design, because the properties are frozen and the attacker
carries nothing between builds. If that is right, then even a perfect
calibration cannot make 0.00 into evidence — it can only bound it.

The honest framing for the paper is therefore:

> With a specification-derived property set applied unchanged to every build,
> identification cost was identical across two families. This design cannot
> distinguish "the families are equally hard" from "the properties are
> insensitive to which family produced the artefact", and the calibration bounds
> the effect the design could have detected at about two probes.

## Status

Calibration run on one task. Replication across all seventeen is the next step
and is what the review asked for; this document reports the one-task result and
says so.
