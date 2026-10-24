# H0–H5 transfer experiment: aggregate result (static attack arm)

Date: 2026-09-28/29. Design: 6 programs x 6 arms x 6 builds = 216 builds,
1296 attack applications per program (36 dev x 36 targets, all arm pairs).
Attack arm: static (deterministic, always runnable). Ghidra/LLM/symbolic
arms per protocol order remain future work.

## Usable rate

216/216 builds gate-passed (100%). Zero exclusions in the final run on
every program. (Probe-stage calc: 12/12; codec pilot under flattener-v1:
29/36 with 7 exclusions -> diagnosed -> fixed -> full rerun, see below.)

## Second repair: renamer import/use desync (Cython blocker, disclosed)

The Ghidra feasibility probe found Cython rejecting a seed-dependent
subset of H0/H1/H5 builds: the sandbox-check template
`import uuid, sys, multiprocessing` kept its spelling (visit_Import only
renames asnames) while use sites renamed uuid/multiprocessing (absent
from reserved) -- the 5th binding/use desync of one family. CPython
tolerated it (NameError caught by try/except; gate passed); Cython
fails statically, which silently gates the Ghidra arm (compile-or-skip
= selection bias toward less-obfuscated builds). Fix: uuid +
multiprocessing reserved in both renamers (SymbolRenamer,
UnicodeIdentifierEncoder); regression test test_module_binding_use_
agreement added (20 renamer tests green). Host verified safe for the
re-armed check (12 CPUs, non-VM OUI). Full static H0-H5 rerun followed
(outputs changed; one consistent compiler family; prior run superseded
as pilot, never cited). Post-fix: 216/216 usable, T=1.00 in all 30
comparisons (reconfirmed), codec H5 S now 1.00 (prior 0.944 dip was
desync fallout), sched H1 0.889/H5 0.778 (seed-dependent absolute-S
variation; T-anchored conclusions unchanged).

## Mid-experiment compiler repair (disclosed, not hidden)

The codec pilot (flattener-v1 with entry-rotation hack) excluded 7/18
H0/H1/H5 builds with UnboundLocalError. Diagnosis by transformation
family: ControlFlowFlattener chained blocks in SHUFFLED order, so any
>=3-block function executed out of order whenever the shuffle moved a
later block ahead (rotation only masked it for 2-block functions).
Fix: execution chain follows original program order; shuffled order is
textual layout only; LUT slot-collision bails to unflattened; LUT grown
to max(n*64,512). Verified: codec flattened 12/12 across seeds; new
3-block order-sensitive regression tests green (tests/test_flatten_entry.py).
All six programs were then (re)run with the fixed compiler, so the
inferential sample uses one consistent transform family. Pre-fix runs
were untracked pilot data, overwritten, never cited. No pass sets, arms,
seeds, programs, or protocol definitions changed.

## Transfer result: T = 1.00 everywhere

Median T per arm vs H0 control, all six programs: 1.00, p=1.0000,
verdict FAIL-TO-DISTINGUISH in all 30 comparisons (36 T values each).
No arm reduces static-attack transfer. This is a clean falsification
of transfer resistance for this attack class, not a null to hide.

## The attack is purely target-determined

Strongest form (calc, target H3:0, VM-A): S_cross = 0.50 for all 36 dev
builds regardless of source arm -- H0 seed-only, H2 rep, H3 same-family,
H4 cross-family (threaded VM), H5 mixed. An artifact developed on an
H0 build recovers exactly as much from a VM-A target as one developed
on that target itself; cross-family H4->H3 likewise. In every sub-1.0
case (calc VM arms, auth H0/H5, sched H0/H1/H5, codec H5), self-pair S
equals cross-pair S exactly. The developed artifact carries no
build-specific information that ever helps or hurts: success is a pure
function of the target build. The static attack keys on
semantics-preserved features (function I/O mapping transfers by design)
plus target structure (which functions are recoverable).

## Absolute recovery (S) does vary: robustness without transfer resistance

- calc: VM arms (H3/H4/H5) S=0.50 vs 1.00 elsewhere. Execution-model
  diversification halves static recovery -- but transfers perfectly.
- auth: H0/H1/H5 S=0.667 vs H2/H3/H4 S=1.00. Heavyweight legacy arms
  degrade absolute recovery vs lightweight rename+rep/VM arms.
- sched: H1 S=0.667, H0/H5 S=0.889, H2/H3/H4 S=1.00. Same pattern.
- codec: H5 S=0.944, all others 1.00.
- parser/store: S=1.00 in all arms (ceiling).

Diversification buys absolute robustness in cases, zero transfer
resistance against this attack class. Both facts are reported; neither
is substituted for the other.

## The five questions

1. Representation diversification (H2): no transfer reduction (T=1.00).
2. Execution-model diversification (H3/H4): no transfer reduction;
   halves absolute recovery on the one VM-eligible program.
3. VM-A vs VM-B cross-transfer: perfect (H4->H3 = self).Independent
   VM organizations do not impede this attack class.
4. Combination (H5): no additional reduction (T=1.00).
5. Attack classes benefiting: none observed in the static arm.
   Covered taxonomy: function/semantic/constant/name.
   Uncovered: cfg/dataflow/vm -- the static arm never exercises them.

## Scope limitation: VM coverage

Only calc has VM-eligible functions (H3/H4 4/4, H5 3/4 per build).
parser/auth/store/codec/sched: 0 eligible -> H3/H4 reduce to
rename-only there (+rep content in H5). The execution-model hypothesis
is tested on exactly one program. The coverage metric surfaced this as
designed. A follow-up corpus needs VM-eligible programs (numeric/
loop-heavy functions passing _eligible) before any VM transfer claim.

## Diversity vs transfer

Structural diversity mean 0.16-0.24 per program; D_VM on calc mean
0.74 over 594 pairs (cross-family ~0.98-1.00, same-family permutation
distance varies). T constant at 1.00 throughout: builds look different
(D high), attacks transfer anyway. "Looks different" != "resists transfer".

## Cost (means over 36 builds/arm)

- H0: 5194B, 0.034s build. H1: 5172B, 0.012s. H2: 1350B, 0.005s
  (smaller than H0: isolation strips pipeline defaults -- by design).
- H3: 4260B, 0.009s. H4: 4116B, 0.010s. H5: 7848B, 0.023s.
- Calc VM arms ~19KB vs H0 ~2.6KB (~7x size on VM-eligible code).
- Perf probes (startup/runtime/peak RSS) recorded per build in
  experiment.json costs; all demo runs ok.

## What this means for the paper

The honest central empirical result at this stage: heterogeneous
diversification (representation + execution-model + mixed) yields
measurable structural diversity and absolute-robustness gains but NO
static-attack transfer resistance (T=1.00, target-determined attack).
The D<->T dissociation is itself publishable evidence for the claim
that diversity metrics cannot proxy for transfer measurement. Next,
per protocol order: Ghidra-transfer arm (primary), then LLM, then
symbolic -- transfer must be tested against attacks that key on
the diversified features before any planner (G1) calibration, which
remains blocked on measurements that discriminate.

## Post-hardening rerun (A1 string default + A4 CONST masking)

216/216 usable, zero exclusions, T=1.00 in all 30 comparisons
reconfirmed. Absolute-S regime unchanged: calc VM arms 0.50; auth
H0/H1/H5 0.667 vs H2/H3/H4 1.00; sched H1/H5 0.778; codec H5 dip gone
(1.00); parser/store ceiling. VM matrix on new-emission builds:
self 1.00 (18/18); cross-seed H3 0.056 / H4 0.051 / H5 0.022;
H3<->H4 0.028 -- positive preserved (chance-level regime identical;
exact cell values shift with re-seeding, as expected for permutation
agreement rates).

Reproducibility fix (same batch): experiment seeds derived from
`hash(name)` were PYTHONHASHSEED-randomized per process, silently
re-seeding every run. Now sha256-based (stable); verified
bit-identical calc builds across two processes. Reported numbers are
distributionally stable; exact cell values are seed-regime draws.

## v2.0 endpoint: T_const_split (protocol-v2 amendments 1-2)

Registered arm and instrument: `docs/research/protocol-v2.md`,
amendment 1 (arm, 2x2 factorial, seeds, scoring) and amendment 2
(instrument validity: flatten folded sequence constants). Both were
written before the number they govern. Full report:
`docs/research/const-split-results/RESULTS.md`
(corrected hash `a78ca807...`; disclosed pre-amendment hash
`19a48e75...`).

Design: C0 rename-only control, C1 +`split_vars`, C2
+`unfold_constants`, C3 both; all other transforms isolated OFF;
3 builds per arm per program, seeds `master_seed*1000+201+i`; all six
corpus programs; every build through the semantic gate. 72/72 builds
usable, zero exclusions.

### Gates

- Denominator `S(B_j|P_j)` = 1.00 for every usable build: PASS.
- Negative control C0->C0 = 1.000 (36 pairs): PASS.
- String specificity control = 1.000 in every cell: PASS. No arm in
  this factorial touches string literals, so movement here would have
  voided the arm; it did not move.

### Result

| mechanism | cross-arm | matched same-arm | delta |
|---|---|---|---|
| C0 -> C2 (`unfold_constants`) | 0.989 | C2 -> C2 = 0.989 | -0.000 |
| C0 -> C3 (both) | 0.995 | C3 -> C3 = 0.995 | -0.000 |
| C0 -> C1 (`split_vars`) | 1.000 | C1 -> C1 = 1.000 | 0.000 |

`T = S(A->B)/S(B->B)` is `0.989` for the unfold arm, but the matched
same-arm cell is also `0.989`. The hiding rule is build-invariant: it
removes the same literals from every build, so it lowers the absolute
recovery ceiling without making one build's extraction fail on
another. **No transfer resistance.** The endpoint is recorded as not
supported, and the result is explicitly underpowered rather than
falsified:

- The corpus carries 7-11 literal constants per program; the integer
  subset is 4.0-4.3 distinct values per cell. One hit moves the score
  by ~0.14-0.25, so the design cannot resolve effects below ~0.05.
- `split_vars` acts on only 4 assignment sites in the whole corpus
  (codec 3, sched 1) at 30% probability, so C1 is effectively a no-op
  here (1.000 everywhere, `n_int` unchanged). The C3 row is therefore
  C2's effect plus noise, not evidence about splitting.
- Corrected vs pre-amendment: the folded-sequence fix moved sched from
  1.000 to 0.970 (its nested tuple now supplies 3 integer literals)
  and aggregate absolute loss from 0.006 to 0.011; the verdict did not
  change. Both tables are reported.

### Mechanism finding (reported, not corrected)

`unfold_constants` emits three branches. CPython folds `(v ^ m) ^ m`
and `(b << s) + r` back to `v` at compile time; only `sum([parts])`
survives into the bytecode pool. Those two branches still keep `v` out
of the emitted source text, but do not hide it from the compiled
constant pool that this endpoint measures. The weak absolute effect
(1.1%) is consistent with one third of one branch surviving
compilation on a literal-poor corpus.

### Scope

This instrument measures literal **search**, not value recovery.
`C` split as `C ^ m` and `m` is algebraically recoverable by an
analyst who models the rule; a positive result would have supported
"hides literals from search", never "hides values".

### Consequence for the planner

Constant hiding joins the v1.0 pattern: a build-invariant absolute
lever, not a transfer lever, for this attack class. A test with power
to detect a real transfer effect needs a literal-rich calibration
program and must be pre-registered as a new experiment (v3.0); adding
a program to the frozen v2.0 corpus after measurement would be
post-hoc tuning. Likewise, making all three unfold branches emit
non-foldable arithmetic changes the transform and belongs to the v3.0
hardening track, not to this endpoint.
