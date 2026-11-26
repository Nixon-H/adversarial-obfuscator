# Maximum Security addendum — farm repository retention

**Status:** current companion to `MAXIMUM_SECURITY.md`, 2026-11-27. The base
document is operator-frozen; new parser surface is documented here so the
inventory remains complete without rewriting that file.

## Build flags

| flag | security meaning |
|---|---|
| `--keep-farm-repo` | Retains the disposable cloud-build farm repository for debugging. This is **not recommended** and is excluded from maximum-security recipes because the repository contains the uploaded payload source. Default behavior deletes the repository after use. |
| `--public` | Deprecated legacy alias. It no longer changes behavior because disposable farm repositories are deleted by default; use `--keep-farm-repo` only for deliberate debugging retention. |

Operational rule: do not use `--keep-farm-repo` in a release build. If it is
used for debugging, treat the retained repository as sensitive source-bearing
evidence and delete it as soon as the investigation ends.

## Environment variables

| variable | security meaning |
|---|---|
| `NIXON_SOURCE_COMMIT` | Explicit 40-hex source revision for VCS-less builds, such as Docker source copies or sdists. It is provenance metadata, not secret material. |
| `NIXON_TEST_TIMEOUT` | Test-harness housekeeping only: per-test wall-clock budget in seconds. It has no product-security effect and must not be used to weaken runtime behavior. |
