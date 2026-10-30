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


## Round 94: the cause is not renaming — it is string replacement

The hypothesis in the previous section (inconsistent binding renames) is wrong.
Minimal tests of tuple patterns, class patterns and bare captures all **compile**
after renaming:

| shape | result |
|---|---|
| `case (1, x) | (2, x):` | compiles, both alternatives get the same name |
| `case P(x) | P(x):` | compiles |
| `case x:` | compiles |

Looking at the source explains it. The patterns are **string literals**:

```python
case 'normal' | 'gauss':
case 'rectangular' | 'uniform':
```

The string obfuscation pass replaces those constants with encoded lookups, so a
constant pattern becomes a **capture pattern** — and two alternatives then bind
two different names:

```python
case _nixon_A(_nixon_x) | _nixon_A(_nixon_y):
```

which CPython rejects as "alternative patterns bind different names".

## What this changes

It is not a renamer bug at all. It is a **string-pass** bug: replacing a string
constant inside a `match` pattern changes the pattern's *kind*, from matching a
value to capturing a name. The renamer was a red herring, and the previous
section's proposed fix would not have helped.

That is worth recording as a process note: I had a plausible mechanism, wrote it
down, and the minimal test refuted it in one command. The refutation cost less
than the theory.

## Severity and scope

Any `match` with a string-literal pattern breaks, and `match` on strings is the
common case. The fix belongs in the string pass, which must leave `match`
patterns alone — they are not ordinary constants.

## Status

Open, with the cause correctly identified this time. Not fixed because the string
pass is applied after the whole tree is rewritten, and the repair needs a
pattern-aware exclusion rather than a renamer method.
