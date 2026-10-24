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
- T_CFG_hash: develop records bytecode-CFG profile of B_i; PRIMARY is out-degree-multiset Jaccard (pure topology; gate history: content-labeled edges failed H2->H2 at 0.767 due to rep tuple-rewrites, switched pre-cross-arm). Secondaries: content edge-Jaccard, block-hash Jaccard.
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

## Amendment 1 (2026-10-24): T_const_split arm, registered before measurement

T_const_split was specified at registration but its arm was not: the
decision log ordered "const-split arm" third, after the VM and structural
arms. This amendment fixes the arm and the instrument **before any
const-arm number is taken**. Nothing above is edited; the transfer
definition, denominator rule and frozen G2 spec are untouched.

### Motivation (from v2.0 status note 1)

S_const showed zero transfer signal in v1.0 for a structural reason, not
an empirical one: no v1.0 arm ever enabled a constant-hiding transform
(`split_vars` OFF in every H0-H5 pass set). Measuring `T_const_split`
therefore needs a new configuration *and* a literal-search attack.

### Arms (2x2 factorial, everything else isolated OFF)

| arm | `rename` | `split_vars` | `unfold_constants` |
|-----|----------|--------------|--------------------|
| C0  | yes      | no           | no                 |
| C1  | yes      | yes          | no                 |
| C2  | yes      | no           | yes                |
| C3  | yes      | yes          | yes                |

All other transforms forced OFF (`cfg_flatten`, `opaque_predicates`,
`bogus_exceptions`, `mba_subs`, `fragment_strings`, `unicode_ids`,
`enhanced_junk`, `break_decompiler`, `code_checksums`, `dynamic_code`,
`obf_calls`, `exception_flow`, `strip_meta`, `rep_diversify`,
`vm_dispatch`). 3 builds per arm per program, seeds
`master_seed*1000 + 201 + i` (a fresh seed block; hetero uses 11+, seed
control uses 101+, so no build is reused). Every build must pass the
existing semantic gate or it is excluded and reported.

### Instrument (`scripts/transfer/const_attack.py`)

- **Develop P_i**: `compile(B_i)` (never executed), walk `co_consts`
  recursively, keep `int` (excluding `bool`), `float`, `str` with
  `len >= 2` and not starting with `_`, `bytes` with `len >= 2`. Drop
  `None`, `True`, `False`, `Ellipsis`, code objects and tuples. Dedupe.
- **Apply**: the same extraction on `B_j`.
- **S**: `|P_i ∩ B_j| / |P_i|` over the distinct extracted values.
- **T**: `S(B_j|P_i) / S(B_j|P_j)`. `S(B_j|P_j)` is 1.00 by
  construction, so the frozen denominator gate is satisfied by every
  cell; the informative gate is C0->C0, which must be >= 0.80 or the
  instrument is rejected.
- **Cells excluded** when either build fails to compile or yields fewer
  than 3 constants (nothing to measure), reported as exclusions.
- **Specificity control**: the same score restricted to the `str` subset
  is reported for every cell. No arm in this factorial touches string
  literals, so the string hit rate must stay at 1.00. If it moves, the
  instrument is measuring build shape rather than literal hiding and the
  arm is void.

### Pre-registered predictions

1. C0->C0 = 1.00: renaming does not touch constants.
2. C0->C1 < 1.00 on int-bearing programs: `split_vars` replaces
   `x = C` with `a = C^m; b = m`, so C is absent from `co_consts`.
3. C0->C2 < 1.00: `unfold_constants` rewrites small ints into
   arithmetic expressions.
4. C0->C3 <= min(C0->C1, C0->C2): both mechanisms act on the same
   population.
5. String subset stays 1.00 in all cells (specificity control).
6. The effect is **absolute**, not transfer-resistant, if
   C1->C1 remains 1.00: the same hiding rule hides the same constants in
   every build. Prediction 6 is the one that decides whether constant
   hiding is a transfer lever or another absolute-robustness-only lever,
   and it is stated here so a 1.00 cannot be rationalized after the fact.

### Scope note registered with the predictions

This instrument measures **literal search**, which is what a
signature/template matcher does. It does not measure **value recovery**:
`C = a ^ b` is algebraically recoverable, and a determined analyst who
models the split rule can undo it. A positive `T` result therefore
supports "hides literals from search", never "hides values".

### Freeze

`config_freeze_hash_const` = sha256 over the canonical arm table above
plus the seed block and the instrument parameters. Recorded in the
results file. Configurations are frozen at these values; results are
reported as measured, and no pass set is tuned after the first number.

## Amendment 2 (2026-10-24): instrument validity — flatten folded sequences

Registered after amendment 1 and after the first pre-amendment run, and
**before the corrected number was taken**. The motivation is mechanical
validity, not result direction: the pre-amendment aggregate is disclosed
alongside the corrected one, and no arm, seed, pass set or gate changes.

### Defect (observed, reproducible)

CPython folds a constant sequence display into a single tuple constant in
`co_consts`: `[101, 103, ..., 197]` arrives as one tuple. Amendment 1's
rule "drop tuples" therefore dropped the whole folded population. On the
sensitivity fixture the instrument saw 2 integer literals where the
source has 22; the 20-element list was invisible. That under-counts
exactly the population this arm is meant to hide, so the pre-amendment
numbers are measured on a blind instrument for any program carrying a
folded sequence.

### Correction (the only change)

Recurse into `tuple` and `frozenset` constants and tag their scalar
elements, recursively for nested tuples. The container itself is not
counted: a signature matcher searches for elements, not the folding
artifact. Everything else is unchanged — same type tags, same `bool`
exclusion, same `MIN_TEXT_LEN`, same drops for `None`, short strings and
code objects, same `S`, `T`, arms, seed block, `MIN_CONSTANTS` and
semantic gate.

### Predictions (stated before the corrected number)

1. `C0->C0` stays 1.00: renaming does not touch constants, and both
   sides receive the same deterministic extraction.
2. `n_int` can only increase. The corpus carries only 2-3 folded
   elements per program, so aggregate movement should be small; the
   fixture is where the defect is large and is used by the sensitivity
   test.
3. The string specificity control stays 1.00 in every cell.
4. The verdict is recomputed on the corrected instrument. If the worst
   `delta` (cross-arm minus matched same-arm control) stays `>= -0.05`,
   the conclusion is unchanged: absolute-only loss, no transfer
   resistance. If it falls below `-0.05`, that is the reported result.
   Pass sets are not changed either way.

### Scope note registered with this amendment

The instrument measures the **bytecode** constant pool. `unfold_constants`
has three branches: `sum([parts])` survives compilation, while `(v^m)^m`
and `(b<<s)+r` are folded back to `v` by the CPython compiler. Those two
branches still hide `v` from a **source-text** search (the literal does
not appear in the emitted source), but they do not remove it from the
compiled pool. This asymmetry is reported, not corrected: changing the
transform would change the arm after registration, and the endpoint is
defined at bytecode level.
