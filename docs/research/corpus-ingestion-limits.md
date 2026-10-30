# Half the External Modules Cannot Be Gated

**Date:** 2026-10-30
**Found by:** attempting two more sources in rounds 113 and 147.

## The count

| source | gated? | reason |
|---|---|---|
| more_itertools.recipes | **yes** | no relative imports |
| cpython statistics.py | **yes** | stdlib, absolute imports |
| boltons.strutils | **yes** | absolute imports |
| more_itertools.more | **no** | `from .recipes import ...` |
| cpython requests/utils | **no** | `from .exceptions import ...` |
| attrs validators | **no** | `from ._config import ...`, and a cascade |

**Three of six.** Every module that could be gated is either a single file or a
stdlib file with absolute imports; every module that could not is a file inside a
package.

## Why a package shim is not enough

`attrs/validators.py` was retried inside a synthetic `attr` package with empty
`__init__.py` and a stub `exceptions.py`:

```
ModuleNotFoundError: No module named 'attr._config'
```

The module's relative imports reach further into the package than one level, so a
shim would have to reproduce the package's module graph — at which point the gate
is testing a reconstruction, not the code.

## What this means for the corpus

The acquisition plan's 12–15 projects is **unreachable by dropping single files in
a directory**. Real packages need one of:

1. **Vendored whole packages** — copy the package directory, gate it as a package,
   and record the version. Costs disk and a licence file per package, and is the
   honest way to import third-party code.
2. **AST-level extraction** — parse the package, take the functions whose bodies do
   not reference relative imports, and synthesise a module. Cheaper, but it edits
   the code being tested, which is exactly what round 86's acquisition plan ruled
   out.

Option 1 is correct and was not done here.

## The honest status of the corpus

The gate covers **three external sources, all single-file**, plus the stress
fixture. It has found four defects in them. It is a **real** corpus and a **narrow**
one, and the narrowness is structural rather than incidental: the sources that are
easiest to ingest are also the least like application code.

That is worth stating in the paper, because "three external modules" reads like a
sample size when it is closer to a sample **type**.

## Round 148: the limit was solvable — vendor the package

The conclusion above that "half the external modules cannot be gated" was correct
about **single-file** ingestion and wrong about the **fix**. Vendoring the package
whole works.

`more_itertools` is now vendored at `scripts/transfer/corpus/pkg/more_itertools/`
— `recipes.py`, `more.py`, and an `__init__.py` that re-exports both. Gating each
module inside that package, with the other module present unmodified:

| module | k=0 | k=2 |
|---|---|---|
| `recipes` | imports | imports |
| **`more`** | **imports** | **imports** |

`more.py` is **175 KB and 117 top-level functions**, and it previously failed with
`ImportError: attempted relative import with no known parent package`. Inside a
real package it obfuscates and imports cleanly at both build indices.

## What changed in the corpus

| | before round 148 | after |
|---|---|---|
| gated sources | 3 single-file | 3 single-file + **1 package (2 modules)** |
| largest gated module | 61 KB | **175 KB** |
| previously rejected | `more.py`, `requests/utils.py`, `attrs/validators.py` | `more.py` now **passes** |

So the corpus is no longer limited to single files. `requests/utils.py` and
`attrs/validators.py` would need their own packages vendored — a mechanical job
this round did not do — but the obstacle is now **effort**, not structure.

## The honest correction

Round 147 said the narrowness was "structural rather than incidental". That was
half right: single-file ingestion is structurally narrow, and **vendoring is the
structural fix**. One round of the fix produced the largest module this programme
has ever gated, and it passed.

The prior conclusion that AST-level extraction was the only alternative was also
unnecessary — no extraction, no editing of the code under test, just the package as
upstream ships it.

## Status

`more.py` is now the strongest single piece of evidence that the obfuscator handles
real library code: 175 KB, 117 functions, relative imports, and it survives at two
build indices. It is not yet in `artefact_gate.py`'s module list; that is a small
edit for the next round.

## Round 149: the gate cannot check package modules yet

Adding `more_itertools/{recipes,more}.py` to `artefact_gate.py`'s module list
fails:

```
FAIL pkg/more_itertools/more seed=4242 k=0: fails at import:
     attempted relative import with no known parent package
```

The gate's `check_one` writes the artefact to a temp file and imports it **as a
standalone module**. That is exactly the situation that made these files
un-gateable before they were vendored — vendoring gave the *repository* a package,
but not the *gate* an import context.

So the round 148 result ("both modules pass inside a real package") is true and was
measured by a one-off script; it is **not yet represented in the gate**.

## What the gate would need

`check_one` must accept a package layout: write the artefact as
`<tmp>/<pkg>/<module>.py`, write the package's other modules unmodified,
`<tmp>/<pkg>/__init__.py`, and then run the import in a subprocess with `<tmp>` on
`sys.path`. That is a second code path — roughly 20 lines — not a configuration
change.

Not done this round. The attempt is reverted so the gate stays honest about what it
checks rather than carrying a case that fails for a reason unrelated to the
obfuscator.

## The honest status

| claim | measured by | in the gate? |
|---|---|---|
| three single-file sources pass | `artefact_gate.py` | **yes** |
| `more_itertools` package passes | one-off script, round 148 | **no** |
| `requests`, `attrs` | not measured | no |

The corpus grew this round in evidence but not in automation, and saying so is more
useful than a gate that reports a failure it does not understand.
