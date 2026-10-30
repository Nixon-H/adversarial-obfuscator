# Calibration Pilot: Structural Ranking Survives the Obfuscation

**Date:** 2026-10-30
**Script:** `scripts/transfer/pilot_min.py` (committed, reproducible)
**Scope:** three fixtures, two unrelated decoys each, one obfuscated build per
fixture. This is the Phase-2 calibration step, not the study.

## Result

| fixture | candidates | plain top-1 | obf top-1 | build (s) | rank both (s) |
|---|---|---|---|---|---|
| accumulate | 3 | 1 | 1 | 0.09 | 0.01 |
| count_words | 3 | 1 | 1 | 0.01 | 0.01 |
| clamp | 3 | 1 | 1 | ~0.0 | 0.01 |

**3/3 top-1 on unprotected, 3/3 top-1 on obfuscated.** The oracle-free
attacker, ranking purely by structural heuristic, puts the target first
whether or not the source was transformed.

This is a **negative result for the protection** at this size. It is also
the first number in the programme that was produced by an attacker with no
oracle channel, so it is the first recovery number worth taking seriously.

## What four defects taught us

The path to 3/3/3 produced four false readings, and **every one of them made
the protection look better than it is**:

| defect | false reading |
|---|---|
| `not name.startswith("_")` filter | excluded every renamed candidate → 0/3 |
| "first callable in `dir()`" as reference | picked `accumulate` for all fixtures → 0/3 |
| name-based scoring | names are what obfuscation changes → 0/3 |
| plain path passed to the obfuscated scoring call | loaded unrenamed functions against renamed candidates → 0/3 |

Each was a harness bug that produced "the protection works". The fourth
survived three rounds of fixing because the other three were also plausible.
A pilot that reports 0/3 for obfuscated and 3/3 for plain reads like a
strong result, and it was four bugs.

## The sibling condition (added round 11): the protection is not what matters

The third caveat below said unrelated decoys are trivially separable and the
real corpus has siblings. That is now measured rather than asserted.

Fixtures: one target and four sibling functions with the **same arity** and
near-identical bodies (`total += v` versus `total += v * 2`; `lo <= v < hi`
versus `lo < v <= hi`; `total = 0` versus `total = 1`).

| condition | plain top-1 | obf top-1 | obf top-3 |
|---|---|---|---|
| unrelated decoys | 3/3 | 3/3 | 3/3 |
| **siblings** | **0/1** | **0/1** | **0/1** |

The heuristic **fails on siblings — and it fails identically on the
unprotected source**. The obfuscation is not what defeats it; the presence
of near-duplicate functions is. Two consequences:

1. The structural heuristic is too weak for a realistic corpus, and its
   weakness has nothing to do with protection. Reporting an obfuscated 0/1
   without the plain 0/1 would have claimed a security benefit that does not
   exist.
2. Whatever the study measures on a realistic corpus must control for
   sibling density, because that variable dominates the outcome.

This is the most useful negative in the programme so far: it says the
attacker needs semantics, not shape, and that a shape-based attacker's
results cannot distinguish protection from corpus difficulty.

## Caveats, stated as limits on the claim

1. **n = 3.** Three fixtures with two decoys each. This is calibration, not
   evidence about a corpus.
2. **Easy decoys.** The decoys are unrelated functions with different arity
   and shapes. The real corpus has sibling functions that differ subtly,
   which is where structural ranking should fail.
3. **One obfuscation config.** One seed, one pass set. Family-varying
   builds are untested.
4. **Ranking only.** The attacker produces a ranking; a real analyst also
   has to *understand* the function. Its cost is not measured here.
5. **Behavioural scoring is evaluator-side.** The pilot uses ability to
   match behaviour, which is legitimate for the evaluator and forbidden to
   the attacker. The guard test in `tests/test_artifact_only_attack.py`
   enforces that separation for the attacker.

## Consequence for the protocol

The calibration supports one conclusion and one action:

- **Supported:** the attacker is not too weak (gate G5's baseline condition)
  and the cost of a build plus a ranking is milliseconds, so the corpus
  arithmetic in the review is about test construction, not build time.
- **Action:** the fixtures must get harder — sibling functions, similar
  arity, similar size — before any of this counts as evidence about the
  protection. A 3-candidate ranking with obvious decoys is not a test.

## What this does not show

It does not show the obfuscation is weak in general, and it does not show it
is strong. It shows that at n = 3 with unrelated decoys, a fixed structural
heuristic ranks correctly. Every sentence beyond that needs the harder
corpus.

## The spec-directed attacker (round 12): a realistic attacker solves it anyway

Round 11 concluded the shape-only attacker is too weak to test the
protection, because siblings defeat it whether or not the source is
obfuscated. The realistic attacker is not shape-only: the protocol grants
every attacker the **task definition**, and a function's specification is
enough to identify it among same-shaped siblings.

`scripts/transfer/spec_attack.py` implements that attacker. The spec is a
set of executable properties written from the task description -- "sum of
the values in [lo, hi)", "hi is exclusive", "lo is inclusive" -- with inputs
the attacker chooses. It contains no reference outputs and no ground-truth
labels: properties, not answers. Candidates that violate a property are
discarded.

| condition | spec-passing | target found |
|---|---|---|
| plain, sibling decoys | **1 of 4** | yes |
| obfuscated, sibling decoys | **1 of 4** | yes |

The attacker isolates the correct function exactly, before and after
obfuscation. Two of the five properties were added precisely because
`sibling_b` (`lo < v <= hi`) satisfied the rest: a boundary probe at
`hi` was needed to separate it. That is the shape of the real task -- an
analyst writing tests from a specification -- and it costs a handful of
probes.

### What this establishes

At realistic difficulty, with an attacker that uses the task definition,
**the obfuscation provides no measurable protection against function
identification** in this setting. The instruction-level obfuscation changes
how the function looks; it does not change which observable behaviour
matches the specification, and the specification is what the attacker has.

This is a negative result about the protection, obtained with an
oracle-free attacker on sibling-difficulty fixtures. It is still n=1 task
and one obfuscation config, so it is a calibration finding, not a corpus
result. But it is the second consecutive negative, and it points the same
way as the first: the variable that decides these outcomes is not the
transformation.

### What it does not establish

- It does not show obfuscation is useless. It shows that *identification*
  among siblings is unaffected. Understanding, modifying, or extracting
  logic from a semantically-recovered function is not measured here.
- It does not quantify cost: probe count is small, and the cost endpoint
  protocol v3 asks for is not yet instrumented across tasks.
- n = 1 task. The property set is hand-written per task, which is the
  attacker labour the study needs to price.
