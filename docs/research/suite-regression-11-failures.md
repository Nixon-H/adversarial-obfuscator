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
