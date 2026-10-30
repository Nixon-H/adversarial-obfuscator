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
