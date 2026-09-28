# H0–H5 exclusion-rate probe (power estimation, NOT inferential)

Date: 2026-09-28. Program: calc (canonical stress: tuple-unpack loop,
dict builtins). n=2 per arm, static attack arm. Elapsed 13.9s.

## Usable rate per arm (gate-passed / attempted)

| Arm | Usable | Excluded | VM coverage | Mean size | Mean build |
|-----|--------|----------|-------------|-----------|------------|
| H0 | 2/2 | 0 | 0/8 (no VM, as designed) | 2642 B | 0.14 s |
| H1 | 2/2 | 0 | 0/8 | 2318 B | 0.01 s |
| H2 | 2/2 | 0 | 0/8 | 928 B | 0.00 s |
| H3 | 2/2 | 0 | 8/8 | 19054 B | 0.03 s |
| H4 | 2/2 | 0 | 8/8 | 18326 B | 0.03 s |
| H5 | 2/2 | 0 | 6/8 (one build: 3/4 eligible virtualized) | 16406 B | 0.03 s |

Overall usable rate: **12/12 = 100%** (vs ~25% pre-renamer/flattener
repair on the same program — the repair eliminated the exclusion
catastrophe; the frozen `g2-baseline` tag preserves the old numbers).

## Attack producibility

Static-arm artifacts developed and applied for all 12 builds
(T lists non-empty in every arm; sanity_unprotected recorded).
No arm shows artifact-production failure.

## T values (n=2, degenerate — NO inference)

All T = 1.00 in every arm (expected at n=2: self-pairs dominate;
falsification correctly refuses claims). These numbers must not be
cited as results.

## Freeze decision

Exclusions acceptably low (zero) → proceed with planned **n=6** per
arm per program across the 6-program corpus, preserving the frozen
protocol (same transfer definition, endpoints, gate, stats, negative
control). No transformation changes between probe and powered run.

## Open observations (not blockers)

- H5 coverage 6/8: one eligible function skipped in one build
  (eligibility passed, compile-time skip). The coverage metric exists
  precisely to surface this; diagnose only if it persists at n=6.
- VM arms carry ~7x size overhead vs H0 on calc (19KB vs 2.6KB) —
  recorded as cost data, not a defect.
- H2 output smaller than H0 (928B vs 2642B): isolation strips the
  default pipeline (strip_meta/unfold/obf_calls off) — expected and
  by design; cost comparisons must use H0 as baseline, not raw sizes
  across differently-isolated arms without noting it.
