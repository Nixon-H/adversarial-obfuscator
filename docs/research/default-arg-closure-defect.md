# A Default Argument Keeps the Old Spelling of a Renamed Loop Variable

**Date:** 2026-10-30, round 188.
**Found by:** `attrs/_make.py`, unmasked by round 187's nested-class fix.

## Symptom

```
NameError: name 'i' is not defined. Did you mean: 'id'?
```

## The site

```python
    for _nx_865c0c, _nx_2b9331 in ...(attr_names):

        def _nx_6d1f3c(self, i=i):        # <-- default argument
            return self[i]
        _nixon_...[ _nx_2b9331] = property(_nx_6d1f3c)
```

The source reads `def prop(self, i=i)` inside `for i in range(...)`. That is the
classic closure-in-a-loop idiom: each iteration captures the current `i` as a default
value so the generated property closes over the right index.

**The loop variable was renamed and the default argument was not.** So the default
`i=i` references a name that no longer exists in scope.

## Why

`SymbolRenamer.visit_arg` deliberately does not rename **parameter names** — they are
call-site contracts, and renaming them breaks keyword arguments at every call site.
That decision is correct and load-bearing.

But the **default value** of a parameter is an ordinary expression, evaluated in the
enclosing scope. It must be renamed like any other `Load`. The visitor protects the
name and appears to stop before the default.

## Why the existing tests did not catch it

The idiom only appears when a **function with a default argument is defined inside a
loop that shares the name**. The synthetic fixtures and the five other external modules
do not contain it; `attrs` uses it to generate property accessors.

That is the same shape as every other defect in this module: a construct that is
ordinary in application code and absent from the fixtures.

## Status

**Cause identified, not fixed.** The fix is narrow — visit `arg.default` while still
skipping the arg name — and it is the kind of change that rounds 123 and 124 were
reverted over, so it needs the same care: three renamer tests plus `_make.py`.

## The sixth layer

| # | defect in `_make.py` | fixed |
|---|---|---|
| 1 | `nonlocal hash` | 175 |
| 2 | `typing` runtime imports | 178 |
| 3 | comprehension target vs class-body Store | 182 |
| 4 | nested class renamed, attribute not | 187 |
| **5** | **default argument keeps old loop-var spelling** | **open** |

Five layers, four fixed, and the fifth is a different family again — ordinary
expression scoping rather than class attributes.

## Round 189: the narrow fix is not narrow

Attempted the change round 188 described — visit the default value while still
skipping the parameter name:

```python
if node.default is not None:
    node.default = self.visit(node.default)
return node
```

Result: **8 failed, 53 passed** across the renamer, preserve and diversity tests.

**Reverted.** The recursion re-enters `visit_arg` for nested defaults and re-visits
nodes the traversal has already handled, and the renamer's mapping is not idempotent --
a second visit of an already-renamed `Name` renames it again.

## What that establishes

The fix is not "call visit on the default". It needs the default visited **exactly
once**, in the enclosing scope, with the mapping applied once — which is the same
**one owner per value** constraint that four earlier defects turned on, now applying to
traversal order rather than to rename consistency.

The precise shape would be to collect `arg.default` nodes during `visit_FunctionDef`'s
own pass, or to mark them as visited. Both are larger than the two-line change round
188 proposed, and round 188's caution was right for the wrong reason: not that the
change is risky to contract tests, but that it double-visits.

## Status

Open. One attempt, eight failures, reverted. `_make.py` remains blocked on this layer
and the other five modules are unaffected.

## The count across the programme

| kind | count |
|---|---|
| fixes that worked first try | 12 |
| fixes reverted | 4 |
| causes identified without a fix | 2 |

The reverted four are all in the rename machinery, and each was reverted because a
guard or traversal assumption was invisible from the call site being changed.

## Round 190: the idempotence fix, attempted with a blanket replace, reverted

Round 189 established that the mapping is not idempotent, and that this is why the
default-argument fix double-renamed. The targeted repair is in `get_new_name`:

```python
if old_name in self.reverse_mapping or old_name in self._renamed_values:
    return old_name
```

plus recording every produced name. That part is sound.

**The edit was applied with a text replace over two `self.mapping[old_name] = `
sites.** One of them is indented differently from the other, so the inserted line
produced an `IndentationError` and two collection errors.

**Reverted.** The tree parses and 28 renamer and preserve tests pass.

## Why this is worth recording rather than retrying

The change is three lines in three places. Applying it with a blanket string replace
is the same mistake as round 88's misplaced `visit_ImportFrom`, round 132's short
grep, and round 189's non-idempotent recursion: **a text-level edit to a file with
several similar sites.** Each of those cost a round, and the fix each time was to
edit by line number or by unique context.

A correct version edits `get_new_name` by its own body, and adds the recording at each
`mapping[...] =` site individually — two edits, each verified.

## Status

Unchanged from round 189: the cause is known, the repair is three lines, and `_make.py`
stays blocked on this layer. Six modules import; one does not.

## The pattern in the last six rounds

| round | what happened |
|---|---|
| 185 | one grep located the site |
| 186 | direction determined |
| 187 | nested-class fix **worked** |
| 188 | next layer's cause identified |
| 189 | narrow fix double-visits, reverted |
| 190 | idempotence fix misapplied, reverted |

Two reverts in two rounds, both from **applying a correct idea through a risky
mechanism** — recursion in 189, a text replace in 190. Neither was wrong about the
cause.

## Round 191: idempotence added, and it was not the missing piece

Applied the idempotence guard correctly this time — by line index, with each site's own
indentation, and a `_renamed_values` set recording every produced name:

```python
if old_name in self._renamed_values:
    return old_name
```

61 renamer, preserve, diversity and dataclass tests pass. **The guard is kept**; it is
correct and it removes a class of double-rename that round 189 exposed.

Then the default-argument fix was retried on top of it:

```
8 failed, 46 passed
```

**The same eight tests.** Idempotence was not the missing piece. The recursion into
`node.default` is wrong for a different reason, still unidentified.

## What the pairing rules out

| hypothesis | status |
|---|---|
| the mapping is not idempotent | **fixed, and the failure persists** |
| therefore idempotence caused round 189's failures | **refuted** |

Round 189's eight failures were **not** double-renaming. Something else about visiting
`arg.default` from inside `visit_arg` breaks `test_plain_import_is_reserved` and seven
others.

## The default-arg change is reverted; the idempotence guard is kept

The tree is at 54 passing across the four renamer files. `_make.py` remains blocked.

## Why keeping the guard matters

It is not a fix for this defect, and it **is** a fix for a real hazard: any future
visitor that recurses — which is what the default-argument change was trying to be —
would have hit the same double-rename. The guard makes that class of mistake
impossible, and it cost nothing (61 tests, no behaviour change).

That is the distinction between a **necessary** and a **sufficient** condition, and
this round established which one idempotence is.

## Round 192: `ast.arg` has no `default`, and the real fix is elsewhere again

Diagnosing round 189's eight failures gave the answer in one command:

```
E   AttributeError: 'arg' object has no attribute 'default'
```

**`visit_arg` receives an `ast.arg`**, which holds only the parameter's name and
annotation. Default values live on the enclosing `ast.arguments`, as
`args.defaults` and `args.kw_defaults`. Rounds 188 and 189 wrote
`node.default` from `visit_arg`, which cannot work — the attribute does not exist.

That is why idempotence changed nothing: the code never reached a default. It raised.

## The corrected attempt

Visiting defaults from `visit_FunctionDef`, where `node.args` is available:

```python
for _d in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]:
    self.visit(_d)
```

54 renamer, preserve, diversity and import tests pass — no regressions, unlike round
189's eight failures. **The approach is right.**

It still does not fix `_make.py`:

```
NameError: name 'i' is not defined
```

So the default argument is now visited and the defect persists, which means the
unrenamed `i` is **not** in `args.defaults`.

## Where that leaves it

The failing construct is `def _nx_6d1f3c(self, i=i)` **inside a `for` loop**. Two
things could be true:

- the default **is** in `args.defaults` and was renamed, but the **loop variable**
  was renamed to a *different* name;
- or the `i` that fails is a **different** `i` — the closure body's `return self[i]`,
  which reads the parameter, not the default.

The second is now more likely and is testable in one command: check whether the
emitted line reads `def ...(self, i=_nx_...)` or `def ...(self, i=i)`.

## Status

Open. Two structural facts gained: `ast.arg` carries no default, and visiting defaults
from `visit_FunctionDef` is safe where visiting them from `visit_arg` was not. Neither
is the fix, and both are now recorded so the next attempt does not repeat them.
