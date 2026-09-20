# Ours vs Nyami (+wider landscape) — additive comparison & integration plan

Date: 2026-09-20. Scope: our pipeline (`obfuscator/`, `irgen/`, `llvmgen/`,
`encrypt/`, `vm/`, `runtime/`-Rust, `native/`-C/C++, `relay/`-Rust,
`scripts/`+`scripts/phases/`, `tests/`, `adversarial_loop.py`,
`benchmark_ai_resistance.py`) vs Nyami commercial (docs-summary +
changelogs v1.1–9.0 + `obf-test.py` deep dig) + general landscape
(PyArmor, pyinstaller/Nuitka/Cython, OLLVM, general anti-debug practice).

Core principle applied throughout: **strictly additive where possible,
selectively evolutionary where necessary, never regressive.** No strong
Rust/C component is replaced with Python. Verdicts: **Keep / Improve /
Replace / Add alongside / Reject**.

---

## 1. What we already have (catalogue, condensed)

### 1a. Rust runtime (`runtime/src/`, 39 modules, ~10k lines, deps only `libc`+`serde_json`)
Pure-Rust AES-CTR, Merkle ledger + CRC32 `.text` integrity, per-exec
recompilation, polymorphic JIT + reg-permutation, ROP gadget scanner +
dispatch chains, Path-ORAM, TEE/SGX dispatch + FFI, HPC/RDPMC emulator
detection + HPC-bound keys, RDRAND entropy + replay-poison nonces,
per-run CFG mutation, SSA variants, state-dependent ISA, class-dispatch
engine, branch/cache/multicore/port entanglement, crypto-CFG tokens,
transient-exec guards, self-healing regions, degradation engine,
exec-guard, sw-attestation challenges, `platform/` page-alloc abstraction
(VirtualAlloc/VirtualProtect + mmap/mprotect), `memguard` scrub/lock.
31/39 modules have `#[cfg(test)]` (~293 tests). Built `opt-z/LTO/strip`.

**Concrete Rust benefits (must not lose):** memory safety without GC,
zero-cost abstractions, fearless concurrency (entanglers/JIT), `no_std`-
friendly crypto with no OpenSSL dependency, deterministic builds,
`PagePerm` abstraction giving us page-protection on both OSes, tiny
release binaries.

### 1b. C/C++ (`native/`, ~13k lines incl. generated `payload.h`)
`core.cpp` (crypto primitives + Python-compile engine, 3 build flavors:
full/`WHITEBOX_ONLY`/`COMPILE_ONLY`), Linux ELF + Windows PE runners,
C VM-interpreter stub, micro-JIT fragment reassembly, chained
per-block key derivation + temporal ratchet, pthread C attestation,
cross-process/distributed-VM channel, fragment migration, GPU-dispatch
stub (CPU fallback), self-healing region restore, SSE4.1 SIMD VM,
struct-layout randomization, header-only ROP executor. Makefile builds
`.so`s, cross targets (`relay-win`, `linux-arm`), mingw stubs,
`-Wall -Werror` compile checks.

**Concrete C benefits (must not lose):** direct syscalls/mmap/mprotect,
inline asm where needed (SIMD), header-only zero-overhead ROP exec,
C-ABI interop with both Rust and CPython (`PyMarshal_ReadObjectFromString`
pattern lives here), cross-compilation to targets Rust doesn't cover well.

### 1c. Rust relay (`relay/src/`, 8 files, ~660 lines)
Pure native launcher: clap CLI → optional `init_runtime` → 12 Linux
anti-debug checks → payload exec. `config_embed` bakes the runtime
manifest at compile time. No networking (quarantined 2026-09-20).

### 1d. Python AST layer (`obfuscator/`, `irgen/`, `llvmgen/`, `encrypt/`, `vm/`)
~20 AST transformers (renamer, string-obf, opaque predicates, CFF, MBA,
junk, reflection, unicode-ids, metadata-strip, checksum inject, dynamic
codegen…), classification/routing pass, dataflow obfuscation, decoy APIs,
LLM-specific layers (attention-poison, reasoning traps, adversarial dead
code, prompt injection, fingerprinting — **no Nyami equivalent**),
custom IR + optimizer, OLLVM passes (bcf/fla/sub) via llc, pure-Python
AES-CTR + ELF patcher + NYCO-like NIX container + x86_64 XOR stub,
dynamic-ISA Python VM + per-build opcode shuffle + fused/split ops.

### 1e. Orchestration & assurance (`scripts/`, ~80 dirs + 30 build phases + ~50 audit phases; `tests/`, 2700 collected; `adversarial_loop.py`, `benchmark_ai_resistance.py`)
200+-flag `build.py` over phased pipeline (obfuscate→config→compile→
encrypt→payload→package→phase2→ROP→adversarial→provenance→…→HPC/TEE/GPU/
poly/temporal/dispersal), ~50 audit/eval phases (claims, proofs, redteam
angr/bninja, SMT validation, leakage, ZK state, FHE VM…), AI-resistance
benchmark harness scoring 4 free models + self-improving adversarial loop.
Unique in landscape: **evidence-carrying pipeline** (every protection
claim has a verification phase).

### 1f. What we have that Nyami lacks entirely
LLVM pipeline, ROP chains, ORAM, TEE/SGX, HPC-bound keys, SIMD/micro-JIT
VMs, ZK/FHE experiments, Merkle ledger proofs, adversarial AI loop,
~50 audit phases, LLM-specific poisoning, Nuitka/GitHub build farms,
whitebox-AES *flow entanglement* (different from Nyami's white-box cipher).

---

## 2. Feature-by-feature comparison (Nyami capability → ours → verdict)

### A. AST/source transforms — mostly PARITY, ours broader
| Nyami | Ours | Verdict |
|---|---|---|
| Seeded renamer, short names | `SymbolRenamer` + unicode-ids | **Keep** (ours stronger) |
| Integer/number convertor | `ConstantUnfolder` + MBA-adjacent | **Keep** |
| CFF, opaque predicates, MBA(4), junk, WIF, minifier | All present as transformers | **Keep** |
| Per-function encrypt-at-call-time / Lite (marshal+zlib) | FunctionTransformer + marshal paths, but marshal via **hookable Python `marshal.loads`** (pipeline.py:260,964,988; sources.py:988) | **Improve** (see §4-I1) |
| Per-function separate compression, 4-backend contest | Single zlib-9 (`marshal.dumps`+compress) | **Improve** (see §4-P4) |
| Optimization levels 0–5 (incl. decoy/junk stripping) | 200+ flags but no coherent O0–O5 ladder | **Add alongside** (see §4-P5) |
| GUI/gamepad compat handling | Nuitka farm exists; no explicit compat profile | **Improve** (fold into P5) |
| `__all__` preservation (importable modules) | **Missing** | **Add alongside** (P6) |

### B. Bytecode / VM — OURS STRONGER, one Nyami idea to steal
| Nyami | Ours | Verdict |
|---|---|---|
| Abstract-ISA interpreter | Python dynamic-ISA VM + Rust `simd_vm` + C `vm_stub` + micro-JIT | **Keep** |
| EXTENDED_ARG Decompiler Breaker | **Missing as such** (we have junk/NOPs, not targeted decompiler-killers) | **Add alongside** (I3) |
| Per-wrapper `<frozen>` compile+eval (5×EvalCode/3×CompileString in native) | Our eval sites are Python-level | **Add alongside** in Rust (I4) |
| `_verify_eval` DLL-range check | **Missing** | **Add alongside** in Rust (I5) |

### C. Strings/constants — PARITY/ours stronger
XOR-per-session, ChaCha20 variant, multi-encoding, 5-scheme KDF, cipher
suite → our string tables + swizzle + `OpcodeMorpher` + AES-CTR cover it.
**Keep.** (Nyami's "SHA-512 as cipher" is marketing; ignore.)

### D. Crypto/packaging — PARITY, one real gap
AES-GCM per-build, 5 stubs, pyzstd, NYCO+watermark, bootstrap pack →
covered by NIX container + AES-CTR + manifest + ledger. Gaps:
- **White-box 8-round Feistel (key-as-S-boxes)** vs our `core.cpp`
  "educational 4-round AES-lite, linear key schedule, **no true S-box**"
  (file's own comment) → **Replace** the toy cipher (R1), keep everything
  around it.
- Reorder+substitution container packing → our MULTIDIM+ISR primitives
  exist but aren't a loader container → **Add alongside** (I2).
- Parallel contests/ThreadPool+GIL-release build speedup → our build is
  single-threaded Python → **Improve** (P7).

### E. Native compilation — NYAMI LEADS, adopt pattern
Nyami PYTOC (py→pyx→C→pyd, true in-memory exec) vs our Nuitka farm +
`compile_payload_to_cython` helper buried in pipeline.py:1394 (no CLI
flag, no in-memory exec) → **Add alongside**: `scripts/build.py
--pytoc` + memfd/`ExtensionFileLoader` delivery hardening (I1), Cython
kept as *alternative* to Nuitka (specialize: Nuitka for standalone
binaries, Cython for single-file importable `.pyd`).

### F. Anti-debug — PARITY, two Nyami extras
11 methods/tiers, IDP-called, trace/profile polling, audit hooks, frame
validation, native watchdog, driver detection → our antidbg(12 checks)+
CROSS_PLATFORM_GUARD+timing traps+`_getframe` walkers+attestation cover
~80%. Gaps: **folded QPC check** (xor/and/cmp/cmov vs stored ref, not
bare threshold) → **Add alongside** (I6, Rust); **kernel-driver
detection (beta)** → **Reject** (beta, Windows-only, rootkit-adjacent).
Python watchdog loop → ours should stay **native** (already have the
threads; just add the checks).

### G. Anti-VM — NYAMI LEADS narrowly
13-signal weighted `VM_CONFIDENCE` + KOD vs our boolean VM checks →
**Add alongside**: scored confidence + policy (I7, Python orchestration +
existing Rust/C detectors). KOD itself = existing `scrub_and_exit` with
a policy trigger — no new primitive needed.

### H. Anti-tamper — SPLIT
Hydra 3-thread cross-verify, HMAC challenge-response on builtins,
namespace-isolated executor w/ SHA-256 pre-exec verify, bind-once
frame-walk host dict, IAT-vs-GetProcAddress verify, per-build randomized
exports → verdicts: Hydra pattern **Add alongside** (I8, Rust threads —
we have threads but no cross-respawn topology); HMAC builtin
challenge-response **Add alongside** (I9, Python); namespace-isolated
executor **Add alongside** (I10, Python); bind-once host dict
**Improve** our `globals()` bridge (P8); IAT verification **Add
alongside** in `native/` Windows path (I11, C — 20 lines, huge hook-
resistance win); randomized exports **Improve** (P9, build-time symbol
shuffle — cheap).

### I. Anti-memory-dump — NYAMI LEADS, adopt carefully
`co_code` zeroing via `ob_sval` offset + `gc.get_objects` sweep +
segfault fallback; page-RO; split secrets; marshal-only load; byte-list
keys → ours: `secure_zero` is **best-effort Python** (own docstring admits
GC copies survive) + `memguard`/`platform` page tools **exist but are not
wired to the Python payload path**. Plan: **Improve** by moving the wipe
to C/Rust (I12) — do NOT try to outsmart CPython allocator from Python.
Byte-list keys → **Improve** (P10, emit-time change, free).

### J. Licensing — NYAMI LEADS, adopt subset
PBKDF2-HWID→AES-GCM-AAD, in-kernel HWID commitment, trial strings,
SELF/SECURE_DELETE, detached waiter → ours: HWID sources collected but
no productized lock; no trials; no user macros. **Add alongside**:
PBKDF2-HWID lock (I13), trial expiry (I14), user macros incl.
`IS_OBFUSCATED`/`__all__` (P6), secure-temp delivery incl. stale purge +
O_EXCL/0600 + waiter (I15). In-kernel HWID → defer to phase 2 (needs TEE
story). Blockchain license helpers in pipeline.py (Cloudflare/KV/Solidity)
→ **keep code, don't expand** (niche).

### K. Serialization — NYAMI LEADS, top adoption
NYSER1 lambda-template `Code.replace` reconstructor vs our plain
`marshal.dumps/loads` → **Add alongside** NYSER1-style serializer (D1):
Python AST-level now, Rust later. Kills marshal-hooking as a class.

### L. Delivery/UX — NYAMI LEADS on packaging, we lead on assurance
PyInstaller spec automation, version-select matrix, auto module install,
API/CI, dashboard → verdicts: PyInstaller spec gen **Add alongside**
(I16, Python — 1 day); version-select **Improve** (P11 — gate matrix is
currently ad-hoc); auto-deps **Reject** (pip-install-at-obfuscation is a
supply-chain hole); hosted API/dashboard **Reject** (service, not
pipeline; our `GitHubBuildFarm` already covers CI).

### M. Test-suite health (found during catalogue — fix first)
18 collection errors (missing `z3`, 14 absent helper modules, 3
`test_data/*.py` mis-collected). Not Nyami-related but blocks proving
any of the above. → **Improve** (T0).

---

## 3. Weak / redundant components (honest list)

1. **`native/core.cpp` whitebox cipher (WEAK, file admits it)** — 4-round
   AES-lite, linear schedule, no S-box. Anything relying on it for real
   secrecy is theater. → **Replace** cipher core only (R1); keep the 3
   build flavors, compile engine, ABI.
2. **Python `marshal.loads` on critical paths (WEAK)** — hookable single
   choke point, exactly what Nyami v6 fixed. → **Improve** → marshal-only-
   via-CTypes loader + NYSER1 alongside (I12/D1); keep marshal for
   non-critical paths.
3. **Python `secure_zero` (WEAK by language)** — cannot work reliably
   under CPython GC. → **Improve** by moving to C (`memset`+`explicit_
   bzero`+`mlock/mprotect`) behind the existing `memguard` API (I12).
4. **`encrypt/aes.py` pure-Python AES (SLOW but CORRECT)** — fine for
   build-time use; must never be runtime hot path. → **Keep** for build,
   route runtime through Rust `decrypt` (already exists; verify wiring).
5. **Overlapping Rust/C attestation (REDUNDANT trio)** — `sw_attestation`
   + `attestation.c` + `relay/attestation.rs` do challenge-response three
   ways. → **Improve**: keep Rust as canonical, C as FFI shim, relay's as
   launcher-only; dedupe protocol (P12).
6. **867-line `rop.rs` + header `rop_exec.h` + `irgen/rop_compiler.py`
   (OVERLAP, not redundant)** — three levels (scan/chain, exec, compile).
   Keep all; add a doc line owning each layer. **Keep.**
7. **80 `scripts/` dirs / 80 phases (BLOAT RISK, not yet redundant)** —
   real capability (evidence pipeline) but unnavigable. → **Improve**:
   phase registry + dependency graph (P13), no deletions.
8. **Nyami-chasing traps to REJECT**: kernel-driver detection (beta,
   rootkit-adjacent), auto-pip-install, hosted service, SHA-512-"cipher",
   Lua obfuscator, roulette/levels/gamification.

---

## 4. Integration plan (additive; nothing strong removed)

### T0. Test hygiene FIRST (Python, 0.5 d) — unblocks proof of everything
Declare `z3` dependency or skip-mark SMT tests; create the 14 missing
helper modules or prune their imports; exclude `test_data/*.py` from
collection. Benefit: green baseline to measure regressions.

### Phase 1 — crypto + serializer core (weeks 1–3)
- **R1 Replace toy whitebox (C++, native/core.cpp only).** Real 8-round
  Feistel, SHA-256-expanded S-boxes, no key bytes at rest. Keeps flavors/
  ABI. Benefit: turns theater into actual WhiteBox. Risk: interop with
  existing blobs → version the blob header.
- **D1 NYSER1-style serializer (Python now: `obfuscator/nyser.py`;
  Rust later).** Lambda-template `Code.replace` reconstructor + readers.
  Benefit: kills marshal-hook deobfuscation class. Risk: version-sensitive
  (`co_*` fields drift 3.10–3.14) → gate by `python_version` matrix (P11).
- **I12 Marshal-only-via-CTypes + C wipe (C + Python emit).** Loader emits
  `ctypes.PyMarshal_ReadObjectFromString`, zero `marshal.loads` on hot
  path; buffers wiped via C `explicit_bzero` + `mlock`. Benefit: removes
  the #1 hook point. Risk: CPython ABI drift → pin per-version offsets
  with tests.
- **P10 Byte-list keys (Python emit, free).** Emit keys/salts as
  runtime-assembled lists. Benefit: no plaintext secrets in output.

### Phase 2 — delivery hardening (weeks 3–5)
- **I1 `--pytoc` + secure-temp delivery (Python CLI + C).** Cython
  py→pyx→C→pyd as Nuitka alternative; memfd-else-O_EXCL/0600 +
  stale-purge + atexit + detached waiter. Benefit: single-file native
  artifacts + fileless-capable delivery. Risk: Cython version matrix →
  reuse P11.
- **I2 Reorder+substitution container (Python, wire MULTIDIM+ISR).**
  Benefit: breaks the current single-shape loader signature. Risk: none
  (pure emit change).
- **I15 Secure cleanup of build artifacts (Python).** 3-pass overwrite
  before delete. Benefit: forensics hygiene. Trivial.
- **I16 PyInstaller spec automation (Python).** Hidden-import scan +
  spec gen. Benefit: exe delivery parity. 1 day.

### Phase 3 — runtime watchers (weeks 5–8, Rust-first)
- **I6 Folded QPC check (Rust `timing`).** Dual-timer + xor/and/cmp/cmov
  vs stored ref. Benefit: threshold-patching resistance. Small.
- **I5 `_verify_eval` (Rust `exec_guard`).** DLL-range check on resolved
  eval pointer. Benefit: anti-hook. Small.
- **I11 IAT verification (C, Windows path).** GetProcAddress ground truth
  at init + periodic. Benefit: kills IAT hooking. ~20 lines + thread.
- **I8 Hydra threads (Rust).** 3 cross-respawning watchers (trace/profile,
  heartbeat, IAT). Benefit: self-healing monitor. Risk: AV heuristics
  flag aggressive respawn → make tiers (Off/Monitor/Enforce).
- **I4 Per-wrapper compile+eval (Rust `jit` + Python emit).** Each staged
  function compiles own `<frozen>` source. Benefit: no central loader
  choke. Risk: startup latency → measure (Nyami got 30 s→3 s; we budget).
- **P9 Randomized exports (build-time, Rust/C).** Symbol shuffle per
  build. Benefit: moving target. Cheap.

### Phase 4 — policy + product (weeks 8–10, Python)
- **I7 VM confidence scoring (Python + existing detectors).** Weighted
  0–100 + policy (warn/kill). Benefit: fewer false-positive kills than
  booleans. Risk: fingerprinting backlash → document + default-off KOD.
- **I13/I14 HWID lock + trials (Python + Rust `decrypt`).**
  PBKDF2→AES-GCM-AAD machine binding; `1h/1d/1w/1mo` expiry in payload.
  Benefit: actual licensing story. Risk: support burden (HW changes) →
  trial-first rollout.
- **P6 User macros (Python).** `IS_OBFUSCATED`, `GET_HWID`, `__all__`
  preservation. Benefit: DX + importable modules. Small.
- **P5 O0–O5 ladder (Python).** Coherent optimization/decoy policy over
  the 200 flags. Benefit: reproducible presets, compat profiles.
- **P8 Bind-once host dict (Python).** Frame-walk-set, identity-enforced
  exec. Benefit: closes injectable-`globals()` hole.
- **I9 HMAC builtin challenge-response (Python).** Verify
  exec/eval/compile/__import__ before use. Benefit: anti-patch.
- **I10 Namespace-isolated executor (Python).** SHA-256 pre-exec verify.
  Benefit: defense in depth on exec path.

### Phase 5 — architecture hygiene (ongoing)
- **P11 Version matrix (Python).** 3.10–3.14 CI × feature gates
  (NYSER1 fields, Cython, eval offsets). Benefit: stops version rot.
- **P12 Attestation dedupe (Rust canonical).** One protocol, C shim,
  relay launcher-only.
- **P13 Phase registry (Python).** Declared deps + DAG + `--list-phases`.
  No deletions. Benefit: navigability without losing evidence pipeline.

### Rejected (with reason)
Kernel-driver detection (beta/rootkit-adjacent); auto-pip-install
(supply-chain hole); hosted API/dashboard (service, not pipeline);
SHA-512-as-cipher (not a cipher); Lua; gamification; single-sha
integrity; int-list hiding; settrace-hygiene; in-file XOR keys.

---

## 5. Language choices (per change)
Rust: I4, I5, I6, I8, P9, P12 (concurrency, threads, pointers, no-GC
guarantees, existing modules own the code). C/C++: R1, I11, I12-wipe
(syscalls, page control, ABI, existing files own it). Python: D1-now,
I1-CLI, I2, I7-policy, I9, I10, I13/14-policy, I15, I16, P5, P6, P8,
P11, P13, T0 (ecosystem, AST, orchestration, iteration speed).

## 6. Risks & compatibility
- CPython drift (3.10–3.14 `co_*`, marshal, C-API offsets) → P11 matrix
  + per-version golden tests; NYSER1 version-gated.
- AV/EDR heuristics (Hydra respawn, page-RO, IAT threads, HWID) →
  tiered enforcement (Off/Monitor/Enforce), default Monitor.
- Startup latency (per-wrapper compile, Hydra) → budget + measure;
  Nyami precedent (30 s→3 s) shows headroom via caching (our
  `per_exec_recompile` already caches).
- Cross-compilation (mingw/ARM) → R1/I11 changes gated to tested targets;
  existing `relay-win/linux-arm` jobs stay green.
- No wire-format breaks without blob-version bump (R1/D1 change loader).

## 7. Priority order (if forced to cut)
T0 → R1 → D1 → I12 → I1 → I6 → I11 → I5 → I8 → P9 → I7 → I13/14 → P6 →
I2 → I15 → I16 → P5 → P8 → I9 → I10 → P11 → P12 → P13.
First shippable hardening milestone: **T0+R1+D1+I12** (crypto real +
serializer new + hook point closed + green tests).
