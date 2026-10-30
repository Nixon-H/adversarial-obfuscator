# An Enum Member's Bare-Name Load Is Renamed, Its Store Is Not

**Date:** 2026-10-30, round 183.
**Found by:** `attrs/_make.py`, unmasked by round 182's comprehension fix.

## Symptom

```
AttributeError: type object '_nx_ffd075' has no attribute 'Hashability'.
Did you mean: 'hashability'?
```

## What the message says

The class has an attribute **`hashability`** (lowercase). The code asks for
**`Hashability`**. One was renamed and the other was not.

## The mechanism, and why it is the inverse of round 182

`SymbolRenamer.visit_Name` refuses to rename a `Store` inside a class body:

```python
if Store and _class_depth > 0 and _func_depth == 0 and _comp_depth == 0:
    return node
```

So an enum member declared as `Hashability = ...` in a class body keeps its name.
**Correct.** But a bare-name **reference** to that member — `Hashability.SOMETHING`
or `Hashability` used as a value — is a **`Load`**, and Loads are not guarded, so the
reference is renamed.

That is the same desync as round 182 with the legs swapped: there the **Store** was
skipped and the **Load** renamed inside a comprehension; here the **Store** is skipped
and the **Load** renamed at class scope.

## Why the guard cannot fix it as written

The guard's justification is that class attributes are read via **`self.kind`**, and
`visit_Attribute` never renames an attribute name — so skipping the Store keeps the
pair in step. That reasoning holds for **instance** attributes.

It does **not** hold for a class-level name read as a **bare `Name`** rather than
through an attribute. `Hashability` is exactly that: an enum member referenced by name.
The guard covers one access pattern and not the other.

## The fix this implies

Either:

- record every class-body `Store` name and skip its bare-name `Loads` too — a
  per-class scope set, which is the same "know the declarations before renaming"
  shape as round 177's pre-pass; or
- stop renaming class-body `Store`s **and** treat their names as reserved globally,
  accepting that enum and class constants keep their spelling.

The second is smaller and loses little: class constants are already reachable by
name, so obfuscating their spelling has limited value.

## Status

Cause identified, not fixed. Fifth layer in `_make.py`, fourth distinct class of
defect in it, and the third instance in this programme of **"a value must have one
owner"** appearing at a new site.
