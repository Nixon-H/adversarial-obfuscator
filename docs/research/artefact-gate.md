# The Artefact Gate: Compile, Import, Exercise

**Date:** 2026-10-30
**Script:** `scripts/transfer/artefact_gate.py`

This implements the recommendation section 6 of the paper makes, and on its
first run it found **nine failures across 63 artefacts** in two new classes.

## What it does

For every corpus module — nine synthetic tasks, eight corpus tasks, six external
tasks — it generates artefacts at several build indices and then:

1. **parses** them (`compile`), catching syntax errors;
2. **imports** them (`exec_module`), which executes module-level code;
3. **exercises** every surviving callable against the task's properties,
   catching failures that only appear when code runs.

It reports the module, the build index and the exception.

## First run

```
artefacts checked: 63
failures: 9
```

| class | example | count |
|---|---|---|
| `_sumprod` undefined | `external/all_equal`, `external/dotproduct` | 5 |
| `_nx_ee5c35` undefined | `external/median_low` | 3 |
| (one more) | — | 1 |

## What these are

`_sumprod` is a private helper in `cpython/statistics.py`. It is imported and
used by the public functions, and after obfuscation the reference survives while
the binding does not — **the same defect class as `hexversion`**, in a module the
earlier fix was not tested against.

That is the point of a gate rather than a fix: the two renamer repairs were
verified against the cases that had been reported, and this input contains more
of the same kind. A pass-level fix without a corpus-level check leaves the
corpus-level failures intact.

## Why the gate belongs in the repository

Five defects were found by accident, in the order the work happened to reach
them. The gate turns that into a fixed check that runs in one command and
reports by module and index. It is the cheapest assurance this project can have
for a tool whose output is executed, and it is the concrete form of the paper's
recommendation.

## Status

**The gate finds failures; they are not all fixed.** `_sumprod` and
`_nx_ee5c35` are open, and they may share a cause with the renamer defect or be
a separate one — the next step is to reduce `_sumprod` to a minimal case, as
`hexversion` was reduced, rather than to guess.

The gate's value so far: it converted "we fixed the renamer defects" into
"the renamer defects are fixed for the inputs we checked", which is a smaller and
truer statement.
