# Relay network modules — quarantined (not part of the obfuscator)

Moved out of `relay/src/` on 2026-09-20. These modules implement
proxy/C2 networking (SOCKS5 + websocket tunnel + Cloudflare API +
DNS-over-HTTPS) and are **unreachable from the launcher**: `main.rs`
only calls `payload::launch_payload` (+ optional `init_runtime` /
`antidbg`), and nothing else in the repo imports them (only the
archived fuzz targets did). The shipped `orbital-relay` binary is a
pure native payload launcher with no networking.

- `tunnel.rs` (262 ln) — websocket tunnel + `GatewayConfig` (ws_url,
  api_key, socks_password, Cloudflare overrides)
- `socks5.rs` (158 ln) — SOCKS5 handshake/parser
- `cloudflare.rs` (719 ln) — Cloudflare Workers/API deploy client
- `dns.rs` (108 ln) — DNS-over-HTTPS via `dns.google`, CF IP ranges
- `fuzz_targets/socks5_handshake.rs`, `fuzz_targets/dns_response.rs` —
  fuzz harnesses for the above (kept `config_parse.rs` + `fuzz_target_1.rs`
  in `relay/fuzz/`)

Companion trim (same date, required for `cargo build` to pass):
- `relay/src/lib.rs`: dropped the four `pub mod` lines
- `relay/Cargo.toml`: dropped now-unused deps
  (`tokio`, `tokio-tungstenite`, `futures-util`, `reqwest`, `url`,
  `ipnetwork`, `chrono`, `rand`); `relay/fuzz/Cargo.toml`: dropped the
  two `[[bin]]` stanzas that pointed at the archived harnesses.
