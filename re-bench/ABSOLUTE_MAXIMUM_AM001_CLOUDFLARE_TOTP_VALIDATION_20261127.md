# AM-001 Cloudflare Worker + dual-TOTP validation — 2026-11-27

**Status:** focused implementation validation, not a new adversarial benchmark
campaign and not a production Cloudflare deployment audit.

## Scope

This evidence validates the newly generated Cloudflare Python Worker target for
server-side split execution. The worker was generated from a payload containing
one confidential function:

```python
@remote
def hidden_pricing(x, scale=2):
    coefficient = 991
    return coefficient + x * scale
```

The generated worker ran locally through `pywrangler dev` / Wrangler `4.168.0`
with the Python Workers runtime and a local SQLite-backed Durable Object binding.
Test-only HMAC and TOTP seeds were supplied through `.dev.vars`; those values
are deliberately not recorded here.

This is stronger than a mock because the request passed through the real
worker startup, Python Worker runtime, generated Worker code, and Durable
Object plumbing. It is weaker than a production deployment validation because
it did not use a Cloudflare account, public HTTPS edge deployment, real
authenticator enrolment, or the operator's production secrets.

## Positive controls

| check | result |
|---|---|
| Direct valid protocol-v1 request with both fresh TOTP codes | `{"result": 1012}` |
| Embedded split-client call with `_nx_totp` and `_nx_totp_secondary` | `{"result": 1012}` |
| Durable Object binding initialized | yes; Wrangler reported `env.REPLAY (ReplayRegistry)` |
| Worker secret bindings initialized | yes; Wrangler reported the three hidden environment variables |

The expected value was `1012` because the test used `x=7`, `scale=3`, and the
server-side coefficient `991`.

## Negative controls

| check | observed response |
|---|---|
| Exact replay of the accepted request | `remote request replayed` |
| Tampered positional arguments without a valid replacement signature | `remote request signature mismatch` |
| Correctly signed but stale timestamp | `remote request expired` |
| Valid HMAC request missing the first TOTP code | `remote request authentication failed` |
| Valid HMAC request with a wrong second TOTP code | `remote request authentication failed` |

The missing/wrong-TOTP negative controls are important: the requests had valid
HMAC signatures, so rejection was caused by the additional server-side
authenticator gate rather than by transport-signing failure.

## Artifact boundary scan

| artifact | confidential coefficient name | confidential coefficient value | split marker/runtime import |
|---|---:|---:|---:|
| split client | absent | absent | absent |
| generated Cloudflare `src/remote_impl.py` | present | present | not applicable |

The generated worker implementation module was owner-only (`0600`). The
generated project also includes `pyproject.toml`, `wrangler.jsonc`, `.gitignore`,
and `DEPLOYMENT.md`; Wrangler attached `remote_impl.py` as an additional Python
module. No deployment-authentication secret is embedded in `wrangler.jsonc` or
the generated worker source.

## What this validates

- The generated modular Python Worker project is syntactically and operationally
  valid; runtime implementation code is isolated in `remote_impl.py` to avoid
  collisions with service-runtime helpers.
- `pywrangler dev` accepts the generated project when the required
  `pyproject.toml` is present.
- Protocol-v1 canonical HMAC verification interoperates with the existing
  Python client.
- The embedded client strips reserved TOTP kwargs before signing/dispatch and
  sends them as top-level authentication fields.
- The server rejects requests unless both independent TOTP factors are fresh.
- SQLite-backed Durable-Object nonce state rejects exact replay in the real
  local Workers runtime.

## What this does not validate

- No public Cloudflare deployment was performed; no Cloudflare account token or
  production secret was used.
- No Google/Microsoft Authenticator device enrolment was performed; test-only
  seeds were used locally.
- No adversarial benchmark artifacts were rebuilt or retroactively revalidated.
- Free-tier CPU, quota, abuse-resistance, rate-limiting, account identity, or
  production logging behavior was not measured.
- TOTP does not prove the customer machine is uncompromised. It is an additive
  oracle-access gate, not host attestation and not a replacement for server-side
  execution.

Machine-readable evidence:
`ABSOLUTE_MAXIMUM_AM001_CLOUDFLARE_TOTP_VALIDATION_20261127.json`.
