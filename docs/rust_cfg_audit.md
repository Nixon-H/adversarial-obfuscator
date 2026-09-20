# Rust cfg() Audit

## runtime/src/

| File | cfg() | Purpose | Fallback? |
|------|-------|---------|-----------|
| decrypt.rs | `target_arch = "x86_64"` | x86-64 memory fence (`mfence`) after JIT code copy | ✅ No-op on other arch (asm! block not compiled) |
| timing.rs | `target_arch = "x86_64"` | `rdtsc()` via x86_64 intrinsic | ✅ Returns 0 on non-x86_64 |
| timing.rs | `not(target_arch = "x86_64")` | Stub rdtsc returning 0 | ✅ Primary path uses this fallback |
| port_entangle.rs | `target_arch = "x86_64"` | CPUID-based CPU generation detection (Intel/AMD family+model) | ✅ Returns `CpuGeneration::Unknown` |
| port_entangle.rs | `not(target_arch = "x86_64")` | Stub returning Unknown | ✅ Primary path uses this fallback |
| hpc_detect.rs | `target_arch = "x86_64"` | CPUID hypervisor bit check via inline asm | ✅ Returns `false` on non-x86_64 |
| hpc_detect.rs | `not(target_arch = "x86_64")` | Stub returning false | ✅ Primary path uses this fallback |
| hpc.rs | `target_arch = "x86_64"` | `read_pmc_raw()` via RDPMC instruction | ✅ Returns `Err("RDPMC not supported")` |
| hpc.rs | `not(target_arch = "x86_64")` | Stub returning Err | ✅ Primary path uses this fallback |
| hpc.rs | `target_arch = "x86_64"` | `read_pmc()` — perf_event_open wrapper | ✅ Returns Err on non-x86_64 |
| hpc.rs | `not(target_arch = "x86_64")` | Stub returning Err | ✅ Primary path uses this fallback |
| hpc.rs | `target_arch = "x86_64"` | `read_tsc()` via RDTSC intrinsic | ✅ Returns 0 on non-x86_64 |
| hpc.rs | `not(target_arch = "x86_64")` | Stub returning 0 | ✅ Primary path uses this fallback |
| hpc.rs | `target_arch = "x86_64"` | `PerfEventAttr` struct + `perf_event_open()` syscall wrapper | ✅ Functions return 0/Err on fallback |
| hpc.rs | `target_arch = "x86_64"` | `read_l2_cache_misses()` via perf_event_open | ✅ Returns 0 on non-x86_64 |
| hpc.rs | `target_arch = "x86_64"` | `read_branch_mispredictions()` via perf_event_open | ✅ Returns 0 on non-x86_64 |
| lib.rs | `target_os = "linux"` | `/proc/self/status` TracerPid anti-debug check | ✅ No-op: ignores config |
| lib.rs | `not(target_os = "linux")` | Stub no-op for anti-debug | ✅ Primary path uses this fallback |
| jit.rs | `target_arch = "x86_64"` | MFENCE after JIT code write (2 occurrences) | ✅ No-op on other arch |

## relay/src/

| File | cfg() | Purpose | Fallback? |
|------|-------|---------|-----------|
| lib.rs | `target_os = "linux"` | Guards `antidbg` module (Linux-specific ptrace, procfs) | ❌ Module only compiled on Linux; no module loaded on other OS |

> 2026-09-20: the `full-network` networking modules (`tunnel`,
> `cloudflare`, `dns`, `socks5` + their fuzz harnesses) were quarantined
> to `archive/relay_net/` (see its README); `lib.rs` no longer declares
> them and `Cargo.toml` dropped the network deps. `config_embed`
> (build.rs-embedded `runtime/manifest.json`) stays — it is launcher
> config, not networking.

## Notes

### `full-network` feature in relay (retired 2026-09-20)
The `full-network` feature enables C2/networking modules (`tunnel`, `cloudflare`, `dns`, `socks5`, `config_embed`). Per ROADMAP Phase 7, these should be stripped from the native launcher build — the binary should be a pure launcher with no C2. This feature exists mainly for development/testing and should not be enabled in production builds.

### `target_os = "linux"` in relay/src/lib.rs
The `antidbg` module uses Linux-specific interfaces (ptrace, `/proc/self/status`). On non-Linux targets, no anti-debug module is compiled. If cross-compilation targets are desired (e.g. Windows via MinGW), a platform-agnostic anti-debug module should be added.
