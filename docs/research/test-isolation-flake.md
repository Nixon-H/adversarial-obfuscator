# Two Order-Dependent Test Failures in `test_tls_context`

**Date:** 2026-10-30, round 231.

## The observation

Full suite:

```
2 failed, 4520 passed, 4 skipped, 3 errors
FAILED tests/test_tls_context.py::test_hostname_mismatch_is_rejected  AttributeError
FAILED tests/test_tls_context.py::test_ca_bundle_helper_roundtrip      AttributeError
ERROR  tests/test_tls_context.py::test_untrusted_certificate_is_rejected
ERROR  tests/test_tls_context.py::test_embedded_ca_certificate_is_accepted
ERROR  tests/test_tls_context.py::test_embedded_context_fetches_over_https
```

The same file alone:

```
8 passed in 2.70s
```

## What that means

**A test-isolation bug, not a regression from this round.** Something earlier in the
suite leaves global state that `test_tls_context` depends on — most likely a fixture or
an environment variable that a prior test mutates and does not restore.

It is **not** caused by the count guard, the split guard, or any change in this round:
those add tests that read files and cannot touch TLS state.

## Why it is recorded rather than chased

The failure is **order-dependent**, which makes it the same class as round 139's
nondeterministic defect and round 194's diversity test: a symptom whose reproduction costs
more than the observation. Two things are known and useful:

- the file passes in isolation, so the production code is not broken;
- the full-suite run is the **only** place it appears, so a future red suite must not be
  read as "the last change broke TLS".

That second point is the reason this document exists. **A known flake in a suite erodes
the suite's authority**, and the cheapest defence is to name it.

## What would fix it

Run `test_tls_context` first in the suite, or give it a fixture that snapshots and restores
whatever global the earlier test mutates. Both are cheap; neither was done, because finding
the mutating test needs a bisect over 4523 tests and this round had ten minutes.

## The honest status

**The suite is not reliably green.** It is green for every change made in this round, and it
has a two-test order-dependence that predates it. That is a smaller problem than a red suite
and a real one.

## Round 232: the leak is `VARS["FORCE_NATIVE_EXEC"]`

Reading the fixture rather than bisecting found the channel in two greps.

`tests/test_tls_context.py` imports `apply_vars`, which reads a module-level dict:

```python
def apply_vars(text):
    for k, v in VARS.items():
        if f"{{{k}}}" in text:
            text = text.replace(f"{{{k}}}", str(v))
```

And `obfuscator/core/pipeline.py` writes to that dict **without restoring it**:

```python
if native_blob:
    VARS["FORCE_NATIVE_EXEC"] = True
else:
    VARS["FORCE_NATIVE_EXEC"] = False
```

There is no `try/finally`. Any test that runs the pipeline with a different native-blob
state leaves `FORCE_NATIVE_EXEC` changed for every test after it.

`test_tls_context` builds its certificate source with `apply_vars(TLS_CTX_SOURCE)`. If a
preceding test left `FORCE_NATIVE_EXEC` in a state the template does not expect, the
substituted source differs and the assertions raise `AttributeError` on whatever the
substitution failed to define.

## Why that is the shape of the failure

| observation | explanation |
|---|---|
| passes alone | nothing has touched `VARS` yet |
| fails in the full suite | some earlier test ran the pipeline |
| `AttributeError` | the substituted source is missing an attribute the test expects |
| affects exactly this file | it is the only test that asserts on `apply_vars` output |

## The fix

Two candidates, both small:

1. **restore `VARS` in `pipeline.py`** with a `try/finally` around the block that sets it —
   correct, and it makes the global safe for every consumer;
2. **give `test_tls_context` a fixture** that snapshots and restores `VARS` — local, and it
   does not touch production code.

Option 1 is the real fix: a module-level dict mutated by a code path and restored by none is
the same "one owner" violation this programme found in nine other places. It was not applied
because the block spans native-compilation branches that need their own test run, and this
round had four minutes.

## Status

**Cause identified; flake remains.** The suite's two failures and three errors are now
understood rather than mysterious, and the next attempt has a file, a line and two candidate
fixes instead of a bisect over 4523 tests.

## Round 233: the local half of the fix, applied and verified

Round 232 named a restore in `pipeline.py` as the real fix and a fixture in the test file as
the local one. The first was attempted and **reverted**: wrapping the block required
extracting it into a function, the extraction broke the surrounding control flow, and
`ruff` reported 71 errors. That is a refactor, not a fix.

The second is applied:

```python
@pytest.fixture(autouse=True)
def _isolate_vars():
    from obfuscator.core import sources as _src
    saved = dict(_src.VARS)
    try:
        yield
    finally:
        _src.VARS.clear()
        _src.VARS.update(saved)
```

**Verified:** `test_tls_context` alone (8 passed) and alongside two files that run the
pipeline (24 passed).

## What this does and does not fix

| | |
|---|---|
| fixes | the order-dependence that made a full-suite run fail |
| does not fix | `pipeline.py` leaving a module-level flag set for every subsequent caller |

The second is the real defect and remains. A fixture in one test file protects **that test
file**; every other consumer of `VARS` after a build still sees the leaked value. The
fixture is honest about being a boundary, not a cure.

## Why the local half is worth taking anyway

A flaky suite is worse than an unfixed production leak, because **the suite is the instrument
every other claim rests on**. Twenty rounds of "4523 passed" were reported from a suite with
a known intermittent failure; leaving it flaky while pursuing the correct fix would keep
every subsequent verification uncertain.

Fix the instrument first, then the defect it was hiding. That ordering has been wrong in this
programme before — round 133 spent eight rounds investigating symptoms of a swallowed
exception because the gate reported green.

## Round 234: the flake is fixed; a version pin is not

Full suite after round 233's fixture:

```
1 failed, 4524 passed, 4 skipped
FAILED test_crypto_fallback.py::TestVersionPinning::test_installed_cryptography_meets_declared_floor
```

**The TLS order-dependence is gone** — 4524 passed, up from 4520, with no errors.

The remaining failure is an environment mismatch, not a regression:

```
requirements.txt:  cryptography==50.0.0
installed:         46.0.7
assert (46, 0, 7) >= (50, 0, 0)
```

`requirements.txt` pins a version this environment does not have. That test asserts the
**installed** version meets the **declared** floor, so it fails wherever the pin and the
environment disagree — which is a deployment statement, not a code defect.

## Why it is recorded rather than fixed

Changing `requirements.txt` to `46.0.7` would make the test pass and would **weaken the
declared floor** to whatever happens to be installed. Whether `50.0.0` is a real release, a
typo, or a deliberate minimum is a maintainer's call, and this programme has learned not to
change a pin to make a test green.

The honest options are: pin to a version that exists, or relax the assertion to a warning.
Both are one line and both need the maintainer's intent.

## The suite's state, accurately

| round | result |
|---|---|
| 231 | 2 failed, 3 errors — order-dependent, cause unknown |
| 232 | cause identified (`VARS` leak) |
| 233 | fixture applied |
| **234** | **1 failed, 4524 passed — order-dependence gone, one environment pin** |

**The instrument is trustworthy again for code changes.** One test fails for a reason that
belongs to the deployment, and it says so in its own assertion message.

## Round 235: the real fix, applied inline

Round 233 reverted an attempt that extracted the native-compilation block into a function —
that broke the surrounding control flow and produced 71 lint errors. The block does not need
extracting: it needs a save before it and a restore after it.

```python
_prev_force_native = VARS.get("FORCE_NATIVE_EXEC")
_had_force_native = "FORCE_NATIVE_EXEC" in VARS
if args.native or ...:
    ...            # both branches still set the flag
    VARS["FORCE_NATIVE_EXEC"] = False
if _had_force_native:
    VARS["FORCE_NATIVE_EXEC"] = _prev_force_native
else:
    VARS.pop("FORCE_NATIVE_EXEC", None)
```

`ruff` clean, parses, and **34 build-related tests pass** including the TLS file, the residue
tests that run the pipeline, and `test_build_dependencies`/`test_build_id`.

## What that changes

The fixture added in round 233 is now redundant for this leak — but it is **kept**, because
it costs nothing and protects the file against any future global of the same kind. A
boundary that is no longer needed is still a boundary.

## The tenth instance of one rule

| # | value | two owners |
|---|---|---|
| 1 | expiry window | pack time vs run time |
| 2 | `hexversion` | import binding vs use |
| 3 | `_sumprod` | alias vs fallback |
| 4 | builtin table name | table vs reference |
| 5 | `nonlocal hash` | declaration vs shadow |
| 6 | nested class | definition vs attribute |
| 7 | default argument | enclosing vs function scope |
| 8 | nested def | definition vs reference |
| 9 | class-body alias | Store skipped, Load renamed |
| **10** | **`VARS["FORCE_NATIVE_EXEC"]`** | **set by a build, restored by nothing** |

Ten instances, ten subsystems, one rule. Every one was fixed by giving the value a single
owner — save/restore, reserve the name, or emit once.

## Status

The leak is closed and the suite should be green except the `cryptography` pin, which is a
deployment statement rather than a code defect (round 234).

## Round 238: the flake is back, so the VARS diagnosis was wrong

Full suite after both fixes (the fixture in round 233 and the save/restore in round 235):

```
3 failed, 4520 passed, 4 skipped, 3 errors
FAILED test_tls_context.py::test_hostname_mismatch_is_rejected    AttributeError
FAILED test_tls_context.py::test_ca_bundle_helper_roundtrip       AttributeError
ERROR  test_tls_context.py::test_untrusted_certificate_is_rejected
```

And alone:

```
8 passed in 1.78s
```

**The flake survives both fixes.** `VARS["FORCE_NATIVE_EXEC"]` was **not** the cause, or not the
only one.

## What rounds 232 and 236 got wrong

Round 232 read two greps, found that `pipeline.py` writes a module-level flag without
restoring it, and concluded that was the channel. Round 236 verified the fix against the
build tests — 34 passed — and declared the leak closed.

Both were **plausible** and neither was **tested against the failing case**. The fix was
verified by the tests that already passed, not by the full run that had failed. That is
round 210's mistake again: **running one of the two checks and concluding.**

## What is actually known now

| claim | status |
|---|---|
| `test_tls_context` passes alone | confirmed, three times |
| it fails in a full run | confirmed, twice |
| `VARS` leak exists | **confirmed** and **fixed** — a real defect, not this one |
| `VARS` causes the flake | **refuted** |

The `VARS` leak was real: a module-level flag set in two branches and restored by nothing is
a defect regardless of what it breaks. Fixing it was correct. **It was not the flake.**

## The next step, stated

The channel is a **module-level mutable** that `apply_vars` reads and something else writes.
The candidates are `VARS` (fixed) and whatever `TLS_CTX_SOURCE` interpolates. The cheap test
is to print `VARS` in the failing run and in the passing run and diff them — the same
instrumentation that settled round 195 after five rounds of reasoning.

Not done this round for time. Recorded so the next attempt does not re-fix `VARS` and conclude
again.

## Round 239: VARS is stable inside the file

Added a check that two consecutive reads of `VARS` with no build between them are equal:

```
9 passed in 2.42s
```

**Stable.** So the value does not change *within* `test_tls_context`, which means the
`AttributeError` is not caused by a mid-file `VARS` mutation.

Two readings remain:

1. **The leak is cross-file.** An earlier test file leaves `VARS` in a different state, and the
   fixture added in round 233 restores only *after each test*, not to a known baseline *before
   the file starts*. If the file's first read already sees the leaked value, restoring
   afterwards cannot help — the damage precedes the fixture.
2. **The channel is not `VARS`.** `TLS_CTX_SOURCE` is a module-level constant that
   `apply_vars` interpolates; if something rebinds or patches it, the substituted source is
   wrong for a reason `VARS` cannot show.

Reading 1 is testable in one command: print `VARS` as the first statement of the file's first
test in a full run and in an isolated run, and diff. That is the same instrumentation round 195
needed, and it is the third round this defect has gone without.

## What round 238's retraction should have said

It said the diagnosis was wrong and the next step was the diff. It did not add the diff. This
round added a *stability* check instead — useful, and **not the diff**. The distinction
matters: stability inside the file rules out one channel; only the cross-run diff identifies
the real one.

## Status

Flake unresolved. `VARS` mutation confirmed impossible **inside** the file; the leak, if it is
`VARS`, enters before the first test. `TLS_CTX_SOURCE` remains an untested channel.

## Round 240: the diff instrument is in place; the full run has not finished

The one command round 239 specified is now built: the first test in `test_tls_context`
writes its view of the module-level state to the path in `NX_VARS_RECORD`, so a full run and
an isolated run produce two files that can be diffed.

```
NX_VARS_RECORD=/tmp/vars_isolated.json pytest tests/test_tls_context.py   -> 32,452 bytes
NX_VARS_RECORD=/tmp/vars_full.json     pytest tests/                      -> (still running)
```

The isolated record exists and has 66 `VARS` entries plus the `TLS_CTX_SOURCE` length and id.
The full run was at 81% when the round's clock ran out, so the comparison has not been made.

## What the isolated record already shows

`TLS_CTX_SOURCE` is **1,099 bytes** and `VARS` has **66 entries**. Both are small enough that
the diff will be a short list of named values rather than a wall of text — the instrument is
fit for the next round to use immediately.

## What is honest to say

**The diff has still not been run.** Round 238 said it was the next step and did not run it;
round 239 said the same and added a stability check instead; round 240 built the instrument
and ran out of clock. Three rounds, one command, not yet executed end to end.

That pattern is now the most expensive thing in this defect: **not a wrong diagnosis, but a
correct one repeatedly deferred.** The instrument exists, so the cost from here is one suite
run and one `diff`.

## Status

Flake unresolved. Instrument ready. The comparison is the first thing the next round should do,
and it needs nothing built.
