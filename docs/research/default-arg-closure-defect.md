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

## Round 189: the narrow fix is not narrow

Attempted the change round 188 described — visit the default value while still
skipping the parameter name:

```python
if node.default is not None:
    node.default = self.visit(node.default)
return node
```

Result: **8 failed, 53 passed** across the renamer, preserve and diversity tests.

**Reverted.** The recursion re-enters `visit_arg` for nested defaults and re-visits
nodes the traversal has already handled, and the renamer's mapping is not idempotent --
a second visit of an already-renamed `Name` renames it again.

## What that establishes

The fix is not "call visit on the default". It needs the default visited **exactly
once**, in the enclosing scope, with the mapping applied once — which is the same
**one owner per value** constraint that four earlier defects turned on, now applying to
traversal order rather than to rename consistency.

The precise shape would be to collect `arg.default` nodes during `visit_FunctionDef`'s
own pass, or to mark them as visited. Both are larger than the two-line change round
188 proposed, and round 188's caution was right for the wrong reason: not that the
change is risky to contract tests, but that it double-visits.

## Status

Open. One attempt, eight failures, reverted. `_make.py` remains blocked on this layer
and the other five modules are unaffected.

## The count across the programme

| kind | count |
|---|---|
| fixes that worked first try | 12 |
| fixes reverted | 4 |
| causes identified without a fix | 2 |

The reverted four are all in the rename machinery, and each was reverted because a
guard or traversal assumption was invisible from the call site being changed.
