# Relay Configuration

The relay binary (`orbital-relay`) is configured through CLI arguments
(clap). This document reflects `relay/src/cli.rs`, `relay/src/config.rs`
and `relay/src/main.rs` as they exist in the tree; earlier revisions of this
file described a `--init-runtime` opt-in and a `config/relay.json` that do
not exist.

## CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `-p`, `--payload <path>` | string | — | Path to the payload file to launch |
| `--no-init-runtime` | flag | off | Skip protection-runtime initialisation. The runtime runs **by default**; this is the debug opt-out |
| `--antidebug` | flag | on | Anti-debugging checks are compiled as on-by-default; the current clap surface has no supported `false` value |
| `--serve-remote` | flag | off | Serve `@remote` function implementations instead of launching a payload |
| `--remote-bind <addr>` | string | `127.0.0.1:8787` | Bind address for `--serve-remote` |
| `--allow-remote` | flag | off | Allow a non-loopback bind. The endpoint speaks plain HTTP; put it behind TLS |
| `--remote-bundle <path>` | string | — | Operator Python bundle used for functions the Rust side does not register |

The remote shared secret is read from `NIXON_REMOTE_SECRET`; it is never
accepted on the command line or from a repository file.


## Split-execution service

A production-shaped loopback validation command is:

```sh
NIXON_REMOTE_SECRET=<64-hex> \
PYTHONPATH=/path/to/repository \
orbital-relay --serve-remote \
  --remote-bind 127.0.0.1:8787 \
  --remote-bundle /secure/operator-bundle.py
```

`PYTHONPATH` is needed only because the generated Python operator bundle uses
the repository's verification registry. The bundle itself is mode `0600` and
must never ship with the client. The loopback reference endpoint is plain HTTP
by design; non-loopback deployments must put it behind TLS and the client
refuses non-loopback plain HTTP before emitting a request.

## Cloudflare Worker alternative

`orbital-relay --serve-remote` remains the self-hosted reference service. The
build can alternatively emit a deployable Cloudflare Python Worker with:

```text
--transforms remote remote-bundle=/secure/operator-bundle.py \
  remote-cloudflare=/secure/cloudflare-worker
```

The generated worker contains the operator-side implementations and must never
ship to customers. It verifies the same protocol-v1 HMAC envelope, supports
customer-bound derived credentials, requires fresh six-digit codes from two
independent TOTP seeds for customers without an enrolled device, implements
request-bound phone approval for enrolled customers, and uses a SQLite-backed
Durable Object for replay, rate-limit, quota, approval, and enrolment
accounting.

The recommended configuration stores only this worker secret:

| secret | meaning |
|---|---|
| `NIXON_REMOTE_MASTER_SECRET` | Worker-only 64-hex master secret used to derive each customer's HMAC secret and two independent TOTP seeds |

Optional policy secrets are `NIXON_REMOTE_DISABLED_CUSTOMERS`,
`NIXON_REMOTE_RATE_LIMIT_PER_MINUTE`, `NIXON_REMOTE_QUOTA_PER_DAY`,
`NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE`,
`NIXON_REMOTE_TOTP_PAIR_MAX_USES`, `NIXON_REMOTE_APPROVAL_MODE`,
`NIXON_REMOTE_APPROVAL_EXPIRY_SECONDS`, `NIXON_REMOTE_MAX_PENDING`, and
`NIXON_REMOTE_TOTP_WITH_APPROVAL`. Use:

```sh
python3 -m obfuscator.cloudflare_remote provision-master master-provisioning.json
python3 -m obfuscator.cloudflare_remote provision-customer customer.json \
  --customer-id CUSTOMER --master-secret-file master-provisioning.json
```

The customer artifact then uses `NIXON_REMOTE_CUSTOMER_ID` plus the derived
customer `hmac_secret` as `NIXON_REMOTE_SECRET`. Legacy shared mode requires
explicit `NIXON_REMOTE_ALLOW_SHARED=1` and the original three shared secrets;
it is compatibility behavior, not the recommended design.

Deployment instructions are written into the generated project's
`DEPLOYMENT.md`, including phone-approval enrolment and the admin endpoint for
dynamic key revocation and customer disable/enable. TOTP and phone approval
are additional server-side access gates, not host
attestation and not protection for plaintext client-side logic. They are enforced
only by the generated Cloudflare Worker; the Rust reference relay accepts the
same signed protocol envelope but enforces neither TOTP nor approval.

## `AppConfig` (`relay/src/config.rs`)

`AppConfig` is the small, CLI-derived launch configuration:

```rust
pub struct AppConfig {
    pub payload_path: Option<String>,
    pub init_runtime: bool,   // !cli.no_init_runtime
    pub antidebug: bool,
}
```

It is built by `AppConfig::from_cli(&cli)`.

## Runtime baseline (`runtime_config.json`)

Before launching, the relay loads a build-produced baseline:

1. `NIXON_RUNTIME_CONFIG`, if set and non-empty;
2. otherwise `runtime_config.json` next to the relay executable.

The file must contain an integer `integrity_expected_crc`. The field is
required deliberately: `{}` fails closed rather than silently disabling the
integrity check. Only that baseline is read from the file; the remaining
`nixon_runtime::RuntimeConfig` fields keep their defaults.

## Runtime Manifest (embedded)

`relay/build.rs` reads `runtime/manifest.json`, injects a fresh
`build_seed` (`NIXON_BUILD_SEED` or 32 bytes from the OS RNG), and emits it
as `RUNTIME_MANIFEST` in `relay/src/config_embed.rs`. The manifest therefore
carries the runtime version, encryption description, integrity settings and
self-destruct configuration compiled into the binary at build time.

`runtime/gen_manifest.py` regenerates the same document shape; keep its
`encryption.key_derivation` string in step with
`runtime/src/decrypt.rs::derive_block_key`.

## `~/.config/orbital-relay/config.json`

`Config` is a **separate**, persisted settings file for the broader client /
Cloudflare / worker feature set. It is loaded from
`$HOME/.config/orbital-relay/config.json` and, when saved, is created and
re-chmodded to `0600`. Its shape is:

```rust
pub struct Config {
    pub client: ClientConfig,
    pub cloudflare: CloudflareConfig,
    pub worker: WorkerConfig,
    pub cached_services: Vec<ServiceRecord>,
}
```

This file does not configure payload launch. There is no `--config` flag and
no `config/relay.json` in the repository.
