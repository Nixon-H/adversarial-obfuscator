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
