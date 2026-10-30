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
