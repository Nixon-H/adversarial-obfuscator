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

## Round 208: the cause was the annotation stripper, not the renamer

The one command:

```
T import 'typing' reserved_at_visit=...      <- never printed
T 'import typing' in output: False
T line 3: _nx_ftable = dict([(0, _nx_bi_NotImplementedError)])
```

**`visit_Import` never saw `import typing`** — the statement was already gone by the time
the renamer ran. `TypeHintStripper.visit_Import` removed it:

```python
new_names = [n for n in node.names if n.name != 'typing']
```

That is right for `from typing import List`, where the name is an annotation the stripper
also removes. It is wrong for the **module** form: `import typing` binds the module, its
uses are attribute accesses nothing removes, and seventeen of them remained in
`_collections.py`.

## The fix

`import typing` is no longer stripped. Twenty minutes of round 207 went into the renamer
for a statement that never reached it.

## Result

| package | before | after |
|---|---|---|
| `urllib3/_collections` | `NameError: _nx_6a5df9` | **`NameError: _nixon_ǪৼĺႭᛎ`** — a new layer |
| `attr/_make` | imports | imports |
| `more_itertools/recipes` | imports | imports |

The `typing` defect is closed and the module moves to a different undefined name — this
one **unicode**, which is `get_random_var_name`'s output rather than the md5 form. A
different producer, so a different mechanism.

## What round 207 got wrong

Round 207 extended the renamer's pre-pass to reserve import bindings, which was **correct
and irrelevant**: the import was already deleted. The instrumentation would have shown
that in one command, and it did — in this round, not the last.

That is the fifth time in this programme that a fix addressed the component the last
experiment had implicated rather than the component the artefact showed.

## Status

`typing` closed. `urllib3/_collections` has a second layer, unicode-named, not reduced.
`requests` still blocked on packaging. Neither is in the gate.

## Round 209: the class-body alias, and a fix that is too broad

The unicode name is a **class-body alias**:

```python
    getheaders = _nixon_ǪৼĺႭᛎ        # source: getheaders = getlist
    getallmatchingheaders = _nixon_ǪৼĺႭᛎ
```

The **Store** (`getheaders`) is skipped by the class-body guard; the **Load** on the right
is renamed. Five such aliases in a row, all pointing at nothing.

## The attempt

Skip **every** `Load` inside a class body, on the theory that class-body names are class
attributes and the guard already protects their Stores.

```
urllib3/_collections   rc=0   <- fixed
attr/_make             rc=1   NameError: name 'Attribute' is not defined
more_itertools/recipes rc=0
```

**It broke `attrs`.** `Attribute` is a **module-level class** used inside a class body;
skipping all class-body Loads stopped it being renamed there while its definition at
module level still was.

**Reverted.** 42 renamer and preserve tests pass.

## What that establishes

The distinction is not "Store vs Load" or "class body vs module". It is **which scope
binds the name**:

| name | bound where | used where | correct |
|---|---|---|---|
| `getheaders` | class body | class body | keep |
| `getlist` | class body (a method) | class body | keep |
| `Attribute` | module level | class body | **rename** |

A single `_class_depth` counter cannot tell the last row from the first two. That needs a
per-class set of the names the class body binds — built before the class body is visited,
which is the same pre-pass shape as round 177's nonlocal fix and round 195's defaults.

## Status

`urllib3/_collections` is back to the unicode-name failure. The fix is now **stated
precisely** — a per-class binding set — rather than attempted with a counter that cannot
express it. `requests` remains blocked on packaging.

## Round 210: fixed with the per-class binding set, and why the gate still refuses it

The fix round 209 specified — reserve every name the **class body** binds, including
methods a class-body alias points at — works:

| package/module | result |
|---|---|
| `urllib3/_collections` | **imports** |
| `attr/_make` | imports |
| `attr/_next_gen` | imports |
| `more_itertools/recipes` | imports |

42 renamer, preserve, import and dataclass tests pass. `attrs` is unaffected, which round
209's blanket version was not.

## Why `urllib3` is not yet in the gate

Adding the package gives **7 failures**, none of them the obfuscator:

```
FAIL pkg/urllib3/_base_connection: ImportError: No module named 'urllib3.util'
FAIL pkg/urllib3/_request_methods:  ImportError: No module named 'urllib3.util'
```

`urllib3` has **subpackages**. The gate writes one flat directory per package and a
single `__init__.py`; `urllib3.util` is a directory it does not create. Reverted.

That is the same class as `requests` needing `urllib3` importable: **the gate's
package layout is one level deep**, and both remaining sources are deeper than that.

## What would fix both

`check_one`'s package branch would need to copy the **tree** rather than the top-level
`*.py` files — `shutil.copytree` for each package, then the artefact overwriting one
module inside it. That also solves `requests`+`urllib3` in one move, since both would be
copied into the same temp root.

About six lines. Not attempted here: the artefact is only `_collections.py`, whose fix is
verified, and a gate change that writes whole trees is worth its own measured round.

## Status

`urllib3`'s `typing` and class-body-alias defects are **closed and verified**. The package
is not gated because the gate's layout is one level deep, and that is written down as the
next change rather than worked around.

## Round 211: copying trees does not help, and the reason is a different defect

Replaced the flat `os.listdir` copy with `shutil.copytree` for every vendored package,
which fixed the `urllib3.util` subpackage problem. It did **not** give a green gate:

```
artefacts checked: 48
failures: 18
FAIL pkg/attr/_cmp: cannot import name 'cmp_using' from 'attr._cmp'
FAIL pkg/attr/_compat: cannot import name 'PY_3_11_PLUS' from 'attr._compat'
```

**The failure moved.** With trees copied, each package's real `__init__.py` runs, and it
does `from ._cmp import cmp_using`. The obfuscated `_cmp` no longer exports `cmp_using`
under that name, so the package fails to import — for a reason that has nothing to do with
`urllib3`.

**Reverted.** The gate keeps its flat layout and its 76 green artefacts.

## What this establishes

The gate's flat layout was **masking** a different defect: obfuscated modules do not
preserve the names their package `__init__` re-exports. `all_preserve` handles a module's
own `__all__`, and this is the **importer's** side of the same contract.

That is a real finding and a fifth-order one: it only appears when a package's `__init__`
imports from a module the gate has obfuscated. The synthetic fixtures and every
single-file source cannot produce it.

## Status

`urllib3`'s two defects are closed and verified by direct import. Neither `urllib3` nor
`requests` is in the gate, and the blocker is now:

1. a module's re-exported names must survive (a new defect, not yet investigated);
2. only then does the tree-copy layout pay off.

Recorded in that order so the next attempt does not re-run the tree copy and conclude the
layout was wrong.

## Round 212: the module has no `__all__`, and that is the whole story

```
_cmp.py declarations:  def cmp_using(  ...  def _make_init()  ...
_cmp.py __all__:       absent
generated 'cmp_using': False
```

`cmp_using` is a **public function with no `__all__` entry**, so the renamer treats it as
an ordinary name and renames it. `attr/__init__.py` then does
`from ._cmp import cmp_using` and fails.

## Why this cannot be fixed inside the module

`all_preserve` handles a module's **own** `__all__`. Here there is no `__all__` — the
export contract exists only in **another file**, which the renamer never sees. A per-module
transform cannot know that a name is imported elsewhere.

Three ways out, none of them local:

1. **Do not rename public module-level functions at all.** Simple, safe, and it gives up
   most of the identifier obfuscation this tool exists for.
2. **Rename and rewrite the importer too** — a whole-program pass over every module in the
   package. That is what `obfuscator/core/sources.py` would need, and it is a redesign.
3. **Require `__all__`** and refuse to obfuscate a module that exports without one.
   Honest, but it makes the tool unusable on most real packages.

The current behaviour picks none of these and quietly breaks the import.

## What this means for the corpus

`urllib3` and `requests` stay un-gated, and not because of the gate's layout. The blocker
is a **product design question** about cross-module naming, which is larger than any fix
this programme has made and needs a decision rather than an experiment.

## The honest position

Twelve defects have been found and eleven fixed, all of them inside one module's
transformation. This one is the first that **cannot** be fixed inside a module, and saying
so is more useful than a tenth attempt at the renamer.

`_cmp`'s rename is not a bug in the renamer. It is the renamer doing exactly what it was
built to do, in a situation where doing it breaks the caller.
