# Protocol v3 — Response to Independent Review

**Date:** 2026-10-30
**Supersedes:** `protocol-v2.md` for the primary endpoint (v2 remains the record of the earlier design).
**Review bound as evidence:** `ev-1282a3af5d68` (fresh-context adversarial review, 2026-10-30).

Above all: this document changes the study in response to a review that was
asked to be hostile. Each point is answered with a verdict: **accept**,
**reject with reason**, or **defer**. Nothing here is adopted because a
reviewer said it; each acceptance names the cost it imposes.

---

## 1. Novelty — verdict: accept, partially

The review's strongest point: CoDiver exists to *invalidate analysis
knowledge* across partitions; DSVMP and DynOpVM already evaluate
re-analysis after a mapping change; SANER 2024 measures whether an
obfuscation-resilient matcher trained on version *N* survives to *N+1*.
So "frozen vs adaptive transfer" is not itself new.

What the review adds that the plan lacked: **a mechanism argument is
required**, because VM stale-map failure has a structural cause (opcode
renumbering) with no source-level analogue. A benchmark that merely
repeats CoDiver's evaluation on `.py` files is not a contribution.

**Accepted consequence:** the paper cannot claim novelty from the
transfer framing. It must either (a) exhibit a source-level mechanism by
which per-build diversity denies amortization, or (b) be a benchmark and
report that the mechanism is absent. (b) is a legitimate paper and is the
one this protocol now targets.

## 2. Budget currency — verdict: accept, and it was undefined

The review is right: without a currency, *R*_A and *R*_C are not
comparable and the primary contrast is undefined. `protocol-v2.md` said
"matched budgets" without defining them.

**Adopted definition — one currency, mechanically logged:**

> **Attacker cost** = total CPU-seconds consumed by attacker tooling
> (subprocess user+sys time, summed) **plus** 0.5 s per target execution,
> charged for every execution of the protected artifact or the candidate
> under test.

Two components, both automatic, both recorded per run. Wall-clock is
reported but never used for matching (it is noisy under load). LLM
tokens, analyst minutes, and solver calls are **not** used as primary
currency because the review is correct that they are the least
reproducible quantities and would carry most of the paper's value.

## 3. The frozen arm — verdict: accept, demoted

The review's point: for source-level transforms there is no compact
learned artifact whose reuse is natural; the plausible attacker is a
normalizer plus a per-build plugin; "frozen" describes stale regexes no
attacker runs. The plan itself half-admits this.

**Adopted:** the frozen arm is **demoted to a diagnostic**, reported as
a lower bound on what a naive reuse strategy achieves. It is **no longer**
the primary endpoint. The emission `G = R_A - R_F` is dropped as the
"primary contrast" and appears only in an appendix table.

## 4. MIX vs fixed — verdict: accept, dropped from primary

The review's arithmetic is sound: arms A/B/C are already independently
seeded, MIX is marginal-matched, so MIX differs only in the *cross-build
correlation* of the family used — a second-order property. An adaptive
attacker pays one family-fingerprinting step once, and the plan's own
transform-firing manifest makes that step trivial. An interaction needing
~2× the fixed-family adaptation cost is not detectable with ~30 clusters.

**Adopted:** MIX is dropped from the primary design. The comparison becomes
**seed-only vs family-varying**, which is a main effect and needs roughly
a quarter of the N.

## 5. Corpus size — verdict: accept, cut

The review's count stands: 12 seeds × 5 arms × 30 projects = 1,800 builds;
× 3 policies × ≥2 attack families ≥ 10,800 attack runs, each needing
generation, semantic gating, and a hidden test suite. No cost model
existed.

**Adopted:** 12–15 held-out projects, **one task per project**, two fixed
families + unprotected + a same-build ceiling. Estimated runs drop by an
order of magnitude and are budgeted per project before data collection.

## 6. Endpoint — verdict: accept, changed

The review: "behavioral recovery on finite hidden tests" cannot separate
understanding from equivalent reimplementation, and public-repo corpora
inflate recovery through memorisation.

**Adopted:** the primary endpoint is **not** recovery rate. It is the
**reuse curve**:

> **Attacker cost per target as a function of *k* previously analysed
> builds of the same program**, *k* = 0…5, for seed-only versus
> family-varying diversity.

Reasoning, and why this answers the review: recovery rate is a
construct-validity minefield; **cost to reach a fixed, pre-registered
recovery threshold** is measurable, logged, and has a natural zero
(k = 0 is cold start). If cost flattens at *k* = 1, per-build diversity
buys nothing and deployers should stop paying for it. If it keeps rising,
that is the first credible evidence for per-build source diversification.
Either sign is publishable.

## 7. What this protocol does not fix

Stated plainly, because a protocol that hides its weaknesses is worse than
one that does not:

- **Memorisation.** A public-repo corpus lets a model-based attacker recall
  source. The defence is to report the unprotected-baseline recovery and
  treat it as an upper bound, not to claim a sequestered holdout one person
  cannot maintain.
- **VM coverage.** Still one eligible function. The VM arm is out.
- **Reproducibility.** The build is not yet byte-identical (~100 differing
  lines between pinned builds). The cost endpoint is more tolerant of this
  than recovery-rate inference, but the residual must be characterised
  before Phase 3, not after.
- **The attacker.** The repository's current static attack calibrates
  against ground truth and confirms with ground-truth vectors
  (`scripts/transfer/attack.py`); it is oracle-assisted and cannot be the
  primary attacker.

---

## Revised design, in one table

| Element | v2 | **v3** |
|---|---|---|
| Primary endpoint | *R*_A − *R*_F (adaptation gap) | attacker cost per target vs *k* |
| Arms | 5 (H0–H4) incl. MIX | 4 (unprotected, family A, family B, same-build ceiling) |
| Projects | 30 × 5 tasks | 12–15 × 1 task |
| Budget currency | undefined | CPU-seconds + executions |
| Frozen arm | primary | diagnostic (appendix) |
| LLM track | optional secondary | out |
| VM arm | secondary | out |
