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

`remote-cloudflare=DIR` additionally writes a deployable Cloudflare Python
Worker project. The worker is serverless but still server-side: it contains
the confidential implementations inside the operator-controlled Cloudflare
account, verifies protocol-v1 HMAC requests, supports customer-bound derived
credentials, requires two independent RFC 6238 TOTP codes, and uses a
SQLite-backed Durable Object for nonce replay, accepted-request rate limiting,
daily quota accounting, HMAC-valid TOTP-failure throttling, and verified-code-pair replay limitation. `remote-cloudflare-name=NAME` overrides the
default worker name. The generated `DEPLOYMENT.md` contains exact provisioning
and deployment steps. Confidential implementations are isolated in
`src/remote_impl.py` so they cannot collide with service-runtime helper names.
Dual TOTP is enforced by the Cloudflare Worker, not by the self-hosted Rust
reference relay.

The recommended worker mode stores only `NIXON_REMOTE_MASTER_SECRET`. The
provisioning utility derives an independent HMAC secret and two independent
TOTP seeds for every customer ID. Customers receive only their derived
credentials. Shared-secret mode remains available only through explicit
`NIXON_REMOTE_ALLOW_SHARED=1` compatibility configuration and is not
recommended for new deployments.

Runtime configuration:

| variable | security meaning |
|---|---|
| `NIXON_REMOTE_URL` | Remote-function endpoint. Network endpoints must be HTTPS; plain HTTP is accepted only for the loopback reference relay or local development service. |
| `NIXON_REMOTE_SECRET` | 64-hex HMAC key held by the client. In customer-bound Cloudflare mode it is derived per customer; in legacy shared mode it is shared. It authenticates requests but is not a confidentiality boundary against the customer machine. |
| `NIXON_REMOTE_CUSTOMER_ID` | Non-secret customer/deployment identity sent as transport metadata. It is never forwarded to the remote implementation as an application kwarg. |
| `NIXON_REMOTE_MASTER_SECRET` | **Worker-only** 64-hex master secret used to derive per-customer HMAC secrets and TOTP seeds. It must never be placed in a customer artifact or environment. |
| `NIXON_REMOTE_ALLOW_SHARED` | Explicit compatibility opt-in for the original shared-secret Cloudflare mode. Not recommended for new deployments. |
| `NIXON_REMOTE_TOTP_SECRET` | Legacy shared-mode worker-only primary base32 TOTP seed. Not used in recommended customer-bound mode. |
| `NIXON_REMOTE_TOTP2_SECRET` | Legacy shared-mode worker-only secondary independent base32 TOTP seed. Not used in recommended customer-bound mode. |
| `NIXON_REMOTE_DISABLED_CUSTOMERS` | Worker-side comma-separated static revocation list. |
| `NIXON_REMOTE_RATE_LIMIT_PER_MINUTE` | Worker-side accepted-request fixed-window rate limit per customer; default 60. |
| `NIXON_REMOTE_QUOTA_PER_DAY` | Worker-side accepted-request fixed-window daily quota per customer; default 10,000. |
| `NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE` | Worker-side fixed-window budget for HMAC-valid TOTP failures per customer; default 10. Successful dual-TOTP authentications decrement their provisional attempt and do not consume this budget. |
| `NIXON_REMOTE_TOTP_PAIR_MAX_USES` | Worker-side maximum number of requests permitted with one verified TOTP code pair during its short replay window; default 1. Raising it improves burst usability but weakens capture containment. |
| `NIXON_REMOTE_TOTP` | Optional first six-digit authenticator code for controlled non-interactive tests. It expires quickly and must not be treated as a static production secret. |
| `NIXON_REMOTE_TOTP_SECONDARY` | Optional second independent six-digit authenticator code for controlled non-interactive tests. |
| `NIXON_REMOTE_TOTP_PROMPT` | When `1`, interactive clients prompt for the Google Authenticator and Microsoft Authenticator codes if no per-call codes were supplied. |
| `NIXON_REMOTE_APPROVAL_MODE` | Worker-side phone-approval policy: `enrolled` (default; approval required once the customer has an enrolled device key), `required` (fail closed until enrolment), or `off` (typed TOTP only). |
| `NIXON_REMOTE_APPROVAL_EXPIRY_SECONDS` | Worker-side lifetime of a pending approval request; default 120. |
| `NIXON_REMOTE_MAX_PENDING` | Worker-side cap on concurrent pending approval requests per customer; default 8. |
| `NIXON_REMOTE_TOTP_WITH_APPROVAL` | When `1`, typed dual TOTP remains required in addition to phone approval as defense-in-depth. Default off because request-bound approval is strictly stronger than typed codes. |
| `NIXON_REMOTE_APPROVAL_TIMEOUT` | Client-side ceiling in seconds for approval polling before failing closed; default 150. |
| `NIXON_REMOTE_RP_ID` | Worker-side WebAuthn relying-party identifier used to verify passkey assertions. Defaults to the request Host header (port stripped), which is correct when the approval page is opened on the worker's own domain; pin it explicitly when the page is served through a custom domain or alias. |
| `NIXON_VAPID_PUBLIC` | Worker-side VAPID public key (base64url) enabling browser push subscriptions on the approval page. Without it the page skips push enrolment entirely. |
| `NIXON_VAPID_PRIVATE` | Worker-side VAPID private key (base64url) used to sign payload-less push tickles. Owner-only; never present in customer artifacts. |
| `NIXON_VAPID_SUBJECT` | Worker-side VAPID subject (`mailto:` or URL) required by push services; defaults to a placeholder and should be set to operator contact. |
| `NIXON_REMOTE_ANOMALY` | Worker-side anomaly detection switch; default enabled. Set `0`/`false`/`off` to disable. Detection is alert-only: it never blocks execution. |
| `NIXON_REMOTE_ANOMALY_MAX_APPROVALS` | Approvals within the sliding window at or above which the high-velocity anomaly fires; default 5. |
| `NIXON_REMOTE_ANOMALY_WINDOW_SECONDS` | Sliding window in seconds for approval-velocity detection; default 600. |

## Alert-only anomaly detection

Two approval-time signals are tracked per customer inside the Durable Object
and surface in three places: machine-readable `anomalies` tags on pending-list
items, a visible warning card in the approval page at decision time, and
`outcome: "anomaly"` audit events whose detail contains only fixed tags.

- `novel-function` — the function has never been approved for this customer.
  A function becomes operator-vouched only through an approval; denials leave
  it novel, so a repeatedly re-requested unknown function keeps alerting
  instead of being silently legitimised.
- `high-velocity` — approvals within the sliding window reached the configured
  threshold. Detection precedes recording, so a burst is judged against prior
  history rather than inflating its own baseline.

This is deliberately detection without enforcement: every alert still requires
the same user-verified passkey decision, and false positives can never lock
out legitimate use. The value is concentrated in the approval page warning —
the human approver is the last control that cannot be cryptographic, and the
warning is the machine's only channel for telling them something is unusual
before they sign. Enforcement tiers (cooling-off holds) remain possible future
work behind explicit operator opt-in.

Current operator-bundle limitation: the bundle contains the marked function
implementations, not arbitrary module-level helper functions or constants.
Marked functions must therefore be self-contained or import their dependencies
inside the function body. Reads of unbundled module globals are statically
rejected. Unsupported shapes (nested functions, async functions, duplicate
names, indirect markers, and combined decorators) also fail the build closed
rather than silently changing semantics.

Operational boundary: moving a function server-side prevents artifact
extraction from revealing that function's implementation. Customer-bound
credentials, static and dynamic revocation, fixed-window rate limits, daily
quotas, TOTP-failure throttling, request-bound phone approval, and
metadata-only audit events are implemented server-side controls. They limit
blast radius and abuse, but do not make a compromised endpoint trustworthy.
For customers with an enrolled approval device, typed-code capture and
request-independent piggybacking are fixed: no copyable secret transits the
customer machine, and the phone's ECDSA signature binds exactly one displayed
request. Approval still does not prove host integrity, cannot stop a deceived
user from approving a malicious operation, and relies on single-use enrolment
tokens being delivered without interception. Unmarked client-side logic
remains extractable.

Cloudflare deployment boundary: Cloudflare and anyone with access to the
Cloudflare account are trusted infrastructure. The free tier is suitable for
lightweight remote functions, not heavy computation or tight client loops.
The implementation must remain out of customer artifacts, repositories, logs,
and deployment output.
