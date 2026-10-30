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

## Round 116: the control separates it, the audit does not find it

Two of the three planned steps, both run.

**Step 1 — control.** Generating with `obf_calls` disabled:

| configuration | result |
|---|---|
| with `obf_calls` | `NameError: name '_nx_f24f62' is not defined` |
| without `obf_calls` | **imports** |

So the defect requires that pass. That is the first piece of hard evidence in
three rounds of guessing.

**Step 2 — audit the table it produces.** Running `CallGraphObfuscator` alone on
the module and comparing every table entry's value name against the definitions,
imports and builtins in the resulting tree:

```
truly undefined table entries: 0
```

**The pass on its own produces a valid table.** So the undefined name appears
**later**: some subsequent transform either renames a function definition and
not its table entry, or removes a definition the table references.

## Where that leaves it

| claim | status |
|---|---|
| the order (table before rename) | confirmed, round 115 |
| the defect requires `obf_calls` | **confirmed by control** |
| the defect is *caused* by `obf_calls` alone | **refuted** — its output is valid |
| what removes or renames the target afterwards | unknown |

**Step 3 — decide.** Not taken, because the decision depends on the unknown. The
next step is to bisect the **remaining** passes the same way: disable each in
turn and see which one turns a valid table into a broken one. That is the same
control that just worked, applied to the rest of the pipeline.

## What three rounds of this have cost, and taught

Round 114: guessed folding, wrote a fix, reverted it.
Round 115: confirmed the order, called it the cause, corrected that.
Round 116: a control at last, which refuted the straightforward reading.

The control took one command. Reaching for it first would have saved two rounds.

## Round 117: the defect is the interaction of two passes

The control from round 116, applied to every pass in turn:

| pass disabled | result |
|---|---|
| **`symbol_rename`** | **imports** |
| **`obf_calls`** | **imports** |
| `cfg_flatten` | imports |
| `bogus_exceptions` | fails |
| `split_vars` | fails |
| `unfold_constants` | fails |
| `mba_subs` | fails |
| `opaque_predicates` | fails |
| `string_encode` | fails |

Two of the nine make the defect disappear: the table pass and the rename pass.
The others are irrelevant, and `cfg_flatten` also happening to import is a
separate observation worth checking later.

So it is the **interaction**: a table is built, then a rename runs over both the
definitions and the table, and the two do not agree. Round 115 said this was a
precondition; it is now shown to be the mechanism's location, by control.

## What remains unknown, precisely

`visit_Name` renames every `Name` by id, so a table entry and its definition
should receive the same spelling. They do not, which means one of three things:

1. **the table's value is not a `Name`** at the time the renamer runs (it may be
   a string, or a nested attribute, that `visit_Name` does not reach);
2. the table is **re-emitted** after renaming by a pass that keeps a stale copy;
3. the definition is **skipped** by the renamer while the table entry is not.

Distinguishing those needs one dump: the tree immediately after `obf_calls`,
and the tree immediately after the renamer, with the table entry and the
definition's spelling shown side by side. That is the next step and it is small.

## The method, at last

| round | method | outcome |
|---|---|---|
| 114 | guessed a cause, wrote a fix | reverted |
| 115 | reasoned from pass order | corrected |
| 116 | one control | refuted the reading |
| **117** | **one control per pass** | **located to two passes** |

Four rounds. The last two used the method the whole programme has been
recommending, and the last two produced the only hard results.

## Round 118: the dump clears both passes

The one dump from round 117's plan:

| stage | table value node type | truly undefined entries |
|---|---|---|
| after `obf_calls` | `Name` | 0 |
| after `symbol_rename` | `Name` | **0** |

**The two passes that the bisect implicated produce a valid table.** Their
output has no entry naming an undefined function.

So the bisect was reading a **precondition** rather than a cause: both passes are
**necessary** for the defect to appear, but neither produces it. Something later
breaks a table that is correct at this point.

## Where that leaves it, honestly

| claim | status |
|---|---|
| defect requires `obf_calls` | confirmed by control |
| defect requires `symbol_rename` | confirmed by control |
| their combined output is invalid | **refuted by dump** |
| which pass breaks it afterwards | unknown |

That is the fourth reading of this defect to be corrected. The bisect narrows the
**preconditions** but not the **cause**, and the two are not the same thing.

## Why the bisect misled

Disabling a pass that is *necessary but early* removes the defect downstream,
because the defect needs a table to exist at all. So "disabling X fixes it" does
not mean "X breaks it" — it means "X is upstream of the break". I treated those
as equivalent for a round.

The right next step is a **forward** bisect rather than a backward one: dump the
table after **every** pass and find the first stage where an entry stops matching
its definition. The pass immediately before that stage is the cause.

## Round 119: the cause is `EnhancedJunk`, found by forward bisect

The forward bisect looks at the passes **after** the renamer, where the dump said
the tree was still valid.

| pass disabled | result |
|---|---|
| `unicode_ids` | fails |
| `strip_meta` | fails |
| `dynamic_code` | fails |
| `attention_poison` | fails |
| `decoy_apis` | fails |
| `adaptive_rewrite` | fails |
| **`enhanced_junk`** | **imports** |
| `break_decompiler` | fails |
| `code_checksums` | fails |
| `fragment_strings` | fails |
| `rep_diversify` | fails |
| `vm_dispatch` | fails |

And the confirmation, comparing the emitted table:

```
default             _nx_ftable = dict([(0, callable), (1, iter), (sum([2]), ValueError), ..., _nx_f24f62 ...])
enhanced_junk off   _nx_ftable = dict([(0, iter), (1, iter), (2, callable), (3, TypeError), ...])
```

With the pass enabled the table references `_nx_f24f62`, a name that is never
defined. With it disabled the table has no such entry.

## The mechanism, stated

`EnhancedJunk` runs **after** the renamer. It creates or replaces function
definitions, and the function table built by `CallGraphObfuscator` — earlier in
the pipeline — retains an entry pointing at a name that the pass removed or never
defines.

This is the **fourth** defect in the same structural family:

| defect | binding written | use read |
|---|---|---|
| expiry | window fixed at pack time | recomputed at run time |
| `hexversion` | import not renamed | use renamed |
| `sumprod` | fallback rebinds | alias renamed |
| **`_nx_f24f62`** | **table built before junk pass** | **junk pass rewrites definitions** |

Four instances of one rule being violated: **a value must have one owner**. The
programme has now paid for this four times.

## The fix, specified

Either emit the function table **after** `EnhancedJunk` runs, or have
`EnhancedJunk` leave table-referenced definitions alone. The first is smaller and
matches how the `__future__` fix was solved — reorder once at the end rather than
teach every pass a rule.

Not applied: the last five rounds established that an unverified change to this
pipeline costs more than it saves. The next round applies it with a minimal
reproduction first.

## Round 120: the defect is nondeterministic

`EnhancedJunk.visit_Module` only **adds** statements — it never removes or
replaces a definition. So it cannot be the cause of an unbound name in the way
round 119 stated. What it can do is **shift the random stream**.

Testing that:

| seed | build index | result |
|---|---|---|
| 4242 | 0 | fails |
| 4242 | 2 | fails |
| 7 | 0 | fails |
| **7** | **2** | **imports** |
| 1234 | 0 | fails |
| **1234** | **2** | **imports** |

**The same module imports or fails depending on the seed and build index.** The
defect is nondeterministic.

## What that means

`EnhancedJunk` was a red herring of the same kind as `symbol_rename` and
`obf_calls`: **toggling it changes the random stream**, and the defect appears
when the stream happens to reach a particular state. The bisect in round 119
located a **trigger**, not a cause — the third time a control has separated a
precondition from a cause on this defect.

The real cause is that **a rename is not consistent across its call sites** for
some random states. `get_new_name` has two branches — the `dynamic_unbounds`
md5 branch and the random branch — and if the same original name reaches them at
different times, the two call sites receive **different new names**.

## Severity

This is worse than a broken build. An obfuscator that is **nondeterministic in
correctness** produces artefacts that pass a test run and fail in the field, with
no change to the input. Every release is a dice roll on whether a given function
table resolves.

The guard that would catch it is cheap: **run the gate across several seeds**,
not one. The current gate uses `master_seed=4242` only.

## Status

Cause narrowed to an inconsistent rename across call sites, dependent on random
state. Not fixed. The immediate action this justifies is in the gate, not the
transform: widen the seed sweep so the flakiness cannot hide.
