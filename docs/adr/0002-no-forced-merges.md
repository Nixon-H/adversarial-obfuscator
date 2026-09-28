# ADR 0002 — No Forced Merges

## Context

`master` is the only supported checkout (see `SECURITY.md`), and CI
runs the expensive matrix (Python 3.10–3.14, Rust runtime + relay,
C shared libs) on every push and pull request. A forced merge
(`--force` push, force-merge of a red PR, landing without CI) would
silently void every invariant the test-suite enforces — including the
security invariants in `tests/test_security_invariants.py`.

## Decision

No forced merges to `master`. All changes land via push/PR **with a
green CI run** (`.github/workflows/ci.yml`: `on: [push, pull_request]`,
matrix `python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]`).
No `--force` pushes, no merging over red checks, no direct landing of
unreviewed security-gate changes.

## Alternatives considered

- **Merge queue / required-checks branch protection.** Desirable but
  server-side state: could not be confirmed from this tree
  (UNVERIFIED). Adopt if hosting supports it; this ADR is the policy
  until then.
- **Allow force-pushes for history hygiene.** Rejected: a rewritten
  `master` invalidates every pinned reference (docs cite
  `file:line`, audits cite commits). Hygiene is not worth breaking
  the evidence chain.

## Consequences

- Occasionally slower landings (wait for the full matrix).
- Every security-relevant change has a CI receipt tying it to the
  3.10–3.14 matrix and the invariant tests.
- Positive: `git log` on `master` stays a linear, auditable record
  (e.g. recent reaudit checkpoints `9e0762d`, `325a8a8`).

## Evidence

- CI trigger + matrix: `.github/workflows/ci.yml` (`on: [push,
  pull_request]`, `python-version: ["3.10", …, "3.14"]`).
- Supported-version floor the matrix protects:
  `obfuscator/nyser.py:50`, `obfuscator/py_matrix.py:29`,
  `scripts/build.py` floor `sys.version_info < (3, 10)`.
