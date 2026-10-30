# Corpus Acquisition Plan: How to Close the Last Gap

**Date:** 2026-10-30
**Status:** plan, not data. Nothing here is claimed as done.

The reviewer's remaining objection is the only one better statistics cannot
touch: eight tasks written by one author is not a benchmark. This document is
the concrete protocol for replacing it, written so the work can be executed
without re-deriving the requirements.

## What the review requires

> ≥12 external projects, ≥40–50 tasks, ≥2 independent spec authors, the
> unprotected baseline arm, and a behavioural-equivalence gate on 100% of
> builds.

Each of those is answered below with a procedure, not an intention.

## Selection criteria

A project is eligible when all of these hold:

1. **Pure, deterministic functions.** No I/O, no clock, no randomness, no
   global state. Determinism is required because the evaluator compares
   behaviour across builds.
2. **Importable in isolation.** The function must be callable without
   instantiating the application. This excludes most web and CLI code and is
   the binding constraint on yield — expect roughly 5–10 eligible functions
   per 1,000 lines.
3. **Testable from a specification.** There must be a way to state what the
   function does without restating its implementation. A function whose
   contract is "whatever the tests assert" is not eligible.
4. **Licence permits redistribution of derived artefacts.** Apache-2.0, MIT,
   BSD, PSF. Exclude GPL for the source-derived artefacts the study
   distributes, and exclude anything with no licence.
5. **Not in a model's likely training set.** Cannot be verified. Mitigation: use
   repositories created recently, and report the unprotected-baseline recovery
   as an upper bound rather than pretending contamination is absent.

## Acquisition procedure

1. Pin the commit hash. Record it in the manifest with the licence text.
2. Run a **candidate extractor** that keeps only functions where:
   - every argument and return value is JSON-serialisable, and
   - the body has no `import` of I/O modules, and
   - the function has at least one branch or loop (trivial one-liners are not
     discriminating).
3. For each candidate, write **two to five properties** from the docstring or
   from the public API documentation — not from the body. Record the source of
   the specification (docstring line, README section, or "inferred from name",
   which is the weakest and must be flagged).
4. Run the **evaluator-distinguishability gate** (`task-validity.md`). A task
   whose target is not uniquely identified by the evaluator inputs is repaired
   by adding a separating input, or dropped with the reason recorded.
5. Run the **behavioural-equivalence gate** on every build. A build that fails
   it is excluded and counted in the reporting; it is never silently dropped.

## The independent-author requirement

Two spec authors is the requirement, and it is the one hardest to satisfy from
inside a single session. The procedure:

- author A writes properties from documentation only;
- author B writes properties from the same documentation without seeing A's
  set;
- disagreements between the sets are the interesting object — they indicate an
  ambiguous specification, and the task is either clarified or dropped.

Without a second person, the honest substitute is to report **single-author
specifications as a limitation and to measure author sensitivity**: have a
model with no access to the implementation write a property set from the
docstring alone, and report how often it agrees. That is weaker than two
humans and must be labelled as such.

## What this plan is not

- It is **not** started. No external project has been acquired.
- It does **not** claim the current 51 cells are a corpus. They are a
  calibration set with a validity gate, and they are labelled that way.
- It does **not** resolve the memorisation problem. Public code may be in a
  model's training data; the mitigation is reporting, not elimination.

## Effort estimate, with its basis

| step | basis |
|---|---|
| select and pin 12–15 projects | one day, mostly licence review |
| extract eligible functions | ~10 per 1,000 lines, mechanical |
| write 2–5 properties per task | measured here: 4 per task, 1–2 essential (`authoring-cost-proxy.md`) |
| dual authoring | doubles the property work |
| generate 12 seeds × 2 families | the existing runner, unchanged |
| gate and score ≈360 cells | ~0.01 s per cell for scoring; build time dominates |

The property writing is the real cost, and it is measured rather than guessed:
four assertions per task, one or two of which are load-bearing. At 40 tasks
that is roughly 160 assertions — feasible for one person with a working
instrument, which is what this repository now has.

## Why this is the honest stop

Every gap in this programme has been closed by building an instrument:
the attacker, the validity gate, the cost currency, the equivalence test, the
document guards. This one cannot be. It requires **code written by other
people** and **a second author**, and neither is an instrumentation problem.

Writing the protocol is the most useful thing available, because it converts
"needs a corpus" from a wish into a checklist someone can execute.
