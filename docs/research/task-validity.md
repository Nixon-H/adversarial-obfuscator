# Task Validity: Nine of 24 Cells Are Ambiguous by Construction

**Date:** 2026-10-30
**Script:** `scripts/transfer/evaluate_tasks.py`

## The separation that resolved it

Rounds 14–15 could not attribute nine zero-hit cells because a single number
conflated two questions. Splitting them:

- **identity** — decided by the evaluator, which alone holds the original
  function: run each candidate of the obfuscated build on evaluator inputs
  (different from the attacker's) and keep those matching the original;
- **conclusion** — decided by the attacker's frozen property set;
- **score** — does the attacker's passing set intersect the evaluator's
  identity set?

## Result

| quantity | value |
|---|---|
| cells | 24 (8 tasks × 3 builds) |
| evaluator-unique identity | **15** |
| attacker hit (intersects truth) | **20** |
| **cells where the evaluator cannot name a unique target** | **9** |

The nine ambiguous cells are exactly the nine that read zero in round 14.

## What that means

In those nine cells the evaluator itself cannot say which function is the
target: a sibling is behaviourally identical to it **on the evaluator's
inputs**. The task, as written, has no unique answer. No attacker can be
scored on it, and a zero there says nothing about the attacker or the
protection.

The cause is task design: siblings were chosen to be near-duplicates, and
for several of these tasks the evaluator input set does not separate them.
`first_negative` is representative — `fn3` uses `x <= 0` where the target
uses `x < 0`, and none of the three evaluator inputs contains a zero.

## What this fixes

1. Rounds 14–15's "zero-hit cells" are explained: they are **invalid tasks,
   not failures**. The correct reporting is to exclude them and say why.
2. It also shows the attacker is stronger than round 14 suggested: 20 of 24
   cells intersect the truth, and among the 15 valid ones the property set
   finds the target.
3. It gives the task set a **validity gate**: every task must be checked for
   evaluator-distinguishability before it is used, and a task that fails is
   repaired by adding a separating input, not by hoping.

## Limits

- The evaluator inputs remain finite. "Unique" means unique **on these
  inputs**, which is the same caveat the study must carry everywhere.
- The seven repaired-or-ambiguous tasks have not been fixed yet; the count
  above is the honest current state, not a target.
- Attacker hit rate on valid cells only: 15 of 15 by construction of the
  intersection test, which is why the meaningful measure is the *validity*
  rate (15/24) rather than the hit rate.

## Round 17: the k=4 cells are not ambiguous tasks — they are an open defect

Repairing the ambiguous tasks required looking at why four cells have
**zero** candidates matching the original. The answer is not ambiguity:

`sumselected`, k=4, seed 5505, evaluator inputs
`[([1,2,3,4],1,4), ([2],2,3), ([9,9],9,10)]`:

| | values |
|---|---|
| original | `[6, 2, 18]` |
| candidates | `[None, None, None]`, `TypeError`, `[9, 0, 0]`, `[None, None, None]`, **`[7, 3, 19]`** |

No candidate matches. The closest, `[7, 3, 19]`, is the original plus one in
every position — which is exactly `sibling_c`, the sibling that starts its
accumulator at `1` instead of `0`. So the module contains the siblings and
**nothing that behaves like the target**.

Two explanations remain, and the evidence does not choose between them:

1. the target function is dropped from the build at this seed; or
2. the target is present but its behaviour changed.

Both are serious. Neither is established: a textual search cannot settle it
because the transformation rewrites the comparison expression, so the
target's body does not survive verbatim for a grep to find.

**Status: open defect, needs investigation before any k=4 number is used.**
The correct action is to name every candidate by behaviour against the
original and check whether a function with the target's behaviour exists at
all in the module — not to score the cell.

This is recorded rather than fixed because a wrong answer here would be a
false claim about the product in either direction: "obfuscation drops
functions" if it does not, or "tasks are merely ambiguous" if it does.

## Round 18: the target is dropped, and it is seed-dependent

Round 17 left the k=4 cells as an open defect with two candidate
explanations. This round decides between them.

**The target's behaviour is absent from the module.** Every candidate was
tested against the original on 200 randomly generated argument tuples; zero
candidates matched. So it is not a changed behaviour that the evaluator's
three inputs happened to miss -- the function is gone.

**It requires several functions to reproduce.** Same seed, same build index:

| source | candidates matching the original |
|---|---|
| target + 1 sibling | 1 |
| target + all 3 siblings | **0** |

**It is seed-dependent.** With all three siblings and the same build index,
`master_seed` 1–10 all preserve the target; in the range 5500–5510 exactly
one seed (5505) loses it — **1 of 11**.

### Why this matters beyond the pilot

A build that silently drops a function is a correctness defect, not a
measurement artefact. In the study it would appear as an attacker failure,
or as an ambiguous task, and both readings would be wrong. That is how it
first appeared: as nine "zero-hit cells" that survived three rounds of
misdiagnosis.

**Status: open product defect, reproducible at seed 5505.**

### What is needed next

A minimal reproduction at the source level (the 4-function input above is
already minimal for this case) and a bisect over build options to find which
transform drops the function. That is product debugging, not research
instrumentation, and it should be filed separately from the study.

## Round 19: the culprit is a two-transform interaction

Bisecting the pass list at seed 5505, build index 4, over the four-function
source:

| pass set | target survives |
|---|---|
| rename, dead_code, opaque_pred, string_encode, vm (base) | no |
| base minus rename | no |
| base minus **dead_code** | **yes** |
| base minus **opaque_pred** | **yes** |
| base minus string_encode | no |
| base minus vm | no |

Either of two removals fixes it, which points at an interaction rather than
a single faulty transform. Isolating:

| pass set | survives |
|---|---|
| dead_code alone | yes |
| opaque_pred alone | yes |
| **dead_code + opaque_pred** | **no** |
| rename + dead_code | yes |
| rename + opaque_pred | yes |
| rename + dead_code + opaque_pred | no |

So the minimal trigger is **`dead_code` together with `opaque_pred`**. Adding
`rename` neither causes nor prevents it.

Across twelve seeds with that pair, **1 of 12** loses the function (seed 12).
So the defect is a seed-dependent interaction between two transforms, not a
property of either one.

### Why this is the right shape of answer

It gives product debugging three things it can act on:

1. a **minimal repro** — two transforms, not five;
2. a **named interaction** — dead-code insertion and opaque predicates
   combined;
3. a **rate** — about one seed in twelve, so it will hit roughly 8% of builds
   and cannot be dismissed as a one-off.

### Still open

The mechanism is not identified: whether dead-code insertion deletes the
target's body, or opaque-predicate injection mislays it, requires reading the
transform implementations rather than bisecting pass sets. That is the next
step and it is product work.

Until then, any build using both transforms is suspect, and the study must
either exclude the pair or verify every build behaviourally before use.

## Round 20: the mechanism — an opaque predicate that is false, not opaque

The four function definitions are all present in the failing build, so the
function was never dropped. It is **behaviourally broken**, and the body
shows why:

```python
def sumselected(values, lo, hi):
    if _nx_ftable[0](1, 2, 65537) == (pow(3, (0 << 4) + 3, 65537) + 7) % 65537:
        if 16 == 22 ^ 6:
            pass
        else:
            print('SIG_10_OK')
        total = 0
        for v in values:
            if lo <= v < hi:
                total += v
        return total
    else:
        pass
```

The **entire body** is inside the predicate. Evaluating it:

| side | value |
|---|---|
| `_nx_ftable[0](1, 2, 65537)` = `1 * 2 % 65537` | **2** |
| `(pow(3, (0 << 4) + 3, 65537) + 7) % 65537` | **34** |

`2 == 34` is **False**, so the body never runs, the `else: pass` executes,
and the function returns `None`.

**Every result from the suspect builds was `None`.** That is one `if`
statement with an unsatisfiable condition, emitted as an "always true" opaque
predicate.

### What this is

A semantic corruption bug in the opaque-predicate transform: the predicate is
not opaque, it is simply false. It is silent -- the code compiles, imports,
and returns `None` -- and it affects every function it wraps, at a rate of
about one seed in twelve when combined with dead-code insertion.

### Why the combination matters

`opaque_pred` alone did not reproduce it at these seeds, and `dead_code` alone
never did. The pair changes the constants the predicate is built from, which
is why the interaction is the trigger rather than either transform alone.

### Correct framing

Earlier rounds called this "the target is dropped" (round 18) and "the target
behaviour is absent" (round 17). Both were descriptions of the symptom. The
defect is **a false opaque predicate wrapping a function body**, and with the
mechanism visible the fix is obvious where the diagnosis was not.
