# Renaming Breaks `match` Alternative Patterns

**Date:** 2026-10-30
**Found by:** the second external module (`cpython 3.13 Lib/statistics.py`),
which uses structural pattern matching.

## Symptom

Obfuscating the module produces code that does not compile:

```
SyntaxError: alternative patterns bind different names
```

at

```python
case _nixon_ตŵぴふիぅ(_nixon_ᛠひჄफąथॢ陾) | _nixon_ตŵぴふիぅ(_nixon_ɺ轎ჟӈॾɦъԶฮ):
```

## Cause

An alternative pattern binds the same names in every alternative:

```python
case Point(x) | Point(y):
```

is only legal if both alternatives bind the same names — in practice the same
name repeated. The renamer rewrites each `MatchAs` / `MatchStar` binding
independently, so the alternatives end up binding **different** renamed names,
which CPython rejects at compile time.

## Why it had not been seen

`match` is Python 3.10+, and no fixture in this repository or in the first
external module used it. The internal corpus is written in a style that predates
it, and `more_itertools` avoids it. `cpython`'s `statistics.py` uses it for
argument dispatch.

This is the same pattern as the dataclass and renamer defects: **a language
feature absent from the local fixtures, broken by a pass that does not know
about it.**

## Severity

Any module using alternative patterns with captures fails to compile. That is a
smaller population than dataclasses — `match` is rare in library code — but it is
a **hard failure** on valid Python, and it is the fifth such defect.

## Status

Open. The fix is to rename the bindings of a `MatchOr` consistently across its
alternatives (or to skip renaming any name bound in a `match`), which is a
targeted change to the renamer's `visit_MatchOr`, a method it currently lacks.

## The count

| # | defect | feature | found by |
|---|---|---|---|
| 1 | 30-day expiry | key derivation | reading |
| 2 | false opaque predicates | transforms | behavioural gate |
| 3 | emptied dataclass | annotations | external module 1 |
| 4 | unbound import/kwarg names | renaming | external module 1 |
| 5 | **alternative-pattern binding** | **match** | **external module 2** |

Five defects, three of them from external code, and every one of them is
invisible to a test that only checks the module compiles **before** obfuscation.
