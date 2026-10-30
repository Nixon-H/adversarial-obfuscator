# `typing` Imports Are Stripped Even When The Names Are Runtime

**Date:** 2026-10-30, round 178.
**Found by:** `attrs/_make.py` after the `nonlocal` fixes unmasked it.

## Symptom

```
NameError: name 'NamedTuple' is not defined
```

## Cause

`TypeHintStripper.visit_ImportFrom` removed **every** `from typing import ...`:

```python
if node.module == 'typing': return None
```

The reasoning is sound for annotations — `x: List[int]` can drop `List` once the
annotation is stripped. But `NamedTuple`, `Protocol`, `TypedDict`, `Literal`,
`Generic`, `TypeVar`, `runtime_checkable` and `final` are **runtime values**, used as
base classes or decorators:

```python
class _Attributes(NamedTuple):
```

Strip the import and the class body refers to nothing.

## The fix

Keep the import, filtered to the runtime names:

```python
_runtime = {'NamedTuple', 'Protocol', 'TypedDict', 'Literal',
            'Generic', 'TypeVar', 'runtime_checkable', 'final'}
kept = [a for a in node.names if (a.name or a.asname) in _runtime]
```

If nothing survives, the import is removed as before — so a module that imports only
`List`, `Dict`, `Optional` still loses them.

## What it cost and what it bought

The list is **hand-written**, which is the kind of thing that goes stale. The honest
alternative — treating every `typing` import as runtime — costs more obfuscation than
this programme needs and cannot be wrong. The list is the compromise: it covers the
names that are actually used as values in the sources gated so far.

## What it did not fix

`_make` now reports:

```
NameError: name '_nx_b06893' is not defined
```

A **renamed** name that nothing binds — a different defect in the same module,
previously masked by this one. That is the **third** time in `attrs` that fixing a
defect revealed the next one, and it is the same pattern as `_make`'s `NamedTuple`
being masked by `nonlocal`.

## Status

`typing` defect: **fixed**, five modules import, `_make` blocked on a new and
separate `NameError`. Not attempted in the remaining time; it needs the same
reduction discipline as the last three.
