# Matched-Callable-Count Experiment on the Independent Task Pool

**Date:** 2026-11-02, round 259. Follow-up to `matched-count-experiment.md` (round 258) and
`callable-count-confound.md`. New script: `scripts/transfer/matched_external.py`.

## The question

`matched_families.py` equalised module-level callable counts and drove the family difference from
+0.33/+0.33/0.00 to +0.00/+0.00/+0.00 on 17 hand-written tasks. Its own audit then showed the null
is *forced* on 10 of those 17 (`probes == k`), so the empirical content rested on 7 tasks.

The 6 tasks in `scripts/transfer/blind_tasks.py` were specified from docstrings and doctests by an
author who had not read the research programme, over three vendored third-party modules. They are
the strongest independent evidence in the repository. This experiment asks:

> With callable counts matched, is the family difference still 0.00 on those 6 tasks — and how many
> of their cells have residual discrimination cost `c > 0` rather than being forced?

The author's own external tasks in `external_tasks.py` (`all_equal`, `dotproduct`, `take` from
recipes.py; `median_low` from statistics.py) are run as a second, labelled group. They share the
vendored modules but not the independence: their specifications were written by the programme's
author. Reporting them separately is the point — pooling would silently launder 4 author-specified
tasks into the independent group.

## Method, as implemented

For each task, each family (FAM_A/B/C copied verbatim from `reproduce.py`) and each seed in
(11, 22, 33), `generate_variant(module_source(name), 4, {"master_seed": seed, "pass_sets":
[family]})` was called on the task's whole vendored module; `k` was counted as the
`ast.FunctionDef` / `ast.AsyncFunctionDef` / `ast.ClassDef` nodes in `tree.body`; each
(task, seed) cell was equalised to the maximum of its three `k` values by appending
`def _nx_pad_<i>(): return None` to the generated text, re-parsing with `ast.parse` and
re-checking `k_after == k_before + pads`; probes were measured twice with a fresh
`AccumulatingAttack().apply(path, props)` — once unpadded, once padded — and the comparison is
`table_diversity()`'s statistic verbatim: `seed_only = [p(f1,11), p(f1,22), p(f1,33)]`,
`varying = [p(f1,11), p(f2,22), p(f1,33)]`, `diff = mean(varying) − mean(seed_only)`, so only the
seed-22 cell crosses families and one probe there appears as +0.33. Generation is deterministic for
a fixed source and seed (two calls hashed identical), so each task's artefacts were generated
independently with no cross-task caching. A task is loaded only if its target is still a
module-level function and every property is true on the un-obfuscated target; otherwise it is
reported as unevaluable and the run continues. **All 10 tasks were evaluable; `median_low` was
present; nothing was dropped.**

Reproduce with:

```
python3 scripts/transfer/matched_external.py --json /tmp/matched_external.json
```

Runtime ~41 s, no network, writes only to a temporary directory.

## Groups

| group | tasks | modules | who wrote the specs |
|---|---|---|---|
| blind | `is_prime`, `multinomial`, `median_high`, `multimode`, `bytes2human`, `a10n` | recipes.py (2), statistics.py (2), strutils.py (2) | another author, from docstrings/doctests |
| prior | `all_equal`, `dotproduct`, `take`, `median_low` | recipes.py (3), statistics.py (1) | the paper's author |

An honest limit of the design: the two groups share modules, so this is 3 independent codebases and
6 independent specifications, not 10 independent programs. The 4 prior tasks add a second estimate
on the same code, not new material.

## Callables before equalisation, pads, matched probes

`k` = module-level callables including classes. Every task shows the same pattern: **A has one
fewer than B and C, and B and C are equal**. Counts are seed-invariant (verified over all three
seeds for all 10 tasks).

| group | task | module | k A/B/C | pads A/B/C | k after | matched probes A/B/C |
|---|---|---|---|---|---|---|
| blind | `is_prime` | recipes.py | 68/69/69 | +1/+0/+0 | 69 | 73/73/73 |
| blind | `multinomial` | recipes.py | 68/69/69 | +1/+0/+0 | 69 | 71/71/71 |
| blind | `median_high` | statistics.py | 39/40/40 | +1/+0/+0 | 40 | 46/46/46 |
| blind | `multimode` | statistics.py | 39/40/40 | +1/+0/+0 | 40 | 40/40/40 |
| blind | `bytes2human` | strutils.py | 37/38/38 | +1/+0/+0 | 38 | 36/36/36 |
| blind | `a10n` | strutils.py | 37/38/38 | +1/+0/+0 | 38 | 36/36/36 |
| prior | `all_equal` | recipes.py | 68/69/69 | +1/+0/+0 | 69 | 73/73/73 |
| prior | `dotproduct` | recipes.py | 68/69/69 | +1/+0/+0 | 69 | 71/71/71 |
| prior | `take` | recipes.py | 68/69/69 | +1/+0/+0 | 69 | 71/71/71 |
| prior | `median_low` | statistics.py | 39/40/40 | +1/+0/+0 | 40 | 46/46/46 |

Matched probes are identical across A/B/C in **all 30 task/seed cells**, so every per-task diff is
exactly 0.00, not 0.00 after rounding.

## Probe difference, per task and pairing, before → matched

Every task's row is the same and the script prints all ten:

| tasks | A-vs-B before | A-vs-B matched | A-vs-C before | A-vs-C matched | B-vs-C before | B-vs-C matched |
|---|---|---|---|---|---|---|
| all 6 blind + all 4 prior | +0.33 | +0.00 | +0.33 | +0.00 | +0.00 | +0.00 |

The baseline column reproduces `table_diversity()`'s published +0.33/+0.33/0.00 on material the
original experiment never touched, so the harness is validated twice over.

## Aggregate by group

| group | tasks | pairing | before | matched |
|---|---|---|---|---|
| blind | 6 | A-vs-B | +0.33 | +0.00 |
| blind | 6 | A-vs-C | +0.33 | +0.00 |
| blind | 6 | B-vs-C | +0.00 | +0.00 |
| prior | 4 | A-vs-B | +0.33 | +0.00 |
| prior | 4 | A-vs-C | +0.33 | +0.00 |
| prior | 4 | B-vs-C | +0.00 | +0.00 |

The 0.00 holds exactly on the independent group and on the prior group. The question left is how
much of it is information.

## Residual discrimination cost — and a defect in the old definition

`matched_families.py` defined `c = probes − k`. That is exact only when the attacker probes exactly
the callables the AST counts. On these vendored modules it does not:

* `AccumulatingAttack.apply()` probes `types.FunctionType` bindings from the executed namespace, so
  it **does** probe imported stdlib functions (`dataclass`, `lru_cache`, `namedtuple`,
  `decompress`), aliases (`padnone = pad_none`, conditional `batched`) and module-level closures,
  and it **never** probes classes;
* `k` counts classes and does not know about imports.

So define `m` = the attacker's real candidate base (`types.FunctionType` bindings) and report both
`c = probes − k` (the old definition, kept for comparability) and `c' = probes − m` (the residual
the counter actually charges). On the 17 hand-written tasks `k == m` on every task, so the paper's
7-task count is unaffected; on these modules `k ≠ m`:

| module | k | m | m − k | what moves between the two counts |
|---|---|---|---|---|
| recipes.py | 68 | 70 | +2 | +`dataclass`, +`lru_cache` (imported), +`padnone`, +`batched` (aliases); −`Stats` (class), −`_shift_to_odd` (`@lru_cache` wrapper) |
| statistics.py | 39 | 39 | 0 | +`namedtuple` (imported), +`_quartic_invcdf`, +`_triweight_invcdf` (closures); −`StatisticsError`, −`NormalDist` (classes), −`_normal_dist_inv_cdf` (overwritten by the C import) |
| strutils.py | 37 | 35 | −2 | +`decompress` (imported); −`DeaccenterDict`, −`HTMLTextExtractor`, −`MultiReplace` (classes) |

Per task, at seed 11 (values are seed-invariant):

| group | task | m A/B/C | c = p−k | class under c | c' = p−m | class under c' |
|---|---|---|---|---|---|---|
| blind | `is_prime` | 70/71/71 | +4/+4/+4 | load-bearing | +2/+2/+2 | **load-bearing** |
| blind | `multinomial` | 70/71/71 | +2/+2/+2 | load-bearing | +0/+0/+0 | forced |
| blind | `median_high` | 39/40/40 | +6/+6/+6 | load-bearing | +6/+6/+6 | **load-bearing** |
| blind | `multimode` | 39/40/40 | +0/+0/+0 | forced | +0/+0/+0 | forced |
| blind | `bytes2human` | 35/36/36 | −2/−2/−2 | undefined | +0/+0/+0 | forced |
| blind | `a10n` | 35/36/36 | −2/−2/−2 | undefined | +0/+0/+0 | forced |
| prior | `all_equal` | 70/71/71 | +4/+4/+4 | load-bearing | +2/+2/+2 | **load-bearing** |
| prior | `dotproduct` | 70/71/71 | +2/+2/+2 | load-bearing | +0/+0/+0 | forced |
| prior | `take` | 70/71/71 | +2/+2/+2 | load-bearing | +0/+0/+0 | forced |
| prior | `median_low` | 39/40/40 | +6/+6/+6 | load-bearing | +6/+6/+6 | **load-bearing** |

Counts of tasks by class:

| group | tasks | c > 0 | c == 0 | c < 0 | c' > 0 | c' == 0 |
|---|---|---|---|---|---|---|
| blind | 6 | 3 | 1 | 2 | **2** | 4 |
| prior | 4 | 4 | 0 | 0 | **2** | 2 |

Three readings matter:

1. **The literal `c` is contaminated on these modules.** `multinomial`'s +2 and
   `dotproduct`/`take`'s +2 are the net +2 offset between `k` and `m` on recipes.py — four probed
   imports/aliases against two probed-out class/wrapper entries — not discrimination. The old rule
   would book all 4 prior tasks as load-bearing; the correct base says 2.
2. **`c` can be negative**, because `k` counts three classes on strutils.py that the attacker never
   probes. The "forced iff `c == 0`" rule is simply undefined there. This is a defect in the
   round-258 definition, not in the data; it has no effect on the 17 hand-written tasks, where
   `k == m`.
3. Under the correct base, **2 of the 6 blind tasks are load-bearing** — `is_prime` (+2) and
   `median_high` (+6) — and **4 are forced**. The prior group gives the same 2-of-4.

## Checks actually run

* **Pad additivity:** in all 90 cells, `matched_probes == base_probes + pads`; no deviation. Each
  appended no-op costs exactly one probe, as in the hand-written experiment.
* **Exactness:** matched probes are equal across families in **30/30** task/seed cells.
* **Seed-invariance:** `k`, `m` and probes are each invariant across seeds 11/22/33 on every task.
* **Trajectory, not just total:** the per-property sequence of surviving-candidate counts is
  identical across A/B/C in **30/30** task/seed cells. Total probe counts could coincide while the
  intermediate profiles differ; they do not.
* **Unevaluable tasks:** none. `median_low` was present; no function was renamed; no module was
  missing. The script reports such failures instead of dropping them.

## Verdict

**The 0.00 holds exactly on the independent tasks.** On the 6 blind tasks the unmatched difference
is +0.33/+0.33/0.00 and the matched difference is +0.00/+0.00/+0.00, with identical probe counts in
all 18 blind task/seed cells. The 4 prior tasks behave identically. The residual discrimination
cost is family-invariant on every task, so nothing in this counter distinguishes the families once
callable count is held constant.

**But most of it is still forced, and the extension adds only four informative tasks, two of them
independent.** Under the attacker's real candidate base, 4 of 6 blind tasks and 2 of 4 prior tasks
have `c' = 0`: the first property eliminates every sibling and the equality is arithmetic. The
informative blind tasks are `is_prime` (`c' = 2`) and `median_high` (`c' = 6`); the informative
prior tasks are `all_equal` (`c' = 2`) and `median_low` (`c' = 6`). So the paper's load-bearing base
grows from **7 to 11 tasks** — 7 hand-written, 2 blind, 2 prior — not to 14, which is what the old
`c = p − k` definition would suggest (it books `multinomial` and both `dotproduct`/`take` on the
net `k`/`m` offset rather than on discrimination). Of the 11, only the 2 blind tasks are
independent of the paper's author.

## What this does and does not strengthen

This is a replication on independent material, not a new source of power. The 0.00 now holds on 6
specifications written by someone who had not read the programme, on three third-party modules the
paper never used, and the property that carries the result — `c'` is identical across families — is
observed on 2 of those 6 tasks with real (non-zero) residual cost. That is genuine, if modest:
the earlier 7-task base was all hand-written by the paper's author, and two independent tasks now
replicate the invariance with costs of 2 and 6 probes instead of the arithmetic `probes = k`.
What it does **not** do is multiply the evidence. Four of the six blind tasks and two of the four
prior tasks are forced: on them, matching counts makes a difference impossible under this counter,
so they could not have falsified anything. The prior group adds no independence at all — its
specifications are the author's, and its two extra entries under the old definition were the net
`k`/`m` offset, not discrimination. The total base is 11 tasks over four codebases (the hand-written
benchmark plus three vendored modules) and one instrument; a reviewer who found 7 tasks thin will
find 11 tasks thin. If the paper's title-level claim needs breadth, this experiment does not supply
it — it supplies consistency. The honest sentence is: *the matched result replicates on two
independent tasks and is forced on four; the load-bearing base grows from 7 to 11, but its
independent share from 0 to 2.*

## Surprises

1. **`c` is negative on strutils.py** under the round-258 definition, and `k ≠ m` on all three
   vendored modules. The attacker probes imported functions and closures and skips classes; the AST
   callable count does neither. The definition of residual cost should be stated against the probe
   base, not against AST callables. This does not retroactively invalidate round 258 (there
   `k == m` on all 17 tasks), but it does mean `c` and `probes − k` are not the same quantity in
   general.
2. **Family A inserts no module-level callable at all on these modules; B and C insert exactly
   one.** On the 17 hand-written tasks the same is true (`k_source == k_A`, `k_B = k_C = k_A + 1`),
   so the confound has a single identifiable cause: B and C include `string_encode`, which emits
   one `_nixon_…` string-unsealing helper (an HMAC-authenticated hex decode), and A's pass set does
   not contain `string_encode`. The gap is one everywhere; only the absolute number inserted differs
   from what a reader of the round-258 table might assume.
3. **Matched probes can be below matched `k`** (`bytes2human`: `k = 38`, probes = 36). `k` is not
   the probe base, which is exactly the defect above.
4. **The prior group's apparent strength was partly spurious.** Its 4/4 load-bearing rate under
   `c` collapses to 2/4 under `c'`; two tasks were being credited for imported decorators.

## What this changes in the paper

* The scope sentence can say the matched result replicates on 6 blind (docstring-derived) tasks and
  4 author external tasks over three vendored third-party modules; the load-bearing subset grows
  from 7 to **11** tasks, of which only 2 are independent of the author.
* Define the residual cost against the attacker's candidate base (`m`), or add the caveat that
  `probes − k` is only the residual when the module has no imports, aliases or classes. On the
  paper's own 17 tasks the two coincide, so no number changes; the definition does.
* `B-vs-C` remains structurally blind: B and C insert exactly one helper each on every task
  measured in both experiments.
* Do not describe the extension as broadening the evidence base. It replicates the invariance on
  two independent tasks and is forced on four; the independent share of the load-bearing base is 2.
