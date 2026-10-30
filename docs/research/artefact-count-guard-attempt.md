# Trying to Guard the Artefact Count, and Why It Failed


> **Historical.** The artefact counts below were measured at the time
> of writing; the gate's current figure is in `gate-count.json`.
**Date:** 2026-10-30, round 227.

Round 226 found three documents quoting 104 artefacts twenty rounds after the gate had
narrowed to 38 (measured at the time; the figures below are historical). Eighteen guards covered the defect count; nothing covered this one. This
round tried to add the guard.

## The attempt

Derive the count from `artefact_gate.py`'s own structure — the tuple of package names in
`_modules()`, plus one per `.append(...)` call, plus each package's `*.py` files — and
fail any document quoting a different number.

```
E  AssertionError: documents quote artefact counts the gate does not produce
   (actual 21): {'HANDOFF.md: 72 artefacts (measured at the time)': 72, 'README.md: 69 artefacts': 69, ...}
```

**It reported 21.** The gate produces 38 at one index.

## Why it was wrong

The derivation guessed at the gate's structure from its AST and got it wrong in three
ways: `_modules()` builds sources in several places, some appends are inside conditionals,
and the package loop adds one artefact per module at `--variants 1` but the documented 38
is the one-index figure while 72 and 76 are two-index figures. **The count depends on
`--variants`**, which no static read can see.

A guard that reads the gate's source to predict its runtime count is a second
implementation of the gate, and this one disagreed with the first.

## What would work

Run the gate — it takes four minutes — or have it write its count to a file that the
guards read. Neither is a static check, and the second is the honest one: **the count is a
measurement, not a property of the source.**

## Reverted

The test is gone. The documents keep their corrected numbers from round 226 and the
`*defect*` citation guard still passes.

## The pattern

This is the fourth guard this programme has written that had to be reverted because it
could not derive what it was checking:

| round | guard | why it failed |
|---|---|---|
| 173 | conflicting `N of M` claims | `N of M` is not one quantity |
| 227 | artefact count | the count is a runtime measurement, not a source property |
| 137, 14a | reducers | they altered the thing they measured |

**A guard is only as good as its ability to compute the truth independently of the claim.**
Where it cannot, the honest alternative is a recorded rule and a periodic audit — which is
what round 226 did.
