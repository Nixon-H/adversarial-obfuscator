# Two Invented Names in a Return Tuple

**Date:** 2026-10-30, round 196.
**Found by:** `attrs/_make.py`, unmasked by round 195's default-argument fix.

## Symptom

```
NameError: name '_nx_ec3de3' is not defined
  at line 1069:  return (_nx_ec3de3, _nx_e8fc6a)
```

## What is established

Both names appear **exactly once** in the entire emitted module — on line 1069, in the
`return`. Nothing binds either of them. They are **invented**.

That is the same signature as round 122's defect, where `_nx_f24f62` appeared once in a
function table and nowhere else: `get_new_name` was called for a name, produced a
spelling, and the corresponding binding was never emitted or never patched.

## What the source probably says

Nine lines above, the function builds `state` from `self.__slots__` and writes hashes
through `__bound_setattr`. The source's final statement is most likely
`return (state, hashes)` — two **locals**, which the renamer would not rename if they
are parameters, or would rename **consistently** if they are assignments.

Inventing both suggests the `return` was rewritten against a mapping that contained
entries for two names whose **definitions** were in a scope the traversal never reached.

## What is not established

**Which two source names.** The mapping is not printed, and the emitted file has no
other occurrence to compare against. One command would settle it — print
`renamer.mapping` for the function containing line 1069 — which is the technique that
solved round 195 after five rounds of not doing it.

## Status

Open, with the signature identified: **invented names, each appearing once**. That is
the third instance in this programme of the round-122 pattern, and the lesson attached
to it is the same — *a name that appears exactly once in the output is a rename that
lost its target*.

## The six layers in `_make.py`

| # | defect | fixed |
|---|---|---|
| 1 | `nonlocal hash` | 175 |
| 2 | `typing` runtime imports | 178 |
| 3 | comprehension vs class-body Store | 182 |
| 4 | nested class renamed, attribute not | 187 |
| 5 | default argument kept old loop-var spelling | **195** |
| 6 | two invented names in a return tuple | open |

Five fixed, one open. Layer 6 has the **cleanest signature yet** — two names, one line,
zero bindings — which makes it the most tractable of the six.

## Round 197: neither invented name is in the renamer's mapping

The one command round 196 named:

```
_nx_ec3de3 <- NOT IN reverse_mapping
_nx_e8fc6a <- NOT IN reverse_mapping
reverse_mapping size: 176
```

**Both invented names are absent from the renamer's own reverse mapping.** The renamer
produced 176 names in this run and neither of these is among them.

## What that means

They did not come from `get_new_name`. The `_nx_` prefix and six hex digits match the
**md5 branch** of `get_new_name` exactly:

```python
self.mapping[old_name] = "_nx_" + md5(old_name.encode()).hexdigest()[:...]
```

but that branch records into `reverse_mapping`, and these are not there. So one of:

1. a **second** `SymbolRenamer` instance ran and its mapping is the one that produced
   them — `apply_ast_mutation` constructs a renamer, and some paths construct another;
2. the names came from a **different transformer** that also emits `_nx_<hex>` — the
   internal-rename path, which uses its own mapping;
3. `reverse_mapping` was **cleared or replaced** after they were produced.

## Why this is the important question now

If a second renamer runs, then the first one's reservations — imports, `__all__`,
nonlocal targets, nested classes, all of them — **do not apply to the second**, and
every fix in rounds 175–195 is only guaranteed for one of the two passes.

That would explain why each layer of `_make.py` needed its own fix: the module is large
enough to exercise a path that constructs a second renamer.

## Status

Open. The invented names are **not** from the mapping I have been inspecting, which
means the renamer I instrumented is not the only one transforming this file. The
next command prints how many `SymbolRenamer` instances are constructed during a single
generation.

## Round 198: the names are real, and my round-197 check was inverted

`reverse_mapping` is keyed by the **old** name, so looking up a *new* name in it always
returns nothing. Round 197's conclusion — "a second transformer is implicated" — was an
artefact of reading a dict the wrong way round.

Inverting the mapping correctly:

```
_nx_ec3de3 <- slots_getstate
_nx_e8fc6a <- slots_setstate
mapping size: 176
```

**They are ordinary renamer output.** One instance, one mapping, no second transformer.

## The actual defect

```
'slots_getstate' in source:  True
'slots_getstate' in output:  True     <- the DEFINITION kept its name
'_nx_ec3de3' as def:         False
count of _nx_ec3de3:         1        <- kept by the REFERENCE in the return
```

The **definition** was not renamed; the **reference** was. That is the same desync as
rounds 182 and 187 — a `Store` preserved and a `Load` renamed — at a new site: a
module-level function definition whose name also appears in a sibling's `return`.

## Why the definition was not renamed

`visit_FunctionDef` renames when the name is not reserved, does not start with `__` or
`_`, and is not in `protected_functions`. `slots_getstate` satisfies all three, so
something else is preserving it — most likely `protected_functions`, which is populated
from `sources.py` and which round 128 measured as **empty** for a different module.

Not tested. The command is the same one that has worked six times: print
`protected_functions` and `current_function` at the moment `visit_FunctionDef` sees
`slots_getstate`.

## Status

Open, with the signature corrected: not invented names, but **a definition left alone
while its reference was renamed**. Third instance of that desync, and the first where
the `Store` is a `def` rather than a class-body assignment or a comprehension target.
