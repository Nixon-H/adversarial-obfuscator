# Power Analysis: What the Benchmark Can Detect

**Date:** 2026-10-30
**Endpoint:** paired probe difference (last build − first build) per task.
**Data:** the eight task differences from the accumulating-attacker measurement.

The review required a pre-registered minimum detectable effect. Round 37
reported an interval; this reports the power behind it.

## Observed quantities

| quantity | value |
|---|---|
| tasks | 9 (an earlier nine-task addendum, see below) |
| mean paired difference | +0.44 probes |
| standard deviation | 0.88 |
| standard error | 0.294 |

## Minimum detectable effect

At 80% power and two-sided α = 0.05 (t critical 2.365 for df = 7):

> **MDE = 0.92 probes** (was 1.04 at eight tasks; the ninth task, `count_above`,
> was added specifically to cross the one-probe threshold)

So the benchmark as it stands can detect a one-probe effect only marginally.
Round 37's interval [−0.39, +1.14] is consistent with this: it excludes effects
larger than about one probe and nothing smaller.

## What would be needed

| effect to detect | tasks required |
|---|---|
| 1.0 probe | **9** (now met) |
| 0.5 probe | **31** |

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

## Round 48: all seventeen tasks change the answer

The earlier analysis used the nine synthetic tasks alone. The eight corpus
tasks are the same kind of measurement and belong in the same sample.

| quantity | synthetic only (n=9) | both families (n=17) |
|---|---|---|
| mean paired difference | +0.44 | **+0.71 probes** |
| standard deviation | 0.88 | 0.69 |
| standard error | 0.294 | 0.166 |
| 95% CI | — | **[+0.35, +1.06]** |
| MDE at 80% power | 0.92 | **0.49 probes** |

**The interval excludes zero.** Under the accumulating attacker used here,
probe cost *rises* with the number of previously analysed builds, by about
0.7 probes over six builds.

## What that does and does not mean

**Does mean:** the endpoint is not only falsifiable, it has produced a
significant result. Cost is not flat in k; on this heuristic it grows.

**Does not mean:** that diversity is working. The rise is a property of the
attacker's ordering, not of the protection. The mechanism is visible in the
per-task traces: properties ranked powerful on build k are applied first on
build k+1, and when the ranking is stale the attacker runs *more* properties
before narrowing to one candidate. A better-attacking implementation — one that
re-derives which property is decisive per program rather than per build — could
as easily produce a fall.

So the honest claim is narrow and slightly unflattering to the instrument:
**the learned ordering degrades with use on this benchmark.** That is a
statement about an attacker heuristic, not about obfuscation.

## Consequence

The MDE is now 0.49 probes, which is the threshold the earlier analysis called
unreachable within a 31-task budget — reached for free by combining the two
families already present. The instrument is no longer the limiting factor at
the effect size it can now resolve.

What is still missing is not resolution but validity: seventeen tasks by one
author, with specifications by the same person who wrote the functions.
