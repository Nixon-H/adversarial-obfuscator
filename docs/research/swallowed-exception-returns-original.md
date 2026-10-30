# `apply_ast_mutation` Returns the Original Source When Any Pass Raises

**Date:** 2026-10-30
**Found by:** tracing the eleven failing contract tests to the output, not the code.

## The finding

`apply_ast_mutation` ends with:

```python
    return code_output, secure_map
except Exception as e:
    print(f"Error during AST mutation: {e}")
    traceback.print_exc()
    return source_code, {}
```

**Any exception anywhere in the transform returns the unmodified input.** The
caller receives a tuple of the same shape as success, with no error and no flag.

## What it was hiding

A call to `_apply_final_rename` — a helper added in round 123 and **removed from
the tree** when that change was reverted — was left behind at the call site:

```
Error during AST mutation: _apply_final_rename.__init__() takes 2 positional
arguments but 3 were given
```

The revert restored the file but not the call. From round 125 to round 132, every
call to `apply_ast_mutation` raised `TypeError` internally, printed a message to
stdout, and returned the **original source**.

That is why:

- the output was ten lines with no `_nixon_` names at all;
- the renamer's mapping **did** contain `helper` (it ran, then its tree was
  discarded);
- the artefact still compiled and ran — it was the input.

## The two defects

**1. An incomplete revert.** A change was reverted in the file but its call site
was not. Eight rounds of investigation followed.

**2. A broad except that returns the input on failure.** This is the more
dangerous one. Every caller of `apply_ast_mutation` — 44 tests and however many
production call sites — cannot distinguish "obfuscation applied" from
"obfuscation failed and you got your source back". The print goes to stdout and
is invisible to a program.

For a tool whose value is that its output is transformed, **returning the input on
failure is worse than raising**: the caller pays for obfuscation and receives
none, with a success-shaped return value.

## What the fix was

One line: remove the stale call. The seven audited files went from **11 failed /
66 passed** to **77 passed**.

## What should change beyond that

The `except` should not return `(source_code, {})`. Options, in order of
preference:

1. re-raise, so the caller sees the failure;
2. return `(None, {})` or a flag, so the caller must handle it;
3. if a fallback is genuinely wanted, make it **opt-in** and **logged through the
   caller's channel**, not printed.

None applied here. The immediate defect is fixed and the suite is green; changing
the error contract touches every call site and deserves its own round with a
measurement.

## The lesson

Two reverts in this programme were made on a wrong inference — I attributed these
eleven failures to my own fix, twice, and reverted two possibly-correct changes.
The real cause was a *previous* incomplete revert, made invisible by an `except`
that turned a `TypeError` into "here is your source code back".

**A revert is not complete until its call sites are gone too**, and **a broad
except that returns the input is a silent failure generator**.
