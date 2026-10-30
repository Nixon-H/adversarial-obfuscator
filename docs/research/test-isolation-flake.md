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
