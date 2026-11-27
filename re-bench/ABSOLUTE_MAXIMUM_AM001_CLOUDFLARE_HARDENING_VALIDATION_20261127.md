# AM-001 Cloudflare customer-bound hardening validation — 2026-11-27

## Scope

This evidence validates the hardened generated Cloudflare Python Worker in the
real local Workers runtime (`uvx --from workers-py pywrangler dev`, Wrangler
4.168.0 generation). It is stronger than the unit-test SQL doubles because the
Worker, Python module attachment, Durable Object binding, SQLite usage accounting,
and client transport were exercised over loopback HTTP.

It does **not** validate public Cloudflare deployment, a real Cloudflare account,
real authenticator enrolment on physical devices, production abuse resistance,
Cloudflare free-tier behavior under load, host integrity, or FIDO2/passkey
approval. No public deployment was performed.

## Configuration under test

- customer-bound mode using worker-only `NIXON_REMOTE_MASTER_SECRET`
- distinct derived credentials for `acme`, `brute`, `revoked`, and `quota-cust`
- dual independent derived TOTP seeds per customer
- static revocation list containing `revoked`
- test minute rate limit and daily quota configured low enough to exercise
  enforcement with a small number of live requests
- test HMAC-valid TOTP failure limit configured to two for the isolated
  `brute` customer
- positive burst/quota phases used an explicit controlled multi-use TOTP pair
  allowance; a separate strict single-use phase validated pair-replay rejection

## Results

| check | meaning | result |
|---|---|---|
| `direct_valid_result_correct` | direct valid customer-bound request returned the expected remote result | PASS |
| `embedded_client_result_correct` | embedded split-client request returned the expected remote result | PASS |
| `exact_replay_rejected` | exact replay was rejected | PASS |
| `tampered_args_rejected` | tampered arguments were rejected by HMAC verification | PASS |
| `stale_timestamp_rejected` | stale timestamp was rejected | PASS |
| `missing_customer_rejected` | customer-bound mode rejected a request without customer identity | PASS |
| `cross_customer_credential_rejected` | one customer credential could not be used under another customer identity | PASS |
| `missing_totp_rejected` | missing primary TOTP was rejected despite a valid HMAC signature | PASS |
| `wrong_second_totp_rejected` | wrong secondary TOTP was rejected despite a valid HMAC signature | PASS |
| `revoked_customer_rejected` | statically revoked customer was rejected | PASS |
| `implementation_exception_generic` | implementation exception details were not returned to the client | PASS |
| `rate_limit_allows_configured_window` | requests within the configured minute window succeeded | PASS |
| `rate_limit_rejects_after_window` | request after the configured minute window was rate-limited | PASS |
| `daily_quota_enforced` | request after the configured daily quota was rejected | PASS |
| `totp_failure_limit_enforced` | HMAC-valid TOTP guessing was throttled after the configured failure budget | PASS |
| `totp_pair_reuse_rejected` | reuse of one verified TOTP code pair with a different nonce was rejected in strict single-use mode | PASS |
| `client_implementation_absent` | client artifact did not contain the implementation marker/coefficient material | PASS |
| `operator_implementation_present` | operator implementation module contained the confidential implementation | PASS |
| `worker_logs_avoid_secrets_args_and_exception_messages` | worker logs avoided secrets, argument values, and implementation exception messages | PASS |

Aggregate: **ALL CHECKS PASSED**. Machine-readable evidence:
`ABSOLUTE_MAXIMUM_AM001_CLOUDFLARE_HARDENING_VALIDATION_20261127.json`.

## Security interpretation

The controls validated here are complete within their narrow server-side scope:
customer credential separation, revocation, replay rejection, fixed-window
rate/quota enforcement, TOTP-failure throttling, and metadata-only audit/error
handling. They do not turn a compromised customer machine into a trusted host.
Typed TOTP remains capturable and is not request-bound; the server cannot prove
physical authenticator-device separation; unmarked client-side plaintext remains
extractable; Cloudflare remains trusted infrastructure. The documented future
improvement for stronger approval is request-bound FIDO2/passkey authentication,
but that requires platform/hardware integration and was not claimed or
validated here.
