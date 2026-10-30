# Multi-Task Calibration: 8 Tasks, 15/24 Unique Identification

**Date:** 2026-10-30
**Task set:** `scripts/transfer/tasks.py` — eight hand-written tasks, each a
target with three same-arity siblings and an executable property set.

## Why hand-written

The review warned that a public repository corpus lets a model-based attacker
recall source, inflating recovery. Hand-written tasks cannot be recalled, so a
favourable result cannot be explained by memorisation. The cost is that they
are synthetic, and that cost is recorded here rather than hidden.

## Result

Across 8 tasks × 3 build indices (k = 0, 2, 4):

- **15 of 24** (task, k) cells identify the target uniquely;
- probe counts per task stay in a narrow band (e.g. sumselected 7–10,
  clamp01 10–14, running_total 5–8);
- apply time per cell is 0.0002–0.0038 s.

## The failures are not what they look like

Nine cells report zero hits, which reads like semantic corruption by the
obfuscation. It is not. Direct execution of the same builds gives

    k=0 seed=5501 -> [6, 0, 0, 5]
    k=4 seed=5505 -> [6, 0, 0, 5]

identical values, so the transformation preserved behaviour and the property
set should have matched.

The harness explanation: `apply_spec` counts a candidate as a failure when it
raises, and one sibling in these modules raises `TypeError` on the property
inputs (different arity). That should only eliminate that sibling, so the
zero-hit cells remain unexplained and are recorded as **an open harness
defect**, not as evidence about the protection.

**This document exists because that distinction matters.** A zero-hit cell
attributed to "obfuscation breaks semantics" would be a severe claim about
the product; it was wrong, and it was caught by executing the function
directly instead of trusting the aggregate.

## What is established

- The task set exists and is committed, with specs and siblings.
- Probe cost is small and stable across tasks and build indices.
- 15/24 unique identification with an oracle-free attacker.

## What is not

- Why nine cells read zero. That is a harness defect to fix before any of
  these numbers is used.
- Whether the corpus is representative. Eight synthetic tasks are not.
- Priced property authoring, which remains the unpriced labour in the study.
