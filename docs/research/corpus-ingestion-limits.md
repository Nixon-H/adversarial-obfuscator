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
