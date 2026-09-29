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
