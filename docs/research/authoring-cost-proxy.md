# Pricing Property Authoring: A Reproducible Proxy

**Date:** 2026-10-30
**Method:** for each task, find the smallest subset of evaluator inputs that
separates the target from every sibling, at each of the three build indices.

Property authoring is human labour and this session cannot time a human. What
it can measure is a reproducible proxy: **how much specification is actually
required to identify the target**, which bounds the authoring effort from
below and is the same number for anyone repeating the measurement.

## Result

| task | properties authored | minimum inputs to separate |
|---|---|---|
| sumselected | 4 | 1 |
| countchars | 4 | 1 |
| clamp01 | 5 | 2 |
| is_even | 4 | 2 |
| maxlen | 4 | 2 |
| running_total | 4 | 1 |
| signdiff | 4 | 1 |
| first_negative | 4 | 2 |

**38 properties authored across nine tasks** (4–5 each); the minimum needed
to separate is **1–2** (median 1.5, max 2).

*(Corrected round 69: this read 33 across eight tasks before the ninth task was
added in round 47. `reproduce.py` regenerates the count from the task files.)*

## What this says

- **Authoring is small at this scale**: four or five executable assertions per
  task, which is minutes of work for someone who knows what the function does.
- **Most properties are redundant for identification.** One or two suffice.
  The surplus is not waste: it is what makes the set robust to a build that
  perturbs a boundary, which is exactly the case the sibling fixtures test.
- **The cost scales with tasks, not builds.** The same property set applies
  unchanged across build indices. That is one reason the earlier cost curve
  could not have detected a build effect even if one existed: the labour is
  paid once per task, so it cannot enter a per-build measurement. The endpoint
  itself was later withdrawn and replaced (see `retraction-cost-curve.md`).

## What it does not say

- It is **not** analyst-minutes. A person writing these assertions also has to
  read the obfuscated artefact, decide what to test, and iterate when a
  property is wrong — none of which is measured here.
- It does **not** generalise to a real corpus, where a specification may be
  ambiguous, missing, or expensive to reconstruct from documentation.
- It prices *identification* only. Understanding or modifying a recovered
  function needs different, probably larger, effort.

## Why it still belongs in the paper

The review's second-ranked failure mode was corpus infeasibility: 10,800
attack runs with no cost model. This gives the model a first term — the
labour per task is **four assertions**, and it is paid once per task rather
than once per build. That is a small number, and it is the number that
decides whether the study is feasible at all.
