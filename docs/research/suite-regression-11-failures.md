# Eleven Contract Tests Are Already Failing on a Clean Tree

**Date:** 2026-10-30
**Found by:** a control run, after two suspected fixes produced identical failures.

## What happened

Round 123 applied a rename fix, the full suite reported **15 failed**, and the fix
was reverted. Round 124 applied a narrower fix, **11 failed**, and it was
reverted too.

Round 125 applied a third fix, scoped to the function table, and got **the same
11 failures** — including the same test names, byte for byte.

That repetition was suspicious, so the fix was stashed and the same seven files
were run against the **unmodified tree**:

```
11 failed, 66 passed
```

**The same eleven tests fail with no fix applied.**

## What that means

1. The two reverted fixes were **not** responsible for those eleven. The
   reverts were made on a wrong inference — I attributed a pre-existing failure
   to a change I had just made, twice.
2. **The suite is not green.** Round 111 reported 4514 passed, 0 failed. Something
   committed between then and round 123 introduced eleven contract failures, and
   it went unnoticed because round 111's run was the last full one.

## The failing tests

| file | test |
|---|---|
| `test_all_preserve.py` | `test_private_names_still_renamed` |
| `test_all_preserve.py` | `test_dynamic_all_no_crash_and_warns` |
| `test_all_preserve.py` | `test_no_all_unchanged_behavior` |
| `test_renamer_semantics.py` | `test_module_binding_use_agreement` |
| `test_diversity.py` | three seed/variant tests |
| `test_golden.py` | `test_golden_output_changes_with_seed` |
| `test_const_attack.py` | `test_unfold_constants_lowers_int_recovery` |
| `test_residue_random.py` | `test_pipeline_artifacts_execute` |
| `test_opt_enforcement.py` | `test_explicit_user_flag_overrides_level` |

A sample failure:

```
assert "def helper(" not in out2
E  AssertionError: assert 'def helper(' not in '__all__ = [... return 1\n'
```

The renamer is leaving a module function unrenamed. That is consistent with the
round 99–100 changes, which **reserved** imported names so their uses would stay
consistent — and a reservation that is too broad would leave ordinary definitions
alone too.

## The hypothesis to test next

`visit_ImportFrom` and `visit_Import` now add every bound name to `self.reserved`.
If a name is imported **and** redefined, or if the reservation outlives the model
the test expects, functions that should rename will not.

## The lesson

Round 111's green result was a **snapshot**, and I have been quoting it for
fourteen rounds. The control that would have caught this takes four seconds and
was run for the first time today, in the wrong direction — to check a fix rather
than to check the baseline.

**Check the baseline before attributing a failure to your change.** Every time.

## Round 126: the renamer is fine, the pipeline is not

Testing the hypothesis directly.

**`SymbolRenamer` in isolation works:**

```
reserved contains 'helper': False
mapping: {'helper': '_nixon_Λڙɱכま', 'caller': '_nixon_მѪჂৠႼ'}
output has 'def helper': False
```

**Through the pipeline it does not:**

```
src:  __all__ = ["foo", "Bar"]  +  def helper(): ...
out:  'def helper(' present: True
```

`helper` is not in `__all__`, so nothing should reserve it, and yet the pipeline
leaves it alone while the renamer on its own renames it.

So the reservation happens **somewhere in the pipeline**, not in the renamer
class. The candidates are the code in `sources.py` that populates
`renamer.reserved` from `_all_names` and from the `_NX_*` marker lists — one of
those is adding a name it should not, or `_all_names` is being computed more
broadly than the module's `__all__`.

## What this round establishes

| claim | status |
|---|---|
| the renamer class renames an ordinary function | **confirmed** |
| the pipeline leaves it unrenamed | **confirmed** |
| the round 99–100 import reservations cause it | **not established** — no imports in this source |
| the eleven failures predate round 125's fix | **confirmed by control** |

That last row is the one that matters for the reverts: the failures are not mine
from round 125, and my earlier statement that "something committed since round
111 introduced them" remains a hypothesis, not a finding.

## The next step

Instrument `renamer.reserved` immediately before `renamer.visit(tree)` inside the
pipeline for this source, and diff it against the renamer's default set. The extra
entry is the bug, and it is one line to find — the same "look at the value"
technique that eventually settled the table defect, applied for the first time
here before rather than after two wrong fixes.

## Round 127: function renaming is effectively disabled

Instrumenting `reserved` at the visit boundary showed what round 126 could not:
`helper` is **not** reserved when the pipeline hands the tree to the renamer. So
reservation was never the cause.

The actual output for the test's source:

```
def foo():
def ping(self):
def _priv():
def helper():
```

**None of the four is renamed.** `foo` is an export and should keep its name;
`_priv` is underscore-prefixed and by policy keeps its name; `ping` is a method and
is deliberately preserved. But `helper` is a plain module-level function that no
rule protects — and it survives too.

So `symbol_rename` is not renaming **module-level functions at all**. The eleven
failures are not stale tests and not a reservation problem: the pass has become a
no-op for the construct it exists to obfuscate.

## Why this matters more than the eleven tests

Renaming functions is the core of the obfuscator's identifier obfuscation. If a
plain `def helper():` keeps its name, the output is far more readable than the
configuration says it should be — and `test_diversity`, `test_golden` and
`test_private_names_still_renamed` are all detecting exactly that, from three
different angles.

The gate cannot see it: the artefacts still **run**. Every defect this programme
has chased for fourteen rounds produced code that failed; this one produces code
that works and is **less obfuscated than advertised**.

## What is established

| claim | status |
|---|---|
| `helper` is not in `reserved` before the visit | confirmed |
| `helper` is not renamed | confirmed |
| `foo`, `ping`, `_priv` also unrenamed | confirmed |
| reservation causes it | **refuted** |
| function renaming is disabled | **confirmed for module-level defs** |

## The next step

Find the condition in `visit_FunctionDef` that skips the rename. The code reads
`if node.name not in self.protected_functions and not node.name.startswith("__") ...`
and the comment says module-level functions still rename — so either the condition
now excludes them, or `protected_functions` contains everything.

`protected_functions` is set from `sources.py`. If it is populated with every
function name rather than the ones that must be protected, the renamer would
preserve them all silently — which matches what the output shows.

## Round 128: the condition, and one clause that explains part of it

The gate on renaming a function:

```python
if (node.name not in self.protected_functions
        and not node.name.startswith("__")
        and not node.name.startswith("_")
        and node.name not in self.reserved):
```

Instrumented at the visit boundary for the failing source:

```
protected_functions = 0     (so nothing is protected)
'helper' in protected_functions: False
reserved = 310 entries      (and 'helper' is not among them)
```

So for `helper`, **every clause passes** — yet it is not renamed. The
`startswith("_")` clause explains `_priv` and nothing else in the failing set.

Two facts that must both be true and are not:

1. the condition admits `helper`;
2. the output contains `def helper(`.

## What that means

Either the `if` body does not reach its rename for module-level functions, or the
name is rewritten and then **rewritten back**, or the emitted `def helper(` comes
from a path that bypasses the renamer entirely — a copy of the original source
concatenated after the transformed tree.

That third possibility is worth checking first, because the earlier `_MOD_SRC`
inspection showed `__all__` at the top of the output followed by `def foo():`
with the **original formatting**, including a blank line the AST unparser would
not normally produce.

## Established vs not

| claim | status |
|---|---|
| `protected_functions` is empty | confirmed |
| `helper` is not reserved | confirmed |
| the condition's clauses all pass for `helper` | confirmed by reading |
| functions are not renamed in the output | confirmed |
| **why** | **not established** |

## The next step, unchanged

Check whether the output contains the original source verbatim — search for a
second `__all__` assignment or a duplicate module body. If the emitted artefact is
the transformed tree **plus an untouched copy**, no renamer change would fix it
and the eleven failures have a completely different cause from the one this
document has been pursuing.
