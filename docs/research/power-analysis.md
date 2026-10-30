# Power Analysis: What the Benchmark Can Detect

**Date:** 2026-10-30
**Endpoint:** paired probe difference (last build − first build) per task.
**Data:** the eight task differences from the accumulating-attacker measurement.

The review required a pre-registered minimum detectable effect. Round 37
reported an interval; this reports the power behind it.

## Observed quantities

| quantity | value |
|---|---|
| tasks | 8 |
| mean paired difference | +0.38 probes |
| standard deviation | 0.92 |
| standard error | 0.324 |

## Minimum detectable effect

At 80% power and two-sided α = 0.05 (t critical 2.365 for df = 7):

> **MDE = 1.04 probes**

So the benchmark as it stands can detect a one-probe effect only marginally.
Round 37's interval [−0.39, +1.14] is consistent with this: it excludes effects
larger than about one probe and nothing smaller.

## What would be needed

| effect to detect | tasks required |
|---|---|
| 1.0 probe | **9** |
| 0.5 probe | **35** |

Nine tasks is one more than the current eight, which means the benchmark is
**marginally underpowered for exactly the effect it reports a bound on**. That
is worth saying plainly: the bound in round 37 is about one probe, and the
design that produced it had barely enough tasks to support a bound of that
size.

## What this does not cover

- **The validity endpoint.** Forty-eight of forty-eight cells have unique
  identity, which is a census of the benchmark rather than an estimate from a
  sample. No power calculation applies; the benchmark is what it is.
- **Task heterogeneity.** The standard deviation is computed across eight
  tasks written by one author on similar problems. Real corpora would be more
  variable, so the 35-task figure is a lower bound for that case, not an
  estimate.
- **Probes as effort.** A probe-count MDE says nothing about analyst time.

## Consequence for the study design

Two actionable numbers:

1. **Add one task** and the design reaches 80% power for a one-probe effect at
   the observed variance. That is cheap and should be done before any
   confirmatory comparison.
2. **A half-probe effect is out of reach** without roughly four times the
   benchmark. If the real effect is that small — plausible, since learned
   ordering can help or hurt — then this instrument cannot settle the question
   at any corpus the plan can afford, and the honest endpoint is the bound
   rather than a verdict.

The second is the more important statement. It defines the limit of what this
line of work can conclude, which is a more useful contribution than another
number inside the current resolution.
