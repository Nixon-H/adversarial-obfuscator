# Generated Function Table Gets a Tuple Key From Constant Folding

**Date:** 2026-10-30
**Found by:** `boltons/iterutils.py` (BSD-3, 61 KB, 42 functions), the fifth
external module and the largest yet gated.
**Fixture verified valid** — `compile(source)` passes on the input.

## Symptom

```
NameError: name '_nx_f24f62' is not defined
```

at build indices 0, 2 and 4.

## What the emitted table looks like

`CallGraphObfuscator` builds a function table at module top:

```python
_nx_ftable = dict([(0, callable), (1, iter), (sum([2]), ValueError), (sum([2, 1]), ...)])
```

The third entry's **key** is `(sum([2]), ValueError)` — a **tuple** — where it
should be the integer `2`. A later entry appears to have been consumed into the
same key.

## Cause

A constant-folding pass rewrites the integer key `2` into `sum([2])` **inside a
dict-literal position**. `(sum([2]), ValueError)` then parses as a two-element
tuple rather than `key: value`, so the table gains a tuple key and loses the
entry for `2`. The lookup that follows cannot resolve.

## What is established

- The generated table is the site: the tuple key is visible in the emitted
  source.
- A plain user-written `{0: str, 1: int, 2: list}` survives the same pipeline at
  all three indices — the defect needs the generated table, not merely an
  integer key.
- It reproduces at every build index of this module.

## What is not established

**A minimal reproduction.** I tried a user-written integer-keyed dict and it
worked, which narrows the trigger to the table construction but does not isolate
it. Writing the table by hand in isolated form did not reproduce, so the trigger
involves the interaction between the table insertion and whichever pass folds
keys — and attributing it without that reduction would repeat the mistake of
round 102.

## Status

Open, located to the generated table, not reduced. The next step is to instrument
which pass emits `sum([2])` inside the dict literal — the same isolation method
that found `hexversion` and `isqrt`, rather than reading the passes.

## The count

Eight defects. This one is the first found in a module over 50 KB, and the first
where the observable is a wrong **data structure** rather than a missing binding.


## Round 114: the cause is not the folding, it is the order

I instrumented this expecting a dict-key or tuple problem and got it wrong twice.

**The folding is harmless.** `(sum([2]), ValueError)` evaluates to `(2,
ValueError)`; `sum([2, 1])` evaluates to `3`. The table's keys are correct after
evaluation. What is not correct is a **value**: the table maps an index to a
**function name**, and one of those names is undefined at the point the table is
built.

```
_nx_ftable = dict([(0, callable), (1, iter), (sum([2]), ValueError), ..., (n, _nx_f24f62), ...])
```

`_nx_f24f62` is a renamed name. The table is emitted **before** the rename pass
runs, so the entry keeps the pre-rename spelling while every other reference in
the module gets the new one. The table then points at a name that exists only in
its own construction line.

**That is a third instance of the same structural defect** as `hexversion` and
`_sumprod`: a binding written before a rename, and a use after it.

## What I got wrong, in order

1. guessed "dict keys are unfolded into tuples" — wrote a `visit_Dict` fix;
2. the fix kept the keys but the module still failed, so I inspected the emitted
   table and found the tuple *is* the key and the key is correct;
3. only then did I look at the **values** and find the undefined name.

Two rounds of guessing before reading the artefact, which is the same mistake as
rounds 87–88. The instrument was available the whole time: dump the emitted
table and look at it.

## Status

Open. The fix is to build the function table **after** renaming, or to rename
its entries in step — the same "one owner per value" shape that solved the core
digest and the licence key.

The dict-key change was reverted: it addressed a problem that does not exist.

## Round 115: the order is confirmed, the mechanism is not

The pipeline applies the table insertion before renaming — `sources.py` line 422
calls `CallGraphObfuscator().visit(tree)`, line 538 calls `renamer.visit(tree)`.
That is the order round 114 predicted.

But the mechanism does not follow from it as cleanly as I wrote. The table's
values are `ast.Name` nodes, and the renamer's `visit_Name` renames every Name
by id, so a Name in the table should get the same new spelling as the function
definition. Something else is needed to explain an entry that no definition
matches, and I have not found what.

**So the corrected status is: order confirmed, mechanism unknown.** The previous
section presented the order as the cause; it is a precondition, not a
demonstration.

## What the next attempt should do

Instrument rather than reason, for the third time:

1. run the pipeline with `call_obf` disabled and see whether the defect
   disappears — that separates "the table" from "everything else";
2. if it disappears, dump the tree immediately after `call_obf.visit` and
   compare the table's Name ids against the module's actual definitions;
3. only then decide whether to move the pass or to rename its entries.

The three defects in this class (`hexversion`, `_sumprod`, `_nx_f24f62`) each
took a minimal reproduction to fix. This one does not have one yet, and the last
two rounds have shown what happens when I skip that step.
