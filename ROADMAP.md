# NIXON — Project Roadmap

## Architecture

```
┌──────────────────────────────────────────────┐
│              15(14).py                        │
│         Python Obfuscator Engine              │
│  (AST transforms, packaging, build farm)      │
│         ↓ generates config                    │
├──────────────────────────────────────────────┤
│          build.py (Pipeline Wrapper)           │
│  obfuscate → generate config → compile rust    │
├──────────────────────┬───────────────────────┤
│                      │                       │
│  nixon_stub.cpp      │  orbital-relay (Rust) │
│  Windows PE Loader   │  Native C2/Tunnel     │
│  VEH, HellsGate,     │  SOCKS5 ↔ WebSocket   │
│  anti-dump, HW bind  │  ↔ Cloudflare Worker  │
│  reflective load     │  Anti-debug, stripped │
│                      │  2.8MB static binary  │
└──────────────────────┴───────────────────────┘
```

---

## Status Summary

### ✅ DONE

#### Python Obfuscator (`15(14).py`)
- All 6 AST transform modes working (cfg-flatten, opaque-predicates, bogus-exceptions, mba-subs, fragment-strings, unicode-ids)
- CLI with 6 commands (build, obfuscate, auth, clean, build-farm, version)
- GitHub Actions build farm (Cython + Nuitka cross-compile)
- Cloudflare deployer integration

#### C++ Stub (`nixon_stub.cpp`) — 85%
- VEH anti-dump, HW breakpoint clearing
- PEB walking, hash-based API resolution
- HellsGate syscall stubs
- AMSI/ETW patch via HW breakpoints
- Hardware fingerprint + 150K-iter key derivation
- Reflective PE loader
- Python marshal deserialize + exec
- Self-destruct (wipe PE + ROP exit)
- **Missing**: `payload.h` auto-generation (template exists)

#### C++ Core (`nixon_core.cpp`)
- WhiteboxCrypto + WhiteboxEnhanced (educational, 4-round)
- CompileToMarshal (Python → marshal bytes via C-API)
- **Cleaned**: ORAM dead code removed, FHE blocked out, leak fixed

#### Rust Relay (`orbital-relay`) — First Port Complete
- 8 modules, 0 compiler errors
- SOCKS5 handshake (RFC 1928, all addr types)
- WebSocket ↔ Cloudflare Worker bridge with failover
- Cloudflare Workers API (deploy, list, delete, test)
- DNS-over-HTTPS resolver + CF IP range detection
- Anti-debug checks (ptrace, TracerPid, timing, VM, /proc, env)
- Config management (JSON file, profiles, fallback)
- Release binary: 2.8MB stripped

#### Infrastructure
- Git repo initialized
- `.gitignore` covering all generated artifacts
- `Makefile` with 10 targets (core, wb, py_compile, relay, test, etc.)
- `requirements.txt` with 7 pinned deps
- Test suite: 11 passing, 1 skipped
- `payload.h` + `payload_contract.md` for stub interface
- `orbital-relay_obfuscated.py` from full pipeline test

---

### 🔜 PHASE 1 — Pipeline Integration (Next)

| # | Task | Est. Effort | Priority |
|---|------|-------------|----------|
| 1.1 | **Wire pipeline** — `build.py` chains obfuscation → config gen → Rust compile | 1-2h | 🔴 High |
| 1.2 | **Cross-compile Rust** — Windows (x86_64), macOS (x86_64 + ARM), Linux (ARM) | 4-6h | 🔴 High |
| 1.3 | **Config embedding** — Bake API keys / settings into Rust binary at compile time via `include_bytes!` + XOR | 2-3h | 🟡 Med |
| 1.4 | **Auto `payload.h` generation** — `15(14).py` generates header with encrypted payload for stub | 3-4h | 🟡 Med |

### 🔜 PHASE 2 — Hardening

| # | Task | Est. Effort | Priority |
|---|------|-------------|----------|
| 2.1 | **Rust anti-debug enhancement** — seccomp BPF, /proc/self/mem integrity, code integrity checks | 4-6h | 🟡 Med |
| 2.2 | **Traffic obfuscation** — TLS fingerprint spoofing, HTTP/2 padding, request jitter | 6-8h | 🟡 Med |
| 2.3 | **Payload embedding** — Option to embed Python payload directly in Rust binary (base64 + XOR in .rodata) | 3-4h | 🟡 Med |
| 2.4 | **Stub + Relay integration** — `nixon_stub.cpp` reflectively loads the Rust binary instead of Python | 8-12h | 🟡 Med |

### 🔜 PHASE 3 — Ship

| # | Task | Est. Effort | Priority |
|---|------|-------------|----------|
| 3.1 | **End-to-end tests** — Obfuscate → embed → run → verify C2 | 4-6h | 🟡 Med |
| 3.2 | **CI/CD** — GitHub Actions: build all targets, run tests, publish artifacts | 3-4h | 🟢 Low |
| 3.3 | **Domain fronting** — Route Cloudflare Worker traffic through legitimate domains | 6-8h | 🟢 Low |
| 3.4 | **Documentation** — Usage examples, build instructions, architecture docs | 2-3h | 🟢 Low |

---

## Pipeline Flow (Wired)

```
               ┌──────────────────────────────┐
               │  python3 build.py             │
               │  --payload myscript.py        │
               │  --cf-token XXX               │
               │  --cf-account YYY             │
               └──────────┬───────────────────┘
                          │
              ┌───────────▼───────────┐
              │  Phase 1: Obfuscate   │
              │  15(14).y → AST       │
              │  transforms applied   │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Phase 2: Generate    │
              │  orbital-relay.json   │
              │  + payload.h          │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Phase 3: Compile     │
              │  make relay           │
              │  (Rust → stripped     │
              │   binary)             │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Phase 4: Package     │
              │  build/               │
              │  ├── orbital-relay    │
              │  ├── payload_obf.py   │
              │  └── payload.h        │
              └───────────────────────┘
```

## Cross-Compile Targets

| Target | Triple | Status | Notes |
|--------|--------|--------|-------|
| Linux x86_64 | `x86_64-unknown-linux-gnu` | ✅ Working | Default target |
| Linux ARM64 | `aarch64-unknown-linux-gnu` | ❌ | Needs `aarch64-linux-gnu-gcc` |
| Windows x86_64 | `x86_64-pc-windows-gnu` | ❌ | Needs `mingw-w64` |
| Windows ARM64 | `aarch64-pc-windows-msvc` | ❌ | Needs cross-toolchain |
| macOS x86_64 | `x86_64-apple-darwin` | ❌ | macOS SDK needed |
| macOS ARM64 | `aarch64-apple-darwin` | ❌ | macOS SDK needed |

## Key Decisions

- **Python obfuscator → stays Python** (porting adds zero security)
- **C++ stub → stays C++** (VEH, HellsGate, inline asm — Rust can't match)
- **Relay → Rust** (done — native binary, no Python dependency)
- **Config → JSON at runtime, XOR-embedded at compile time** (future)
- **Payload → separate file, not embedded** (for now — embedding adds complexity)

## Threat Model

| Adversary | Cost to Break | Countermeasure |
|-----------|--------------|----------------|
| Script kiddie | Hours | Obfuscation, anti-debug |
| Competitor | Days | Native binary, stripped, anti-tamper |
| LE with warrant | Weeks | Hardware binding, remote attestation (future) |
| Nation-state | Months | Nothing locally is unbreakable |

The goal is **"too expensive to break for your threat model"**, not *literally* unbreakable.
