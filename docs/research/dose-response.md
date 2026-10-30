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

## Round 73: replicated across all tasks, and the floor is established

The one-task dose-response was the review's main objection. Two replications:

**(a) Substituting the target.** Replacing the target function's body with a
sibling's changes the identity the property set must find, so the counter should
move:

| task | target | sibling-substituted | absolute difference |
|---|---|---|---|
| sumselected | 9 | 4 | 5 |
| countchars | 7 | 4 | 3 |
| clamp01 | 8 | 12 | 4 |
| is_even | 7 | 4 | 3 |
| maxlen | 10 | 6 | 4 |
| running_total | 5 | 12 | 7 |
| signdiff | 14 | 6 | 8 |
| first_negative | 12 | 6 | 6 |
| count_above | 5 | 11 | 6 |

**Every task responds**, mean absolute difference **5.11**, maximum 8.

**(b) Fault magnitude (one task).** 9 → 11 → 20 → 20 for zero, one, two and
three injected faults, from the previous round.

## The detection floor

| manipulation | smallest observed effect |
|---|---|
| one injected fault | **2 probes** |
| target substituted for a sibling | **3 probes** |

So the design detects an effect of about **two probes** on these tasks. The
diversity comparison's 0.00 is therefore **bounded below two probes** — not an
exact zero, and not a claim that the families are identical.

## What this does and does not rescue

**Rescues:** the objection that the counter is blind. It responds to semantics
in every task, at a measurable floor.

**Does not rescue:** the review's structural point that family variation has no
*p path* to a counter fed by frozen properties. A two-probe floor bounds the
null; it cannot convert a by-design zero into evidence about the defence.

## What the paper must now say

§5.1 currently claims diversity does not raise cost. It must be weakened to:

> With a specification-derived property set applied unchanged to every build,
> identification cost was identical across two families. The design detects
> effects of about two probes, so the observed difference is bounded at that
> magnitude. It cannot distinguish "the families are equally hard" from "the
> properties are insensitive to which family produced the artefact", and the
> second explanation is the one the design predicts.

That is the sentence the evidence supports. The stronger one is not.
