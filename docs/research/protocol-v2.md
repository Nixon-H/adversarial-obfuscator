# Experiment v2.0 (pre-registered 2026-09-29, no measurements taken)

## Status of v1.0 (tag `exp-v1.0`)

v1.0 established the boundary condition: semantic-mapping attacks and
ambient decompiler counters are invariant to the H0-H5 syntactic ladder
(static T=1.00 everywhere, target-determined; Ghidra Path A: counts are a
binary-mass proxy, row-invariant). Two v1.0 caveats carried forward:

1. **S_const exhausted**: constant endpoint shows zero transfer signal
   in existing telemetry (all sub-1.0 pairs have S_cross == S_self;
   parser/calc/store/codec uniformly 1.0). Additionally no arm ever
   enabled constant-hiding transforms (split_vars OFF in all H0-H5
   pass sets). A const-transfer result needs both a new transform
   configuration AND a literal-extraction attack -- neither exists.
2. **Taxonomy grouping degenerate**: `taxonomy_transfer` filters on
   `hetero:`/`seed_only:` prefixes while builds are keyed `H0:`-`H5:`,
   so all v1.0 taxonomy T_hetero/T_seed lists are EMPTY and their
   verdicts vacuous. v1.0 inference rested on experiment.py's per-arm
   (H0-vs-Hx) analysis, which is sound. v2.0 fixes grouping to be
   arm-aware (no freeze issue: v2.0 is a new experiment, and the
   transfer definition itself is unchanged).

## v2.0 hypothesis

Transfer resistance (T < 1.0) emerges strictly when the attack's feature
space targets transform-mutable artifacts (opcode tables, structural
CFGs, split literals) rather than functional semantics.

## Endpoints (new; v1.0 definitions untouched)

- T_VM_table: develop extracts opcode->handler map M_i from B_i
  (table-extraction machinery exists via D_VM); apply decodes B_j with
  frozen M_i; S = fraction of functions correctly attributed/traced.
- T_CFG_hash: develop records block-hash n-gram profile of B_i;
  apply Jaccard/graph-edit match on B_j. CFG extracted at Python
  AST/bytecode level (NOT binary: Cython scaffolding would recreate
  the mass-proxy confound).
- T_const_split: develop extracts literal constants from B_i; apply
  searches B_j; S = hit rate. Requires split_vars/MBA-constant
  configurations absent from v1.0 arms.

## Gates (anti-denominator-collapse)

- S(B_j|P_j) >= 0.80 required for every reported T cell; cells below
  are EXCLUDED under the frozen denominator rule, never scored as wins.
- Pre-registered predictions: self-transfer ~= 1.00 (extraction works);
  cross-seed VM ~= 0.00; unflattened->flattened CFG collapse;
  H0 verbatim const match vs split-arm miss.
- Falsification symmetric to v1.0: if specialized arms also yield
  T ~= 1.00, the hypothesis fails; report, do not re-tune.

## Scope and discipline

- VM arm: single-program deep-dive (calc is the only VM-eligible
  program); reported as microbenchmark, never pooled into macro-averages.
- Corpus configs frozen; no pass-set tuning after first numbers;
  held_out discipline carries to G1.
- New arms validated on calibration programs before any held_out run.

## Decision log

- v2.0 arms NOT YET BUILT at registration time. Construction order:
  VM-dispatcher arm, structural-signature arm, const-split arm.
