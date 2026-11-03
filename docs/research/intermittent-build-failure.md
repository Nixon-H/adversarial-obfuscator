# Intermittent build failure: one artefact in ~24 emits nothing and exits 1

**Date:** 2026-11-03. Found by the OS x Python x configuration matrix in CI.

## What happened

The `config 2sections-3zips-L3` job (ubuntu, py3.13, `--portable --section-count 2 --zips 3
--opt-level 3`) built an artefact that:

- exited **1**
- printed **nothing** on stdout
- printed **nothing** on stderr

The other 23 jobs in the same matrix passed. Re-running the failed job **passed**. Five local
rebuilds of the same configuration **all passed**.

## What that means

**The builder is not deterministic, and occasionally emits an artefact that fails silently.**

This is not the same as the defects fixed earlier: those reproduced every time. This one appeared
once in 24 CI jobs and did not reproduce in 6 attempts (1 CI re-run + 5 local).

Rate is therefore roughly **1 in 10 to 1 in 30 builds**, which is exactly the range that gets
dismissed as "flaky" and is exactly the range that ships.

## Why it is hard to catch

- exit code 1 with no output means the failure path did not use `os.write(2, ...)`, so it is not the
  self-integrity check (that one now prints its reason) and not the kill ladder (that one exits 137).
- An uncaught exception would print a traceback, so the exception was caught somewhere that discards
  it.
- Both the debug and silent variants are produced; the checker runs `demo_protected.py`.

## What to try next

1. Build in a loop (30-50 iterations) of exactly this configuration and capture the failing artefact
   bytes when it happens, then diff it against a passing build.
2. If the failing build is reproducible from its seed, the seed names the bug.
3. If it is not, instrument the build to log the seed and the section/zip parameters for every run,
   so a failure is always attributable.

**Not fixed. Recorded so the next attempt does not start from "it passed on retry, so it is fine".**
