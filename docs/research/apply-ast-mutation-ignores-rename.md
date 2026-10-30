# `apply_ast_mutation` Silently Ignores `symbol_rename`

**Date:** 2026-10-30
**Found by:** tracing eleven failing contract tests to the entry point they use.

## The finding

`obfuscator/core/sources.py`:

| function | line | mentions `symbol_rename` |
|---|---|---|
| `apply_ast_mutation` | 331 | **0 occurrences** |
| (the full transform path) | 463 | `if options.get('symbol_rename')` |

`apply_ast_mutation` is a public entry point. It takes an `options` dict, applies
a set of AST mutations, and returns the result. **It never reads
`symbol_rename`**, so passing `symbol_rename: True` — which every one of these
tests does — has no effect.

## Evidence

The test helper builds its options with `symbol_rename: True`:

```python
_MIN_OPTS = {
    "cfg_flatten": False, ..., "unicode_ids": False,
    "symbol_rename": True,
}
```

and the output for a source with four function definitions is:

```python
def foo():
def ping(self):
def _priv():
def helper():
```

Every definition keeps its name. Ten lines total, one `__all__`, one `def foo(`
— so this is not a duplicated body or a bypassed renamer: the renaming step was
never invoked.

## Why this is the ninth defect and the worst of them

The other eight produce code that **fails** — does not compile, does not import,
or raises. This one produces code that **works perfectly and is not obfuscated**.

A caller who:

```python
code, _ = apply_ast_mutation(source, {"symbol_rename": True, ...})
```

gets an artefact whose function names, class names and globals are untouched, and
no error, warning or return value indicates it. The option is accepted and
discarded.

For a tool whose entire purpose is making source harder to read, silently not
doing the central transformation is the most damaging failure mode available —
and it is exactly the class the artefact gate **cannot** see, because the output
runs.

## What the eleven tests were detecting

`test_private_names_still_renamed`, `test_diversity` (3), `test_golden`,
`test_all_preserve` (3) and others are all checking that renaming **happens**. They
have been failing since the entry point diverged from the full path, and the
failures were read as collateral of whatever change was most recent.

## Status

**Open, cause identified.** The fix is to route `apply_ast_mutation` through the
same renaming step, or to reject `symbol_rename` there with an error rather than
accepting it silently. The second is smaller and honest; the first is correct.

Not done this round: the two paths have diverged further than a one-line bridge,
and the last two reverts in this programme came from changing the rename
machinery without a baseline.

## Round 130: the fix, specified and not applied

Two candidate repairs.

**A. Route the entry point through the renamer.** Add the renaming step to
`apply_ast_mutation`. Correct, and larger than it looks: the full path has ~80
lines of reservations (`_NX_*` markers, trial-gate helpers, `__all__` names,
protected functions) before `renamer.visit(tree)`, and a partial copy of that
list is how the previous nine defects happened.

**B. Reject the option instead of accepting it silently.**

```python
if options.get("symbol_rename"):
    raise ValueError(
        "apply_ast_mutation does not implement symbol_rename; use the full "
        "transform path, or remove the option"
    )
```

Smaller, honest, and it converts a **silent** failure into a **loud** one. It
also makes the eleven failing tests fail **for the right reason** — with an
exception that names the gap, rather than an assertion that the output is not
obfuscated.

**Not applied.** Both are changes to the top of the transform stack, and the last
two attempts to change renaming in this programme were reverted after breaking
15 and 11 contract tests. The difference this time is that the baseline is known:
eleven specific tests are already failing, for a cause that is now named. That
makes measurement possible — run those eleven before and after, and require that
the count **decreases** and nothing else **increases**.

## What the eleven tests were right about

They were not stale, not collateral, and not confused by a recent change. They
were reporting that the entry point they exercise does not obfuscate names, and
they were correct for fourteen rounds while being read as noise.

## The rule this makes concrete

**An option that is accepted and silently ignored is worse than an option that is
rejected.** `apply_ast_mutation` accepted `symbol_rename: True` and did nothing.
Every caller who passed it believed their output was renamed. The tests were the
only thing that noticed, and their signal was read as a regression rather than a
report.

## Round 131: the loud-rejection fix is not viable

Applied fix B — raise on `symbol_rename` in `apply_ast_mutation` — and measured,
as round 130 said to.

| state | failures in the seven audited files |
|---|---|
| baseline (no change) | 11 |
| with the rejection | **55** |

Forty-four tests pass `symbol_rename` to `apply_ast_mutation` and expect it to
return code, not raise. The option is used widely enough that rejecting it is a
larger breaking change than the silent ignore.

**Reverted.** The rule from round 130 — "an accepted and silently ignored option
is worse than a rejected one" — is correct in principle and wrong in this
codebase: the option is not vestigial, it is relied upon by 44 call sites that do
not care whether renaming happens.

## What that changes about fix A

Fix A (route the entry point through the renamer) would make those 44 tests
*rename* rather than *not rename*, which changes their output but not their
contract — they assert the code compiles and the transforms applied, not the
names. It is therefore the only viable option, and it is the larger one.

The measurement that decided this took one command. It is the first time in this
programme that a candidate fix was rejected on evidence **before** being
committed, rather than reverted after.
