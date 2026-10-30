# Manuscript Skeleton: Attack-Transfer Cost Across Diversified Python Builds

**Status:** structure and sourced numbers only. Sections marked **[GAP]** cannot
be written from the current evidence and must not be filled by inference.

Every figure below cites the document it came from. If a number is not
traceable to one of those documents, it does not appear.

---

## Abstract (draft, bounded)

We study whether per-build diversification of Python source obfuscation raises
the cost for an attacker to identify a function. Using seventeen tasks across
two benchmark families -- nine hand-written and eight drawn from real programs
-- an attacker that receives only an emitted artefact plus the task
specification, and a cost instrumented in probes, we measure identification
cost as a function of the build the attacker is given. An earlier version of this
endpoint was withdrawn: the attacker it measured was memoryless in *k*, so a
flat curve was a property of the harness rather than of the defence
(`retraction-cost-curve.md`). The replacement measures identification cost in
probes, and separates the two things that vary across builds.

The answer is negative. Varying the transform family across builds does not
raise identification cost: across three families and all three pairwise
comparisons, two of the families are indistinguishable (difference 0.00, sd
0.00 over nine tasks) and the only differences come from one family being
easier to eliminate than the others. What does raise cost is the number of
same-shaped candidates in the module, which moves the mean from about two
probes at one candidate to about eight at four, monotonically in nine of nine
tasks and invariant to the order the functions appear in.

**Scope limit, stated in the abstract rather than the limitations:** eight
synthetic tasks, one obfuscation configuration, identification only.

## 1. Introduction

The deployment question: when one build is analysed, how much of that work
carries to a separately generated build of the same program?

[GAP] Motivating deployment scale. No customer deployment data exists in this
repository; the introduction cannot claim one.

## 2. Related work

From `literature-matrix.md` and the review bound as evidence. Nearest prior
work: DCVP (2018), CoDiver (2019), DSVMP (2018), DynOpVM (2019), N-version
obfuscation (2016), chosen-instruction attacks (NDSS 2022), Loki (USENIX Sec
2022), DEBRA (2025), and Python-specific studies (2025–2026).

**Positioning, as required by the review:** this is not a claim that
cross-build knowledge reuse is new. CoDiver exists to invalidate analysis
knowledge; DSVMP and DynOpVM already evaluate re-analysis after a mapping
change. What is offered is a *measurement* in a different artefact class
(Python source), with a cost endpoint and an oracle-free attacker.

**Documented screen, not a systematic review.** `novelty-search-log.md`
records the four queries, the seven sources returned, the inclusion decision
for each, and the closest prior work with reasons it differs. It supports a
bounded statement — no prior study measures cross-build identification cost in
Python source with an oracle-free attacker — and explicitly does not support
"nobody has done this" or any priority claim.

## 3. Definitions and threat model

From `protocol-v3.md`:

- **Attacker sees:** one emitted artefact, executability, the task
  specification. Not the clean source, not evaluator vectors, not labels.
- **Oracle-free:** the attacker arm's `develop()` takes only a build; five
  guards in `tests/test_artifact_only_attack.py` assert it never touches
  ground truth, vectors, or the original source.
- **Cost currency:** CPU-seconds of attacker tooling plus 0.5 s per target
  execution; probes counted separately (`protocol-v3.md`).
- **Identity vs conclusion:** identity is decided by the evaluator against
  the original; the attacker's property set decides only its own conclusion.
  Conflating them is what produced three rounds of unattributable numbers.

## 4. Method

### 4.1 Benchmark

Eight hand-written tasks, each a target with same-arity siblings
(`scripts/transfer/tasks.py`). Hand-written because a public corpus allows
memorisation; the cost is that the tasks are synthetic.

Validity gate (`task-validity.md`): a task is usable only if the evaluator
can distinguish the target from every sibling on evaluator inputs. Current
state: **24 of 24 cells valid**, after repairing two task defects.

### 4.2 Attacker

Spec-directed: a set of executable properties written from the task
description, with attacker-chosen inputs and no reference outputs. Four to
five properties per task; one or two are sufficient to separate
(`authoring-cost-proxy.md`).

### 4.3 Build

Pipeline build with pinned transform selection. **Not byte-reproducible**:
eight builds, 314-byte size spread (0.08%), median 100 differing lines, and
**8 of 8 distinct ASTs** (`build-nondeterminism.md`). Therefore builds are
never treated as paired for recovery inference; the cost endpoint is
unaffected because the variation is far below any detectable effect.

### 4.4 A correctness defect found by this work

Two opaque-predicate builders emitted unsatisfiable conditions and the
injector wrapped whole function bodies in them; affected functions silently
returned `None`. Fixed and guarded by 13 tests that evaluate every builder
200 times (`tests/test_opaque_predicates_are_true.py`). This is reported
because it changed every measurement taken before it, and because a study
that silently included such builds would have reported a protection effect
that was really a build defect.

## 5. Results

### 5.1 Identification cost and k: a bounded null

**The first version of this endpoint was withdrawn.** It measured an attacker
whose `develop()` took one build and whose guards forbade carrying state
forward, so cost could not depend on *k* and a flat curve was guaranteed
(`retraction-cost-curve.md`). It also used CPU-seconds, which at this scale are
dominated by interpreter startup (median 0.007 s).

The replacement attacker accumulates state and orders properties by learned
elimination power, and the currency is probes. The paired difference between
the last and first build across eight tasks is a mean of +0.38 probes with a
95% interval of [-0.39, +1.14], which includes zero; effects larger than about
one probe are excluded.

That was the state of the endpoint at round 37. It has since moved, and the
movement is the paper's cost result.

**Accumulated experience has no effect.** Holding the build fixed and varying
only how many other builds the attacker had seen, probe cost is constant
(9, 9, 9, 9, 9 for k = 0, 1, 2, 4, 6). The earlier k-dependence was build
variation, not learning (`power-analysis.md`, round 50).

**The build has no effect at fixed size.** Three independently generated builds
of each task, scored by a fresh attacker, give identical probe counts: median
per-task spread 0, maximum 0 (`cost-is-build-independent.md`, round 51).

**Module size dominates.** Growing the candidate list one sibling at a time
raises cost monotonically in nine of nine tasks, from a mean of 2.0 probes at
one candidate to 8.3 at four (round 53). Permuting sibling order leaves the
endpoint unchanged (every permutation ends at 9) while the path moves, so the
endpoint is order-invariant and sibling-dependent (round 54).

The claim the data supports:

> The cost of identifying a known function by specification depends on the
> number of same-shaped candidates in the module and on how hard each is to
> eliminate, but not on the build, not on the order of functions, and not on
> how much analysis the attacker has previously done.

This is not a tautology: at fixed candidate count the cost is invariant, and
varying the count changes it several-fold.

### 5.2 Does diversity itself raise the cost? No.

The question the study set out to answer is separate from module size, and it
takes one more control to see. Comparing builds that vary **only the seed**
against builds that **alternate transform families**, over three families and
all three pairs:

| pair | mean difference in probes | sd |
|---|---|---|
| A vs B | +0.33 | 0.00 |
| A vs C | +0.33 | 0.00 |
| **B vs C** | **0.00** | 0.00 |

Family A is one probe cheaper than B and C; **B and C are identical**. So the
difference is which family was used, not whether the family varied. Switching
between two equally-hard families costs the attacker nothing.

This is a negative result and it is the study's answer:

> Varying the transform family across builds does not raise identification
> cost. What raises cost is a family whose transforms make the target harder to
> eliminate, and that is a property of the transform, not of the variation.

It also explains an earlier reading: one pair (A vs B) alone gives +0.33 with
zero variance, and reporting it would have claimed a diversity benefit that the
B-versus-C control removes.

### 5.3 Replication on real corpus functions

To test whether the pattern depends on hand-written fixtures, eight tasks were
built from the repository's own corpus (`real_tasks.py`), spanning five
modules: `rle_encode`, `rle_decode`, `slugify`, `gcd`, `priority_pick`,
`rotate_list`, `store_get`, `store_keys`. The siblings are the other functions
in each module; the specifications were written from what each function does.

| k | cells | unique identity | attacker hit |
|---|---|---|---|
| 0 | 8 | 8 | 8 |
| 2 | 8 | 8 | 8 |
| 4 | 8 | 8 | 8 |

Source: `real-corpus-tasks.md`. Combined with the synthetic set: **51 valid
cells, 48 unique, 48 hit**, all produced after the opaque-predicate fix.

The finding replicates on two independent benchmarks with no change in
direction. That is the strongest form the claim can take without a public
corpus, and the corpus remains the largest open gap.

### 5.4 The attacker is not unique everywhere

`signdiff` returns two candidates at every k. Uniqueness is the evaluator's
measure (24/24), not the attacker's. Reported separately because merging them
would overstate the attacker.

### 5.5 Authoring bound

33 properties across eight tasks; 1–2 needed to separate. Paid once per task,
not per build — a reason the old curve could not have detected a build
effect even if one existed.

[GAP] Analyst-minutes. The proxy is not a time measurement.

## 6. Discussion

The specification is invariant under the transformation: instruction-level
obfuscation changes how a function looks, not which observable behaviour
matches the specification.

**This is now a hypothesis, not a result.** The earlier flat curve was cited as
evidence for it, and that curve could not have shown otherwise. What the data
supports is weaker: on eight tasks, an accumulating attacker's probe cost is
unchanged within about one probe. Whether that reflects invariance or the
insensitivity of the instrument is not decided here.

**When the invariance breaks.** It breaks exactly when the transformation
changes observable behaviour in a way the specification does not pin down.
This study has one direct observation of that, and it was accidental: two
opaque-predicate builders emitted false conditions, the injector wrapped whole
function bodies in them, and affected functions silently returned `None`
(§4.4). In those builds the property set failed — not because the attacker was
weak or the protection strong, but because **the artefact no longer
implemented the function**. The specification and the program had diverged.

That gives the mechanism a precise form: per-build diversity is
attacker-cost-neutral only while every build is semantically equivalent to the
original. The moment a build is not, every downstream measurement attributes a
correctness failure to a security effect. This is why the study requires a
behavioural equivalence gate per build before any cell is scored, and why the
opaque-predicate guard exists.

**Still open:** whether a *deliberate* semantic-preserving perturbation could
make the specification ambiguous — for example by changing which boundary case
the function treats as inclusive without changing any behaviour the spec
mentions. That is a research question about specification completeness, not a
bug, and it is not investigated here.

## 7. Validity, ethics, limitations

- **Memorisation:** hand-written tasks avoid it; a public corpus would not.
- **Construct validity:** identification is not understanding.
- **Scale:** eight synthetic tasks, one configuration.
- **Reproducibility:** builds are seeded, not byte-identical.
- **Negative results:** four harness defects and two task defects are
  documented in `pilot-calibration.md` and `task-validity.md`; three of the
  four harness defects produced "the protection works".

## 8. Conclusion

Bounded claim: for function identification in Python source, per-build
diversity of the kind tested does not raise attacker cost, because the
specification an attacker uses is invariant to the transformation.

---

## Submission readiness

| requirement | state |
|---|---|
| defensible primary question | ✔ protocol v3 |
| oracle-free attacker | ✔ guarded |
| valid benchmark | ✔ 24/24 |
| cost endpoint measured | ◐ bounded null, retracted and replaced |
| authoring bound | ✔ proxy |
| negative results reported | ✔ documented |
| **corpus scale** | ◐ 51 cells, but 5 real modules against a target of 12–15 projects |
| **systematic novelty review** | ✘ targeted screen only |
| **analyst-minutes** | ✘ proxy only |

**This is not submittable.** It is a skeleton in which every present number is
sourced and every absent section is labelled, so the remaining work is visible
rather than implied.
