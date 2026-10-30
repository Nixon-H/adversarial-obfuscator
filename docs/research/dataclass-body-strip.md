# A Dataclass With Plain Fields Is Emptied by the Obfuscator

**Date:** 2026-10-30
**Found by:** the external corpus attempt (round 83) — the first time this
project was run over code it did not write.

## Minimal reproduction

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Stats:
    count: int
    total: float

def use(s):
    return s.count
```

Obfuscated at build index 4, the class becomes:

```python
class _nixon_ৱϐŝՎぐ:

def _nixon_็ןɟʋȡ(s):
```

`IndentationError: expected an indented block after class definition`.

## Cause

A dataclass whose fields are **bare annotations** has a body consisting only of
`AnnAssign` statements. The annotation-stripping pass removes them, and the
class is left with no statements. Nothing then inserts a `pass`, so the output
is not valid Python.

## Severity

**Any dataclass with plain fields breaks.** That is not an edge case; it is the
ordinary way dataclasses are written. The build succeeded, produced a file, and
the file did not compile — so a pipeline that does not compile-check its own
output would ship it.

## Why it took an external module to find

Every fixture in this repository's corpus was written by the same author, and
none used a bare-annotation dataclass. The hand-written tasks use plain
functions; the in-repo corpus modules use dicts and tuples. The pattern is
common in the wider Python ecosystem and absent from the local sample, which is
precisely the argument for an external corpus that the earlier rounds could not
satisfy.

## Status

Open product defect, with a minimal reproduction. The fix is either to keep an
`AnnAssign` when it is the class's only body, or to emit `pass` when a class body
becomes empty. A guard should assert that every generated artefact compiles,
which is cheaper than any of the analysis this programme has been doing.

## What this says about the corpus gap

The gap was not only about statistics. Two rounds ago the corpus was a matter of
sample size; this round it produced a class of defect that internal fixtures
structurally could not. The honest conclusion is that the corpus gap was also a
**coverage** gap, and coverage was the more urgent of the two.

## Round 84: fixed, and the same module found a second defect

**The dataclass defect is fixed.** Two changes:

1. `TypeHintStripper.visit_ClassDef` now leaves a class alone when its body is
   entirely `AnnAssign` statements, because in a dataclass those annotations
   *are* the fields. It also inserts `pass` if a body empties for other reasons.
2. `MetadataStripper` now inserts `pass` when removing a leading docstring
   leaves a class or function with no statements.

Verified: the minimal repro compiles at build indices 0, 2 and 4, and the
dataclass keeps `count` and `total` in `__dataclass_fields__`. Seven guards in
`tests/test_dataclass_body_preserved.py` assert compilation **and** field
preservation — compiling is not enough, since a fieldless dataclass constructs
wrongly.

## The second defect, still open

Running the external module further produced:

```
NameError: name '_nixon_ぐ疧Ꮃゕџ' is not defined
```

An emitted reference to a renamed name that no longer exists. This is a
different failure from the empty body — the code parses and compiles, and fails
at import.

**Status: open, not reproduced minimally.** It appeared on
`more_itertools.recipes` (1,000+ lines, 70 functions) at build index 4 and has
not been reduced. Recording it rather than chasing it in the remaining time,
because a name-resolution failure on a large module is exactly the class of
defect the local fixtures cannot surface.

## What the external corpus has now produced

| round | defect | status |
|---|---|---|
| 83 | dataclass with plain fields emptied | **fixed, guarded** |
| 84 | undefined name after renaming | **open** |

Two defects in two rounds, on one module, from code this project did not write.
The internal corpus produced none in eighty rounds. That ratio is the argument
for the corpus, and it is stronger than any of the statistics this programme was
built to gather.
