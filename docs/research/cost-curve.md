# Cost Curve: Diversity Buys Nothing at Identification (k = 0..5)

**Date:** 2026-10-30
**Script:** `scripts/transfer/cost_curve.py`
**Currency (protocol v3):** CPU-seconds of attacker tooling, plus 0.5 s per
target execution. Probes counted separately.

## The measurement

One task (`sumselected`, four same-arity siblings), six builds of the same
program with different seeds, a frozen property set applied to each.

| k (builds previously seen) | identifiable | probes | charged seconds |
|---|---|---|---|
| 0 | yes | 13 | 6.205 |
| 1 | yes | 13 | 6.514 |
| 2 | yes | 10 | 5.021 |
| 3 | yes | 13 | 6.019 |
| 4 | yes | 13 | 6.511 |
| 5 | yes | 10 | 5.018 |

**The curve is flat.** Identification succeeds at every k, probe counts stay
between 10 and 13, and charged time stays between 5.0 and 6.5 seconds. The
variation is candidate-ordering noise, not a trend.

## What this means

Protocol v3 asked for exactly this and said both directions were publishable:

> If cost flattens at k=1, per-build diversity buys nothing and deployers
> should stop paying for it. If it keeps rising, that is the first credible
> evidence for per-build source diversification.

The answer here is the first: **flat at k = 0**, not even at k = 1. The
property set transfers perfectly because the specification of a function does
not change when its source is transformed, and a property set is the
attacker's actual asset.

## Why the shape attacker could not have produced this

The shape heuristic (rounds 10–11) failed on siblings regardless of
obfuscation, so its cost curve would have measured noise. The spec attacker
succeeds on both, so its curve is meaningful: it is flat because the attack
does not depend on anything the transformation changes.

## Limits

1. **n = 1 task.** One function, four siblings, six builds. This is a
   measurement, not a corpus result.
2. **The property set is given.** Its authoring cost is not in the curve,
   and authoring is the analyst labour a real study must price. If writing
   properties per task is expensive, that cost is real but it is paid once
   per task, not once per build -- so it does not create a k-dependence.
3. **Identification only.** Cost to *understand* or *modify* a recovered
   function is not measured and could behave differently.
4. **Probe counts are small** (10–13), so the charged time is dominated by
   Python startup and build cost rather than by attacker effort. A
   deployment-scale study should measure analyst-minutes, not seconds.

## Consequence

Two of the three calibration results now agree, and the third (round 10's
3/3) is explained by corpus easiness rather than protection. Together they
support one honest statement at this scale:

> For function identification in Python source, per-build diversity of the
> kind tested does not raise attacker cost: the specification an attacker
> uses is invariant to the transformation, and the frozen property set
> applies unchanged to every build.

That is a negative result about the protection. It is publishable as a
benchmark/measurement contribution only with the corpus and the priced
authoring cost the protocol still requires.
