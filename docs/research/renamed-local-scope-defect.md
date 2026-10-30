# A Renamed Local Is Undefined in One Comprehension

**Date:** 2026-10-30, round 179.
**Found by:** `attrs/_make.py`, unmasked by round 178's `typing` fix.

## Symptom

```
NameError: name '_nx_b06893' is not defined
```

## What is established

The name appears **39 times** in the emitted module — it is the renamed form of a
heavily reused local (an attribute-name loop variable). Thirty-eight of those
occurrences are inside comprehensions or `for` loops that bind it:

```python
X = {_nx_b06893 for _nx_b06893, _nx_815be9 in Z.items() ...}     # line 496
Y = sorted(((_nx_b06893, _nx_815be9) for _nx_b06893, _nx_815be9 in Z.items()))  # 511
for _nx_b06893, _nx_2063c1 in self._cls_dict.items(): ...        # 870
```

Those are self-contained: the comprehension binds the name it uses.

## What is not established

**Which reference is unbound, and why.** The traceback names the name, not the line,
and the `NameError` is raised at import so it could be any of the 39. The candidates:

1. a comprehension **body** reading a variable bound by its own `for` — legal, and
   the shapes at 496 and 511 look legal;
2. a name used **after** its comprehension, where Python 3's comprehension scoping
   means it does not leak (this would be a defect in the **source**, not the
   transform);
3. a rename that made two distinct locals **collide**, so a body reads a name that
   a *different* scope binds;
4. a rename that split one local into two spellings across function boundaries.

## Why this was not reduced

Reducing `_make.py` would take the same structure-preserving reducer used in rounds
175–177, and the reducer has a known limitation for this shape: the defect surfaces
as a `NameError` at **import**, so trimming statements changes which code runs and
which reference is reached first. The eighth defect took four reductions for the same
reason.

## Status

Open, with a package-level reproduction, a count of the occurrences and four
candidate mechanisms — none tested. Not guessed at, because the last three defects
in this module each took a reduction to settle and one of them (`nonlocal`) was
reported with a wrong cause first.

## The sequence in `_make.py`

| round | defect | how it surfaced |
|---|---|---|
| 174 | `nonlocal hash` | compile error |
| 178 | `typing` runtime imports | import error |
| **179** | **renamed local unbound** | **import error** |

Three defects in three rounds from one 4900-line module, each revealed by fixing the
last. The module is the most productive artefact in the corpus and the only one that
has produced more than two.

## Round 180: the line, and the shape that explains it

The traceback names it:

```
File ".../attr/_make.py", line 2534, in <module>
File ".../attr/_make.py", line 2536, in _CountingAttr
File ".../attr/_make.py", line 2536, in <genexpr>
NameError: name '_nx_b06893' is not defined
```

Line 2536 is inside `class _CountingAttr`, immediately after `__slots__`:

```python
class _CountingAttr:
    __slots__ = ('_converter', ..., 'eq_key', ...)
    __attrs_attrs__ = (*tuple((_nx_f2bbdf(name=_nx_b06893, alias=_default_init_alias_for(_nx_b06893), ...
```

The source has the same shape at line 2758, with `Attribute(...)` in place of the
renamed `_nx_f2bbdf` and `name` in place of `_nx_b06893`.

## What this rules out

The name **is** bound by that comprehension's own `for name in (...)` — so mechanism 1
from round 179 (a body reading a name nothing binds) is **not** it. The binding exists
on the same line.

## What it suggests

A **class-body generator expression** cannot see names bound elsewhere in the class
scope. It can see its own `for` target, so the shape above is legal — *as long as the
`for` target and the body use the same spelling*. They do.

Which leaves the two mechanisms that a line-level view cannot distinguish:

- the `for` clause and the body were given **different** spellings by the rename
  (visible only by reading the full 400-character line, not the printed prefix);
- the `for` iterable refers to a **class-level** name, and moving that reference
  inside a generator broke the lookup.

Both are one grep of the full line away, and neither is a guess I am willing to write
down as a cause without it.

## Status

Open. Line located, one mechanism ruled out, two remain, next step is to read line
2536 in full and compare the `for` target with the body's spelling.

## Round 181: the for-target and the body disagree

Reading line 2536 in full (602 characters):

```
for-target: name
count of _nx_b06893 on the line: 2
```

**The comprehension binds `name` and uses `_nx_b06893`.** One of them was renamed and
the other was not.

## Why

`SymbolRenamer.visit_Name` has a guard added for a real problem:

```python
if isinstance(node.ctx, (ast.Store, ast.Del)) and getattr(self, '_class_depth', 0) > 0:
    return node          # never rename a Store inside a class body
```

The reason is documented and sound: a class-body `kind = "box"` is read back via
`self.kind`, which never renames, so renaming the Store alone would desync them.

**A comprehension target is a `Store` inside a class body** — but it is not a class
attribute. It is a loop variable local to the comprehension, and its uses are inside
the same comprehension. The guard cannot tell the two apart, so the target keeps its
name while the body's `Load` is renamed (Loads are not guarded).

That is exactly the desync the guard exists to prevent, produced by the guard itself
for a node type it was not written for.

## The fix this implies

The class-body guard must exclude **comprehension scopes**: a `Store` inside a
`GeneratorExp`, `ListComp`, `SetComp` or `DictComp` is not a class attribute, because
Python gives those constructs their own scope. Tracking that needs a
comprehension-depth counter alongside `_class_depth`.

Not applied this round. It touches the same `visit_Name` that rounds 123 and 124 were
reverted over, and the last four rounds in this module have each shown how a
plausible guard change breaks a different contract. The change is small, testable
against the three `_make`-independent renamer tests plus `_make.py` itself, and it
belongs in a round with the time to run both.

## Status

**Cause identified.** Not "a renamed local is undefined" but "a class-body guard
renames Loads and not Stores for comprehension targets". The wording change matters:
the first is a symptom, the second names the line to change.
