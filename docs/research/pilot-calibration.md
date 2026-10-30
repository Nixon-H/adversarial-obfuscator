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
