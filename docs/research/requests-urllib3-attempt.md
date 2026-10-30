# Vendoring `requests` and `urllib3`: One New Defect, One Packaging Problem

**Date:** 2026-10-30, round 206.

## What was done

Both packages cloned and vendored whole:

| package | modules | licence |
|---|---|---|
| `requests` | 19 | Apache-2.0 |
| `urllib3` | 11 | MIT |

## Result

| module | outcome |
|---|---|
| `urllib3/_collections` | **`NameError: _nx_6a5df9`** — a new defect |
| `requests/utils` | `ModuleNotFoundError: urllib3` |
| `requests/models` | `ModuleNotFoundError: urllib3` |

## The two findings

**1. A tenth-class defect in `urllib3`.** `_collections.py` is pure Python with no
relative imports, and obfuscating it produces a `NameError` for a generated name. That
is the same signature as the `attrs` layers — a name preserved in one place and renamed
in another — in a package that shares no code with `attrs`. Worth reducing the same way.

**2. `requests` needs its dependencies vendored as importable packages, not just
copied.** Both packages were placed under `corpus/pkg/`, but `requests` imports
`urllib3` as an installed distribution; a sibling directory is not on `sys.path` in the
subprocess the gate uses. The gate writes one package into `<tmp>/<pkg>/`; it has no
notion of a second package in the same import root.

That is a gate limitation, not a code defect, and it is the same shape as round 149's:
the check needs a layout the code requires.

## What this establishes

- The corpus can reach **pure-Python library code with absolute imports** and will find
  defects there: `urllib3` produced one within one gating attempt.
- **Multi-package dependencies** need the gate to write several packages into one temp
  root. Three lines in `check_one`, not attempted here.
- `requests` itself is **not yet evidence of anything** — it never got past the import.

## Status

Neither package is in the gate. `urllib3/_collections` is a reproduction at module level
with no reduction; `requests` is blocked on packaging. Both recorded so the next attempt
starts from the layouts that do not work.

## Round 207: the reserved name is still renamed

`_nx_6a5df9` is `typing`. `urllib3/_collections.py` line 3 is `import typing`, and the
generated code uses `_nx_6a5df9.TYPE_CHECKING`, `.TypeVar`, `.Generic`, `.MutableMapping`,
`.cast`, `.overload` and `.Union` — seventeen references that the renamer leaves alone
because they are **attribute accesses**.

The pre-pass from round 177 was extended to reserve every `import` binding before the
visit, on the theory that ordering was the problem. It did not help:

```
urllib3/_collections  rc=1  NameError: name '_nx_6a5df9' is not defined
attrs/_make           rc=0
```

42 renamer, preserve and import tests pass, and `_make.py` still imports, so the change
is harmless — and inert for this module.

## What that establishes

`typing` is in `renamer.reserved` at the time `visit_Import` runs, and the import is
still renamed. Either:

1. `visit_Import` renames **before** consulting `reserved` — it calls
   `get_new_name`, which returns `old_name` when reserved, so this would not explain it;
2. the **`import typing` statement is removed and re-emitted** by a later pass that does
   not consult `reserved`;
3. the name is produced by a **different transformer** with its own mapping.

Round 198 ruled out (3) for `attrs` by counting `SymbolRenamer` instances; the same count
has not been run for this module.

## Status

Open. The pre-pass extension is kept (it is correct and cannot hurt), and the defect is
unchanged. One command distinguishes the three: print the emitted line 3 and whether
`typing` is in `reserved` at that moment.

## The packaging problem is unchanged too

`requests` still fails on `urllib3` not being importable, and the gate still writes one
package into one temp root. Neither is addressed.
