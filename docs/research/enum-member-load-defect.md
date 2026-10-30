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

## Round 184: the reservation does not fix it

Implemented option 2 — in `visit_ClassDef`, reserve every `Store` name the class body
binds, so a bare-name `Load` of a class constant keeps the same spelling.

**It did not change the outcome:**

```
_make   AttributeError: type object '_nx_ffd075' has no attribute 'Hashability'
```

All 61 renamer, preserve, diversity and dataclass tests pass, so the change is
harmless — and inert.

## Why it did not work

The reservation covers `Assign` and `AnnAssign` statements directly in the class body.
`Hashability` is evidently **not** declared that way: it is a member of an `Enum`
subclass, and the reference is `SomeEnum.Hashability` or a name imported from
elsewhere. Reserved names in this renamer apply to `Name` nodes, not to `Attribute`
attributes, so a reservation cannot reach an enum member accessed by attribute at all.

So round 183's option 2 was based on a wrong reading: the site is an **attribute
access**, not a bare name. `visit_Attribute` does not rename attributes, and the
failure says the *class* lacks `Hashability` while having `hashability` — which means
the **declaration** was renamed somewhere the reservation cannot see.

## What that narrows

| possibility | status |
|---|---|
| a bare-name class constant | **refuted** — the reservation would have fixed it |
| an enum member declared via a class-body `Assign` | **refuted** — same reason |
| an enum member declared inside a **function-local class** | not tested |
| a name imported from another module and re-exported | not tested |

The change is kept because it is correct and harmless — class-constant bare-name
Loads were a real risk even if this defect is not that. But it is recorded as **not
the fix**, so the next attempt does not assume the reservation closed anything.

## Round 185: the site is a local alias, not a class attribute

Found by one grep:

```
_make.py:1494:        Hashability = ClassProps.Hashability
_make.py:1497:            hashability = Hashability.LEAVE_ALONE
_make.py:1500:                Hashability.HASHABLE_CACHED
```

`Hashability` is a **local variable inside a function**, assigned from an attribute of
another class and then used as `Hashability.LEAVE_ALONE`. So:

- the **declaration** is a `Store` in a **function** scope, which this renamer **does**
  rename;
- the **uses** are `Hashability.LEAVE_ALONE` — an `Attribute` on a local, which
  `visit_Name` renames through the `Name` node that holds the local;
- `ClassProps.Hashability` itself is an **attribute**, which `visit_Attribute` never
  renames.

## Why the error message reads as it does

```
type object '_nx_ffd075' has no attribute 'Hashability'
```

`_nx_ffd075` is the renamed local. The class it points at still has `Hashability` --
because the **attribute** in `ClassProps.Hashability` was never renamed -- but the code
now looks up `Hashability` on the **renamed local's** attribute path... and that path is
correct. The message says the object lacks the attribute, which means the local refers
to something **other** than `ClassProps`.

**That is the real defect: the local `Hashability` and the assignment source disagree.**
The assignment `Hashability = ClassProps.Hashability` renames its **target**, and the
reference `ClassProps.Hashability` renames nothing — but the local's name is also used
in a **different function's** scope, where the mapping supplies a different spelling.

## What this rules out, finally

| possibility | status |
|---|---|
| bare-name class constant | refuted (round 184) |
| enum member via class-body `Assign` | refuted (184) |
| **class-body attribute accessed by name** | **refuted here** — it is an attribute, untouched |
| **one local aliased across two function scopes** | **now the leading candidate** |

## Status

Not fixed. Four candidates reduced to one, and the one is the same "a value must have
one owner" family: a local's spelling is decided in two scopes and they disagree.

## Round 186: the class is renamed, its member is renamed, the attribute is not

The generated lines:

```python
744:  self._cache_hash = props.hashability is _nx_ffd075.Hashability.HASHABLE_CACHED
1529: _nixon_... = _nx_ffd075.Hashability
2722: return self.hashability is _nx_ffd075.Hashability.HASHABLE or ...
```

`_nx_ffd075` **is `ClassProps`**. The attribute access `_nx_ffd075.Hashability` does
**not** rename `Hashability` — `visit_Attribute` never touches attribute names, which
is correct and necessary for third-party APIs.

So the failure means the **class no longer has a member spelled `Hashability`**. The
member was renamed *in the class body* while every access to it was left alone.

**That is the guard failing in the direction opposite to rounds 182 and 183.** The
class-body Store guard is supposed to skip these assignments; something is renaming
them anyway.

## The remaining candidates, and which this selects

| candidate | status |
|---|---|
| bare-name class constant | refuted (184) |
| enum member via a direct class-body `Assign` | refuted (184) — the reservation would have caught it |
| class-body attribute accessed by name | refuted (185) |
| **member renamed by a path that bypasses the Store guard** | **selected** |

The reservation in round 184 covered `Assign` and `AnnAssign` **directly** in
`node.body`. A member declared through an **annotation-only** statement, a
**conditional** branch, a **nested class**, or an `Enum` functional API call would not
be covered — and would still be renamed by whatever path handles `Store` nodes there.

## Status

Open. The direction of the failure is now known: the **declaration** is renamed and the
**access** is not, which is the opposite of what rounds 182 and 183 assumed. The next
step is to find how `ClassProps.Hashability` is declared in the source — one grep of
`ClassProps`'s body for `Hashability` returned nothing, so it is inherited or created
outside a plain assignment.

## Round 187: a NESTED class, renamed while every access goes through an attribute

The declaration is at line 2971:

```python
class ClassProps:
    ...
    class Hashability(enum.Enum):        # nested class
        HASHABLE = ...
```

`visit_ClassDef` renamed **every** class, including nested ones. But a nested class is
reached only as an attribute of its parent — `ClassProps.Hashability.HASHABLE` — and
`visit_Attribute` never renames attribute names. So the definition became `_nx_...` and
every access still said `Hashability`.

**The failing direction is now explained**: the declaration was renamed by
`visit_ClassDef`, not by a `Store` path or an `Assign` path. Round 186's list of
candidate bypasses was directionally wrong and the real path was the class visitor
itself.

## The fix

```python
_nested = getattr(self, "_class_depth", 0) > 0
if (not _nested and node.name not in self.reserved ...):
    node.name = self.get_new_name(node.name)
```

A nested class keeps its name, because its only access path is an attribute and
attributes are not renamed. Top-level classes are unaffected.

## Result

| check | result |
|---|---|
| renamer / preserve / diversity / dataclass | **61 passed** |
| `_next_gen`, `_cmp`, `_funcs`, `_config`, `_compat` | import |
| **`_make`** | **`NameError: name 'i' is not defined`** |

**The `Hashability` defect is closed.** `_make` moves to a fifth layer: a bare loop
variable `i` undefined somewhere. A different family — ordinary local scoping, not
class attributes.

## The five layers in `_make.py`

| # | defect | fixed |
|---|---|---|
| 1 | `nonlocal hash` | 175 |
| 2 | `typing` runtime imports | 178 |
| 3 | comprehension target vs class-body Store | 182 |
| 4 | nested class renamed, attribute not | **187** |
| 5 | `i` undefined | open |

Four fixed, one open. The module has produced more defects than the other five external
sources combined, and each was invisible until the previous one stopped failing.
