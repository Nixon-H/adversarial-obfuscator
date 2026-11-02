# The "No Channel" Claim Is False: Family Changes Callable Count, and Count Drives Cost

**Date:** 2026-11-02, round 257. Found by the cold-review subagent and confirmed by direct
measurement.

## The measurement

For three synthetic tasks at build index 4, seed 11, counting module-level callables in the
emitted artefact and taking the probe count from the same attack:

| task | A | B | C |
|---|---|---|---|
| `sumselected` | 4 callables, **8 probes** | 5 callables, **9 probes** | 5 callables, **9 probes** |
| `countchars` | 4, **6** | 5, **7** | 5, **7** |
| `clamp01` | 4, **7** | 5, **8** | 5, **8** |

**Family A inserts one fewer module-level callable than B and C, and costs exactly one probe
less.** B and C insert the same number and cost the same.

## What that means for §5.1

The paper claims the property set has **"no channel by which transform-family variation could
reach it"**, and that the null is therefore predicted by construction.

**There is a channel.** Transform family → number of module-level callables inserted → module
size → probe count. The paper's own §5.2 shows that module size is what moves the counter
(2.0 probes at one candidate, 8.6 at four). The diversity comparison never controlled for it.

The arithmetic follows exactly:

- **A-vs-B = +0.33** — one extra probe in one of three seed pairings.
- **B-vs-C = 0.00** — not because families are invisible, but because **B and C insert the same
  number of callables**, so the difference cancels.

The 0.00 that anchors §5.1 is an **artefact of two families happening to add equal counts**, not
evidence of an absent channel.

## What survives and what does not

| claim | status |
|---|---|
| a semantic property set cannot observe a semantics-preserving transform | **survives** — that part is true |
| therefore the diversity null is predicted by construction | **FALSIFIED** — the channel is structural, not semantic |
| B-vs-C 0.00 is evidence about diversification | **falsified** — it is evidence about equal callable counts |
| module size drives the counter | **strengthened** — it explains the family differences too |

## The corrected claim

> The property set cannot observe *semantic* transformation. It **can** observe *structural*
> transformation: families that insert different numbers of module-level callables are
> distinguishable, and the probe count tracks that number. A family comparison therefore
> measures **callable-count difference**, not family diversity, unless the count is held
> constant.

That is a sharper and more useful result than the one withdrawn. It says the metric is not blind
to provenance — it is blind to *semantics* and sensitive to *structure*, and the benchmark
conflated the two.

## The experiment this implies

Re-run the A/B/C comparison with **callable count matched** across families: pad A with a no-op
callable, or strip one from B and C, so all three insert equal counts. If the difference is then
0.00, the channel is entirely structural and the corrected claim above is exactly right. If a
difference remains, there is a second channel and §5.1's original question is partly open.

**Not run.** It is the obvious next experiment and it is one script.

## Why this took 257 rounds to find

Four prior reviews examined the properties, the statistics and the design. None counted the
callables in the output. The cold reviewer did, because it had no investment in the framing —
which is the argument for a fifth review from outside, and the thing the programme said it could
not obtain.
