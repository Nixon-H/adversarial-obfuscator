# Cloudflare passkey (WebAuthn) approval validation — 2026-11-27

Runtime: real local Python Workers runtime via `pywrangler dev` / wrangler (not mocks).

Result: **23/23 checks passed**.

| check | outcome |
|---|---|
| approval page served | PASS |
| page has no raw NUL | PASS |
| page carries visible escape | PASS |
| page requires user verification | PASS |
| unenrolled legacy TOTP executes | PASS |
| passkey enrolment accepted | PASS |
| enrolment token single-use | PASS |
| tampered enrolment proof rejected | PASS |
| enrolled RPC pends without TOTP | PASS |
| valid TOTP does not bypass approval | PASS |
| pending list shows requests | PASS |
| assertion without UV rejected | PASS |
| UV approval accepted | PASS |
| decision response carries pending list | PASS |
| approved result correct | PASS |
| result delivered exactly once | PASS |
| denial accepted | PASS |
| denial propagated to client poll | PASS |
| wrong-RP assertion rejected | PASS |
| admin list keys works | PASS |
| admin revoke key works | PASS |
| revoked key cannot list pending | PASS |
| revoked key cannot approve | PASS |

Worker log scan: no master secret, HMAC secret, TOTP seeds, or enrolment tokens present.

Scope: soft-authenticator produced real WebAuthn attestation/assertion wire shapes end-to-end through the actual runtime's FFI crypto. A physical-phone browser ceremony was not performed; the browser side uses standards-defined `navigator.credentials` calls, but manual device testing is still recommended before production use.
