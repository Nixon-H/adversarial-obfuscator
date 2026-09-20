# Relay Configuration

The relay binary (`orbital-relay`) is configured primarily through CLI
arguments (clap). An optional `config/relay.json` file exists in the
project root for future configuration expansion.

## CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--payload <path>` | string | — | Path to the payload file to launch |
| `--init-runtime` | bool | `false` | Initialize nixon-runtime before launching |
| `--antidebug` | bool | `true` | Enable anti-debugging checks |

## AppConfig Struct (`relay/src/config.rs`)

```rust
pub struct AppConfig {
    pub payload_path: Option<String>,
    pub init_runtime: bool,
    pub antidebug: bool,
}
```

Constructed from the CLI via `AppConfig::from_cli(&cli)`.

## Runtime Manifest (embedded)

The build script (`build.rs`) reads `runtime/manifest.json` and embeds it
as `RUNTIME_MANIFEST` in `config_embed.rs`. This embedded manifest carries
runtime version, encryption algorithm, integrity settings, and self-destruct
configuration — all compiled into the binary at build time.

## `config/relay.json`

Present as an empty placeholder (`{}`) for future settings. Currently unused
by the relay binary. The `--config` CLI flag is not implemented.
