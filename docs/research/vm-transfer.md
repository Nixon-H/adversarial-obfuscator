# v2.0 VM-dispatcher transfer (calc microbenchmark): genuine T < 1

Date: 2026-09-29. Scope: calc only (sole VM-eligible program), H3/H4/H5
builds from the frozen v1.0 rerun (fixed artifacts, no transform
changes). Endpoint T_VM_table per docs/research/protocol-v2.md.
Raw matrix: /tmp/opencode/vm_matrix.json (18x18, all pairs).

## Self-transfer baseline (denominator gate S >= 0.80)

18/18 builds decode at S = 1.000 with their own maps (H3 6/6, H4 6/6,
H5 6/6). Gate passes everywhere: the extractor is sound, so cross
failures are decoding mismatches, not parser failures. No exclusions.

## Cross-seed transfer (T = S_cross, since S_self = 1.0)

- H3 within-arm: mean 0.028, max 0.096 (n=30). Chance level ~= 1/31.
- H4 within-arm: mean 0.033, max 0.192 (n=30).
- H5 within-arm: mean 0.063, max 0.417 (n=30).
- H3<->H4 cross-family: mean 0.042, max 0.192 (n=72).

Pre-registered prediction (self ~= 1, cross-seed ~= 0) confirmed. The
attack genuinely cannot use Build A's recovered opcode table on Build B:
every decode is instruction misalignment at chance level.

Top cross cell h5_0<->h5_3 = 0.417, symmetric both directions: 5/12
chance agreements on two short aligned tables. Interpretable partial
permutation overlap on small n, far below the gate -- not a crash, not
an exception, a decoding mismatch as specified.

## Alignment

Functions aligned by true-op-sequence equality (evaluator scaffolding;
modeled attacker capability is table extraction + frozen decoding).
All VM functions aligned in all builds (H5 3/4 builds align 3/3).

## Extractor development notes (both caught by the gate pre-measurement)

1. Text-segment tail leak: `ast.get_source_segment` on nested elif-If
   nodes spans the whole orelse chain, misattributing every branch.
   Fixed with structural AST matching. Never produced a cross number.
2. Map granularity: pipeline derives encodings per (seed, family,
   function name) -- per FUNCTION, not per build. An initial
   build-level merged map produced phantom conflicts. Restructured to
   per-function maps + true-op-sequence alignment. Never produced a
   cross number.

## Verdict

First genuine, defensible T < 1 result: per-function opcode
permutation breaks frozen-table decoding across seeds and families
while self-decoding is exact. Reported as single-program microbenchmark
per pre-registered scope. T_CFG_hash and T_const_split remain deferred;
no v1.0 artifact or frozen definition was touched.
