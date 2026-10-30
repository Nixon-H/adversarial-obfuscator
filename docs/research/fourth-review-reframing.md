# Fourth Review: The Bound Is a Non-Sequitur; the Paper Is a Methods Note

**Date:** 2026-10-30
**Source:** an independent review of the final draft.

## The objection that lands

> §5.3 calibrates the counter against injected boundary faults and
> target-for-sibling substitution — sensitivity to **semantic difference within
> an artefact** — while the null concerns **transform-family difference**. If
> the channel is zero by construction, the family error is zero, not "<2
> probes"; if it is not zero, §5.3 does not measure it. **It cannot be both.**

This is correct, and it invalidates the "bounded null at ~2 probes" framing I
introduced in round 74.

The calibration measures a **different quantity** from the one the null is
about. Concluding "the family difference is bounded at two probes" from a
calibration of semantic sensitivity is a non-sequitur. Either:

- family variation has no path to the counter (as §3 and §8 both say), in which
  case the expected difference is **zero by construction** and no bound is
  needed; or
- it has a path, in which case the calibration does not measure it.

So the defensible claim is the first one, stated plainly, with no bound
attached:

> A specification-derived property set applied unchanged to every build cannot
> observe transform-family variation, because its assertions are semantic and
> the transformation preserves semantics. A null from this instrument is
> therefore predicted by the design and is not evidence about the defence.

That is a **methodological warning**, not a measurement. The review's suggested
reframing — an instrument-validity note plus the reusable benchmark, gates and
reproduction — is the honest scope.

## The same defect, renamed

The review also notes that §1 says an earlier endpoint was withdrawn "because it
could not fail", while the surviving endpoint's null is predicted by
construction. That is the same defect with a new name, and the observation is
fair. The retraction record should say so rather than presenting the second
design as a repair.

## Where the review is wrong

> §5.1 reports mean difference +0.33 with sd 0.00, which is arithmetically
> impossible for integer per-task differences (three tasks at 1 gives sd≈0.47).

Checked directly:

| per-task differences | mean | sd |
|---|---|---|
| all zeros (B-vs-C) | 0.00 | **0.000** |
| all +0.33 (A-vs-B) | 0.33 | **0.000** |

The per-task differences are **identical**, not mixed: every task shows
0.33 (one build of three costing exactly one more probe) or 0.00. sd = 0.000 is
therefore correct, and the table is not mislabeled.

But the review's underlying point is right and was already recorded in round 57:
**zero variance here is arithmetic, not sampling.** `(0 + 0 + 1) / 3 = 0.33` for
every task. Reporting it as a variance estimate would be wrong; reporting it as
a per-task mean with the note "zero variance is a warning" is what the documents
do.

## What changes

1. **Withdraw the "bounded at ~2 probes" framing** from the abstract, §5.1 and
   §8. The bound does not follow from the calibration.
2. **State the analytic claim**: the instrument cannot observe family variation
   because its assertions are semantic, so the null is predicted by design.
3. **Reframe the scope** as an instrument/methods note rather than a measurement
   study, which is what the review says the residue supports.
4. **Keep the benchmark, gates, reproduction and the defect** — those are the
   reusable contributions and none of them depends on the null.

## What does not change

- The **51-cell singleton result** and its gates: a property of the benchmark,
  independent of the diversity question.
- The **module-size measurements**: the review calls them arithmetic, which is
  substantially right, but they are still the only cost numbers the instrument
  produces and they are reported with a baseline that shows information reduces
  cost by a factor of two at one candidate.
- The **obfuscator defect** and its guards: on-topic as a cost of
  diversification machinery, and the review says to quantify it rather than drop
  it — its incidence rate is measurable and is now the next task.

## Status

The paper's central claim is withdrawn a third time, now to a methods note. That
is the honest residue of four reviews, and it is worth more than the measurement
study it replaces, because a methods note that says "do not measure this way" is
checkable and a null that says "diversity does not cost" is not.
