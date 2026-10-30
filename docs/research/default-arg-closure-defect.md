# A Default Argument Keeps the Old Spelling of a Renamed Loop Variable

**Date:** 2026-10-30, round 188.
**Found by:** `attrs/_make.py`, unmasked by round 187's nested-class fix.

## Symptom

```
NameError: name 'i' is not defined. Did you mean: 'id'?
```

## The site

```python
    for _nx_865c0c, _nx_2b9331 in ...(attr_names):

        def _nx_6d1f3c(self, i=i):        # <-- default argument
            return self[i]
        _nixon_...[ _nx_2b9331] = property(_nx_6d1f3c)
```

The source reads `def prop(self, i=i)` inside `for i in range(...)`. That is the
classic closure-in-a-loop idiom: each iteration captures the current `i` as a default
value so the generated property closes over the right index.

**The loop variable was renamed and the default argument was not.** So the default
`i=i` references a name that no longer exists in scope.

## Why

`SymbolRenamer.visit_arg` deliberately does not rename **parameter names** — they are
call-site contracts, and renaming them breaks keyword arguments at every call site.
That decision is correct and load-bearing.

But the **default value** of a parameter is an ordinary expression, evaluated in the
enclosing scope. It must be renamed like any other `Load`. The visitor protects the
name and appears to stop before the default.

## Why the existing tests did not catch it

The idiom only appears when a **function with a default argument is defined inside a
loop that shares the name**. The synthetic fixtures and the five other external modules
do not contain it; `attrs` uses it to generate property accessors.

That is the same shape as every other defect in this module: a construct that is
ordinary in application code and absent from the fixtures.

## Status

**Cause identified, not fixed.** The fix is narrow — visit `arg.default` while still
skipping the arg name — and it is the kind of change that rounds 123 and 124 were
reverted over, so it needs the same care: three renamer tests plus `_make.py`.

## The sixth layer

| # | defect in `_make.py` | fixed |
|---|---|---|
| 1 | `nonlocal hash` | 175 |
| 2 | `typing` runtime imports | 178 |
| 3 | comprehension target vs class-body Store | 182 |
| 4 | nested class renamed, attribute not | 187 |
| **5** | **default argument keeps old loop-var spelling** | **open** |

Five layers, four fixed, and the fifth is a different family again — ordinary
expression scoping rather than class attributes.
