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


## Round 121: the gate can see it, and the failure pattern is split

The gate now sweeps seeds (`--seeds 4242,7,1234`) and includes
`bulk/iterutils.py`:

```
seeds: 4242,7,1234
artefacts checked: 72
failures: 3
  FAIL bulk/iterutils seed=4242 k=0: fails at import: NameError ...
  FAIL bulk/iterutils seed=7    k=0: fails at import: NameError ...
  FAIL bulk/iterutils seed=1234 k=0: fails at import: NameError ...
```

At `--variants 1` only build index 0 is exercised, and it fails at **every**
seed. Round 120's seed table used `--variants 3` and showed index 0 failing while
index 2 varied. Putting both together:

| build index | behaviour |
|---|---|
| 0 | **always** fails |
| 2 | fails or imports depending on the seed |

## What that split means

Two distinct things are happening, not one:

1. **A deterministic defect at index 0.** Every seed fails, so this is a plain
   inconsistency, not a race — the same class as `hexversion` and `_sumprod`.
2. **A nondeterministic defect at index 2.** Some seeds pass, some fail, so the
   rename sometimes takes the md5 branch and sometimes the random branch at one
   call site and not the other.

Reporting them as one defect has been the reason six rounds of fixes did not
converge: each attempt addressed whichever of the two the last experiment
happened to expose.

## The gate change, and what it costs

`--seeds` defaults to `4242` so existing behaviour is unchanged; passing several
seeds multiplies runtime roughly linearly. A three-seed, one-index sweep is
about three minutes, which is affordable for a release check and not for every
test run.

The gate now reports `seed=` in every failure line, because a failure that
depends on a seed is a different kind of bug from one that does not.

## Round 122: exactly one invented name

Looking at the final emitted text rather than the tree:

```
table entries with _nx_ hex names: 2
  _nx_f24f62   defined:False  occurrences:1
  _nx_e2942a   defined:True   occurrences:5
```

**One entry is an invented name.** It occurs exactly once — in the table — and
nowhere else in the file. Its sibling, generated by the same mechanism at the
same time, occurs five times and resolves correctly.

So the table does not reference a function that was removed. It references a name
that **was never emitted at all**: `get_new_name` was called for that original
name once, produced `_nx_f24f62`, and the corresponding definition was renamed
through a **different** path or not at all.

## This is the md5/random split, seen directly

`_nx_f24f62` is hex, so it came from the `dynamic_unbounds` branch:

```python
self.mapping[old_name] = "_nx_" + md5(old_name).hexdigest()[:...]
```

Its sibling `_nx_e2942a` is also hex and also from that branch — and it resolves.
So for one of the two names the md5 entry was **created** but the definition's
`Name` was never patched to match, while for the other it was.

That is a **write-then-forget**, not a two-branch disagreement: the mapping is
recorded, the table is rewritten, and the definition is missed. Which definitions
get missed depends on traversal order, which depends on the random stream — the
nondeterminism from round 120.

## What the fix has to guarantee

Not "pick one branch consistently" but: **every `Name` binding of an original
identifier is rewritten to `mapping[original]`**, including definitions, and
including ones the traversal reached before the mapping existed.

That is the same predicate the `hexversion` and `_sumprod` fixes needed, in a
different place: **rename on lookup, not at visit time**, so that a mapping
created late still applies to an early-visited binding.

## Status

Cause now precise enough to fix: one invented name, produced by the md5 branch,
with its definition missed. Not fixed this round — the change is to how renaming
is applied across the whole tree, and the last six rounds established that
attempting that without a reproduction is how this defect survived six rounds.

## Round 123: fixed by applying the final mapping once more

The fix is a post-pass after the renamer, `_apply_final_rename`, which rewrites
every `Name`, `FunctionDef` and `ClassDef` binding through the renamer's **final**
mapping. It does not touch `arg` or `keyword.arg`, because parameter and keyword
names are call-site contracts.

The reason it works is the one round 122 identified: the mapping is now applied
**on lookup at the end**, so a mapping created late still reaches a binding
visited early, and the result no longer depends on traversal order.

## Verification

| sweep | artefacts | failures |
|---|---|---|
| 1 index × 3 seeds | 72 | **0** |
| 2 indices × 2 seeds | 96 | **0** |
| 1 index, single seed (before) | 69 | 3 |

The 3 failures that made the gate red in round 121 are gone at every seed tried,
including the two seeds where build index 2 previously imported and the one where
it did not.

## What this defect cost, in rounds

| round | action | result |
|---|---|---|
| 113 | gate a large module | found it |
| 114 | guessed folding, wrote a fix | reverted |
| 115 | reasoned from pass order | corrected |
| 116 | one control | refuted the reading |
| 117 | control per pass | located two passes |
| 118 | dump after each | cleared both |
| 119 | forward bisect | found a trigger, not the cause |
| 120 | seed sweep | found the nondeterminism |
| 121 | seed sweep in the gate | split it into two defects |
| 122 | read the emitted text | found the invented name |
| **123** | **apply mapping on lookup** | **fixed** |

Eleven rounds. Six of them were caused by reasoning instead of measuring. The
five that moved — 116, 119, 121, 122, 123 — each began with an observation of
the **output**, not a hypothesis about a pass.

## The rule, now paid for four times

**A value must have one owner.** Expiry, `hexversion`, `_sumprod` and this table
entry are four instances in four subsystems. Every fix that worked made a single
authority responsible for the final spelling or value; every fix that failed
tried to make two places agree.

## Round 123, corrected: the fix worked on the gate and broke fifteen tests

`_apply_final_rename` made the artefact gate green — 72 artefacts at three seeds,
96 at two indices and two seeds, zero failures — and then the full suite returned
**15 failed, 4499 passed**.

| failing test | what it protects |
|---|---|
| `test_all_preserve.py::test_private_names_still_renamed` | public exports keep their names, private ones still rename |
| `test_all_preserve.py::test_no_all_unchanged_behavior` | modules without `__all__` behave as before |
| `test_const_attack.py::test_unfold_constants_lowers_int_recovery` | constant unfolding still frustrates recovery |
| `test_diversity.py` (3 tests) | different seeds produce different artefacts |
| `test_golden.py::test_golden_output_changes_with_seed` | output changes with the seed |
| `test_renamer_semantics.py::test_module_binding_use_agreement` | binding/use agreement — the property the fix was meant to serve |
| `test_residue_random.py::test_pipeline_artifacts_execute` | artefacts execute |
| `test_opt_enforcement.py::test_explicit_user_flag_overrides_level` | option plumbing |

**Reverted.** The suite is the authority on what the renamer is *supposed* to do;
the gate only knows that the output runs. A change that satisfies the gate and
breaks fifteen contract tests has traded a real property for an apparent one.

Among the failures is the very test the fix was meant to fix —
`test_module_binding_use_agreement`. Applying the mapping indiscriminately
rewrites names that must keep their spelling: reserved names, `__all__` exports,
and anything the renamer deliberately skipped.

## What the next attempt must respect

`_apply_final_rename` has to apply the mapping **only to names the renamer
actually renamed**, not to every name it has a mapping for. The renamer already
knows that distinction — `reserved`, the `__all__` set, and the skip rules in
`visit_Name` — and the post-pass was ignoring all of it.

The correct shape is therefore: collect the names the renamer **did** rewrite and
their new spellings, then apply exactly those to the bindings it missed. That is
a smaller set than `renamer.mapping`, which records intent rather than outcome.

## The guard this argues for

The gate found the defect and the suite found the fix's cost. Neither alone is
sufficient, and this round is the clearest demonstration in the programme: a
green gate with a red suite is the normal shape of a bad fix.

## Round 124: the renamer is the wrong place

The constrained version — rewrite definition names only, skip reserved — still
failed **11 of 77** contract tests, including `__all__` preservation.

The reason is structural: `__all__` is a list of **strings**, not `Name` nodes.
Renaming a definition without rewriting the corresponding string leaves the
module exporting a name that no longer exists. Any fix that touches the renamer
has to synchronise `__all__`, reserved names, exports, and the skip rules at
once — which is exactly the fifteen-test blast radius of the previous attempt.

**Every attempt to fix this in the renamer fails the same way, and the reason is
the same each time: the renamer's mapping is not the authority on what a name
should be. The table is wrong, not the definitions.**

## Where the fix belongs

`CallGraphObfuscator` builds a table mapping indexes to **names**. It runs before
renaming, so the names it records are pre-rename. The smallest correct fix is for
the table to record the **final** names — either by running after the renamer, or
by being rewritten from `renamer.mapping` at the point renaming completes.

That touches one structure instead of the whole renamer, and it cannot break
`__all__`, exports or reserved names because it never touches a definition.

## The score after twelve rounds

| attempt | gate | suite |
|---|---|---|
| guessed folding | — | — |
| blanket mapping pass | green | **15 failed** |
| definitions-only pass | — | **11 failed** |

Two fixes, two reversions, both because they changed the wrong object. The
diagnosis from round 122 stands: one invented name, produced by the md5 branch,
whose definition was missed. The repair must be applied to the **table**, which
is the structure that ended up wrong.

## Round 135: the reduction attempt was invalid, and how

Automatic reduction (drop definitions while the module still raises `NameError`
after obfuscation) produced a 31-line source and a one-function source — and both
were **false positives**.

The failure predicate was `NameError after obfuscation`. Pruning a definition
while leaving a header statement or a default argument that referenced it makes
the **input** raise `NameError` at import, and the predicate cannot tell that from
the defect it was hunting.

Two examples the reducer accepted:

```python
_orig_default_visit = default_visit     # default_visit was pruned
guid_iter = GUIDerator()                # GUIDerator was pruned
```
```python
def pairwise(src, end=_UNSET):          # _UNSET lived in a pruned try/except
    return windowed(src, 2)             # windowed was pruned
```

Both raise on the **original** source. Neither is evidence about the obfuscator.

**The predicate must be: the original source imports cleanly AND the obfuscated
version does not.** That check was missing, which is the same class of error as
round 102's invalid fixture and round 132's short grep: the instrument accepted a
result that a validity check would have rejected.

## What was confirmed

Three hand-written minimal shapes all pass:

| shape | result |
|---|---|
| two functions, one calls the other | imports |
| one function only | imports |
| three functions in a chain | imports |

So the defect needs more than call-graph structure. The reduction has to be rerun
with the validity predicate before it can say what else is required.

## Round 136: the header statements are load-bearing

Reran the reduction with the validity predicate from round 135 — **input must
import cleanly and the obfuscated version must not** — and got a different answer:

```
defs: 45 (none removed)
input imports: False
defect reproduces: False
```

The reducer kept all 45 definitions and still could not produce a valid input,
because it had been reduced to **imports plus definitions only**. The module's
header — the `try/except ImportError` blocks, `_UNSET`, `_REMAP_EXIT`,
`_orig_default_visit`, `guid_iter` — is **required** for the source to import.

And with that header removed, the defect **does not reproduce at all**. So the
header is not incidental scaffolding: it is part of the trigger.

## What that narrows

| component | needed |
|---|---|
| imports | not sufficient (tested: three minimal shapes pass) |
| definitions | not sufficient |
| **header statements** | **required** |

That is new information, and it came from the corrected predicate rather than from
another hypothesis. The previous reduction had silently pruned the header and
accepted invalid inputs, which pointed at definitions.

## The next step

Reduce the **header** while keeping it valid: drop individual header statements,
keep those the source still needs, and check `defect()` after each. The candidate
worth trying first is `_orig_default_visit = default_visit`, because it is the one
header statement that names a **function object** rather than building a sentinel —
exactly the shape the defect is about.

That is one experiment, not a theory.

## Round 137: the header shapes are individually fine

Tested the three header statements in isolation, each with a function that uses
them:

| shape | output imports |
|---|---|
| `_orig = default_visit` (alias of a function object) | **yes** |
| `_UNSET = object()` (sentinel) | **yes** |
| `try: from math import missing / except ImportError: _REM = object()` | **yes** |

All three pass at build index 0. So no header statement is sufficient on its own,
just as no definition was.

## What the reduction has established, cumulatively

| component | sufficient alone |
|---|---|
| imports | no (round 135) |
| definitions (incl. call chains) | no (round 135) |
| header statements | no (round 137) |
| header **and** definitions | still not tested |

The trigger is therefore an **interaction** between a header statement and a
definition, or it depends on module size. Both are testable: build sources that
pair each header statement with each of a few definitions and check the defect.

## Why the reduction has taken three rounds

Round 135's reducer produced false positives because it accepted invalid inputs.
Round 136 fixed the predicate and found the header mattered, but reduced to
imports-plus-definitions, which is invalid on its own. Only in round 137 did the
test become a **controlled comparison**: a valid input containing one header shape
and one function, measured for a property the input does not have.

Each round got closer by making the test smaller and more explicit, and no round
got closer by reasoning about the obfuscator.

## Round 138: the defect resists reduction

Two more controlled experiments.

**Header × body grid** — three header shapes against three body shapes, nine
combinations, all valid inputs:

| | simple | chain | class |
|---|---|---|---|
| alias of function | imports | imports | imports |
| sentinel | imports | imports | imports |
| try/except fallback | imports | imports | imports |

**Nine of nine pass.**

**Size sweep** — synthetic modules of 5, 15, 30 and 45 functions at two build
indices each:

```
n=5   0/2 fail
n=15  0/2 fail
n=30  0/2 fail
n=45  0/2 fail
```

No threshold. Forty-five plain functions obfuscate and import cleanly.

## What the programme has now ruled out

| hypothesis | rounds spent | verdict |
|---|---|---|
| the folding pass makes tuple keys | 114 | refuted |
| pass order (table before rename) | 115 | necessary, not sufficient |
| the table needs `obf_calls` | 116 | necessary, not sufficient |
| the two passes together | 117–118 | refuted by dump |
| `EnhancedJunk` | 119 | trigger, not cause |
| the random stream | 120 | real, but not sufficient alone |
| the renamer renames wrongly | 123–124 | refuted, two fixes reverted |
| a stale call returning the input | 133 | real, a **different** defect |
| imports alone | 135 | not sufficient |
| definitions alone | 135 | not sufficient |
| header statements alone | 137 | not sufficient |
| header × body | 138 | not sufficient |
| module size | 138 | not sufficient |

**Thirteen ruled out.** What remains is something specific to
`iterutils.py`'s content that none of these abstractions capture.

## The honest assessment

This defect has now consumed more rounds than every other defect in the programme
combined, and the reduction has failed at every level tried. The remaining options
are:

1. **Bisect the module by content, not structure** — keep the full source, replace
   individual function *bodies* with `return None` one at a time, and see which
   replacement removes the defect. That is a different axis from dropping whole
   definitions.
2. **Accept the defect as open** and record it with the thirteen refutations, so
   the next attempt does not repeat them.

Option 2 is defensible and option 1 is one experiment. The document now carries
enough refutations that option 1 is cheap to try and cheap to abandon.

## Why this is still progress

Every one of the thirteen refutations is a fact that was not known before, and
five of them cost only one command each. The defect is not closer to fixed, but
the space of explanations is thirteen smaller — and the previous twelve rounds of
this defect were spent on hypotheses that are now excluded by measurement rather
than argument.

## Round 139: the content bisect produced noise, and the reason is known

Replacing each top-level function body with `return None` and checking whether the
defect disappears:

```
baseline defect: True
top-level functions: 42
bodies whose replacement removes the defect: 31
```

**Thirty-one of forty-two.** Replacing almost any body appears to "fix" it, which
is not a signal about content — it is the **RNG** again. Any edit to the module
shifts the random stream, and round 120 established that the defect is
nondeterministic: it appears when the stream reaches a particular state.

So the bisect is measuring the stream, not the code. The same reading applies to
the earlier bisects that "located" `enhanced_junk`, `symbol_rename` and
`obf_calls`: each was a stream shift.

## Confirmed by size

Large synthetic modules do not reproduce it:

| functions | statements each | lines | failures |
|---|---|---|---|
| 10 | 10 | 129 | 0/2 |
| 20 | 20 | 459 | 0/2 |
| 30 | 30 | 989 | 0/2 |

989 lines of dense arithmetic obfuscates and imports cleanly. So the defect is not
volume, not structure, not any single construct — and the reduction techniques
that work on deterministic defects cannot see it.

## What this means for the eighth defect

**A reduction is not possible while the defect is nondeterministic.** The correct
order is:

1. make the defect **deterministic** first — find the seed and build index that
   reproduce it, and fix the stream so the same input always produces the same
   failure;
2. then bisect, because a bisect erases itself when any edit changes the outcome.

The programme has done (2) five times and (1) never. Round 120 found the
nondeterminism and rounds 135–139 continued bisecting anyway.

## The honest status

The eighth defect is **not reduced** and cannot be reduced by the methods tried.
What is known:

- it requires `obf_calls` and `symbol_rename` to both run;
- their combined output is valid;
- it appears at build index 0 always and index 2 sometimes;
- it is insensitive to module size and composition;
- every structural edit perturbs it.

That is a description of a race in the rename/fold interaction, and the next step
is to make it reproducible, not to reduce it.

## Round 140: it is deterministic per input, which reframes the bisect problem

Round 139 concluded that a reduction is impossible while the defect is
nondeterministic. That conclusion was wrong in an important way.

Three runs with the same input and seed:

```
trial 0: hash 47384fb9f1d6  imports=False
trial 1: hash 47384fb9f1d6  imports=False
trial 2: hash 47384fb9f1d6  imports=False
identical across trials: True
```

**The obfuscator is deterministic.** The same source and seed always produce the
same output, and that output always fails. There is no race, no thread, no clock.

## What the nondeterminism actually is

The **choice point** is deterministic for a given input, but **which** choice point
a run reaches depends on the input:

- the defect appears at seed 4242 index 0 and not at seed 7 index 2;
- any edit to the source changes how many random draws precede the table
  construction, so a different branch is taken.

So the defect is a **deterministic function of the input**, and a bisect changes
the input. That is why 31 of 42 body replacements "removed" it: each replacement is
a different input, not a different code path with the same input.

## What a working reduction needs

**Edits that do not change RNG consumption.** Two possibilities:

1. **Reduce the output, not the input.** Take the emitted failing artefact and cut
   it down while it still runs — that is a reduction over the thing that is broken,
   and it never re-runs the generator.
2. **Reseed at the choice point.** Make the pass that builds the table draw from a
   dedicated RNG seeded from the function's identity, so its behaviour is
   independent of everything before it. That would make the defect input-invariant
   and bisectable — and it is also a plausible **fix**, because it removes the
   coupling between unrelated passes.

## Why this is progress

The previous section said "make it deterministic first". It already is. The
mistake was conflating **input-dependence** with **nondeterminism**, and it cost
rounds 139 and part of 138 pursuing a reduction that could not work by
construction.

Option 1 is one command: take the emitted failing file, and reduce **that**.

## Round 141: the output reduction was invalid too, in the same way

Reduced the **emitted artefact** rather than the source — 1533 lines to 384 — and
the reduced file still failed. The failure was:

```
NameError: name 'src' is not defined
  at line 194: if not _nx_182349(src):
```

That looked like a real find, and it is not. Reading the context:

```python
try:
        sys.exit()
except Exception:
    if not _nx_182349(src):      # <- line removed above this
```

The line-level reducer had deleted the enclosing `def` but kept its body. The
`src` reference belongs to `CodeChecksummer`'s template:

```python
def _nx_verify():
    for fn, expected in ...:
        src = inspect.getsource(f)        # bound right here
        if _h.sha256(src.encode())...
```

`src` is a local in that function. My reducer removed the `def`, leaving an
indented block at module level where `src` has no binding.

## Third time, same failure mode

| round | instrument | how it lied |
|---|---|---|
| 102 | fixture | the input was not valid Python |
| 135 | source reducer | pruning created undefined names |
| **141** | **output reducer** | **line removal deleted a `def` and kept its body** |

In each case the artefact produced an alarming, specific, and wrong answer, and in
each case **one validity check would have rejected it**:

- input imports cleanly (round 136, added);
- the reduced output still compiles under a full parse (round 141, **not** added).

A line-level reducer that can break block structure needs `ast.parse` after every
step, not just a "does it fail" predicate.

## What is unchanged

The eighth defect is still open, the source reduction is still blocked by RNG
consumption, and the output reduction needs a structure-preserving cut. Neither of
the three failures weakens those facts.

## What is worth keeping

`CodeChecksummer` is **not** a defect. The template is correct, `src` is bound, and
the integrity check is scoped to a function. That is worth stating because for one
round it looked like the finding.
