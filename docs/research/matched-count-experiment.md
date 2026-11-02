# Matched-Callable-Count Experiment: the Family Effect Is One Callable, and Nothing Else

**Date:** 2026-11-02, round 258. Follow-up to `callable-count-confound.md`; direct test of the
objection raised by the cold review.

## The question

`callable-count-confound.md` established that transform families do not insert equal numbers of
module-level callables (A inserts one fewer than B and C on every task measured), and that the
probe counter tracks callable count. The corrected paper claim is that the property set has no
*semantic* channel but does have a *structural* one, and that B-vs-C 0.00 is an artefact of equal
counts.

This experiment asks the decisive follow-up:

> If all three families insert the **same** number of module-level callables, does the A-vs-B /
> A-vs-C difference go to 0.00?

The script is `scripts/transfer/matched_families.py`. It makes no claim beyond what it measures and
re-uses `reproduce.table_diversity()`'s comparison verbatim.

## Method

* Task pool and source construction are `reproduce._tasks()`: the 9 synthetic tasks in
  `scripts/transfer/tasks.py` plus the 8 real tasks in `scripts/transfer/real_tasks.py` (17 in all).
* Families are `reproduce.py`'s `FAM_A`, `FAM_B`, `FAM_C`; each artefact is generated with
  `generate_variant(src, 4, {"master_seed": s, "pass_sets": [fam]})` for `s in (11, 22, 33)`.
* A module-level callable is a node in `tree.body` that is an `ast.FunctionDef`,
  `ast.AsyncFunctionDef` or `ast.ClassDef` — the definition the confound document used.
* **Equalisation.** For each task and seed, the target count is the maximum of the three families'
  counts, and families below it receive N trivial no-op module-level functions appended to the
  generated source text:

      def _nx_pad_<i>():
          return None

  The result is re-parsed with `ast.parse` and its callable count is re-checked (base + N) before
  it is measured. The pads are appended *after* generation, so the obfuscator never sees them.
* **Comparison.** Identical to `table_diversity()`:

      seed_only = [probes(f1, 11), probes(f1, 22), probes(f1, 33)]
      varying   = [probes(f1, 11), probes(f2, 22), probes(f1, 33)]
      diff      = mean(varying) - mean(seed_only)

  so only the seed-22 cell crosses families, and a one-probe difference there appears as +0.33.
  Each probe count comes from a fresh `AccumulatingAttack` applied to one artefact.

One measurement detail: several real-task sources contain a `_demo` helper that is itself a
candidate callable, and the property lambdas call it (it prints `unknown op`). This happens on the
pre-existing attack path with or without this experiment. Probe counts are unaffected; the
measurement path redirects stdout so the report stays clean. Silencing changes nothing that is
measured — the same call returns the same probe count with and without the redirect.

Run:

    python3 scripts/transfer/matched_families.py

## Counts before and after equalisation

Counts are seed-invariant: A, B and C produce the same count at seeds 11, 22 and 33 for every task.
The pattern from the confound document holds on all 17 tasks, not just the three it tabulated:
**A always inserts exactly one fewer callable than B and C; B and C always insert the same number.**

| task | before A/B/C | pads A/B/C | after A/B/C |
|---|---|---|---|
| `sumselected` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `countchars` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `clamp01` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `is_even` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `maxlen` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `running_total` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `signdiff` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `first_negative` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `count_above` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `rle_encode` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `rle_decode` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `slugify` | 5/6/6 | +1/+0/+0 | 6/6/6 |
| `gcd` | 5/6/6 | +1/+0/+0 | 6/6/6 |
| `priority_pick` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `rotate_list` | 4/5/5 | +1/+0/+0 | 5/5/5 |
| `store_get` | 5/6/6 | +1/+0/+0 | 6/6/6 |
| `store_keys` | 5/6/6 | +1/+0/+0 | 6/6/6 |

The three tasks in the confound document reproduce exactly at seed 11: `sumselected` A 4 callables
/ 8 probes → padded 5 / 9, B 5 / 9, C 5 / 9; `countchars` 4/6 → 5/7 vs 5/7 and 5/7; `clamp01`
4/7 → 5/8 vs 5/8 and 5/8.

## Probe difference, per task and pairing

Raw values at the only seed where families are crossed (seed 22), before equalisation and after:

| task | A k/probes | B k/probes | C k/probes | matched probes A/B/C |
|---|---|---|---|---|
| `sumselected` | 4/8 | 5/9 | 5/9 | 9/9/9 |
| `countchars` | 4/6 | 5/7 | 5/7 | 7/7/7 |
| `clamp01` | 4/7 | 5/8 | 5/8 | 8/8/8 |
| `is_even` | 4/6 | 5/7 | 5/7 | 7/7/7 |
| `maxlen` | 4/9 | 5/10 | 5/10 | 10/10/10 |
| `running_total` | 4/4 | 5/5 | 5/5 | 5/5/5 |
| `signdiff` | 4/13 | 5/14 | 5/14 | 14/14/14 |
| `first_negative` | 4/11 | 5/12 | 5/12 | 12/12/12 |
| `count_above` | 4/4 | 5/5 | 5/5 | 5/5/5 |
| `rle_encode` | 4/4 | 5/5 | 5/5 | 5/5/5 |
| `rle_decode` | 4/4 | 5/5 | 5/5 | 5/5/5 |
| `slugify` | 5/5 | 6/6 | 6/6 | 6/6/6 |
| `gcd` | 5/5 | 6/6 | 6/6 | 6/6/6 |
| `priority_pick` | 4/4 | 5/5 | 5/5 | 5/5/5 |
| `rotate_list` | 4/4 | 5/5 | 5/5 | 5/5/5 |
| `store_get` | 5/5 | 6/6 | 6/6 | 6/6/6 |
| `store_keys` | 5/5 | 6/6 | 6/6 | 6/6/6 |

Difference statistic (mean of the crossed comparison minus the seed-only comparison):

| task | A-vs-B before | A-vs-B matched | A-vs-C before | A-vs-C matched | B-vs-C before | B-vs-C matched |
|---|---|---|---|---|---|---|
| every one of the 17 tasks | +0.33 | +0.00 | +0.33 | +0.00 | +0.00 | +0.00 |
| **mean over 17 tasks** | **+0.33** | **+0.00** | **+0.33** | **+0.00** | **+0.00** | **+0.00** |

Every task's row is literally the same three pairs of values, so the per-task table is collapsed
to one row; the script prints all 17. The baseline column reproduces `table_diversity()`'s stated
A-vs-B +0.33, A-vs-C +0.33, B-vs-C 0.00 exactly, so the harness is validated against the number
under dispute.

After equalisation the probe counts are **identical in all 51 task/seed cells** (A = B = C), not
merely equal to two decimals. The 0.00 is exact, not a rounding artefact.

## Verdict

**Yes.** With callable counts matched, A-vs-B and A-vs-C go to exactly 0.00 on all 17 tasks, and
B-vs-C stays 0.00; the entire measured family effect is the one-callable gap that the cold review
and `callable-count-confound.md` identified. The corrected paper claim — structural channel, not
semantic — is right about this metric.

What that does **not** mean is that an independent experiment discovered the absence of a second
channel. The result is close to entailed by how the counter is defined, and the next section says
exactly how close.

## Why the result is close to entailed

The attack charges one probe per candidate per property until one candidate remains. Write

    probes = k + c

where `k` is the number of module-level callables and `c` is the extra cost of discriminating among
the candidates that survive the first property. Matching `k` can only force the probe difference to
zero if `c` is already family-invariant. So the experiment has real content only where `c > 0`.

Measured `c = probes - k` on each family's own (unpadded) artefact, all three seeds:

| task | k A/B/C | c A/B/C | spread |
|---|---|---|---|
| `sumselected` | 4/5/5 | 4/4/4 | 0 |
| `countchars` | 4/5/5 | 2/2/2 | 0 |
| `clamp01` | 4/5/5 | 3/3/3 | 0 |
| `is_even` | 4/5/5 | 2/2/2 | 0 |
| `maxlen` | 4/5/5 | 5/5/5 | 0 |
| `running_total` | 4/5/5 | 0/0/0 | 0 |
| `signdiff` | 4/5/5 | 9/9/9 | 0 |
| `first_negative` | 4/5/5 | 7/7/7 | 0 |
| `count_above` | 4/5/5 | 0/0/0 | 0 |
| `rle_encode` | 4/5/5 | 0/0/0 | 0 |
| `rle_decode` | 4/5/5 | 0/0/0 | 0 |
| `slugify` | 5/6/6 | 0/0/0 | 0 |
| `gcd` | 5/6/6 | 0/0/0 | 0 |
| `priority_pick` | 4/5/5 | 0/0/0 | 0 |
| `rotate_list` | 4/5/5 | 0/0/0 | 0 |
| `store_get` | 5/6/6 | 0/0/0 | 0 |
| `store_keys` | 5/6/6 | 0/0/0 | 0 |

For 10 of the 17 tasks `c = 0`: the first property eliminates every sibling, probes equal the
callable count, and the matched equality is arithmetic. For the remaining 7 tasks `c > 0`
(4, 2, 3, 2, 5, 9, 7 extra probes) and equality additionally required `c` to be family-invariant.
It is: spread 0 on every task and every seed. So the matched experiment's empirical content is
this: once count is held constant, the different transform families produce **the same
discrimination cost**, i.e. they do not perturb what the property set accepts. A family that
injected a behavioural fault would have shown up here, and does not.

The same invariance holds for the whole trajectory, not just the total: with counts matched, the
per-property sequence of surviving-candidate counts is identical across A, B and C in all 51
task/seed cells. Total probe counts could in principle coincide while the intermediate profiles
differ; they do not differ.

## Bias checks actually run (not assumed)

1. **Pad additivity.** For every one of the 153 artefacts, probes were measured with 0, 1, 2 and 3
   pads appended: 459 measurements, **0 deviations** from `probes(base) + pads`. Each pad costs
   exactly one probe, because calling a zero-argument pad with the property's arguments raises and
   the pad is eliminated on the first property. This is why padding A by one exactly cancels B's
   one extra callable.
2. **Does appending no-ops change the obfuscator's own insertion behaviour?** Appending after
   generation cannot, by construction. To test the stronger counterfactual, each source was
   pre-padded with 2 no-ops and regenerated: in **0 of 153** cells did the emitted callable count
   differ from baseline+2, and in **0 of 153** cells did the probe count differ from baseline+2.
   At this pad level the obfuscator neither drops the pads nor changes how many callables it
   inserts itself, so a hypothetical source-visible pad would have given the same answer.
3. **Symmetric padding.** Equalising to max makes A the only padded family. Repeating with a common
   target of max+2, so that B and C also receive pads, still gives +0.00 for all three pairings.
   The 0.00 is not an artefact of which family was padded.
4. **Exactness.** Matched probe counts are equal across families in all 51 task/seed cells, so the
   difference is 0.00 exactly rather than 0.00 after rounding.
5. **Harness.** The unmatched column reproduces `table_diversity()`'s published
   +0.33 / +0.33 / 0.00, including the three tasks in the confound table.

## How this experiment could still be wrong

These are the real limits of the result, not disclaimers.

* **The null is mostly forced.** On 10 of 17 tasks `probes = k` exactly, so matching counts
  *cannot* leave a difference under this counter. Only the 7 tasks with `c > 0` could have shown a
  second channel. That is a small basis, and it is the honest scope of the evidence.
* **Pads are the easiest possible candidates.** A pad always fails the first property and costs
  exactly one probe. If a family's inserted callable sometimes passed a property, it would cost
  more than one, and padding could not reproduce that. In this data B's and C's extra callable did
  cost exactly one probe — the unmatched A-vs-B difference is exactly +1/3 per task, which is one
  probe in the one crossed seed cell — but that is measured at one cell per task, not for every
  callable a family could insert.
* **Padding up, not stripping down.** The alternative equalisation — removing B's and C's extra
  callable — was not attempted. Their extra callable is a string-decoding helper referenced by the
  transformed code, so deleting it would break the artefact rather than make it comparable. Padding
  A is the safe direction, but it means the matched artefact is "A's own four candidates plus a
  foreign no-op", not a natural five-callable A.
* **One crossed observation per task.** `table_diversity()`'s statistic varies only the seed-22
  cell, so each task contributes one crossed comparison. Three seeds, 17 hand-written tasks, and
  the diffs quantise to multiples of 1/3. A family effect smaller than one probe could not be
  resolved.
* **No claim about semantics.** The property set is behavioural; it cannot see a semantic difference
  that does not change a property outcome. Matched counts remove the only structural quantity the
  counter reads, and `c` is invariant, so nothing is left for this counter to see. That is a
  statement about the instrument, not proof that the instrument is adequate to the original
  question about attacker effort.
* **stdout silencing.** The real-task `_demo` helper is a candidate callable that prints when
  probed. Measurement redirects stdout around the same `AccumulatingAttack.apply` call; probe
  counts were identical in a spot check with and without the redirect. It cannot affect the count,
  but it is a deviation from `table_diversity()`'s literal code path and is recorded as such.

## What this changes in the paper

The corrected claim stands; it should be stated with its scope:

> The property set cannot observe *semantic* transformation. It **can** observe *structural*
> transformation: families that insert different numbers of module-level callables are
> distinguishable, and the probe count tracks that number. With the count held constant the family
> difference is exactly 0.00 on all 17 tasks — the residual discrimination cost is identical across
> families — so on this benchmark the family channel is entirely callable count. That equality is
> partly forced by the counter (on 10 of 17 tasks probes equal the callable count), and it is
> evidence about this metric, not about attacker effort in general.

It should also stop calling B-vs-C 0.00 evidence about diversification: B and C insert equal counts
on every task, and equal residual discrimination cost, so the pairing was blind by construction.
