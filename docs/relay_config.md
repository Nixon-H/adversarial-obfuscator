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
| `--antidebug` | bool | `true` | Enable anti-debugging checks (`--antidebug false` disables) |
| `--serve-remote` | flag | off | Serve `@remote` function implementations instead of launching a payload |
| `--remote-bind <addr>` | string | `127.0.0.1:8787` | Bind address for `--serve-remote` |
| `--allow-remote` | flag | off | Allow a non-loopback bind. The endpoint speaks plain HTTP; put it behind TLS |
| `--remote-bundle <path>` | string | — | Operator Python bundle used for functions the Rust side does not register |

The remote shared secret is read from `NIXON_REMOTE_SECRET`; it is never
accepted on the command line or from a repository file.

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
