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
