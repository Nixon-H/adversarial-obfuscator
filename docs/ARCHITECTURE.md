# Architecture and Implementation

**Status:** current description of `master`. Where this document and the code
disagree, the code wins; where it and a dated design record disagree, this
document wins.

Related: [`EMITTER_PIPELINE.md`](EMITTER_PIPELINE.md) (pass order inside the
packed emitter), [`contracts.md`](contracts.md) (overlapping subsystems),
[`../irgen/SPEC.md`](../irgen/SPEC.md) (IR), [`ROADMAP.md`](ROADMAP.md)
(historical phase design).

---

## 1. Design goals

The system is a **source-to-artefact protection pipeline** with four goals,
in priority order:

1. **The artefact must run.** A build that produces an un-runnable artefact is
   a defect, not a trade-off. The `e2e` gate exists because this failed
   repeatedly.
2. **Each layer must be independently switchable.** A user can take the AST
   ladder alone, or add lowering, packaging, loader gates, and licensing. A
   layer that cannot be isolated cannot be evaluated.
3. **The emitted artefact must carry its own checks.** Integrity, licensing,
   and anti-tamper decisions are made in the artefact where a stage supports
   it — with the explicit caveat that client-side decisions are attacker-editable.
4. **Claims must be measurable.** Every security claim should have a test, a
   gate, or a documented reason it cannot have one.

The fourth goal is why the repository contains a research programme and a
`THREAT_MODEL.md` with an evidence taxonomy. It is also why several features
are labelled inert or experimental rather than removed.

---

## 2. Two artefact producers

There are two entry points, and they are not variants of one thing.

| | Source emitter | Packed loader emitter |
|---|---|---|
| Command | `python3 scripts/build.py --payload P` | `python3 -m obfuscator.core.pipeline build P` |
| Output | `build/<name>_obfuscated.py` | `<dirname(source)>/dist/<name>_protected.py` (+ `_dbg`), `nixon_core.so`, self-signed root cert |
| Payload form | transformed Python source | loader + encrypted payload blob |
| Payload key | none | per-build blob key |
| Applies | AST ladder, lowering, IR/LLVM/encrypt, packaging, native backends | counter-REA shields, section splitting, loader gates, licensing, attestation |
| Licensing flags | refused (no key to bind) | accepted |

The distinction is load-bearing. The source emitter has no encrypted payload,
so it cannot bind a licence token to a key. The packed emitter has a loader, so
it can apply trial, HWID, watermark, section splitting, and the kill ladder.

Both are documented from their live parsers in [`CLI.md`](CLI.md):
260+ options for `build.py`, 69 for the loader CLI.

---

## 3. Source emitter: core path

`scripts/build.py` is a long orchestration file. The stages that matter on the
documented path, in order:

```
payload.py
  │
  ├─ phase_check_conflicts         reject unsound flag combinations
  ├─ phase_obfuscate               AST ladder (O0–O5), 17 canonical flags
  ├─ phase_classify (optional)     route functions: standard / crown-jewel / JIT
  ├─ phase_provenance_removal      strip names, metadata, docstrings
  ├─ phase_dataflow_obfuscation    affine encoding, value splitting, MBA
  ├─ phase_generate_config         config/default.json → build context
  ├─ phase_generate_payload_h      embed payload for native stages
  ├─ phase_ir_compile              Python AST → Nixon IR (SSA-like)
  ├─ phase_variant_pool            clone crown-jewel functions
  ├─ phase_watermark_embedding     IR-level watermark (BCH)
  ├─ phase_llvm_codegen            Nixon IR → LLVM IR → object; OLLVM passes
  ├─ phase_rop_compile             ROP-oriented compilation (opt-in)
  ├─ phase_encrypt_binary          per-block AES-256-CTR + ELF patch
  ├─ phase_vm_compile              VM bytecode for crown-jewel functions
  ├─ phase_jit_generate            encrypted JIT templates
  ├─ phase_compile_relay           Rust relay (native launcher)
  ├─ phase_cross_compile           optional cross targets
  ├─ phase_runtime_manifest        build manifest
  └─ phase_package                 copy into build/, write reports
```

The exact ordering and the optional phases around it are visible in
`scripts/build.py`; the list above is the load-bearing path, not every branch.
`--skip-irgen`, `--skip-llvmgen`, `--skip-encrypt`, `--skip-relay`, and
`--skip-extras` remove stages and are what make the stdlib-only quick start
possible.

### 3.1 AST ladder

`obfuscator/opt_levels.py` defines 17 canonical flags across six levels.
Level 0 disables all 17 ladder transforms; level 4 is the default and enables
14 of 17. **Level 0 is not a byte-identical copy through the CLI**: always-on
passes (symbol rename, integrity checksums, string sealing, adversarial
injection) still run. A byte-identical copy is `--skip-obfuscate` (verified on
a 2,635-byte payload: 2,635 bytes out, `diff` clean). The transformer-level AST
equality holds only when the always-on passes are also switched off, as
`tests/test_opt_enforcement.py` does.

| Level | Name | Enabled |
|---|---|---|
| 0 | O0 (none) | 0/17 — ladder disabled; always-on passes still run |
| 1 | O1 (safe) | 7/17 |
| 2 | O2 (balanced) | 12/17 |
| 3 | O3 (strong) | 13/17 |
| 4 | O4 (recommended) | 14/17 |
| 5 | O5 (aggressive) | 17/17 |

The ladder is the only way to switch a transform **on**. Individual transforms
are switched **off** with `--no-<name>`; there is no `--mba-subs` because the
ladder owns enablement. Level 0 is asserted by
`tests/test_pipeline_wiring.py` and `tests/test_opt_enforcement.py`.

### 3.2 Semantic lowering

`--lowering` rewrites covered call sites to `_nxk_*` kernel calls across 20
families and a verified 140 operations. The registry is in
`obfuscator/lowering.py`; the pure-Python reference kernel is
`obfuscator/lowering_shim.py`; the native kernel is emitted on the `--pytoc`
path (`obfuscator/kernel_gen.py`). Lowered artefacts require the shim on
`PYTHONPATH`; the default build does not.

Measured overhead of the Python shim is **1.46×–3.84×** per family
(`obfuscator/lowering_DESIGN.md`; reproduce with
`python3 scripts/benchmark/lowering_perf.py`). Vendor-native claims of
0.19×–1.56× describe a native kernel and are **not reproduced** here.

### 3.3 IR and LLVM

`irgen/` implements a typed, SSA-like IR (`irgen/SPEC.md`) with a Python→IR
compiler, optimizer, and passes. `llvmgen/` lowers IR to LLVM IR and applies
OLLVM-style passes (bogus control flow, control-flow flattening, instruction
substitution). The IR is also the substrate for watermarking, variant pools,
fragmentation, and the VM compiler.

### 3.4 Encryption and runtime

`encrypt/` implements per-block AES-256-CTR encryption with an ELF patcher and
decryptor stub. `runtime/` is a Rust runtime (decryption, integrity, memory
scrubbing); `relay/` is a Rust launcher. The current judgement on the Rust
runtime is in [`RUNTIME_DECISION.md`](RUNTIME_DECISION.md): it is **not
load-bearing** for the source emitter.

---

## 4. Packed emitter: pass order

The packed emitter is where the loader gates live. Inside `build_project`, the
order is (from [`EMITTER_PIPELINE.md`](EMITTER_PIPELINE.md)):

1. **Template fill** — `LOADER_HEAD + LOADER_BODY` with every placeholder
   resolved. A missing placeholder raises `KeyError`.
2. **Core-integrity insertion** — SHA-256 of `nixon_core.so` baked into a
   self-check that runs before the core loads.
3. **Anti-debug insertion** — must happen before the rename.
4. **Symbol rename** — fixed runtime vocabulary rewritten to per-build names;
   partial rename raises `NameError` at run time.
5. **String-table pass** — every string literal becomes an encrypted-table
   lookup. Line-oriented; cannot see structure across lines.
6. **Table build** — encrypted string table and key from `STRING_TABLE_KEYS`.
7. **Signing and packing** — self-check anchors filled, script HMAC-signed,
   payload sealed into sections.

The insertion rules are the part that cost rounds:

- Code calling a renamed symbol must be inserted **before** the rename, or it
  names something that no longer exists. Inside a `try/except`, it fails
  silently and the feature looks present.
- Do not write implicit string concatenation across lines; the string pass
  rewrites each literal separately and produces a `SyntaxError`.
- Any value used to encrypt the payload at pack time must be reproducible at
  run time from something the artefact carries.

These are documented because four attempts to change the loader failed for the
same reason: the change was written into a place whose invariants had not been
established.

---

## 5. Runtime gates

The packed artefact carries a loader with several independent gates. They are
listed with their defaults and off-switches in
[`TRANSFORMS.md`](TRANSFORMS.md) §6 and analysed attacker-by-attacker in
[`../THREAT_MODEL.md`](../THREAT_MODEL.md).

The important architectural point is **where the decision is made**. A gate
that runs in the client is editable by the client's owner. The tool's honest
position is that these gates raise effort and catch opportunistic tampering;
they do not create a trust boundary. The only architectural answer that holds
against a capable adversary is to move the secret and the trust decision to a
server — which is why [`LICENSING.md`](LICENSING.md) describes the token as
"the client half" of that design, not a replacement for it.

Kill primitives (`_nx_kill`) exit the process and are silent unless
`NIXON_LADDER_DEBUG=1`. They are deliberately uncatchable (`os._exit`), which
is why the failure-mode audit records that a false positive can destroy an
operator's build.

---

## 6. Verification subsystems

The repository has more verification machinery than a normal tool, because the
research programme depends on it.

| Subsystem | What it checks | Where |
|---|---|---|
| Test suite | Contracts and behaviour | `tests/` (283 test files) |
| End-to-end | Every build produces an artefact that **runs** | `make e2e` |
| Artefact gate | Compile, import, run over a corpus, seeds, variants | `scripts/transfer/artefact_gate.py` |
| Reproduction | The paper's ten tables | `scripts/transfer/reproduce.py` |
| Doc guards | Counts and claims in research docs | `tests/test_research_*` |
| CLI guards | Generated reference matches parsers | `tests/test_readme_matches_cli.py` |
| Security invariants | No exec over input, no driver loading, fail-closed integrity | `tests/test_security_invariants.py` |
| Threat coverage | Every threat row has an evidence status | `THREAT_MODEL.md`, `scripts/.../phase_threat_coverage.py` |

`make lint` runs `ruff` plus `scripts/lint/check_undefined_globals.py`. The
latter resolves every global read in the live tree at runtime; it caught
`NameError`s that static analysis could not.

---

## 7. Invariants

These are asserted in code or tests and should be treated as architectural
constraints, not suggestions:

1. **Level 0 disables the ladder, not the pipeline.** `resolve(0)` enables none
   of the 17 flags, but the CLI still applies always-on passes; byte-identical
   output is `--skip-obfuscate`.
2. **A build must produce a running artefact.** `make e2e` executes it.
3. **Untrusted input never selects an executable path.** Emitted loader
   snippets contain no `exec`/`eval` over input-derived names
   (`tests/test_security_invariants.py`).
4. **No driver loading, no IOCTLs.** The BYOVD gate is read-only enumeration.
5. **Failed integrity never downgrades.** Tampered snapshot or stdlib
   fingerprints produce `mismatch`, never a pass.
6. **Missing signal is not safety.** An empty finding never yields `ok`/`True`
   from a real gate.
7. **Build flags must not be able to emit a non-running artefact.** A build
   that succeeds is not evidence the artefact works; run it.

---

## 8. Repository layout

```text
obfuscator/            AST transforms, lowering, loader-gate emitters,
                       licensing, anti-REA, runtime snippets
obfuscator/core/       pipeline.py (packed emitter), transforms.py, sources.py
irgen/                 Nixon IR: compiler, optimizer, passes, watermark, VM input
llvmgen/               LLVM IR codegen and OLLVM passes
encrypt/               per-block AES-256-CTR, ELF patcher, stub
vm/                    VM ISA, bytecode compiler, interpreter
runtime/ relay/        Rust runtime and launcher
native/                C/C++ core, SIMD VM, platform stubs
scripts/               build.py + phases/, benchmark/, evaluation/, transfer/
scripts/transfer/      research benchmark, attacker, gates, reproduction
tests/                 283 test files
docs/                  current docs, ADRs, audits, research record
archive/               superseded native/relay/Rust material
```

`scripts/` also contains a large number of **research and audit phases** that
are not on the default build path: ROI, reachability, invariant engine,
self-audit, claim auditor, synthesis planner, and similar. They are invoked by
flags and should be read as research instrumentation, not as product
guarantees. [`contracts.md`](contracts.md) records which of the overlapping
subsystems is authoritative.

---

## 9. What is load-bearing

| Component | Status | Evidence |
|---|---|---|
| AST ladder | Implemented, tested | `tests/test_pipeline_wiring.py`, `test_opt_enforcement.py` |
| Semantic lowering | Implemented; shim required | `tests/test_lowering_parity_141.py`, `test_opcount_truth.py` |
| IR + LLVM codegen | Implemented; toolchain required | `llc` validation, `tests/` |
| Packed loader | Implemented; the licensing/gates path | `tests/test_licence_binding.py`, `test_split_bootstrap.py` |
| Counter-REA / deception | Implemented, on by default | `tests/test_anti_rea.py` and related |
| Runtime gates | Implemented; client-side by construction | `THREAT_MODEL.md` status per row |
| Native backends (`--pytoc`, PyInstaller) | Best-effort; never fail the build | `tests/test_pytoc.py`, `test_pyinstaller_spec.py` |
| FHE/ORAM/ZK/GPU/TEE/SGX | Research-only; not on default path | Flags exist; not evaluated |
| Synthesis planner | Research scaffold; gains are hand-assigned | `scripts/synthesis/costs.py` |

---

## 10. Extension points

To add a transformation:

1. Implement it under `obfuscator/` (AST) or `irgen/` (IR).
2. Add the flag to the appropriate parser (`scripts/build.py` or
   `obfuscator/core/pipeline.py`).
3. Add it to the ladder in `obfuscator/opt_levels.py` **only if** it is safe at
   the level you are adding it to; level 0 must stay empty.
4. Add a contract test and, if it emits an artefact, an execution test.
5. Regenerate [`CLI.md`](CLI.md): `python3 scripts/gen_cli_reference.py --write`.
6. Classify it in [`TRANSFORMS.md`](TRANSFORMS.md) — what attacker-visible
   representation does it change? If the answer is "none", it is not an
   obfuscation.
7. If it can change the artefact's output, add it to the `e2e` matrix.

The classification step is not bureaucracy. The transformation taxonomy
(`research/transform-taxonomy.md`) records a pass named `vm` that every
heterogeneous configuration believed enabled virtualisation; no consumer read
the option. Configuration diversity without structural diversity is the exact
failure mode the research programme was built to detect.
