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

## Server-side split execution

`--transforms remote remote-bundle=PATH` is the architectural remediation path
for genuinely confidential functions. A module-level function marked
`@remote` is removed before native compilation, AST mutation, farm upload, or
loader embedding. The client artifact carries only a self-contained network
stub; the implementation is written to the operator bundle at `PATH`, which is
mode `0600` and must never ship.

Runtime configuration:

| variable | security meaning |
|---|---|
| `NIXON_REMOTE_URL` | Remote-function endpoint. Network endpoints must be HTTPS; plain HTTP is accepted only for the loopback reference relay. |
| `NIXON_REMOTE_SECRET` | 64-hex HMAC key shared by the client and operator service. It authenticates requests; it is not a confidentiality boundary against the customer machine. |

Current operator-bundle limitation: the bundle contains the marked function
implementations, not arbitrary module-level helper functions or constants.
Marked functions must therefore be self-contained or import their dependencies
inside the function body. Reads of unbundled module globals are statically
rejected. Unsupported shapes (nested functions, async functions, duplicate
names, indirect markers, and combined decorators) also fail the build closed
rather than silently changing semantics.

Operational boundary: moving a function server-side prevents artifact
extraction from revealing that function's implementation. It does not prevent
a customer-machine attacker from invoking the service as an oracle while they
possess valid client configuration, and it does not protect functions left
client-side. The operator service must enforce its own deployment, rate-limit,
accounting, and revocation policy.
