# `nonlocal` Declarations Can Lose Their Binding

**Date:** 2026-10-30, round 174.
**Found by:** vendoring `attrs` whole (`corpus/pkg/attr/`, 13 modules, 6337 lines).

## Symptom

Two of the six modules gated fail to compile:

```
_make       SyntaxError: no binding for nonlocal '_nx_0800fc'
_next_gen   SyntaxError: no binding for nonlocal '_nx_72858d'
```

Four others (`_cmp`, `_compat`, `_config`, `_funcs`) import cleanly.

## What is established

- The **fixtures compile** — `compile(source)` passes on both, so this is not the
  round-102 mistake.
- `_make.py` and `_next_gen.py` both use `nonlocal`; the four that pass do not.
- A **minimal `nonlocal` case does not reproduce**:

```python
def outer():
    count = 0
    def inner():
        nonlocal count
        count += 1
        return count
    return inner
```

  The renamer renames `count` consistently in the `nonlocal` declaration, the
  augmented assignment and the return, and the result compiles. So the defect needs
  something the minimal case lacks.

## What is not established

**Why.** Candidates, none tested:

1. a `nonlocal` whose target is **also** a parameter or a class attribute;
2. `nonlocal` inside a **decorated** nested function (attrs decorates heavily);
3. `nonlocal` where the outer binding is created by `exec` or a comprehension;
4. the interaction with `unfold_constants` or `enhanced_junk`, which both insert
   statements between the binding and the declaration.

## Status

Open with a reproduction at package level and no reduction. That is the same
starting position as the eighth defect in round 113, and the lesson from rounds
113–144 is that the next step is a **minimal reduction with a validity predicate**,
not a guess about passes.

## What it adds

A **tenth** defect, found within one round of the corpus gaining a new source — the
pattern that has held for every external module since round 83. `attrs` is the first
source that uses `nonlocal` at all.

The four modules that pass are in the gate; the two that fail are not, because a
fixture that cannot compile inside the gate would report a failure unrelated to the
obfuscator until the cause is understood — the same judgement as round 149.

## Round 175: reduced to one line, and the cause is a builtin again

The structure-preserving reducer (parse after every step, candidate must parse **and**
fail with `nonlocal`) reduced `_make.py` from 88 top-level statements to **one**,
156 lines, still failing. The offending line:

```python
        nonlocal hash
```

**`hash` is a builtin.** `nonlocal hash` is legal only because an enclosing scope
shadows it. The renamer rewrote the declaration but not the shadowing assignment, so
the declaration named a binding no scope provides.

## The fix

`visit_Nonlocal` and `visit_Global` now leave builtin names alone and reserve them.
That is the conservative half of the repair: it stops the declaration from being
broken without needing to know whether the shadowing assignment was renamed.

Third instance of the same family — a builtin treated as a renameable bindable:

| round | site | symptom |
|---|---|---|
| 143 | function table values | `NameError` at import |
| 174 | `nonlocal` declaration | `SyntaxError` |
| — | (the fix for 143 = emit builtins as attribute access) | |

## What the fix did, and did not, achieve

| module | before | after |
|---|---|---|
| `_cmp` | imports | imports |
| `_funcs` | imports | imports |
| `_make` | `SyntaxError: nonlocal` | **`NameError: NamedTuple`** |
| `_next_gen` | `SyntaxError: nonlocal` | **`SyntaxError: nonlocal`** |

`_make` moved to a **different** failure — `NamedTuple` undefined, which is the
import-reservation family again, not the same defect. `_next_gen` is unchanged,
so its `nonlocal` failure has another cause.

**Both are new information and neither is a fix.** The defect is not closed; it is
narrowed, and two of its four modules now pass.

## Status

Open. The specific `nonlocal hash` cause is fixed and should not recur. What remains
in `_next_gen` is a different `nonlocal` desync not yet reduced, and `_make` now
exposes an undefined import that was previously masked.

## Round 176: the second residual is an ordering dependency, not a missing rule

Reduced `_next_gen.py` to one statement, 344 lines, still failing. The line:

```python
nonlocal frozen, on_setattr
```

Neither is a builtin, so round 175's fix does not apply. They are **parameters of an
enclosing function**, and this renamer never renames parameters. The declaration was
renamed and its target was not — the general case of the same desync.

**A fix was attempted and reverted.** Leaving `nonlocal` targets alone entirely:

```
_next_gen   imports     <- the fix worked here
test_closure   SyntaxError: no binding for nonlocal 'n'
```

The declaration was preserved but `n += 1` inside the same function had **already
been renamed** by `visit_Name`, because the traversal reaches the use before the
declaration. Reserving the name inside `visit_Nonlocal` is too late.

Reverted to the round 175 behaviour. All 54 renamer and preservation tests pass.

## What this establishes

The rule is not "don't rename `nonlocal` targets" — that is necessary and
insufficient. It is **"know every name a scope declares before renaming any use
inside it"**, which is a pre-pass over each function's `nonlocal`/`global`
declarations, and that is a larger change than a round can verify.

That also explains why `_make.py`'s `nonlocal hash` was fixable: a builtin needs no
pre-pass, because its answer is always "leave it alone".

## Where the defect stands

| module | status |
|---|---|
| `_cmp`, `_funcs`, `_config`, `_compat`, `_next_gen` (after 175) | import |
| `_make` | fails differently — `NamedTuple` undefined, the import family |
| `_next_gen` (reverted) | fails — `no binding for nonlocal` |

The estimate in round 175 that `_next_gen` "has another cause" was right, and the
cause is structural: renaming happens in one pass, scope declarations are not known
until it has already started.
