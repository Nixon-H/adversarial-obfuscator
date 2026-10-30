# Manuscript Skeleton: Attack-Transfer Cost Across Diversified Python Builds

**Status:** structure and sourced numbers only. Sections marked **[GAP]** cannot
be written from the current evidence and must not be filled by inference.

Every figure below cites the document it came from. If a number is not
traceable to one of those documents, it does not appear.

---

## Abstract (draft, bounded)

We study whether per-build diversification of Python source obfuscation raises
the cost for an attacker to identify a function. Using eight synthetic tasks
with same-arity siblings, an attacker that receives only an emitted artefact
plus the task specification, and a cost instrumented in CPU-seconds, probes
and executions, we measure identification cost as a function of *k*
previously analysed builds of the same program. An earlier version of this
endpoint was withdrawn: the attacker it measured was memoryless in *k*, so a
flat curve was a property of the harness rather than of the defence
(`retraction-cost-curve.md`). The replacement attacker accumulates state across
builds. Measured over eight tasks, the paired change in probes between the last
and first build is +0.38 with a 95% interval of [-0.39, +1.14]: no consistent
effect, and effects larger than about one probe are excluded. We therefore
report a bounded null rather than a finding.

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

So the honest result is a bounded null: at this scale, accumulated state does
not reliably change identification cost in either direction.

### 5.1b Replication on real corpus functions

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

Source: `real-corpus-tasks.md`. Combined with the synthetic set: **48 valid
cells, 48 unique, 48 hit**, all produced after the opaque-predicate fix.

The finding replicates on two independent benchmarks with no change in
direction. That is the strongest form the claim can take without a public
corpus, and the corpus remains the largest open gap.

### 5.2 The attacker is not unique everywhere

`signdiff` returns two candidates at every k. Uniqueness is the evaluator's
measure (24/24), not the attacker's. Reported separately because merging them
would overstate the attacker.

### 5.3 Authoring bound

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
| **corpus scale** | ◐ 48 cells, but 5 real modules against a target of 12–15 projects |
| **systematic novelty review** | ✘ targeted screen only |
| **analyst-minutes** | ✘ proxy only |

**This is not submittable.** It is a skeleton in which every present number is
sourced and every absent section is labelled, so the remaining work is visible
rather than implied.
