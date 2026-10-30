# Third External Module: `boltons.strutils` Passes All Indices

**Date:** 2026-10-30
**Source:** `boltons/strutils.py` (BSD-3), 48 KB, 34 top-level functions.
**Result:** compiles, imports and survives obfuscation at build indices 0, 2 and 4.

## Why another module

The corpus had two external sources: `more_itertools.recipes` (MIT) and
`cpython 3.13 Lib/statistics.py` (PSF). Both are utility libraries with mostly
value-returning helpers. `boltons.strutils` is a different shape — heavy string
manipulation, regular expressions compiled at module level, and functions that
call each other — so it exercises paths the first two did not.

## What it found

**Nothing.** No new defect. It compiles, imports and exercises cleanly at all
three indices, and the artefact gate now covers **69 artefacts** with zero
failures and zero invalid fixtures.

That is a useful result in itself: the fixes from rounds 99–100 for import
bindings and keyword values hold on a module the fixes were not developed
against. A gate whose corpus keeps growing and keeps returning zero is evidence
that the earlier repairs addressed a class rather than three examples.

## What it does not establish

- **That the obfuscator is correct.** Three external modules is still three.
- **Coverage of constructs.** The stress fixture covers `async`, generators,
  descriptors, `except*`, walrus and `match`; `boltons` adds regular expressions
  and closures but nothing a fourth fixture could not.
- **That the corpus is representative.** All three are utility libraries. No
  application code, no framework, no threaded program.

## The count

| source | licence | functions | gate result |
|---|---|---|---|
| more_itertools.recipes | MIT | 49 doc / 70 total | passes |
| cpython statistics.py (3.13) | PSF | 15 doc / 47 total | passes |
| boltons.strutils | BSD-3 | 34 | passes |
| stress fixture | (own) | 7 constructs | passes |

Four sources, 69 artefacts, zero failures. Six defects were found across the
first three; the fourth has produced none.
