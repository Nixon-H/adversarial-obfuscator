# Shadow Compiler — Nixon Protection Pipeline

## Overview
The Shadow Compiler is a multi-stage pipeline that transforms Python source into an unrecoverable form delivered as a tiny native binary. Phases 1-6 form the baseline pipeline. Phases 7-15 (Phase 2) add advanced protections behind the `--phase2` flag. Phase 2 Extras (Section 19 techniques) are behind `--phase2-extras`.

## Pipeline Architecture
```
Python Source
    │
    ▼
┌──────────────────────────────┐
│ Phase 1: AST Obfuscation     │  obfuscator/core.py
│ 6 transforms                 │  cfg-flatten, opaque-predicates,
│                              │  bogus-exceptions, mba-subs,
│                              │  fragment-strings, unicode-ids
└──────────┬───────────────────┘
           ▼
┌──────────────────────────────┐
│ Phase 2: Classification Pass │  obfuscator/classification.py  ← NEW
│ (routing decision)           │  Detects crown jewel / JIT /
│                              │  standard functions via heuristics
│                              │  + explicit @protect() tags
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Standard (90-95%)│   │ Crown Jewel(5-10%)│   │ JIT Target (<1%) │
│ Shadow IR → LLVM │   │ VM bytecode path  │   │ Encrypted JIT    │
│ → native binary  │   │ full protection   │   │ specialization   │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Phase 3: IR      │   │ Phase 7: VM ISA  │   │ Phase 9: JIT     │
│ Compiler         │   │ + bytecode comp  │   │ Template Gen     │
│ (SSA, optimiser) │   │ + interpreter    │   │ (encrypted IR)   │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Phase 4: LLVM    │   │ Phase 8:         │   │ Phase 10: JIT    │
│ Codegen          │   │ Mutating ISA     │   │ Runtime Cache    │
│ (BCF, FLA, SUB)  │   │ (per-build op    │   │ (on-demand       │
│                   │   │  encoding)       │   │  specialization) │
└────────┬─────────┘   └──────────────────┘   └──────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ ┌─ Phase 11: Variant Pool ──┐│  irgen/variant_pool
│ │ (crown jewel code clones) ││  — disabled by default
│ └───────────────────────────┘│
│ ┌─ Phase 12: Provenance ────┐│  obfuscator/provenance
│ │ Removal                   ││  — disabled by default
│ └───────────────────────────┘│
│ ┌─ Phase 13: Dataflow ──────┐│  obfuscator/dataflow
│ │ Obfuscation               ││  — disabled by default
│ └───────────────────────────┘│
│ ┌─ Phase 14: Semantic ──────┐│  irgen/fragmentation
│ │ Fragmentation             ││  — disabled by default
│ └───────────────────────────┘│
│ ┌─ Phase 15: Watermark ─────┐│  irgen/watermark
│ │ Embedding                 ││  — disabled by default
│ └───────────────────────────┘│
└──────────────────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Phase 5: Block Encryption    │  encrypt/encrypt.py
│ Per-block AES-256-CTR        │  ELF patcher, stub injector
└──────────┬───────────────────┘
           ▼
┌──────────────────────────────┐
│ Phase 6: Runtime (Rust)      │  runtime/ (Rust crate)
│ Decryptor, integrity check,  │
│ memory scrub, self-destruct  │
└──────────┬───────────────────┘
           ▼
┌──────────────────────────────┐
│ Stage 6: Native Launcher     │  relay/ (Rust binary)
│ Stripped C2, synchronous,    │
│ anti-debug, payload exec     │
└──────────────────────────────┘
```

## Phase 1 — AST Pipeline (Done)
- obfuscator/core.py with 6 transforms
- CLI with per-transform toggle
- Whitebox AES payload encryption
- Build pipeline integration

## Phase 2 — Classification Pass (Done, behind `--phase2`)
### Tasks
- [x] Function-level classification (standard / crown_jewel / jit_target)
- [x] Heuristic scoring engine (crypto ops, control flow, constants, startup patterns)
- [x] `@protect('crown_jewel')` / `@protect('jit')` / `@protect('standard')` decorator support
- [x] `extract_decorations()` — explicit tag extraction
- [x] `generate_classification_report()` — terminal report with scores
- [x] CLI: `python -m obfuscator.classification scan <source.py>`
- [x] CLI: `python -m obfuscator.classification classify <source.py> -o report.txt`
- [x] Config-driven thresholds (`crown_jewel_threshold`, `jit_threshold`)
- [x] Build pipeline integration (`--classify`, `--phase2`, `--phase2-only`)
- [x] Verification script: `scripts/verify_phase2.py`

### Why
Without classification every function gets the same protection. Crown jewel functions (crypto, licensing, key derivation) deserve VM bytecode isolation. JIT targets (startup config, init) benefit from encrypted templates rather than bloated protection. The pass routes each function to the right pipeline path.

## Phase 3 — Custom IR Compiler (Done)
### Tasks
- [x] IR spec and text format
- [x] Python→IR compiler (ast → ir)
- [x] IR optimizer (const fold, DCE, block merge)
- [x] CLI: python -m irgen input.py -o output.ir

### Why
IR decouples source from machine code, enabling targeted obfuscation at the right abstraction level.

## Phase 4 — LLVM Codegen + Obfuscation (Done, all passes validated)
### Tasks
- [x] IR→LLVM IR lowering (parser: module @name, func @name(params) -> type, jmp/eq/mod pseudo-ops)
- [x] BCF (Bogus Control Flow) pass — verified `llc` produces valid .o
- [x] FLA (Control Flow Flattening) pass — alloca lift + rename fix for SSA dominance
- [x] SUB (Instruction Substitution) pass — verified `llc` produces valid .o
- [x] .text section integrity check injection
- [x] Call argument type inference + auto-declare for undefined callees
- [x] Unicode function name quoting for LLVM IR (`@"名前"`)
- [x] CLI: `python -m llvmgen input.ir -o output.o --ollvm-passes bcf fla sub`

### Why
LLVM IR gives us access to production-quality codegen while injecting obfuscation at the IR level before lowering.

## Phase 5 — Per-Block Encryption (Done)
### Tasks
- [x] ELF parser (pure Python, no deps)
- [x] Per-block AES-256-CTR encryption
- [x] Position-independent decryptor stub (x86_64)
- [x] Binary patcher (encrypt blocks in-place)
- [x] CLI: python -m encrypt input.bin -o output.bin

### Why
Even if the binary is dumped from memory, each block must be decrypted individually. Static analysis sees only ciphertext.

## Phase 6 — Minimal Runtime (Done)
### Tasks
- [x] Pure Rust AES-256-CTR implementation
- [x] CRC32 integrity checker
- [x] Memory scrubbing (zero on exit)
- [x] Page protection (mprotect/mlock)
- [x] Self-destruct on tamper detection

### Why
The runtime handles decryption, integrity verification, and anti-forensics without any external dependencies.

## Phase 7 — Native Launcher / Relay Refactor (Done)
### Tasks
- [x] Strip C2 code (cloudflare, socks5, tunnel, dns)
- [x] Remove tokio/async (synchronous only)
- [x] Embed runtime features
- [x] Target binary size < 500KB
- [x] Cross-compile: Linux x86_64 + ARM64, Windows x86_64

### Why
The binary should be a pure launcher — decrypt, integrity check, execute, self-destruct. No networking, no C2, no server.

## Phase 8 — VM ISA + Bytecode Compiler (Built, behind `--phase2`)
### Tasks
- [x] Custom VM instruction set (16 registers, 8/16-bit opcodes, variable-width encoding)
- [x] Python→VM bytecode compiler (crown jewel functions only)
- [x] VM interpreter with computed dispatch (state-dependent handler resolution)
- [x] x86_64 VM stub (`native/vm_stub.c`) for native embedding
- [x] CLI: `python -m vm compile`, `python -m vm run`

### Why
Crown jewel functions execute inside a custom VM whose instruction set changes every build. Static analysis of VM bytecode reveals nothing about the original logic.

## Phase 9 — Mutating ISA (Built, behind `--phase2`)
### Tasks
- [x] Level 1: Opcode permutation table (Fisher-Yates shuffle per build)
- [x] Level 2: Handler permutation (semantics-preserving micro-op reordering)
- [x] Level 3: Instruction fusion/splitting (LOAD+ADD→LOAD_ADD, etc.)
- [x] IR mutation pipeline: `python -m irgen.mutation apply input.ir`

### Why
Even if an attacker dumps the VM bytecode, they cannot decode it without the per-build permutation key. The same source produces structurally different bytecode every build.

## Phase 10 — JIT Template Generation (Built, behind `--phase2`)
### Tasks
- [x] Template IR (parameterised IR blocks with slot markers)
- [x] Encrypted template storage (AES-256-CTR with JIT magic header)
- [x] Runtime JIT specializer in Rust (`runtime/src/jit.rs`: mmap → fill → mprotect → exec)
- [x] JIT memory manager (allocation, scrubbing, deallocation)
- [x] CLI: `python -m irgen.jit_template generate input.ir`

### Why
JIT target functions (small, startup code) don't need the full pipeline. An encrypted template that gets specialized and compiled at runtime is smaller and protects against static analysis.

## Phase 11 — Variant Pool (Built, behind `--phase2`)
### Tasks
- [x] Multi-variant code clone generator (4 strategies: loop/recursive/table/unrolled)
- [x] Build-time variant selection (deterministic from build seed)
- [x] Runtime variant selection (BLAKE3-based, different variant per execution)
- [x] CLI: `python -m irgen.variant_pool generate source.py`

### Why
An attacker reverse-engineering one execution sees only one variant. The next run takes a different code path from the pool. Transferable RE knowledge approaches zero.

## Phase 12 — Provenance Removal (Built, behind `--phase2`)
### Tasks
- [x] Error message scanner + integer error code replacement
- [x] Protocol/format string detection + encoding (XOR fragment assembly at runtime)
- [x] Algorithmic constant scanner (SHA-256 IVs, golden ratio, xxHash constants)
- [x] Constant obfuscation (runtime-computed expressions, never stored as literals)
- [x] Library call pattern wrapping (adapter functions with generated names)
- [x] Binary audit: `python -m obfuscator.provenance audit binary.bin`
- [x] CLI: `python -m obfuscator.provenance {scan,strip,audit}`

### Why
Analysts identify algorithms faster through data (strings, constants, imports) than through code. Provenance removal eliminates these fingerprints.

## Phase 13 — Data-Flow Obfuscation (Built, behind `--phase2`)
### Tasks
- [x] Affine variable encoding: `x_enc = (A*x + b) mod 2^64`, per-variable per-build constants
- [x] Value splitting across multiple storage locations (XOR masks, reconstruct on use)
- [x] MBA state encoding: `x = (v*C1) ^ ((v<<S1)|(v>>64-S1)) + (v&M1) - (v|M2)`
- [x] Affine state encoder for VM registers (decode only at I/O boundaries)
- [x] CLI: `python -m obfuscator.dataflow {encode,split,pipeline}`

### Why
Symbolic execution tools handle flattened control flow — they follow data, not structure. Data-flow obfuscation attacks the relationship between variable definitions and uses.

## Phase 14 — Semantic Fragmentation (Built, behind `--phase2`)
### Tasks
- [x] Algorithm analyzer (data-flow analysis to find optimal split boundaries)
- [x] Fragment generator (split function into N fragments, each meaningless in isolation)
- [x] Coordinator generator (encrypted calling sequence, function pointer table at runtime)
- [x] Fragment distribution across modules (different naming pools per module)
- [x] CLI: `python -m irgen.fragmentation {analyze,fragment}`

### Why
A complete function has a recoverable boundary. Fragmentation destroys the natural unit of analysis — fragments distributed across the binary look unrelated.

## Phase 15 — Watermark Embedding (Built, behind `--phase2`)
### Tasks
- [x] BCH error-correcting code (BCH(127,64) with GF(2^8), corrects 30-40% bit loss)
- [x] IR-level watermark embedder (CFG pattern insertion: P0/P1 per bit)
- [x] Watermark detector (IR-level and binary-level via basic block analysis)
- [x] Per-customer build support (CUSTOMER_ID + BUILD_ID → unique watermark bits)
- [x] CLI: `python -m irgen.watermark {gen,embed,detect,detect-binary}`

### Why
Watermarking does not protect code — it identifies it. If protected code leaks, watermarks identify which build and which customer.

## Phase 16 — CI/CD + Per-Build Uniqueness (Built)
### Tasks
- [x] GitHub Actions pipeline for all baseline stages (`.github/workflows/shadow-build.yml`)
- [x] Per-build random seed generation (BUILD_ID, MASTER_KEY, OPAQUE_SEED, STATE_SEED)
- [x] Build manifest (logs seed, config, git hash)
- [x] Artifact archiving (binary + manifest)
- [x] Per-build uniqueness: different opaque predicates, state values, constants, encryption every build

### Why
Every build produces a unique binary. Same source → different binary each time. No two builds are identical. Reversing build N provides zero transferable knowledge to build N+1.

## Optional Protection Techniques (behind `--phase2-extras` flag)

These techniques are available but **disabled by default**. They add complexity without proportional security value for most use cases. Enable individually via config or with the `--phase2-extras` flag:

| Technique | Location | Effect | Why Disabled by Default |
|-----------|----------|--------|------------------------|
| Anti-debug API checks | `relay/src/antidbg.rs` | ptrace, TracerPid, timing, seccomp checks | Catalogued by ScyllaHide; minimal value against professionals |
| Process/VM detection | (available if configured) | Detect debuggers, hypervisors, sandboxes | Easily defeated; attackers use bare metal |
| Memory header wiping | (available if configured) | Zero PE/ELF headers at runtime | Detectable pattern; forensic tools recover anyway |
| Self-deleting binary | (available if configured) | Delete binary file during execution | OS forensics recover deleted files |
| AMSI/ETW bypass | (available if configured) | Security tool evasion, Windows only | Security evasion, not IP protection |
| Import table obfuscation | (covered by provenance removal) | Hide imported function names | Already covered by Phase 12 |
| Packing (UPX etc.) | (available if configured) | Compress binary, decompress at load | Trivially unpacked; minutes of friction |
| Timing checks | (available if configured) | Detect single-stepping debuggers | Defeated by instruction-count-based emulation

## Build Order

| Step | Phase | Component | Est. time | Status |
|------|-------|-----------|-----------|--------|
| 1 | Phase 1 | AST obfuscation (6 transforms) | 2-5s | Built |
| 2 | Phase 2 | Classification pass | 0.5-1s | Built |
| 3 | Phase 12 | Provenance removal | < 1s | Built |
| 4 | Phase 13 | Data-flow obfuscation | 1-3s | Built |
| 5 | Phase 3 | IR compilation + optimisation | 1-2s | Built |
| 6 | Phase 11 | Variant pool generation | 2-5s | Built |
| 7 | Phase 14 | Semantic fragmentation | 1-2s | Built |
| 8 | Phase 15 | Watermark embedding | < 1s | Built |
| 9 | Phase 4 | LLVM codegen (BCF, FLA, SUB) | 3-8s | Built |
| 10 | Phase 10 | JIT template generation | 1-3s | Built |
| 11 | Phase 8 | VM compile (crown jewel fns) | 3-10s | Built |
| 12 | Phase 9 | Mutating ISA generation | 2-5s | Built |
| 13 | Phase 5 | Block encryption + stub | 1-2s | Built |
| 14 | Phase 6 | Runtime compile (Rust) | 30-60s | Built |
| 15 | Phase 7 | Relay compile / cross | 60-180s | Built |
| 16 | Phase 16 | Package + manifest | < 1s | Built |
| 17 | Phase 2 Extras | Optional protection techniques (--phase2-extras flag) | < 1s | Built |

**Total (baseline, no phase2):** ~100-260s
**Total (full phase2):** ~115-320s

## Honest Limits
- **VM interpreter overhead**: Crown jewel functions inside the VM run 10-50x slower than native. The classification pass must be conservative — only 5-10% of functions should be tagged as crown jewel.
- **JIT templates are not baseline JIT**: The template system specialises parameterised IR blocks at startup. It does not do hot-path profiling. It trades startup latency for smaller binary size.
- **Mutating ISA ≠ cryptographic security**: Opcode permutation makes static analysis harder, but a determined attacker with execution traces can reconstruct the mapping. Per-run keys help but do not eliminate this.
- **Variant pool increases binary size**: Each variant is a copy of the function. 3 variants × 5 crown jewel functions can add 100-300KB to the binary.
- **Phase 2 features are experimental**: All Phase 2 features (7-15) are available behind `--phase2` but are not battle-tested. Expect edge cases with complex Python and longer build times.
- **LLVM codegen validated**: All three OLLVM passes (BCF, FLA, SUB) verified to produce valid `.o` files through `llc`. FLA dominance fix (alloca lift + renumber) resolved the last `llc` rejection.
- **No cloud / C2**: The pipeline produces standalone binaries. No phone-home, no C2, no licensing server integration.

## Status (June 2026)
### Baseline Pipeline (always on, no flag needed)
- Phase 1: AST Obfuscation — 6 transforms (rename, flatten, predicates, constants, dead code, substitution)
- Phase 3: Custom IR compiler + optimizer (SSA, constant folding, DCE, block merging)
- Phase 4: LLVM codegen + OLLVM passes (BCF, FLA, SUB, .text integrity)
- Phase 5: Per-block AES-256-CTR encryption + ELF patcher + decryptor stub
- Phase 6: Minimal Rust runtime (AES, CRC32, mprotect, self-destruct)
- Phase 7: Rust native launcher (no C2, no tokio, < 500KB, cross-compile)
- Phase 16: CI/CD pipeline, per-build seeds, build manifest, GitHub Actions
- C++ native core (whitebox AES)
- Anti-debug (12 checks)
- Test suite (146 passing — 20 encrypt + 3 core + 4 obfuscator + 3 pipeline + 2 stub + 2 payload + 113 phase2)

### Phase 2 Extensions (behind `--phase2` flag)
- Phase 2: Classification pass (heuristic scoring + `@protect()` decorators) — 13 tests
- Phase 8: VM ISA + bytecode compiler + interpreter (36 opcodes, computed dispatch) — 9+6+11 tests
- Phase 9: Mutating ISA (3 levels: opcode shuffle, handler permute, fusion/split) — 11 tests
- Phase 10: JIT template generation + Rust runtime specializer (mmap + exec) — 6 tests
- Phase 11: Variant pool (4 strategy generator, build-time + runtime selection) — 9 tests
- Phase 12: Provenance removal (string encoder, constant mangler, library wrapper) — 11 tests
- Phase 13: Data-flow obfuscation (affine encoding, value splitting, MBA expressions) — 9 tests
- Phase 14: Semantic fragmentation (algorithm decomposition, coordinator, pointer table) — 6 tests
- Phase 15: IR-level watermarking (BCH error correction, embed/detect, per-customer builds) — 13 tests
- All 11 Phase 2 component imports verified working via `scripts/verify_phase2.py`
- 113 Phase 2 unit tests total — all passing

### Optional Extras (behind `--phase2-extras` flag, wired as pipeline step 17)
- Anti-debug API calls, process/VM detection, header wiping, self-delete, AMSI/ETW bypass
- Packing (UPX), timing checks, import table obfuscation
- `--phase2-extras` CLI flag sets `config.phase2_extras.enabled = True`, read by `phase_optional_extras()` in build pipeline
- `--skip-extras` flag to bypass
- See "Optional Protection Techniques" section above
