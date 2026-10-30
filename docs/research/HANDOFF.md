# Handoff: What To Do Next, And What Not To Repeat

**Written:** round 168. Read this before touching anything in `docs/research/`.

---

## Where things stand

| | |
|---|---|
| defects found and fixed | **nine** |
| test suite | **4521 passed, 4 skipped, 0 failed** |
| artefact gate | **104 artefacts, 0 failures** |
| reproduction | **8 of 8 tables match** |
| paper | 422 lines, instrument-validity note, internally consistent |
| research documents | 51 |
| sealed reports | 45 |

Everything measurable is measured. Five instruments are green. The three things
that matter most are outside this repository's reach — see "What cannot be done
from here" below.

---

## The one thing worth doing next

**Vendor two packages.** `requests` and `attrs` are collected but not gated because
their relative imports need package context. Rounds 148–150 built exactly the
machinery for this:

1. fetch the package into `scripts/transfer/corpus/pkg/<name>/`;
2. add its modules to `artefact_gate.py`'s `_modules()` list as
   `pkg/<name>/<module>`;
3. run `python3 scripts/transfer/artefact_gate.py --variants 2 --seeds 4242,7`.

This is mechanical. It adds no new claim. It does widen the corpus, which is the
only thing that has ever found defects in this programme — four of the nine came
from code the project did not write.

---

## What cannot be done from here

| gap | why not |
|---|---|
| **An independent specification** | All 38 properties are written by this programme's author. Someone else has to write specifications for the same functions without seeing them. The paper names this as the primary limitation. |
| **Analyst time** | Probes are a resolution unit. No human has been timed. A study needs people and a protocol, not a script. |
| **Comprehension** | Identification is not understanding. Nothing here tests whether an analyst could explain or repair a recovered function. |
| **A venue** | The paper is a draft. Submitting it is a decision, not a task. |
| **External review** | The goal asked for opinions from an advanced model. Four reviews happened, all by the same author. That is not the same thing and the record says so. |

---

## The five rules this programme paid for

Each of these was learned by getting it wrong at least once. They are listed in the
order they cost the most.

### 1. A failing instrument is not evidence about the system

Three times an instrument produced an alarming, specific, wrong answer:

| round | instrument | how it lied |
|---|---|---|
| 102 | fixture | the input was not valid Python |
| 132 | grep | the range ended three lines short of the code |
| 135, 14a | reducers | pruning created the very failure they reported |

**Before trusting a failure: prove the instrument works.** Compile the fixture,
check the range, parse the reduced output.

### 2. Check the baseline before blaming your change

Rounds 123 and 124 reverted two possibly-correct fixes because the suite had
failures that predated them. The eleven failures had been there for fourteen rounds.

**Run the same test on a clean tree.** Four seconds.

### 3. Reproducibility before reduction

Round 139 spent a round bisecting a defect that was nondeterministic in its
**input-dependence**, so every edit changed the outcome. The bisect "found" 31 of
42 function bodies to be responsible — which is noise.

**First make the defect reproduce from a fixed input. Then bisect.** And when
bisecting prose or code, the reduction must be **structure-preserving** —
`ast.parse` after every step, not just "does it still fail".

### 4. Rename on lookup, not at visit time

Four defects in four subsystems were one rule: **a value must have one owner.**

| defect | two owners |
|---|---|
| 30-day expiry | pack-time window vs run-time window |
| `hexversion` | import binding vs renamed use |
| `_sumprod` | aliased import vs fallback assignment |
| builtin table names | table value vs renamed reference |

### 5. A revert is not complete until its call sites are gone

Round 123 reverted a file and left a call to the removed helper. The resulting
`TypeError` was swallowed by an `except` that returned the caller's own source, and
**eight rounds** were spent investigating symptoms of that one stale line.

**And:** an `except` that returns the input turns every future bug into silence.
`apply_ast_mutation` still does this — see below.

---

## Known open items, with severity

| item | severity | note |
|---|---|---|
| `apply_ast_mutation` returns `(source_code, {})` on any exception | **medium** (was high) | **Round 169: it now emits a `RuntimeWarning` naming the exception and saying the caller receives unobfuscated source.** The return is unchanged for compatibility with 34 test and 8 production call sites, but the failure is no longer silent, and `python -W error::RuntimeWarning` turns it into a raise. A full re-raise is still the correct end state. |
| `dotproduct` at build index 0 is not evaluator-unique | low | Reported, not pooled. Fix is a separating input. |
| Two packages un-gated | low | Mechanical; see above. |
| `MAX_PROFILES`/other `_511` ORs | none known | Lower bound only; nothing above it is claimed. |

---

## What not to do

- **Do not add test skips** to make the suite green. The programme's standing rule.
- **Do not widen a conservative guard** to accommodate a false positive. Change the
  text instead — rounds 152 and 155 both did this correctly.
- **Do not trust a bisect** without first confirming the defect reproduces from a
  fixed input.
- **Do not quote a green suite from an earlier round** as current. Round 111's
  result was quoted for fourteen rounds while the suite was red.
- **Do not claim an option works because it is accepted.** That was defect #9's
  shape; it took three rounds to find and it was wrong.

---

## The honest summary

The research question was answered **negatively**, and the answer is about the
**instrument** rather than the defence: a specification-derived property set is
semantic, so transform-family variation has no channel to it, and any null it
produces is predicted by its own construction.

What the work produced that outlives the question: **nine silent failure modes in
the obfuscator**, six of which the project's own tests could not have found, and
five instruments that fail in different directions.

The paper says all of this. Where it says something the evidence does not support,
it marks it `[unverified]` rather than deleting it.
