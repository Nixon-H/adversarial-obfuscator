# Capability audit: ours vs Nyami (with threat-model gate) + roadmap

Date: 2026-09-20 (evening session). Status: **baseline Nyami research
treated as completed context** (`nyami-changelogs.md`, `nyami-docs-
summary.md`, `obf-test-*.txt`, README deep-dig). This document does NOT
repeat that analysis — it audits OUR implementation live (Rust/C/Python
read 2026-09-20), compares capability-by-capability, gates every Nyami
idea against OUR threat model, scans beyond-Nyami, and produces the
decision matrix + roadmap. Supersedes `ours-vs-nyami-plan.md` §2–§4
verdicts wherever they differ; differences are called out explicitly.

Evidence convention: `[S]` = directly established by reading our code
today; `[N-doc]` = Nyami documented (GitBook/site); `[N-log]` = Nyami
changelog claim; `[N-stat]` = established by our static analysis of
`obf-test.py`. Vendor claims are NEVER presented as verified behavior.

Our assumed threat model (used as the gate in §5): protect Python IP
running on **user-controlled machines** against static RE (decompilers,
disassemblers), dynamic RE (debuggers, tracers, API hooking, memory
dumps), and redistribution (copying, HW-unbound sharing). Out of scope:
kernel-level adversaries, nation-state TEE breakage, DRM-grade
unbreakability. Anything failing this gate is REJECTed even if Nyami has it.

---

## 1. Current-implementation audit (live, 2026-09-20)

### 1a. Rust — `runtime/` (39 modules, ~10k lines, deps `libc`+`serde_json` only) + `relay/` (8 files, ~660 lines)
[S] `init_runtime()` wires ~40 `enable_*` flags: AES-CTR decrypt, CRC32 +
Merkle-ledger `.text` integrity, per-exec recompilation cache, polymorphic
JIT (mmap RW→RX flip, `transmute` to fn ptr), ROP gadget scanner +
dispatch chains, Path-ORAM, TEE/SGX dispatch + FFI, HPC/RDPMC emulator
detection + HPC-bound keys, RDRAND entropy + replay nonces, per-run CFG
mutation, SSA variants, state-dependent ISA, class-dispatch (FNV + mprotect
+ mfence), branch/cache/multicore/port entanglement, crypto-CFG tokens,
transient-exec guards, self-healing (Mutex + checker thread + tamper log),
sw-attestation challenges, `platform/` PagePerm abstraction
(mmap/mprotect + VirtualAlloc/VirtualProtect), `memguard` scrub/mlock.
31/38 runtime modules have `#[cfg(test)]` (~250 tests). Release:
`opt-z/LTO/strip/panic-abort`, cross targets, SGX feature gate.
[S] `relay/`: clap CLI → `init_runtime` → 12 Linux anti-debug checks
(fn-pointer table; fork+`_exit` seccomp probe) → payload exec. Zero-test
coverage in `relay/`; `antidebug` CLI flag parsed but never read;
relay `attestation.rs` uses `DefaultHasher` (SipHash, per-process keys)
mislabeled as `sha256_simple` — NOT real SHA-256, 64-bit entropy, secret
is 1 repeated byte. Treat as **protocol placeholder, not crypto** [S].

Rust benefits actually used [S]: inline `asm!` (rdtsc/rdpmc/rdrand/
clflush/mfence/lfence) — impossible in safe Python; executable-memory
lifetimes (`Drop` munmap, guard pages); `Arc<AtomicU64>/Barrier/Mutex`
lockstep threads (GIL-free); `repr(C)` FFI to `simd_vm.c`; zero-copy
`&[u8]` manifest embed; `cfg()` platform/feature splits; Result-chains.
A Python rewrite would lose: RX-page JIT, cycle-accurate traps, GC-free
scrub/timing, ns-scale thread lockstep, static hardened binary.

### 1b. C/C++ — `native/` (~13k lines)
[S] `core.cpp`: WhiteboxCrypto (self-admitted "educational-grade 4-round
AES-lite, linear key schedule, **no true S-box**"), WhiteboxEnhanced,
`CompileToMarshal` (CPython C-API: GIL, `Py_CompileStringExFlags`,
`PyMarshal_WriteObjectToString`); 3 `.so` flavors. `vm_stub.c`: ephemeral
polymorphic VM (vendored SHA-256, mutating ISA, computed-goto dispatch).
`microjit.c`: RWX mmap + call (no W^X flip), self-rolled AES-CTR.
`simd_vm.c`: only true SIMD/CPUID in repo, Rust-linked. `crypto_chain.c`
+ `key_evolution.c`: fragment-key chain (single-SHA256 "HKDF", stub
`aes_gcm_decrypt` that overclaims its name). `stub_win.cpp` (1578 lines):
**strongest C file** — PEB walk via `__readgsqword`, FNV-hashed dynamic
exports (import-hiding, no link-time imports), reflective Python-DLL
load, `PyMarshal_ReadObjectFromString` + `PyEval_EvalCode` dynamic
resolve, RC4 payload path, VirtualLock + volatile wipe, RWX stub emit,
`PAGE_NOACCESS` enclave. `stub_linux.cpp`: ptrace/prctl/sigaction/rdtsc,
2 s watchdog thread (tracer+ptrace+breakpoints), dumpable-off.
`attestation.c`: **weak** — `srand/rand` self-attesting dummy region,
incoherent deadlines, always-false compare. `cross_process.c` (shm 0666,
unsealed), `fragment_migration.c` (3rd SHA-256 copy, leaks), 
`distributed_vm.c` (network no-op + stack-size hazard), `gpu_stub.c`
(CPU sim, nothing GPU), `self_healing.c`/`struct_random.c` (toy, Rust
already reimplements) — all **unwired sims/stubs**, keep honest about it.
`rop_exec.h`: inline-asm stack-pivot (x86-only, CET-fragile).

C benefits actually used [S]: PEB/intrinsics, hashed-export resolution,
reflective DLL, RWX JIT, CPython C-API `.so`s, SIMD, ptrace/prctl,
shm/mmap FD lifecycle. Requires C: `stub_win.cpp`, `rop_exec.h`,
`stub_linux.cpp` guards, `microjit` exec-bridge, `core.cpp` C-API,
`simd_vm` kernels.

### 1c. Python — `obfuscator/` (21 transform classes + 17 modules), `irgen/`
(18), `llvmgen/` (7), `encrypt/` (7), `vm/` (7), `scripts/build.py`
(3809 lines, 250 flags), `scripts/phases/` (~90), adversarial harness
[S] Transforms: hint-strip, fstring-lower, SymbolRenamer, string-XOR,
builtin-alias, ASTMutator(dead code+VM checks), 12-family opaque
predicates, MBA substitutor, call-graph indirection, bogus exceptions,
var-split, const-unfold, meta-strip, unicode-ids, checksum inject,
dynamic-codegen (exec/eval + `.jit` mkstemp), junk, function outlining,
reflection (`getattr(XOR)`), CFF state-machine + CFI LUT, exception-flow,
plus LLM-specific layers with **no Nyami equivalent**: attention-poison,
reasoning traps, adversarial dead code, prompt injection, per-model
fingerprints, honey functions, semantic decoys, dataflow
(Affine/Split/MBA), speculation decoys, context-collapse.
[S] Pipeline: AST → string tables (XOR+zlib+router) → Cythonize hybrid
loader (native blobs + `zlib+marshal` fallback) → HWID/expiry gates →
VM stages → onion lzma+AES-CTR/XOR → NIXON zip → swizzled `.pyc` →
`irgen`→`vm_compile`→`llvmgen` (bcf/fla/sub+CRC) → relay/Rust → AES-CTR
per-block encrypt + stub + payload.h + Nuitka farm + UPX.
[S] Critical-path facts: `marshal.loads` at **2 runtime-emitted sites**
(`pipeline.py:964` `_exec_fallback`, `sources.py:988` Cython VM) — rest is
build-time. `secure_zero` is bytearray-only, docstring admits GC copies
survive. Real wipe exists ONLY natively (`microjit.c`, `stub_win`,
`runtime/jit.rs`, mprotect paths) and is **not wired to payload path**.
HWID: 12-factor weighted fuzzy match (70% threshold) + MAC/disk/machine-id
collection + CF-KV licensing + `--hwid/--bind-mac` — collection exists,
no PBKDF2→GCM product lock. Env gate: strict `version_info ==` + exit(1)
**BUT env-bypassable** (`NIXON_VERIFY_SKIP_VERSION_CHECK`). No
SELF/SECURE_DELETE, no trial engine (only cache-expiry dicts), no user
macros (`IS_OBFUSCATED`/`GET_HWID`/`__all__`), no PyInstaller spec gen
(Nuitka instead), no PYTOC flag, no API server (Cloudflare/Solidity
deploy helpers + build farms instead). Watchdogs EXIST (Linux+C 2 s
pthreads; Win `WatchdogThread` hwBP+PEB+debug-port, 3-strike latch;
Rust checker threads) — but **no 3-thread cross-respawn topology**.
ANTI_DECOMPILER_SOURCE exists but is junk-shapes (`if False`, fake
imports), NOT targeted EXTENDED_ARG corruption. No IAT verification
(though `stub_win` already resolves all imports hash-hidden — the
verification half is missing). No per-build export shuffling. VM
detection is boolean per-check (cpuid flags, DMI strings,
systemd-detect-virt) with an env-keying fuzzy matcher — **no unified
0–100 confidence + policy**.

### 1d. Tests/CI/docs [S]
2700 collected, 18 collection errors: 15× missing `z3` dep (not in
requirements.txt — CI would fail identically), 3× `test_data/*.decoy.py`
mis-collected fixtures. CI (4 workflows): pytest + cargo test + clippy-
less lint + cross checks (ARM/Windows `cargo check`, `make native-test`).
Docs: 6 files (dev prereqs, platform matrix, relay config, ROADMAP
phases, rust cfg audit, stub plan). Targets py3.11+ (CI tests 3.11/3.12;
local 3.13 untested by CI).

---

## 2. Capability comparison (property-level, not name-level)

| # | Capability (property) | Current system [S] | Nyami [N-doc/N-log/N-stat] | Gap | Strength |
|---|---|---|---|---|---|
| C1 | Identifier renaming | Seeded babel + unicode-lookalike ids, scope-aware | Seeded random short names | None — ours stronger | Strong |
| C2 | Numeric literal hiding | `ConstantUnfolder` + MBA rewrite | Hex/oct/bin + expr split | None — parity+ | Strong |
| C3 | Control-flow flattening | State-machine + CFI LUT + exception-flow variant | Switch-dispatch + per-doc example | None — parity+ | Strong |
| C4 | Opaque predicates | 12 math families | Math invariants | None — parity | Strong |
| C5 | MBA arithmetic rewrite | `InstructionSubstitutor` BinOp/Compare | 4 complexity levels | Partial — leveled depth unverified | Medium |
| C6 | Junk / dead code | `EnhancedJunkInserter`, honey functions, adversarial dead code | Junk (moved OFF outer layer v3.1), per-layer decoys | None — ours broader + LLM layers unique | Strong |
| C7 | Whole-module wrap (WIF) | Whole-module wrap exists in pipeline options | WIF macro | None — parity | Medium |
| C8 | Minification | MetadataStripper | Minifier (recode v5) | None — parity | Medium |
| C9 | Per-function encrypt-at-call | FunctionTransformer + outline fragments | Per-func keys, Lite marshal+zlib | Partial — ours lacks per-func key separation + compressed-marshal form | Medium |
| C10 | Optimization ladder | 250 flags, no coherent O0–O5 | O0–O5 with decoy/junk policy + compat profiles | Missing (policy, not mechanism) | Weak-policy |
| C11 | Importable modules (`__all__`) | **Absent** | `__all__` preserved | Missing | — |
| C12 | Custom ISA virtualization | Python dynamic-ISA VM + C `vm_stub` + Rust `simd_vm` + micro-JIT + ROP dispatch | Abstract-ISA interpreter | None — ours deeper (3 substrates) | Strong |
| C13 | Targeted decompiler breaking | Junk-shapes only (`if False`), no EXTENDED_ARG corruption | EXTENDED_ARG-chain corruption vs named decompilers | Missing (technique, not goal) | Weak |
| C14 | Distributed runtime codegen | Rust JIT + per-exec recompile + native per-wrapper eval sites | Per-wrapper `<frozen>` compile+eval (5×EvalCode/3×Compile [N-stat]) | Partial — ours centralizes codegen; theirs fragments it | Medium |
| C15 | Eval-pointer verification | None | `_verify_eval` DLL-range check [N-log] | Missing (small) | — |
| C16 | String/constant encryption | XOR+zlib router + 4 tables + swizzle + OpcodeMorpher | XOR-per-session, ChaCha20 variant, multi-encode, 5-scheme KDF | Parity (their "SHA-512 cipher" is not a cipher — ignore) | Strong |
| C17 | Real white-box cipher | **Toy**: 4-round AES-lite, linear schedule, no S-box (file admits) | 8-round Feistel, SHA-256 S-boxes, no key bytes [N-log] | Missing (only genuine crypto gap) | Weak |
| C18 | Loader container shape | Single-shape b85/XOR/lzma/marshal loader | Reorder + 85-char substitution + chunked b85 + sha (unrecovered MF key) | Partial — primitives (MULTIDIM/ISR) exist, not wired as container | Medium |
| C19 | Single-file native artifact | Nuitka farm + Cython helper (no CLI flag, no in-mem exec) | PYTOC py→pyx→C→pyd + memfd in-mem exec [N-log/N-stat] | Partial — missing productized path | Medium |
| C20 | Fileless temp delivery | memfd + mkstemp + `exec_module` present; plain perms, no purge, no waiter | Stale-purge + O_EXCL/0600 + atexit + detached urandom waiter [N-stat] | Partial — hardening half missing | Medium |
| C21 | Deserializer hardening | `marshal.loads` ×2 runtime hot paths (hookable) | Marshal-only-via-CTypes + NYSER1 lambda-`Code.replace` serializer | Missing (biggest hook-surface gap) | Weak |
| C22 | Anti-debug breadth | 12 relay checks + cross-platform guard + timing traps + frame walkers + C pthreads | 11 methods + tiers + IDP-called + audit hooks + frame validation | Parity (~80%) | Strong |
| C23 | Timing-check robustness | Bare thresholds (`perf_counter_ns`, rdtsc compares) | Folded QPC: dual-timer xor/and/cmp/cmov vs stored ref [N-stat] | Partial — pattern upgrade, not new coverage | Medium |
| C24 | Debug-state monitoring | Watchdog threads exist (Linux 2 s, Win 3-strike, Rust checkers) | Native watchdog + Hydra 3-thread cross-respawn [N-log] | Partial — topology upgrade (respawn), not existence | Medium |
| C25 | VM verdict quality | Boolean per-check + fuzzy env-key matcher, no unified score | 13-signal weighted 0–100 + KOD policy [N-doc] | Partial — scoring/policy layer missing | Medium |
| C26 | Tamper-response topology | Watchdog latches + `scrub_and_exit` + self-healing restore | Hydra cross-verify + HMAC builtin challenge + isolated exec + bind-once dict | Partial — see C27–C30 | Medium |
| C27 | Builtin-hook detection | None on exec/eval/compile/__import__ | HMAC-SHA256 challenge-response per use [N-doc] | Missing | — |
| C28 | Exec-namespace isolation | `exec(code, globals())` injectable bridge | SHA-256 pre-exec verify + bind-once frame-walk host dict [N-log] | Missing (our bridge is the hole) | Weak |
| C29 | Import-table verification | Hash-hidden resolution (hiding ✓) but no verification | IAT vs GetProcAddress at init + periodic [N-log] | Partial — verify half missing | Medium |
| C30 | Build-to-build uniqueness | Per-build seeds/swizzle/morph; symbol names stable | Per-build randomized kernel exports [N-log] | Partial — cheap halves differ | Medium |
| C31 | Memory wiping reliability | Python best-effort (GC-defeated by design) + unwired native tools | `ob_sval`-offset zero + gc-sweep + segfault fallback + page-RO + split secrets | Missing on payload path (tools exist, wiring doesn't) | Weak |
| C32 | Machine binding (licensing) | 12-factor collect + fuzzy 70% + CF-KV; no PBKDF2→GCM product lock | PBKDF2→AES-GCM-AAD + in-kernel commitment [N-doc/N-log] | Partial — productization missing | Medium |
| C33 | Trial/expiry + user macros | Cache-expiry dicts only; no macros | Trial strings + IS_OBFUSCATED/GET_HWID/SELF/SECURE_DELETE/CRASH/DETECT_FILE_TYPE | Missing (DX/licensing) | — |
| C34 | Destructive cleanup | No self/secure-delete, no waiter | Detached urandom waiter + remove import [N-stat]; documented macros [N-doc] | Missing (opt-in feature) | — |
| C35 | Exe packaging automation | Nuitka farm + UPX; no PyInstaller spec gen | PyInstaller spec + hidden-import automation | Partial — alternative exists, parity cheap | Medium |
| C36 | Version targeting matrix | Ad-hoc gates + env-bypassable pin | Version-select 3.10–3.14 + locked bootstrap | Partial — matrix discipline missing | Medium |
| C37 | Evidence/assurance | ~50 audit phases, redteam runners, adversarial AI loop, ledger proofs | None visible (vendor claims only) | **Ours uniquely stronger** | Strong |
| C38 | LLM-specific resistance | Attention/reasoning/prompt/fingerprint/decoy layers | Nothing (their v3.1 note shows AI-false-positive pain, not capability) | **Ours uniquely stronger** | Strong |
| C39 | HW-rooted execution | TEE/SGX dispatch + FFI, HPC-bound keys, ORAM | Nothing comparable documented | **Ours uniquely stronger** | Strong |

---

## 3. Preserve-list (what must not be lost, and why)

- **Rust `runtime/`**: RX-page JIT, asm-level traps/keys, GC-free scrub,
  GIL-free lockstep, static binary, SGX FFI. Any change here is additive
  modules or intra-module improvement — never a Python rewrite.
- **`native/stub_win.cpp`**: hash-hidden imports, reflective DLL, C-API
  bootstrap without link-time Python. Improvements land inside this file.
- **`native/vm_stub.c` + `microjit.c` exec-bridge + `simd_vm.c` kernels**:
  zero-dep C VMs; keep C ABI (Rust already links `simd_vm` correctly).
- **Python AST/LLVM/VM orchestration + `scripts/` evidence pipeline +
  adversarial AI loop + LLM layers**: ecosystem/AI/build-tooling advantage
  is Python-native; rewriting in Rust/C buys nothing and loses iteration.
- **`encrypt/aes.py`**: correct build-time AES; keep for build, never
  promote to runtime hot path (Rust `decrypt` owns runtime).
- **Nuitka farm + Cloudflare/Solidity deploy helpers**: alternative
  delivery paths; PYTOC/PyInstaller arrive *alongside*, not instead.

---

## 4. Threat-model gate (each Nyami idea judged, not copied)

| Nyami idea | Gate question | Ruling + reason |
|---|---|---|
| White-box Feistel | Does our toy cipher protect real secrets? No — theater. Does a real one help? Yes: payload keys live in user-controlled memory. | **ADOPT** (only genuine crypto gap). |
| NYSER1 serializer | Does marshal-hooking break our hot paths today? Yes — 2 runtime `marshal.loads` sites are THE hook point. | **ADOPT** (highest leverage). |
| Marshal-only-via-CTypes | Same hook point, complementary half of NYSER1. | **ADOPT** with NYSER1. |
| PYTOC + in-mem exec | Do users need single-file native artifacts without Nuitka weight? Yes (importable `.pyd`, fileless). | **ADOPT** as alternative path. |
| Reorder/substitution container | Does our single-shape loader have a signature? Yes. Cost ~zero. | **ADOPT**. |
| Secure-temp delivery | Do our temp payloads leave world-readable forensics? Yes (plain mkstemp). | **ADOPT**. |
| Folded QPC | Are bare thresholds patch-trivial? Yes. Cost tiny. | **ADOPT**. |
| `_verify_eval` | Is eval-pointer hooking in our threat model? Yes (dynamic RE). ~30 lines. | **ADOPT**. |
| Hydra cross-respawn | Do one-shot watchdogs die with their watcher? Yes. But: respawn loops trip AV heuristics. | **ADOPT tiered** (Off/Monitor/Enforce; default Monitor). |
| VM confidence + KOD | Do boolean VM checks false-positive (CI/VMs/dev laptops)? Yes — our own `stub_linux` sandbox heuristics would fire in CI. Scoring reduces harm. | **ADOPT scoring; KOD default-OFF**. |
| HMAC builtin challenge | Is `__import__`/exec patching in model? Yes. Cost per-use hashing — measure. | **ADOPT** with perf budget. |
| Isolated exec + bind-once dict | Is `exec(..., globals())` injectable today? Yes — demonstrated hole. | **ADOPT** (closes real hole). |
| IAT verification | Is IAT hooking in model on Windows? Yes. `stub_win` already hides; verify closes loop. | **ADOPT** (Windows path only). |
| Randomized exports | Does it stop anyone beyond signature-scanners? Marginal alone; cheap with symbol shuffle. | **ADOPT as cheap IMPROVE**, never as headline. |
| C-level memory wipe wiring | Do GC-defeated Python wipes protect keys? No — proven ineffective by language semantics. | **ADOPT** (wire existing tools, not new tools). |
| Byte-list keys | Plaintext keys in output? Yes. Emit-time, free. | **ADOPT**. |
| PBKDF2-HWID lock + trials | Is redistribution in model? Yes. Support burden real → trial-first. | **ADOPT subset** (lock+trials+macros; defer in-kernel commitment to TEE story). |
| User macros / `__all__` | DX + importable modules — requested pattern, tiny. | **ADOPT**. |
| O0–O5 ladder | 250 flags unnavigable; compat bugs need profiles. | **ADOPT** as policy overlay (no mechanism change). |
| Per-function 4-backend contest | Is single zlib-9 size-optimal? No. Build-time only, parallelizable. | **ADOPT**. |
| Version matrix 3.10–3.14 | CI tests 3.11/3.12, local 3.13 untested — rot is real. | **ADOPT** discipline. |
| PyInstaller spec gen | Nuitka exists — is exe parity worth 1 day? Yes (user expectation). | **ADOPT alongside**. |
| Decompiler Breaker (EXTENDED_ARG) | Do decompilers threaten IP? Yes — first tool a buyer reaches for. Our junk-shapes don't target them. | **ADOPT** (new technique). |
| Kernel-driver detection [N-log beta] | Kernel adversary in model? **No** — out of scope, rootkit-adjacent, Windows-only beta. | **REJECT**. |
| Auto module install (pip at obfuscation) | Supply-chain hole for marginal DX. | **REJECT**. |
| Hosted API/dashboard, Lua, gamification | Service/business, not pipeline capability. | **REJECT**. |
| "SHA-512 cipher", single-sha integrity, int-list hiding, settrace-hygiene, in-file XOR keys | Marketing or strictly weaker than ours. | **REJECT**. |
| In-kernel HWID commitment | Needs TEE story we haven't productized; premature. | **DEFER** (revisit with SGX phase). |

## Beyond-Nyami scan (neither has it, worth considering)
- **Supply-chain signing of build artifacts** (sigstore/cosign): our
  evidence pipeline asserts claims but artifacts aren't signed — cheap,
  high trust value. **ADD**.
- **Reproducible-build verification**: per-build uniqueness vs
  auditability tension; add `--reproducible` mode (fixed seeds) for
  auditors. **ADD**.
- **Fuzz the loader boundary** (`relay/fuzz` has an empty stub target):
  real harness for config/loader parsing. **ADD** (2 h).
- **Fix relay `attestation.rs` crypto**: `DefaultHasher`-as-SHA256 +
  1-byte secret is worse than nothing (false confidence). Either wire
  real SHA-256 (already vendored in C, or `sha2` crate) or delete module.
  **IMPROVE** (correctness, not feature).
- **Retire or wire the C sims**: `distributed_vm` (stack hazard),
  `attestation.c` (always-false compare), `cross_process` (0666 shm),
  `fragment_migration` (leak), `gpu_stub` (sim-only) are checked-in
  hazards if anyone links them. Either gate behind `NIXON_EXPERIMENTAL`
  or fix. **IMPROVE** (safety).

---

## 5. Decision matrix

| Capability | Current system | Nyami | Gap | Current strength | Recommendation | Language | Reason |
|---|---|---|---|---|---|---|---|
| AST renamer/numbers/CFF/opaque/MBA-base/junk/WIF/minify | 21 transform classes + unicode-ids | Same set, short-name renamer | None | Strong | **KEEP** | — | Ours parity-or-better; no Nyami advantage |
| MBA leveled depth | Single-depth substitutor | 4 complexity levels | Unverified depth | Medium | **INVESTIGATE** | Python | Confirm what L2–L4 add before building |
| Evidence pipeline + audit phases + adversarial AI loop + LLM layers + TEE/HPC/ORAM/ROP | ~50 phases, ledger, AI harness, unique modules | Nothing comparable | Ours ahead | Strong | **KEEP** | — | Architectural moat; never trade away |
| Rust runtime (JIT/RX, asm traps, threads, pages, SGX) | 39 modules, ~250 tests | No equivalent (their native is one pyd) | Ours ahead | Strong | **KEEP** | Rust | Loses capability in any rewrite |
| `stub_win.cpp` reflective loader | Hash-hidden imports, C-API bootstrap | memfd/loader pattern | Ahead (different OS) | Strong | **KEEP** | C | Improve inside the file |
| Toy whitebox cipher | 4-round, linear schedule, no S-box (own admission) | 8-round Feistel, S-box keys [N-log] | Real crypto gap | Weak | **REPLACE** (cipher core only) | C++ | Only genuine crypto deficit; keep flavors/ABI |
| NYSER1-style serializer | Plain marshal, 2 runtime hook points | Lambda-`Code.replace` + readers [N-log/N-stat] | Hook-surface gap | Weak | **ADD** (`obfuscator/nyser.py`, Rust later) | Python→Rust | Kills marshal-hook class; version-gate it |
| Marshal-only-via-CTypes hot path | `marshal.loads` ×2 emitted | CT-only, zero fallback [N-doc] | Same gap, other half | Weak | **IMPROVE** (emit path) | C + Python emit | Remove #1 hook point; pin per-version offsets |
| C wipe wiring to payload | Tools exist, path unwired; Python wipe GC-defeated | ob_sval zero + sweep + page-RO | Wiring gap | Weak | **IMPROVE** (wire memguard) | C/Rust | Can't beat GC from Python; wire what exists |
| Byte-list keys/salts | Plaintext literals in output | Runtime-assembled lists [N-log] | Emit gap | Medium | **IMPROVE** | Python emit | Free, no downside |
| `--pytoc` + in-mem exec | Cython helper, no flag, no memfd path | PYTOC + memfd/ExtensionFileLoader [N-log/N-stat] | Product gap | Medium | **ADD ALONGSIDE** (Nuitka stays) | Python CLI + C | Alternative artifact; specialize per use |
| Reorder/substitution container | MULTIDIM/ISR unwired | Staged container [N-stat] | Signature gap | Medium | **ADD ALONGSIDE** | Python | Zero-cost signature break |
| Secure-temp delivery | Plain mkstemp | Purge+O_EXCL/0600+waiter [N-stat] | Hardening gap | Medium | **IMPROVE** | Python + C waiter | Forensics hygiene |
| Build artifact secure cleanup | Plain delete | 3-pass overwrite [N-doc] | Hygiene gap | Medium | **ADD** | Python | Trivial |
| Folded QPC check | Bare thresholds | xor/and/cmp/cmov vs ref [N-stat] | Robustness gap | Medium | **ADD ALONGSIDE** | Rust (`timing`) | Patch-resistant pattern |
| `_verify_eval` | Absent | DLL-range check [N-log] | Small gap | — | **ADD** | Rust (`exec_guard`) | 30 lines, anti-hook |
| Hydra cross-respawn | Watchdogs w/o respawn topology | 3-thread cross-verify [N-doc] | Topology gap | Medium | **ADD ALONGSIDE** tiered | Rust | Self-healing monitor; AV-safe default |
| Per-wrapper compile+eval | Central loader choke | Fragmented `<frozen>` eval [N-stat] | Architecture gap | Medium | **ADD ALONGSIDE** | Rust `jit` + emit | No central choke; budget latency |
| Randomized exports | Stable symbols | Per-build shuffle [N-log] | Cheap gap | Medium | **IMPROVE** | Build-time | Moving target, cheap |
| IAT verification | Hiding ✓, verify ✗ | GetProcAddress ground truth [N-log] | Half gap | Medium | **ADD** (Windows path) | C | Closes hook loop |
| VM confidence + policy | Booleans + fuzzy matcher, no score | 0–100 + KOD [N-doc] | Policy gap | Medium | **ADD ALONGSIDE** | Python policy + Rust/C detectors | Fewer false kills; KOD default-off |
| HWID product lock | Collect + fuzzy 70%, no GCM lock | PBKDF2→AES-GCM-AAD [N-doc] | Product gap | Medium | **ADD ALONGSIDE** | Python + Rust `decrypt` | Real licensing; trial-first |
| Trials + user macros + `__all__` | Cache dicts only; no macros | Trial strings + 8 macros [N-doc] | DX gap | — | **ADD** | Python | Small, high DX value |
| Decompiler Breaker | Junk-shapes, untargeted | EXTENDED_ARG corruption [N-doc] | Technique gap | Weak | **ADD** | Python (`transforms`) | Targets actual first-tool threat |
| HMAC builtin challenge | Absent | Per-use verify [N-doc] | Anti-patch gap | — | **ADD ALONGSIDE** | Python | With perf budget |
| Isolated exec + bind-once dict | Injectable `globals()` bridge | Pre-exec verify + frame-walk dict [N-log] | Real hole | Weak | **IMPROVE** | Python | Closes demonstrated hole |
| O0–O5 ladder | 250 flags, no ladder | Leveled policy [N-doc] | Policy gap | Weak-policy | **ADD** (overlay) | Python | Reproducible presets |
| Per-function 4-backend contest | Single zlib-9 | Best-of-4 per function [N-log] | Size gap | Medium | **IMPROVE** | Python build-time | Parallelizable, build-only |
| Version matrix discipline | Ad-hoc + bypassable pin | 3.10–3.14 select + locked bootstrap | Discipline gap | Medium | **IMPROVE** | Python CI | Stops rot; gates NYSER1/Cython |
| PyInstaller spec automation | Nuitka only | Spec + hidden-import scan | Delivery gap | Medium | **ADD ALONGSIDE** | Python | 1-day parity |
| `NIXON_VERIFY_SKIP_VERSION_CHECK` bypass | Env-var defeats gate | Fail-closed gate [N-stat] | Self-inflicted hole | Weak | **IMPROVE** (scope bypass to CI) | Python | Gate must hold in prod |
| Attestation trio overlap | 3 protocols (Rust/C/relay) | — | Internal redundancy | Medium | **IMPROVE** (Rust canonical) | Rust | Dedupe, keep launcher role |
| C sims/stubs hazards | Unwired but linkable hazards | — | Internal safety | Weak | **IMPROVE** (gate or fix) | C | `NIXON_EXPERIMENTAL` or fix |
| Relay attestation crypto | `DefaultHasher` mislabeled SHA-256, 1-byte secret | — | Correctness hole | Weak | **IMPROVE** (real hash or delete) | Rust | False confidence worse than none |
| Relay `antidebug` flag + fuzz stub + lint | Flag unread, empty target, no clippy | — | Internal hygiene | Weak | **IMPROVE** | Rust | Wire flag, fill/prune fuzz, add clippy |
| Test hygiene (z3 + fixtures) | 18 collection errors, CI red | — | Proof gap | Weak | **IMPROVE** (T0, first) | Python/CI | Nothing provable until green |
| Artifact signing + reproducible mode + loader fuzzing | Absent | Absent too | Beyond-Nyami | — | **ADD** | Python/Rust | Cheap trust wins neither has |
| Kernel-driver detection | Absent | Beta [N-log] | Out-of-model | — | **REJECT** | — | Rootkit-adjacent, beta, off-threat-model |
| Auto-pip-install, hosted service, Lua, gamification, SHA-512-"cipher" | Absent | Present | Not gaps | — | **REJECT** | — | Supply-chain hole / service / marketing |
| In-kernel HWID commitment | TEE exists, unproductized | In-kernel verify [N-log] | Premature | Medium | **INVESTIGATE** (with SGX phase) | Rust | Defer until TEE story ships |

---

## 6. Roadmap

### Phase 1 — Preserve (untouched, guarded by tests)
Rust `runtime/` + `native/stub_win.cpp`, `vm_stub.c`, `microjit` bridge,
`simd_vm` kernels, `rop_exec.h`, Python AST/LLVM/VM orchestration,
evidence pipeline + adversarial loop + LLM layers, Nuitka farm,
`encrypt/aes.py` (build-time role), Cloudflare/Solidity helpers (frozen
scope). Guard: existing suites stay green; new work never regresses them.

### Phase 2 — Improve (existing weaknesses, same homes)
T0 test hygiene (z3 dep or skip-marks; exclude `test_data` fixtures) →
marshal hot path to CT-only → C wipe wiring → byte-list keys → secure-temp
perms → env-bypass scoping → version matrix → attestation dedupe (Rust
canonical) → relay crypto/flag/fuzz/lint hygiene → C sims gating →
O-ladder overlay → per-function contest → randomized exports →
bind-once dict → `NIXON_VERIFY_SKIP_VERSION_CHECK` scoping.
Languages stay where the code lives; no relocations.

### Phase 3 — Add (new, alongside)
NYSER1 serializer → `--pytoc` → reorder container → folded QPC →
`_verify_eval` → Hydra-tiered → per-wrapper eval → IAT verify (Win) →
VM scoring (KOD off) → HWID lock + trials + macros + `__all__` →
Decompiler Breaker → HMAC builtin checks → isolated executor → secure
cleanup → PyInstaller specs → artifact signing + `--reproducible` +
loader fuzzing.

### Phase 4 — Replace (only justified item + correctness fix)
1. Whitebox cipher core in `native/core.cpp` (theater → real Feistel;
   flavors/ABI/blob-plumbing kept; blob-version bump).
2. Relay `attestation.rs` crypto (real SHA-256 or module deletion —
   mislabeled hash is a correctness hole, not a preference).

### Phase 5 — Validate (per integration, not after all)
- Unit: per-module tests (NYSER1 goldens per Python version; Feistel
  NIST-style vectors; QPC/verify_eval unit + flake audit under load).
- Regression: full `pytest` + `cargo test` green; cross jobs
  (ARM/Windows) unchanged; startup-latency budget measured (Hydra,
  per-wrapper eval) with Monitor-tier default.
- Security: hook-simulation (marshal patch, IAT hook, builtin patch,
  debugger attach) must fail closed; `NIXON_VERIFY_SKIP_VERSION_CHECK`
  absent in prod artifacts; AV-scan the Hydra/IAT/page-RO builds.
- Compatibility: 3.10–3.14 matrix; Nuitka vs PYTOC artifact parity;
  trial-expiry and HWID-mismatch paths produce clean errors.
- Threat-model review per addition (§4 gate re-checked at merge).

### Build order (priority)
T0 → cipher-R1 → NYSER1 → CT-marshal + C-wipe → `--pytoc` + secure-temp →
QPC → IAT-verify → `_verify_eval` → Hydra → randomized exports →
VM-score → HWID/trials/macros → reorder container → secure cleanup →
PyInstaller → Decompiler Breaker → O-ladder → bind-once → HMAC builtins →
isolated exec → contest → matrix → dedupe/sim-gating/relay-hygiene →
signing/repro/fuzz. First milestone: **T0 + R1 + NYSER1 + CT-wipe**
(green tests, real crypto, hook class killed).

---

## 7. Corrections to the earlier plan (`ours-vs-nyami-plan.md`)
- VM verdict: earlier "Nyami leads narrowly" understated our side — we
  HAVE a 12-factor weighted fuzzy matcher (70% threshold), i.e. a
  proto-confidence scorer. Gap is policy/unification, not absence.
- Watchdogs: earlier "we have threads but no topology" stands, but live
  read shows real single watchdogs on BOTH OS loaders + Rust checkers —
  gap is strictly the cross-respawn topology.
- Env gate: earlier "we only warn" was wrong — strict `==` + exit(1)
  exists; the hole is the env bypass variable, a narrower fix.
- HWID: earlier "sources collected" understated — full 12-factor keying
  + CF-KV licensing exists; gap is PBKDF2→GCM productization.
- Marshal: confirmed exactly 2 runtime sites (not "paths" vaguely).
- Attestation trio + relay pseudo-SHA256 + C sim hazards + z3/CI details
  are new findings from the live audit (not contradictions — the earlier
  plan predates this read).
