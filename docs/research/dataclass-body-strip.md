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

## Round 85: the second defect is a version guard with an unbound name

The `NameError` occurs once, at module level:

```python
if _nixon_ぐ疧Ꮃゕџ >= 51183778:
    from itertools import batched as _nx_f882a6
```

- `51183778` decodes to `(3, 13)` shifted — the **build's own** Python version.
- `_nixon_ぐ疧Ꮃゕџ` is never assigned anywhere in the module.

So the pass resolved a version guard at build time, kept the comparison, and
left its left-hand operand as a renamed name with no binding. The code parses,
compiles, and fails at import.

## What kind of bug this is

A **name-resolution failure introduced by renaming**: a symbol was renamed but
its definition was dropped or never emitted. It is the same class as the
opaque-predicate defect — code that looks transformed and does not run — and it
is the third such defect in this project.

Unlike the dataclass one, the fix is not local: it requires finding which pass
emits the guard and either folding the comparison away entirely or ensuring the
name is bound. That is product debugging on a 1,000-line input and it is not done
here.

## The pattern across four defects

| # | defect | symptom | found by |
|---|---|---|---|
| 1 | 30-day expiry | stops decrypting after a month | reading the key derivation |
| 2 | false opaque predicates | functions return `None` | behavioural gate |
| 3 | dataclass body emptied | does not compile | external module |
| 4 | unbound name in version guard | fails at import | external module |

Two of four came from the external module, in two rounds, after eighty rounds of
internal fixtures produced none. The common thread is that each defect is
**invisible to a test that only checks the code runs** — and two of them produce
code that does not run at all.

## The guard this argues for

Compiling and importing every generated artefact, on a corpus of real modules,
would have caught 3 and 4 immediately and 2 the first time a function was
called. That is a smaller piece of engineering than the research apparatus
around it, and it is the thing this programme should recommend to the project
regardless of what the study concludes.

## Round 86: the cause is a rename that misses the import binding

The source is:

```python
from sys import hexversion          # line 40
...
if hexversion >= 0x30D00A2:         # line 952
```

The generated code is:

```python
from sys import hexversion          # binding NOT renamed
if _nixon_ぐ疧Ꮃゕџ >= 51183778:     # use IS renamed
```

**The renamer renames the use and not the import.** `hexversion` is bound, the
comparison references a different, unbound name, and the module fails at import.

`51183778` decodes to `(3, 13)` — the build's own version, so the constant is
the build-time value of the comparison, consistent with the right-hand side
being resolved while the left-hand name was rewritten incorrectly.

## Why this is precise and reportable

It is not a mystery: one pass renames a name at its use site and another leaves
the `ImportFrom` alias alone. The fix is to rename the binding too, or to skip
renaming names bound by imports. Both are local to the renamer.

It is also the clearest instance of the failure class this whole programme has
been circling: **transformed code that is syntactically valid, compiles, and
does not run.** A compile check would not catch it; an import check would.

## What this changes about the recommendation

The earlier recommendation was "compile every generated artefact". This defect
shows that is not enough — the code compiles. The recommendation has to be:

> **Compile and import every generated artefact, over a corpus of real modules.**

Importing executes module-level code, which is where this fails and where two of
the four defects would have been caught. It is still far cheaper than the
research apparatus, and it is the single most useful thing this programme can
hand back to the project.

## Status

Open, with the mechanism identified and a one-line description of the fix.
Not fixed here because the renamer's import handling was not traced in the
remaining time, and a speculative edit to a transform is how the first three
defects were made.

## Round 87: the obvious fix did not work, and that is informative

The proposed fix was to add `visit_ImportFrom` to `SymbolRenamer`, renaming each
alias's binding to match its renamed uses. Implemented, run against the external
module, and **still failing**:

```
k=2 FAILED NameError: name '_nixon_ΗᎮ๔ӼӓĦկᚯぷᎥ' is not defined
k=4 FAILED NameError: name '_nixon_ぐ疧Ꮃゕџ' is not defined
```

Reverted. A transform edit that does not fix the defect is not a fix, and this
programme has already shipped three of those.

## What the failed attempt establishes

**`SymbolRenamer` is not the pass that renames this use.** Adding the import
visitor there changed nothing, so either:

- the rename is applied by a different transformer, and `SymbolRenamer` sees an
  already-renamed tree where the import alias still matches the *original* name;
  or
- the import is removed and re-emitted by another pass, so the binding this
  visitor touches is not the one that survives.

Both hypotheses are testable — count the `ImportFrom` nodes before and after each
pass — and neither was tested in the remaining time.

## Why this is recorded rather than retried

The correct next step is instrumentation, not another edit: log which pass emits
the `if` and which emits the import. That is the same lesson as the
`llvmgen` defect at the start of this work, where four rounds were spent
guessing before one round of dumping the intermediate artefact found the cause.

## Status

Open. Mechanism identified to the line (`from sys import hexversion` unrenamed,
use renamed), pass not identified. The reverted tree is green; the defect remains
and is documented with its reproduction.

## Round 88: the instrument found the cause, and my first attempt at a fix was misplaced

Instrumenting instead of guessing paid off twice in one round.

**1. `SymbolRenamer` is the culprit, confirmed by isolation.** Running it alone
on a minimal source reproduces the defect exactly:

```python
# input
from sys import hexversion
def f():
    if hexversion >= 0x30D00A2: ...
```

```python
# after SymbolRenamer alone
from sys import hexversion
def f():
    if _nixon_सȴƅǮϦ >= 51183778: ...
```

So the pass, the line, and the mechanism are all confirmed: the import binding
is left alone while the use is renamed.

**2. My patch went into the wrong class.** The fix was inserted before the
*first* `def visit_Name` in the file, which belongs to `TypeHintStripper`, not
to `SymbolRenamer`. The renamer's own `visit_Name` is at a different line. So
the fix was never applied to the pass it targeted, which is why the module still
failed and why the minimal repro still failed after "applying" it.

That is a self-inflicted repeat of the same error class: a global text match
applied to a file with several classes defining the same method name.

**Status.** Mechanism confirmed; fix not landed. The correct edit is three lines
inserted immediately before `SymbolRenamer.visit_Name`, and it must be verified
against the minimal repro before the external module.

## The method note this adds

Two rounds, two failures, both from editing without a minimal test. The thing
that worked was isolation: run one pass on a ten-line source. That is the same
technique that settled the `llvmgen` defect and the same one I keep reaching for
too late.

## Round 89: the renamer's import visitor, fixed for the aliased case only

**The bug was one `if`.** The existing `visit_ImportFrom` read:

```python
for alias in node.names:
    if alias.asname:                      # only aliased imports
        alias.asname = self.get_new_name(alias.asname)
```

An unaliased `from sys import hexversion` therefore kept its original binding
while every use of `hexversion` was renamed.

**Fixed** by renaming the unaliased case too, via an explicit `asname`, and
skipping `*` and reserved names. **Verified minimally**: a ten-line source that
failed with `NameError` now runs and returns the right value.

## Not fully fixed

On the external module, `hexversion` is now resolved and a **different** name
fails:

```
NameError: name 'isqrt' is not defined
```

The emitted import is `from math import prod as ..., comb as ..., isqrt as
_nx_cda3e5, ...` — so the binding **was** renamed — but one use survives as bare
`isqrt` inside `stop=isqrt(n)`. So a second inconsistency exists: `visit_Name`
skips that use through an early return (protected-function or local-parameter
handling), while the import was renamed anyway.

So the fix moves the defect rather than removing it, on this module. It is kept
because it is a strict improvement — one class of unbound name is gone — and
because the residual is a *second* bug with its own cause, not a regression.

## Status

| name | binding renamed | uses renamed | result |
|---|---|---|---|
| `hexversion` | yes (after fix) | yes | **resolved** |
| `isqrt` | yes | **no, one use** | **open** |

The next step is the same technique that found this one: isolate
`SymbolRenamer` on a call with a keyword argument whose value is an imported
name, and see which branch of `visit_Name` returns early.
