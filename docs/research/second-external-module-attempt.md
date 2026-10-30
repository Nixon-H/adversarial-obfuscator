# Second External Module: Blocked by a Version Mismatch

**Date:** 2026-10-30
**Goal:** grow the external corpus from one module to two, for scale.
**Result:** not achieved. Recorded so the next attempt starts here.

## What was tried

`Lib/statistics.py` from CPython `main` — 47 functions, 15 documented public
ones with simple contracts (`median`, `median_low`, `mode`, `fmean`, …), which
looked like a good second source.

Three tasks were drafted with properties from the docstrings. Then the module
failed to import:

```
ImportError: cannot import name 'sinpi' from 'math'
```

`math.sinpi` does not exist on Python 3.13. The `main` branch of CPython targets
the version under development, not the one installed here.

## Why the tasks were reverted

The three tasks never passed a gate. Drafting them and then reverting is the
correct handling: a task that cannot be validated on the local interpreter is
not a contribution to the benchmark, and an unvalidated task would have to be
labelled as such in every downstream count.

## The fix, for the next attempt

Pin the **tag**, not the branch:

- `https://raw.githubusercontent.com/python/cpython/3.13/Lib/statistics.py`
  rather than `/main/`.

The same caution applies to any CPython file: `main` may use features the local
interpreter does not have, and the failure appears at import rather than at
fetch, so it is easy to draft tasks before noticing.

## What this reinforces

The acquisition plan says to pin upstream commits. This is the first concrete
demonstration of why: a branch reference silently pulls code that does not run
on the target interpreter, and the failure is invisible until the module is
executed.

That is also, incidentally, the fourth time in this programme that executing
code rather than reading it found the problem.
