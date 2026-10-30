# Build Nondeterminism: Measured, Not Assumed

**Date:** 2026-10-30
**Method:** eight `pipeline build --pin-structure` runs on one source file, each in
its own directory, then pairwise comparison of the normalised artefacts.

This replaces "about 100 differing lines" — a figure that had been quoted
from a single pair — with a distribution and a structural verdict.

## Measurements

| quantity | value |
|---|---|
| artefact size, 8 builds | 414,988 – 415,302 bytes |
| size spread | **314 bytes (0.08%)** |
| pairwise differing lines, 28 pairs | min 100, median 100, max 176, mean 119 |
| distinct ASTs across 8 builds | **8 of 8** |
| build success | 8/8 |

Normalisation before comparison: string blobs over 40 chars, hex literals
over 16 digits, and byte literals over 12 bytes replaced by placeholders.
Without normalisation the diffs are dominated by ciphertext and say
nothing about structure.

## What this means

**The artefacts are behaviourally equivalent but structurally distinct.**
All eight AST dumps differ. The differing lines are few (median 100 of
~4,200, about 2.4%), so the *shape* is nearly the same, but "nearly"
is not "identical": a paired statistical test that assumes a common
artefact across builds would be comparing different programs.

Consequences, stated as constraints on the study rather than as a wish:

1. **Recovery-rate inference must not treat builds as paired.** Every build
   has its own AST. A per-build recovery rate is a legitimate observation;
   a paired difference between two builds that shares an artefact is not.
2. **Cost measurement is unaffected.** The cost endpoint asks how long an
   attacker takes to reach a threshold on a given artefact. Two artefacts
   that behave identically and differ in 2.4% of lines are interchangeable
   for that purpose, and the 0.08% size spread bounds the measurement error
   far below any plausible effect.
3. **The divergence is structural, so "pinned" means "seeded", not
   "reproducible".** `--pin-structure` fixes the transform choices; it does
   not make the output reproducible. That distinction belongs in the paper's
   methods section, not its limitations footnote, because it changes which
   analyses are valid.

## Why this is enough to unblock the pilot

The pilot's primary endpoint is the cost curve (protocol v3). The measured
variation is 0.08% in artefact size and 2.4% in line count, which cannot
produce a cost effect of the size the study needs to detect. The recovery
endpoint, if reported at all, must be reported as an unpaired per-build
rate.

What this does **not** establish: that the *behaviour* is identical. That
requires the differential test suite, which the protocol already requires
as gate G4 and which has not been run across all eight builds here.

## Reproduction

The runs are not stored in the repository (each artefact is ~415 KB and
they are build outputs, not sources). The method is three commands:

```
for i in 1..8: cp fixture h.py into its own dir; python3 -m obfuscator.core.pipeline build <dir>/h.py --pin-structure
normalise each dist/*_dbg.py (blobs, hex, byte literals → placeholders)
pairwise unified diff, count +/- lines; parse each with ast and compare dumps
```
