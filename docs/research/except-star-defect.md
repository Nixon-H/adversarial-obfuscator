# `except*` Blocks Get a Return They Cannot Contain

**Date:** 2026-10-30
**Found by:** a stress module written specifically to test the constructs the
existing corpus does not use — async, generators, descriptors, walrus, and
`except*`. The artefact gate's own conclusion predicted this method.

## Symptom

```
SyntaxError: 'break', 'continue' and 'return' cannot appear in an except* block
```

at build indices 2 and 4, on a module containing:

```python
def grouped(values):
    try:
        if not values:
            raise ValueError("empty")
        return sum(values)
    except* ValueError:
        return 0
```

## Cause

`except*` is PEP 654 exception-group handling. Unlike `except`, its body may
**not** contain `return`, `break` or `continue`, because a handler may run while
its group is being assembled.

A pass in the obfuscator inserts a statement of that kind into the handler — the
opaque-predicate and bogus-handler passes both wrap bodies in conditionals, and
one of them emits a `return` on the resulting path.

## Why it had not been seen

`except*` is Python 3.11+, and nothing in this repository, in
`more_itertools.recipes`, or in `cpython/statistics.py` uses it. The construct is
new enough that no fixture contained it.

This is the fourth defect of exactly this shape: **a language feature absent from
the fixtures, broken by a pass that does not know about it.**

| # | feature | fixture gap |
|---|---|---|
| 3 | dataclasses with plain fields | none used |
| 4 | imports and keyword arguments | fixtures imported nothing |
| 5 | `match` patterns | none used |
| 7 | `except*` | none used |

## Status

Open, with a minimal module committed at `scripts/transfer/corpus/stress.py`.
Also in that module: `async`, generators, descriptors, `functools.wraps`,
walrus, and `match` on classes — the other constructs the existing corpus lacks.
Only `except*` failed; the rest compiled at all three indices, which is itself
worth recording.

## What this says about the method

The gate was built one round ago and its doc argued that a seventh class almost
certainly existed in code the corpus did not contain. One round later, a
five-minute stress module found it.

That is the strongest evidence in this programme for the recommendation it makes:
**the corpus is the instrument**, and expanding it finds defects faster than
reading the transforms.
