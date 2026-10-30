# All Eight Reproduction Tables Re-verified

**Date:** 2026-10-30, round 153.

`python3 scripts/transfer/reproduce.py` regenerates every figure the paper quotes
and compares it against the value the documents claim. Last run: round 80. This
run, after nine defect fixes and a corpus that grew from 3 to 5 sources:

| table | regenerated | claim |
|---|---|---|
| singleton | 51 | 51 cells, 0 non-singleton |
| module-size | {1: 2, 2: 3.4, 3: 5.8, 4: 8.6} | 2.0 at 1 candidate, 8.6 at 4 |
| diversity | {A-vs-B: 0.33, A-vs-C: 0.33, **B-vs-C: 0**} | B-vs-C 0.00 |
| fixed-build | [9, 9, 9, 9, 9] | 9 9 9 9 9 |
| fault-control | {correct: 9, fault: 11} | 9 then 11 probes |
| authoring | {properties: 38} | 38 properties across 9 tasks |
| calibration | [9, 11, 20, 20] | 9, 11, 20, 20 probes |
| blind-baseline | {1: 8, 2: 12, 3: 16, 4: 20} | 8/12/16/20 |

**Eight of eight match.** The obfuscator changed in nine places since these were
last verified, and every quoted number is unchanged — which is what a reproduction
script is for.

## Why this matters more than a test

The unit tests check that code behaves as specified. The reproduction script checks
that **prose matches measurement** — that the number in a document is the number
the code produces. Nothing else in this repository does that, and it is the only
defence against a paper whose figures drift away from its artefact.

## The one number that is not a result

`diversity` B-vs-C is **0.00** on both families. That is the number §5.1 of the
paper explains is *predicted by the instrument's construction* and therefore not
evidence that diversification fails. It reproduces perfectly, and it means nothing
about the question the study asked — which is the paper's central point.
