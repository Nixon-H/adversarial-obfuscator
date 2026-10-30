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
