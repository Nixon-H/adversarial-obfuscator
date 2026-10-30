# Generated Function Table Gets a Tuple Key From Constant Folding

**Date:** 2026-10-30
**Found by:** `boltons/iterutils.py` (BSD-3, 61 KB, 42 functions), the fifth
external module and the largest yet gated.
**Fixture verified valid** — `compile(source)` passes on the input.

## Symptom

```
NameError: name '_nx_f24f62' is not defined
```

at build indices 0, 2 and 4.

## What the emitted table looks like

`CallGraphObfuscator` builds a function table at module top:

```python
_nx_ftable = dict([(0, callable), (1, iter), (sum([2]), ValueError), (sum([2, 1]), ...)])
```

The third entry's **key** is `(sum([2]), ValueError)` — a **tuple** — where it
should be the integer `2`. A later entry appears to have been consumed into the
same key.

## Cause

A constant-folding pass rewrites the integer key `2` into `sum([2])` **inside a
dict-literal position**. `(sum([2]), ValueError)` then parses as a two-element
tuple rather than `key: value`, so the table gains a tuple key and loses the
entry for `2`. The lookup that follows cannot resolve.

## What is established

- The generated table is the site: the tuple key is visible in the emitted
  source.
- A plain user-written `{0: str, 1: int, 2: list}` survives the same pipeline at
  all three indices — the defect needs the generated table, not merely an
  integer key.
- It reproduces at every build index of this module.

## What is not established

**A minimal reproduction.** I tried a user-written integer-keyed dict and it
worked, which narrows the trigger to the table construction but does not isolate
it. Writing the table by hand in isolated form did not reproduce, so the trigger
involves the interaction between the table insertion and whichever pass folds
keys — and attributing it without that reduction would repeat the mistake of
round 102.

## Status

Open, located to the generated table, not reduced. The next step is to instrument
which pass emits `sum([2])` inside the dict literal — the same isolation method
that found `hexversion` and `isqrt`, rather than reading the passes.

## The count

Eight defects. This one is the first found in a module over 50 KB, and the first
where the observable is a wrong **data structure** rather than a missing binding.
