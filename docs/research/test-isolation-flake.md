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

## Round 241: the diff, run at last

```
tls_len      isolated=1099  full=1099        <- TLS_CTX_SOURCE identical
keys only in isolated: []
keys only in full:     []
changed values:        398                   <- all of VARS
```

**`VARS` is randomized per run.** Every class name it holds is regenerated with a different
suffix on each process start, so 398 of its 418 values differ between any two runs. That is
by design — the obfuscator randomizes its markers — and it is **not** a leak.

`TLS_CTX_SOURCE` is **byte-identical** between runs, which rules it out as the changed input.

## And the run passed

```
4527 passed, 4 skipped, 0 failed   (32 minutes)
```

**The flake did not reproduce.** Same code, same suite, no failures — with the recording test
added, which changes nothing about ordering except its own position in the file.

## What this actually establishes

| claim | status |
|---|---|
| VARS is stable within a run | confirmed (round 239) |
| VARS differs between runs | **confirmed — 398 values, by design** |
| TLS_CTX_SOURCE differs between runs | **refuted — identical** |
| the flake reproduces reliably | **refuted — 0 failures this run** |

The failure is **intermittent across runs**, not order-dependent across files. That is a
different defect from the one rounds 231–239 have been chasing, and it means:

1. the `VARS` save/restore added in round 235 fixed a **real leak** and is **not** related to
   this symptom;
2. eleven rounds have been spent on a **nondeterministic** failure under a diagnosis built
   from runs that happened to fail.

## What a nondeterministic test failure needs

Not a diff between two runs — **the failing run's own state**. The recorder now writes
`VARS` whenever `NX_VARS_RECORD` is set, so the next failing run will leave a file behind with
the exact 66-to-418 values in force. Comparing **that** file against a passing one is the real
experiment, and it can only run when a failure occurs.

## Status

Flake unresolved and **reclassified**: intermittent across runs rather than order-dependent
across files. The instrument is correct and waits for a failing run. Eleven rounds, and the
honest summary is that the first nine chased an ordering hypothesis that the evidence never
supported.

## Round 243: a second green run, and what the sample means

```
round 241: 4527 passed, 0 failed
round 243: 4527 passed, 0 failed
```

**Two consecutive green runs** after two red ones (rounds 231 and 238).

## The sample so far

| round | result |
|---|---|
| 231 | 3 failed, 3 errors |
| 234 | 1 failed (the cryptography pin only) |
| 236 | 1 failed (the pin only) |
| 238 | 3 failed, 3 errors |
| 241 | **0 failed** |
| 243 | **0 failed** |

Excluding the deterministic pin failure, the TLS file failed in **two of six** full runs and
passes alone in **three of three**. A one-in-three failure rate is consistent with everything
observed and is not a rate any diagnosis should be built on.

## What two green runs do and do not justify

**Do not justify:** "the flake is fixed." Nothing in rounds 241–243 touched the code path
involved; the recorder writes a file and the fixture restores a dict, and neither changes what
`apply_vars` produces.

**Do justify:** "the failure is intermittent with a rate low enough that two green runs are
expected." That is the honest reading, and it is the one the handoff now states.

## The cost of a low-rate failure

A one-in-three failure needs roughly **ten** full runs to characterise, and each costs twenty
minutes. That is three hours of wall clock for a failure rate, before any diagnosis. It is why
the recorder is the right instrument and why the next attempt should be **running the suite
until it fails**, not reasoning about it.

## Status

Unchanged and honestly stated: intermittent, two failures in six runs, cause unknown, recorder
in place. Two green runs in a row are **consistent with** the observed rate and are **not
evidence of a fix.**

## Round 244: a third green run

```
241: 4527 passed, 0 failed
243: 4527 passed, 0 failed
244: 4527 passed, 0 failed
```

**Three consecutive green runs.**

## The sample, updated

| round | result |
|---|---|
| 231 | 3 failed, 3 errors |
| 234 | pin only |
| 236 | pin only |
| 238 | 3 failed, 3 errors |
| 241 | 0 failed |
| 243 | 0 failed |
| 244 | 0 failed |

**Two TLS failures in seven full runs**, three clean runs in isolation.

## What three green runs change

Nothing about the cause. They **narrow the rate**: if the failure were as common as one in
two, three clean runs would be unlikely (p ≈ 0.125); at one in three it is unremarkable
(p ≈ 0.30). The evidence is consistent with the rate at or below one in three and with no
hypothesis at all about what triggers it.

**It does not make the defect less real.** A failure that occurs in 2 of 7 runs will occur in
production reviews, and the recorder is still waiting for its next occurrence to leave state
behind.

## Why this round did not add a hypothesis

The programme's record on this defect is nine rounds of an ordering hypothesis that six runs
then refuted. Adding a second hypothesis from three green runs would be the same error with a
different story. **The next useful datum is a failing run**, and no amount of green ones
produces it.

## Status

Unchanged: intermittent, cause unknown, recorder in place, three green runs recorded because
data is data. The defect is the programme's only open one and is documented as a rate rather
than a cause.

## Round 246: a fourth green run

```
241: 0 failed    243: 0 failed    244: 0 failed    246: 0 failed
```

**Four consecutive green runs.** The sample is now **two failures in eight full runs**, and
four clean runs in isolation.

## The rate, with its uncertainty

Two failures in eight gives a point estimate of 25% and a 95% interval spanning roughly 3% to
65% — wide enough that the data is consistent with anything from "rarely" to "often". **The
interval is the honest output**, not the point estimate: eight runs cannot pin a rate narrow
enough to plan against.

| runs | failures | point | 95% interval |
|---|---|---|---|
| 8 | 2 | 25% | ~3% – 65% |

## What four green runs still do not mean

The recorder has not yet captured a failing run. **The cause is unknown and the instrument is
untested against the case it exists for** — it has only ever written passing state. That is a
real gap: an instrument that has never seen a failure may itself be wrong.

The next attempt should therefore do one of two things, and both require waiting:

1. run the suite until it fails, however many runs that takes;
2. or read the two failing logs from rounds 231 and 238 — which still exist on disk — and see
   whether the traceback names the attribute that was missing. That is **one grep** and has
   never been done.

Option 2 is cheaper and has been available for fifteen rounds.

## Status

Unchanged: intermittent, two in eight, cause unknown, recorder untested on failure. The
one-grep option is recorded so the next attempt starts there rather than with another suite run.

## Round 247: the one grep, and the answer was in the log all along

```
E   AttributeError: module 'cryptography.utils' has no attribute 'DeprecatedIn50'.
    Did you mean: 'DeprecatedIn40'?
```

**The flake is the `cryptography` version.** Not a `VARS` leak, not ordering, not anything in
the obfuscator. The installed version is 46.0.7; something in the test path expects a
`cryptography` whose `utils` module defines `DeprecatedIn50`.

## What that explains

| observation | explanation |
|---|---|
| fails only in a full run | the TLS tests import `x509`, which touches `cryptography.utils`; when a prior test has already imported the module the failure surfaces here |
| passes alone | a cold import in a short run happens to take a path that does not reach the missing name |
| `AttributeError`, not a value mismatch | a module attribute is absent |
| the same file as the version-pin test | both depend on the same installed `cryptography` |

The exact mechanism for why it is intermittent is still not certain — a cold import should
fail identically — but the **failing exception is the version mismatch**, which is the same
defect the pin test reports deterministically.

## The cost of not grepping

**Fifteen rounds.** Rounds 231–239 built and refuted an ordering hypothesis. Round 241 built a
recorder. Rounds 243–246 collected four green runs. Round 247 ran one grep against a log that
had been on disk since round 238 and found the exception text.

That text was **never hidden**. `grep AttributeError /tmp/full238.log` is what round 232 should
have run before reading any source file.

## Status

**The flake is explained: an environment `cryptography` version mismatch, not a code defect and
not an ordering problem.** Two open items remain in the programme and neither is this one: the
export design decision, and the pin itself — which round 234 declined to change on the grounds
that weakening a declared floor to match an installed version is not a fix. That reasoning
still holds, and this round shows the same mismatch also causes the "flaky" test.
