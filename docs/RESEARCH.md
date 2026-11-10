# Research Background and Objectives

**Status:** current overview. The full evidence record lives in
[`research/`](research/); the paper draft is
[`research/paper-draft.md`](research/paper-draft.md). This document explains
why the programme exists, what it asks, and how it decides what counts as an
answer.

---

## 1. The problem

Python is normally distributed as source, or as bytecode that a determined
analyst can lift back to a close approximation of source. That makes the
usual binary-protection story unavailable: there is no compiled artefact whose
symbols, control flow, and constants are already several transformations away
from the program's meaning.

For a software vendor, three things follow:

1. **The algorithm is readable.** A competitor, a cracker, or a licence
   circumventor can read the logic that the product's value depends on.
2. **Licensing checks are editable.** Any decision made in the client — a
   trial deadline, a feature flag, a hardware binding — executes on a machine
   the attacker controls.
3. **"Closed source" is a distribution convention, not a control.** Shipping
   `.pyc` instead of `.py` raises effort, but not in a way that survives a
   decompiler.

Obfuscation is the practical response. The research literature contains a large
catalogue of transformations and a long record of attacks that defeat them.
What it contains much less of is **measurement**: how much does a given
transformation actually cost an attacker, and does that cost survive when the
vendor ships a *different build* to the next customer?

That second question is the deployment justification for per-build diversity:
the claim that analysing one build does not transfer to another. It is widely
assumed and rarely tested.

---

## 2. The claim under test

> Per-build diversification of Python source obfuscation raises the cost for an
> attacker to identify a function.

The programme tests one narrow version of this claim:

- **Outcome:** identification of a target function among its siblings — not
  full comprehension, not exploit development, not licence bypass.
- **Cost unit:** specification-derived probe evaluations — the number of
  executable properties the attacker must apply to narrow the candidate set to
  one.
- **Attacker:** holds one emitted artefact and the task specification; never
  the clean source, the evaluator's vectors, or the labels.
- **Corpus:** small, deliberately controlled, and extended with third-party
  code so the benchmark is not entirely self-referential.

A second, later design asks a sharper question: when an attacker has analysed
build A, how much of that work helps against build B, and how much adaptation
does B require? That design separates **frozen transfer** from **adaptive
recovery**. It is specified in
[`research/research-program-plan-2026-10-29.md`](research/research-program-plan-2026-10-29.md)
and is **not yet run**; the current paper reports the static-identification
result only.

---

## 3. Research questions

The programme's questions, in the order they became answerable:

| ID | Question | Status |
|---|---|---|
| RQ0 | Does per-build transform-family diversity raise the probe cost of identifying a function, once structural confounds are controlled? | **Answered, negative** — see [`RESULTS.md`](RESULTS.md) |
| RQ1 | How does a specific attack artefact's recovery success change when transferred across seeds and transformation families? | Partially explored (H0–H5 pilot, const-split); the pilot was invalidated by an internal audit |
| RQ2 | How much does target-specific adaptation restore recovery, and at what cost? | **Not run**; designed in the 2026-10-29 plan |
| RQ3 | Do validated source, bytecode, or CFG distances predict recovery or adaptation effort? | **Not established**; current diversity metrics are source-shape proxies, not validated predictors |
| RQ4 | What semantic and operational costs accompany each protection configuration? | Partially measured: lowering overhead, build time, artefact size; no complete cost model |

The distinction between RQ0 and RQ1 is the reason the programme's history is
mostly a record of instrument repair. RQ0 can be answered with a static
property set. RQ1 requires an attacker that carries state between builds, and
the first attempt at that endpoint could not fail — see the retraction in
[`research/retraction-cost-curve.md`](research/retraction-cost-curve.md).

---

## 4. Threat models

There are two, and they must not be conflated.

### 4.1 Product threat model

Applies to the protection toolchain. Stated in full in
[`../THREAT_MODEL.md`](../THREAT_MODEL.md).

| Element | Assumption |
|---|---|
| Attacker | An analyst holding the emitted artefact and a debugger |
| Goal | Read the logic, remove a gate, recover a key, or reuse the payload |
| Build host | **Trusted.** An attacker who can set build arguments is outside the model |
| Root / local admin | **Out of scope.** No user-space control survives a root attacker |
| Kernel | No ring-0 loading; the BYOVD gate is read-only enumeration |
| Claim ceiling | Raises cost and time; does **not** make an artefact unbreakable |

The evidence taxonomy in `THREAT_MODEL.md` classifies every control as
`UNIMPLEMENTED`, `IMPLEMENTED`, `TESTED`, `ADVERSARIAL_TESTED`, or
`ENVIRONMENT_VALIDATED`. Documentation may not claim above the row's status.

### 4.2 Benchmark threat model

Applies to the measurement programme. Stated in
[`research/paper-draft.md`](research/paper-draft.md) §3 and enforced by tests.

| Element | Assumption |
|---|---|
| Attacker sees | One emitted artefact, its executability, the task specification |
| Attacker does not see | Clean source, evaluator vectors, labels, other builds |
| Attacker memory | None across builds in the primary experiment; each build gets a fresh attacker |
| Identity | Decided by the evaluator, which alone holds the original function |
| Conclusion | Decided by the attacker's frozen property set |
| Score | Whether the attacker's passing set intersects the evaluator's identity set |

The oracle-free constraint is tested in
`tests/test_artifact_only_attack.py`: `develop()` takes only a build and a
workdir and references no ground truth, vectors, or original source.

An earlier pilot (`H0–H5`) violated the spirit of this model: its static
attack used clean-source features and known vectors during development. It is
preserved as a pilot and is **not** cited as evidence for the current claim.

---

## 5. Prior work and the bounded novelty statement

The closest prior work, and why each differs:

| Work | Relation |
|---|---|
| **OFCI** (NDSS 2022) | Closest on the outcome: identifies functions in obfuscated binaries, including VM-obfuscated code. Function identification under obfuscation is therefore **not novel**. |
| **CoDiver** (IEEE Access 2019) | Closest on the framing: partition diversity denies reuse of analysis knowledge in virtualised code. The mechanism is structural (stale opcode maps). |
| **DCVP** (ICPADS 2018) | Partitions virtualised code and randomises opcode mappings to limit reuse. |
| **DynOpVM** (ACNS 2019) | Dynamic opcode mapping; evaluates re-analysis after a mapping change. |
| **N-Version Obfuscation** (CPSS 2016) | Program diversity against tampering replication, not semantic identification. |
| **DEBRA** (SURE 2025) | Real-world deobfuscation benchmark; asks whether a method works, not what identification costs across builds. |
| **JsDeObsBench** (arXiv 2506.20170) | Nearest benchmark in scale (36,260 JavaScript programs); different language, different attacker, no cross-build transfer question. |
| **Regano et al.** (Computers & Security 2026) | Closest prior on *effort* measurement; human subjects, no transfer question. |
| **De Sutter et al.** (ACM CSUR 2024) | Documents methodological and reproducibility problems in software-protection research; the reason this programme treats instruments as objects of study. |

**What the programme does not claim.** It does not claim to be first, and it
does not claim that no source-level analogue of CoDiver exists. The novelty
screen is documented in
[`research/novelty-search-log.md`](research/novelty-search-log.md) — eight
queries over two sessions, fifteen sources screened. That supports a bounded
statement, not a priority claim.

The defensible statement is:

> We found no prior study that measures the cost for an attacker to identify a
> function across independently generated builds of the same Python source
> program, at matched budget, with an oracle-free attacker and a
> specification-derived property set.

A full systematic review is still required before any "first" or "to our
knowledge" wording.

---

## 6. Two research tracks

The repository contains two coupled but distinct efforts. Confusing them is the
most common way to over-read the project.

| Track | What it is | Evidence status |
|---|---|---|
| **Protection engineering** | `shadow-compiler`: AST transforms, lowering, packed loader, runtime gates, licensing, native backends | Implemented; tested; individual controls evaluated against named tests, not against a general attacker |
| **Measurement programme** | `docs/research/` and `scripts/transfer/`: benchmark, attacker, protocols, defect discovery, paper | One controlled negative result, one invalidated pilot, one no-transfer-resistance experiment, thirteen defects, a retraction record |

The measurement programme uses the obfuscator as its system under test. It does
**not** evaluate the complete default production build: the experiments use the
source-level research generator (`scripts/diversity/generator.py`,
`ObfuscationTransformer`), not `scripts/build.py` or the packed loader. The
paper says so, and any extension must state which path it studies.

---

## 7. Evidence standard

The programme's rules are unusual enough to state explicitly, because they are
the reason its conclusions are narrower than its early drafts.

1. **A claim gets a check, and the check must be able to fail.** A check that
   cannot fail is not evidence.
2. **Every check gets a stated blind spot.** The blind spot is part of the
   result, not a footnote.
3. **Identity and conclusion are separate.** The evaluator decides identity;
   the attacker decides only its own conclusion. Conflating them produced three
   rounds of unattributable numbers.
4. **A failing instrument is not evidence about the system.** Five separate
   defects were an instrument lying: a fixture that was not valid Python, a
   grep range three lines short, two reducers that altered their input, and a
   version read from the wrong interpreter.
5. **Retractions stay next to what they corrected.** Eight claims were
   withdrawn; the retraction record is part of the evidence.
6. **No test skips to make the suite green.** A failing test is fixed or the
   claim is withdrawn.

These rules are recorded in
[`research/HANDOFF.md`](research/HANDOFF.md) as five lessons the programme
paid for.

---

## 8. What the programme does not claim

- **Not unbreakable.** No construction here resists a root-privileged analyst
  who can observe the plaintext the CPU must execute. The goal is cost, not
  impossibility.
- **Not a general theory of diversity.** The result is about one outcome
  (identification), one artefact class (Python source), and one cost unit
  (probes).
- **Not a validated security metric.** Probe count is a resolution unit, not
  analyst time. No human has been timed.
- **Not a claim that diversification fails.** The claim is that *this
  instrument* cannot distinguish a diversity effect from the callable-count
  confound, and that the observed effect was the confound.
- **Not a claim about the full product.** The benchmark studies a research
  transformation path, not the shipped loader.
- **Not a novelty claim.** The screen is bounded; prior work is close.

---

## 9. Current status

| Item | State |
|---|---|
| Paper draft | Complete, with named caveats; final review verdict was **submit with named caveats**, textual blockers recorded |
| Core result | Reproducible: 10 of 10 tables match |
| Defects | 13 found; 12 fixed; 1 design-level open (cross-module export renaming), with a caller-side mitigation |
| H0–H5 pilot | Preserved, **invalidated** as evidence by the 2026-10-29 readiness audit |
| Const-split experiment | Complete: **no transfer resistance**; any loss is absolute, not transfer-specific |
| Frozen-vs-adaptive study | Designed, **not run** |
| Independent specification | 2 of 11 load-bearing tasks; the primary limitation |
| Analyst-time study | **Not done** |
| Systematic review | **Not done** |

The next step is not another protection layer. It is the frozen-versus-adaptive
experiment with a project-held-out corpus, an adaptive baseline, and a
pre-registered equivalence bound. See
[`LIMITATIONS.md`](LIMITATIONS.md) and the 2026-10-29 plan.
