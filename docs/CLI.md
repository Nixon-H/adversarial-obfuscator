# Command-Line Reference

`shadow-compiler 2.0.0` has two entry points. They do not share a flag set, and
they write to different places.

| Entry point | Output | What it is for |
|---|---|---|
| `python3 scripts/build.py --payload P` | `build/<name>_obfuscated.py` | the source emitter: AST ladder, lowering, IR/LLVM, encryption, packaging |
| `python3 -m obfuscator.core.pipeline build P` | `<dirname(P)>/dist/<name>_protected.py` (+ `_dbg`), `nixon_core.so`, cert | the packed loader: counter-REA, section splitting, licensing, attestation |

For task-oriented examples, see [`USER_GUIDE.md`](USER_GUIDE.md). For the
minimum build with no toolchain, see the quick start in
[`../README.md`](../README.md).

## Which entry point do I want?

- **AST/phase-2 obfuscation only, no external toolchain:** `scripts/build.py`
  with the five `--skip-*` flags. Phase-2 features from `config/default.json`
  still run; add `--phase2-only none` for the ladder alone.
- **Full source pipeline (IR, LLVM, encryption, Rust relay):**
  `scripts/build.py` without the skips; needs `cargo`, `g++`, `llc`.
- **Licensing, trial, HWID, watermark, section splitting, loader gates:** the
  packed loader (`python3 -m obfuscator.core.pipeline build`). The source
  emitter has no payload key, so it refuses those flags.

`-o` on `scripts/build.py` is a staging path, not the final output. The artefact
is always packaged as `build/<payload>_obfuscated.py`; writing outside the build
directory is refused unless `--force-output` is given.

`scripts/build.py` sets `NIXON_LOG_REDIRECT=0` itself, so a plain build prints
to the console. The loader CLI writes `build.log` unless you set
`NIXON_LOG_REDIRECT=0`.

## Verified minimal build

```bash
echo 'print("hello-nixon")' > /tmp/hello.py

NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/qs_hello.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras

NIXON_LOG_REDIRECT=0 timeout 60 python3 build/hello_obfuscated.py
# hello-nixon
```

About one second; ~15 KB from a 21-byte source at the default `--opt-level 4`.
Level 0 disables the ladder but not the always-on passes; `--skip-obfuscate`
is the byte-identical copy path.

The packed loader writes **next to the payload**, not to the current directory:
`<dirname(payload)>/dist/<name>_protected.py`. A build of `/tmp/hello.py`
therefore writes `/tmp/dist/hello_protected.py` (verified 2026-11-10).

## What the skips buy

| Skip | Stage removed | Needs |
|---|---|---|
| `--skip-irgen` | IR construction | — |
| `--skip-llvmgen` | LLVM codegen | `llc` |
| `--skip-encrypt` | Post-link encryption | — |
| `--skip-relay` | Rust relay build | `cargo` |
| `--skip-extras` | Optional native extras | — |

Drop them only when the toolchain is present; a full build is minutes, not
seconds.

## Flags that need a warning

| Flag | Reality |
|---|---|
| `--temporal-keys` | **Inert.** ~19 s of hashing to produce metadata nothing reads. |
| `--crypto-binding` | **Build-time only.** Nothing decrypts at run time. |
| `--randomization-seed` / `SEED` | Seeds part of the pipeline; does **not** make builds byte-reproducible. |
| `--code-genome` | Real but expensive: 50 × 30 = 1,500 evaluations by default. Use `--genome-generations 2 --genome-population 4`. |

The generated tables below carry the long-form notes next to each affected
flag.

---

## Generated reference

The blocks below are machine-generated from the parsers' own `--help` by
`scripts/gen_cli_reference.py`. They are checked in CI by
`tests/test_readme_matches_cli.py`, so they cannot drift from the code.

<!-- BEGIN GENERATED CLI REFERENCE -->

Every option `scripts/build.py` accepts, generated from its own `--help` by
`scripts/gen_cli_reference.py` and checked by `tests/test_readme_matches_cli.py`,
so it cannot drift. Editorial notes are marked where a flag is inert or archived.

**263 options.**

### Input, output and build control

| Option | What it does |
|---|---|
| `--cross CROSS` | Cross-compile targets: win,linux,macos,linux-arm |
| `--force-output` | Allow -o/--output outside the repo build dir (default: refuse absolute/escaping paths) |
| `--generate-payload-h` | Auto-generate payload.h from obfuscated payload (default: on) |
| `--include-original` | Include original payload in build/ |
| `--no-generate-payload-h` | Skip payload.h generation |
| `-o, --output OUTPUT` | Staging path for the obfuscated script (the final artifact is written to build/) |
| `--payload PAYLOAD` | Python script to obfuscate |
| `--python-dll PYTHON_DLL` | Python DLL to embed in payload.h |
| `--rust-exe RUST_EXE` | Rust Windows EXE to embed in payload.h |
| `--skip-conflict-check` | Skip protection conflict detection |
| `--skip-encrypt` | Skip post-link encryption |
| `--skip-extras` | Skip optional extras (antidbg, packing, timing checks) |
| `--skip-irgen` | Skip IR compilation |
| `--skip-llvmgen` | Skip LLVM codegen |
| `--skip-obfuscate` | Skip AST obfuscation |
| `--skip-relay` | Skip Rust relay build |
| `--version` | show program's version number and exit |

### Obfuscation ladder and AST transforms

| Option | What it does |
|---|---|
| `--adaptive` | Enable function-level adaptive protection (auto- classify + strategy selection) |
| `--adaptive-adversarial` | Enable adaptive adversarial rewriting based on benchmark feedback |
| `--adaptive-classifier-loop` | Run classify → protect → benchmark → re-classify → re- protect loop |
| `--advanced-protection` | Enable all Advanced Protection features |
| `--advanced-protection-only ADVANCED_PROTECTION_ONLY` | Comma-separated list of Advanced Protection features to enable |
| `--adversarial-bench` | Run adversarial benchmark generator against all target systems |
| `--adversarial-bench-count ADVERSARIAL_BENCH_COUNT` | Number of adversarial tests to generate (default: 20) |
| `--adversarial-injection` | Enable adversarial dead code + prompt injection |
| `--adversarial-level {1,2,3,4,5}` | Adversarial injection aggressiveness (1-5, default: 3) |
| `--adversarial-loop` | Enable self-improving obfuscation via deobfuscation agent |
| `--cfg-mutation` | Enable live CFG mutation (variant basic-block ordering) **Metadata-only.** The phase writes `cfg_mutation_config`/variants; the runtime module was archived and no component reads them. Not a runtime protection. |
| `--cfg-mutation-variants CFG_MUTATION_VARIANTS` | Number of CFG orderings per function (default: 4) |
| `--class-dispatch` | Enable execution-path-specific JIT codegen **Metadata-only.** Writes `class_dispatch_config.json`; no runtime consumer. Not a runtime protection. |
| `--class-dispatch-count CLASS_DISPATCH_COUNT` | Number of dispatch classes (default: 4) |
| `--classify` | Run classification pass and report |
| `--data-obf-level {1,2,3}` | Data obfuscation intensity (1-3, default: 3) |
| `--data-obfuscation` | Enable data-oriented obfuscation (protect data layout) |
| `--fragment` | Enable micro-JIT fragment reassembly (decrypt->execute->wipe) |
| `--fragment-functions FRAGMENT_FUNCTIONS` | Comma-separated functions to fragment, or 'auto' |
| `--fragment-migration` | Enable cross-platform fragment migration (Item 115) |
| `--fragment-size FRAGMENT_SIZE` | Instructions per fragment (default: 5) |
| `--lowering LOWERING` | Semantic-lowering families CSV (io,scalar,string,conta iner,service,protocol,function,import,fusion + opt-in: arithmetic,truth,slice,format,augassign); default '' = disabled |
| `--micro-fragment` | Enable micro-fragment execution (decrypt->execute->wipe each fragment) |
| `--micro-fragment-size MICRO_FRAGMENT_SIZE` | Bytes per micro-fragment (default: 64) |
| `--no-audit-hook-plant` | [LOADER ONLY -- ignored by this pipeline] Omit the site-packages audit-hook plant detector from the loader (default: detector ON) |
| `--no-bogus-exceptions` | Disable fake exception handlers (default: on) |
| `--no-cfg-flatten` | Disable control-flow flattening (default: on) |
| `--no-fragment-strings` | Disable string fragmentation (default: on) |
| `--no-mba-subs` | Disable MBA expression substitution (default: on) |
| `--no-opaque-predicates` | Disable opaque-predicate insertion (default: on) |
| `--no-snapshot` | [LOADER ONLY -- ignored by this pipeline] Omit the frozen-stdlib snapshot gate from the loader (default: gate ON; also disarmable at runtime via NIXON_SNAPSHOT_OFF=1) |
| `--no-stdlib-audit` | [LOADER ONLY -- ignored by this pipeline] Omit the stdlib function-audit gate from the loader (default: gate ON; also disarmable at runtime via NIXON_STDLIB_AUDIT_OFF=1) |
| `--no-unicode-ids` | Disable Unicode symbol renaming (default: on) |
| `--opt-level {0,1,2,3,4,5}` | Optimization/protection ladder O0-O5 (default: 4, recommended) |
| `--per-exec-recompile` | Enable per-execution recompilation **Metadata-only.** Writes `per_exec_recompile_config.json`; no runtime consumer. Not a runtime protection. |
| `--phase2-extras` | Enable optional extras (antidbg APIs, packing, timing checks, etc.) |
| `--randomization-level {1,2,3}` | Randomization level 1-3 (default: 3) |
| `--randomization-seed RANDOMIZATION_SEED` | Deterministic seed for structure randomization (also read from SEED/NIXON_SEED env when flag is absent) **Partial seeding only.** Seeds structure randomisation, speculation and the CPU-port phase; it does **not** make builds byte-reproducible, because the emitters draw thousands of values directly from `secrets` and several cross the pack/run boundary. |
| `--self-healing` | Enable self-healing runtime (redundant code copies) **Metadata-only.** Writes `self_healing_config.json`; the runtime module was archived and no component reads it. Not a runtime protection. |
| `--speculation-obfuscation` | Enable AST-level speculation obfuscation (Item 123) |
| `--ssa-mutation` | Enable SSA mutation (variant instruction ordering) **Metadata-only.** Writes `ssa_mutation_variants.json`; no runtime consumer. Not a runtime protection. |
| `--ssa-variants SSA_VARIANTS` | Number of SSA variants per function (default: 4) |
| `--struct-randomization` | Enable structure randomization (stack/heap/reg) |
| `--validate` | Run SMT-backed semantic validation after each obfuscation phase |
| `--validate-fail` | Abort build if SMT validation fails |

### Anti-analysis, counter-REA and deception

| Option | What it does |
|---|---|
| `--attack-corpus` | Build permanent corpus of bypasses, deobfuscations, proof failures, replay attacks (Feature 196) |
| `--attack-store ATTACK_STORE` | Store directory for attack captures (default: build/attacks/) |
| `--attention-poison ATTENTION_POISON` | Enable attention poisoning with fan-out N (default: 0 = disabled) |
| `--capture-attacks` | Capture attack results from red team pipeline for replay |
| `--decoy-api-count DECOY_API_COUNT` | Number of decoy APIs to inject (default: 5) |
| `--decoy-apis` | Enable semantic decoy API injection |
| `--false-confidence-audit` | Scan for false confidence patterns in codebase (Feature 173) |
| `--honey-functions HONEY_FUNCTIONS` | Number of honey functions to inject (default: 0) |
| `--independent-audit` | Run independent audit using separate code paths (Feature 181) |
| `--llm-fingerprint` | Enable LLM fingerprint embedding |
| `--llm-resilient` | Enable LLM-resilient AST obfuscation (context collapse + guard vars + string encoding) |
| `--llm-resilient-depth LLM_RESILIENT_DEPTH` | Nesting depth for context collapse (default: 15) |
| `--llm-resilient-vars LLM_RESILIENT_VARS` | Number of dead variables per function (default: 50) |
| `--manipulation-detector` | Detect metric manipulation, hardcoded scores, inflated coverage (Feature 182) |
| `--multi-agent-deception` | Enable multi-agent deception storyline injection |
| `--multi-tool` | Run multi-tool resistance evaluation |
| `--poison-all` | Enable all poisoning techniques |
| `--poison-apis` | Enable fake APIs |
| `--poison-call-graph` | Enable fake call graphs |
| `--poison-imports` | Enable misleading imports |
| `--poison-level {0,1,2,3,4,5}` | Provenance poisoning level (0-5, default: 0 = disabled) |
| `--poison-paths` | Enable believable dead paths |
| `--poison-protocols` | Enable fake protocol parsers |
| `--prompt-resistance` | Compute prompt reconstruction resistance metrics |
| `--provenance-poison` | Enable all provenance poisoning techniques |
| `--provenance-replace` | Enable automated provenance replacement (error codes + string encoding + constant obfuscation) |
| `--reasoning-traps` | Enable reasoning-loop trap injection |
| `--red-team` | Enable autonomous red team pipeline — every build attacks itself |
| `--red-team-output RED_TEAM_OUTPUT` | Output directory for red team attack results (default: build/redteam/) |
| `--replay-attacks` | Replay captured attacks and compare results |
| `--self-critique` | Before release, critically analyze assumptions, evidence, metrics, proofs (Feature 200) |
| `--storyline-count STORYLINE_COUNT` | Number of storylines to inject (default: 3) |
| `--trap-depth TRAP_DEPTH` | Circular chain depth for reasoning traps (default: 5) |
| `--uarch-diversity` | Enable microarchitectural-aware diversity generation (Item 129) |
| `--uarch-watermark` | Embed microarchitectural timing watermark (Item 122) |

### Runtime integrity, anti-tamper and attestation

| Option | What it does |
|---|---|
| `--attestation` | Enable hardware-agnostic attestation engine (whitebox entanglement + dynamic attestation) |
| `--audit-drift` | Detect code changes without corresponding verification updates (Feature 185) |
| `--challenge-response` | Enable standalone challenge-response protocol (extracted from distributed attestation) |
| `--crypto-binding` | Enable cryptographic fragment binding chain **Build-time only.** `verify_chain` decrypts the bound fragments during the build to validate them; nothing decrypts at run time. The chain secret is deliberately not written into `payload.h`. |
| `--dist-attestation` | Enable distributed attestation (Item 116) |
| `--dist-attestation-nodes DIST_ATTESTATION_NODES` | Number of attestation nodes (default: 5) |
| `--driver-check` | [LOADER ONLY -- ignored by this pipeline] Bake the V10 kernel-driver gate into the loader (fail-closed on known-vulnerable BYOVD drivers only when armed; default: off, also armable at runtime via NIXON_DRIVER_CHECK=1) |
| `--ephemeral-isa` | Enable ephemeral per-build VM opcode mapping |
| `--history-bound-decryption` | Enable execution-history-bound decryption key derivation |
| `--hostguard` | [LOADER ONLY -- ignored by this pipeline] Prepend hostguard snippet (bind_host/check_host/isolated_exec) to loader (default: off) |
| `--invariant-engine` | Verify security invariants across codebase (Feature 190) |
| `--recovery-prevention` | Enable distributed execution recovery prevention (Item 119) |
| `--recovery-prevention-nodes RECOVERY_PREVENTION_NODES` | Number of recovery prevention nodes (default: 5) |
| `--rolling-keys` | Enable rolling key evolution for fragment chains |
| `--self-audit` | Run self-audit agent — final pipeline integrity check (Feature 180) |
| `--state-isa` | Enable state-dependent opcode mapping **Metadata-only.** Writes `state_isa_config.json`; no runtime consumer. Not a runtime protection. |
| `--state-isa-history-len STATE_ISA_HISTORY_LEN` | Execution history length for state ISA (default: 8) |
| `--temporal-keys` | Enable temporal micro-key evolution (time-window-based key chain) **Inert and slow.** Derives a window key by ratcheting from epoch 0 to the current 60 s window (~19 s per build, growing every minute), then writes scheduling metadata that nothing reads. Its verifier (`verify_key_in_window`) only compares a timestamp against the key's own fields, so it proves nothing. No key material is written to disk. |
| `--temporal-window TEMPORAL_WINDOW` | Key time window in seconds (default: 60) |
| `--trust-boundary` | Map trust boundaries across all domains (Feature 186) |

### Licensing, binding, watermarking and provenance

| Option | What it does |
|---|---|
| `--customer-salt CUSTOMER_SALT` | Bind the payload key to one customer (hybrid-loader build only: `python3 -m obfuscator.core.pipeline build`). Refused here rather than silently ignored — this pipeline emits no hybrid loader to carry the mask |
| `--dist-watermark` | Enable distributed watermarking (Item 117) |
| `--dist-watermark-shares DIST_WATERMARK_SHARES` | Number of watermark shares (default: 5) |
| `--embed-proof` | Embed proof section into packaged binary |
| `--emit-certificates` | Emit transformation equivalence certificates |
| `--hwid HWID` | [LOADER ONLY -- ignored by this pipeline] HWID string for GET_HWID() macro expansion and HWID-locked fallback. Dynamic (default): any opaque string; the loader collects format(uuid.getnode(), 'x') at runtime. Static (GAP #33): canonical 'HWID:<64 hex chars>' fingerprint (case-insensitive, lowercased) binding the artifact to a known value instead of dynamic collection (documented in obfuscator/hwid_lock.py; default: '') |
| `--hwid-lock` | [LOADER ONLY -- ignored by this pipeline] HWID-lock the bytecode fallback blob (requires --hwid; static 'HWID:<64 hex>' fingerprints unlock via the embedded value, dynamic HWIDs via uuid.getnode(); default: off) |
| `--name-gate` | Rewrite privileged call sites through per-build token map (default: off) |
| `--remote-unlock` | Enable remote fragment unlocking (Item 112) |
| `--remote-unlock-ttl REMOTE_UNLOCK_TTL` | Token TTL for remote unlock in seconds (default: 30) |
| `--rename-internal` | Rename proven-internal public methods/attributes (used only inside their own class; opt-in, default: off) |
| `--sign-key-env SIGN_KEY_ENV` | Env var name holding hex key for artifact signing sidecars (.sig.json; default: '' = disabled) |
| `--trial TRIAL` | [LOADER ONLY -- ignored by this pipeline] Trial period spec, e.g. '7d', '1w2d' (parsed via obfuscator.macros.parse_trial; default: '') |
| `--verify-preservation` | Run machine-checked semantic preservation across pipeline stages |
| `--verify-preservation-formal` | Run formal Z3-based semantic preservation proofs (Item 61) |
| `--verify-watermark` | Verify watermark after embedding |
| `--verify-watermark-survivability` | Verify watermark survivability (Item 95) |
| `--watermark WATERMARK` | Embed semantic watermark string into IR |
| `--zk-state` | Enable ZK state-bound execution (sigma-protocol-based state proofs) |
| `--zk-state-config ZK_STATE_CONFIG` | Path to ZK state config file (optional) |

### Packaging, loaders, native backends and build farm

| Option | What it does |
|---|---|
| `--cpu-gpu-hybrid` | Enable distinct CPU/GPU hybrid protection paths (Item 126) |
| `--cpu-port` | Enable CPU execution port entanglement (Item 129) |
| `--dist-diversity` | Enable distributed diversity pools (Item 118) |
| `--dist-diversity-nodes DIST_DIVERSITY_NODES` | Number of deployment nodes (default: 4) |
| `--dist-diversity-rotation DIST_DIVERSITY_ROTATION` | Variant rotation interval in seconds (default: 3600) |
| `--dist-diversity-variants DIST_DIVERSITY_VARIANTS` | Number of diversity variants (default: 8) |
| `--distributed-mode {simulation,multiprocess}` | Mode for distributed protection features: simulation or multiprocess (default: simulation) |
| `--distributed-vm` | Enable distributed VM execution (Item 113) |
| `--diversity DIVERSITY` | Generate N diversity variants |
| `--diversity-dir DIVERSITY_DIR` | Output directory for diversity variants |
| `--diversity-report` | Generate diversity comparison report |
| `--diversity-threshold DIVERSITY_THRESHOLD` | Minimum diversity score between variants (0.0-1.0) |
| `--fhe-vm` | Enable FHE-VM compilation for crown-jewel functions |
| `--fhe-vm-functions FHE_VM_FUNCTIONS` | Comma-separated function names for FHE-VM compilation |
| `--gpu` | Short flag for --gpu-execution (Item 125) |
| `--gpu-execution` | Enable GPU fragment execution with hardware detection (Item 125) |
| `--gpu-hybrid` | Enable CPU/GPU hybrid protection (Item 126) |
| `--hpc` | Enable hardware performance counter integration (Item 120) |
| `--hpc-key` | Enable HPC-based key derivation (Item 121) |
| `--kernel-assist` | Enable kernel-assisted execution research (Linux) |
| `--kernel-assist-features KERNEL_ASSIST_FEATURES` | Comma-separated kernel features to enable (default: all detected) |
| `--microjit` | Enable polymorphic micro-JIT reassembly |
| `--multi-binary` | Enable multi-binary fragment distribution (Item 110) |
| `--multi-binary-num MULTI_BINARY_NUM` | Number of binaries for fragment distribution (default: 4) |
| `--multi-host` | Enable multi-host execution graphs (Item 114) |
| `--multi-host-count MULTI_HOST_COUNT` | Number of hosts for multi-host execution (default: 3) |
| `--oram` | Enable Oblivious RAM (ORAM) controller |
| `--pyinstaller-spec` | Write a best-effort PyInstaller .spec alongside the output (never fails the build) |
| `--pytoc` | Compile the obfuscated output to a native extension via Cython (best-effort, never fails the build) |
| `--pytoc-out PYTOC_OUT` | Output path for the --pytoc native extension (default: alongside -o as <out>_pytoc.<so/pyd>) |
| `--rop` | Enable ROP chain compilation for crown jewel functions |
| `--sgx` | Enable Intel SGX hardware enclave support (Item 128) |
| `--simd-vm` | Enable SIMD-accelerated VM dispatch (Item 124) |
| `--split-bootstrap` | [LOADER ONLY -- ignored by this pipeline] V10 kernel split-bootstrap: Shamir (n=3,k=2) threshold key + fragmented decoder in the loader instead of the single embedded key path (opt-in until battle-tested; default: off) |
| `--tee` | Enable trusted execution environment partition (Item 127) |
| `--tee-type {software,sgx,sev,apple}` | TEE type (default: software) |
| `--vm-threshold VM_THRESHOLD` | [LOADER ONLY -- ignored by this pipeline] VM-score verdict threshold embedded in loader snippet (default: 50.0) |

### Verification, proofs and formal checking

| Option | What it does |
|---|---|
| `--claim-audit` | Scan for unsupported security claims like 'secure', 'unbreakable', 'tamper-proof' (Feature 172) |
| `--confidence-interval` | Compute security confidence intervals from metric samples (Feature 179) |
| `--confidence-level CONFIDENCE_LEVEL` | Confidence level for intervals (default: 0.95) |
| `--evidence-completeness` | Compute evidence completeness score for all claims (Feature 187) |
| `--evidence-ledger` | Generate evidence ledger mapping claims to source files, tests, benchmarks, and runtime traces |
| `--gate-threshold GATE_THRESHOLD` | Global gate threshold override, as a ratio of the baseline metric (0.0-1.0; e.g. 0.9 = at least 90 percent of baseline) |
| `--min-resilience MIN_RESILIENCE` | Minimum resilience score (0.0-1.0); auto-tune up to 3 iterations |
| `--min-security MIN_SECURITY` | Minimum security score (default: 0.5) |
| `--proof-aware-optimizer` | Use proof-aware optimizer (Item 99) |
| `--proof-carrying` | Enable proof-carrying obfuscation (Z3 equivalence certificates) |
| `--proof-coverage` | Generate proof coverage report (Feature 153) |
| `--proof-soundness` | Run proof soundness harness (Feature 174) |
| `--prove-fragments` | Run fragment safety proofs (Item 93) |
| `--prove-vm` | Run VM correctness proofs (Item 92) |
| `--reality-score` | Compute 0-100 Reality Score for every protection feature |
| `--release-confidence` | Combine all verification metrics into single release confidence score (Feature 197) |
| `--reproducibility-score` | Compute reproducibility score for build artifacts (Feature 178) |
| `--verification-bundle` | Generate independent verification bundle (tar.gz + SHA256 manifest) of all build artifacts |
| `--verification-bundle-output VERIFICATION_BUNDLE_OUTPUT` | Output directory for verification bundle (default: build/verification_bundle/) (set to empty string to use default) |
| `--verification-diversity` | Run multiple verification strategies and detect disagreements (Feature 184) |
| `--verify-jit` | Verify JIT reassembly correctness (Item 97) |
| `--verify-mba` | Verify MBA substitutions with SMT before applying |
| `--verify-mutations` | Verify mutation safety (Item 96) |

### Research, evaluation and reporting

| Option | What it does |
|---|---|
| `--analyst-time` | Estimate analyst reverse-engineering time from complexity metrics |
| `--artifacts-output ARTIFACTS_OUTPUT` | Output directory for research artifacts (default: build/artifacts/) |
| `--assumptions-report` | Generate assumption report for all protection features |
| `--attack-surface` | Enumerate attack surfaces across all categories (Feature 189) |
| `--benchmark` | Run AI obfuscation benchmark on protected output |
| `--benchmark-integrity` | Verify benchmark integrity with SHA256 hashing and tamper detection (Feature 183) |
| `--benchmark-model BENCHMARK_MODEL` | Specify LLM model to test against (gpt4, claude3, gemini, deepseek, or 'all') |
| `--benchmark-report` | Generate HTML benchmark report |
| `--classify-features` | Classify all 129 protection/research features and generate report |
| `--code-genome` | Enable code genome evolution |
| `--cost-model` | Run reverse engineering cost model estimation |
| `--coverage-map` | Generate protection coverage map after all stages |
| `--coverage-output COVERAGE_OUTPUT` | Output directory for coverage map (default: build/coverage/) |
| `--dependency-graph` | Validate dependency graph and detect cycles (Feature 188) |
| `--eval-summary` | Run full evaluation summary report |
| `--evaluate` | Generate unified evaluation report (all 9 metrics) |
| `--evolution-generations EVOLUTION_GENERATIONS` | Number of evolution generations (default: 3) |
| `--evolution-iterations EVOLUTION_ITERATIONS` | Number of evolution steps per build (default: 1) |
| `--feature-effectiveness` | Score features by demonstrated security improvement, not existence (Feature 193) |
| `--fingerprint-model {gpt,claude,gemini,deepseek,copilot}` | AI model to fingerprint as (default: gpt) |
| `--generate-artifacts` | Generate paper-ready research artifacts from build outputs |
| `--genome-generations GENOME_GENERATIONS` | Evolution generations (default: 50) |
| `--genome-population GENOME_POPULATION` | Population size (default: 30) |
| `--io-research` | Enable approximate indistinguishability obfuscation research |
| `--io-research-functions IO_RESEARCH_FUNCTIONS` | Comma-separated function names for iO research |
| `--knowledge-base` | Build persistent historical record of assumptions, failures, fixes, discoveries (Feature 199) |
| `--knowledge-graph` | Generate security knowledge graph of protection relationships |
| `--knowledge-graph-output KNOWLEDGE_GRAPH_OUTPUT` | Output directory for knowledge graph (default: build/knowledge_graph/) |
| `--longitudinal-tracking` | Track security metrics over time and detect drift (Feature 195) |
| `--metrics` | Collect quantitative resilience metrics after build |
| `--plaintext-exposure` | Measure actual plaintext lifetime during execution (Feature 151) |
| `--protection-roi` | Compute security gain vs runtime/complexity/maintenance cost for each feature (Feature 194) |
| `--reachability-report` | Generate reachability coverage report classifying every feature as REACHABLE/PARTIALLY_REACHABLE/UNREACHABLE (Feature 169) |
| `--retirement-report` | Generate feature retirement report analyzing features for low effectiveness, high overhead, poor survivability |
| `--runtime-truth` | Record what actually executes vs what was intended (Feature 192) |
| `--security-debt` | Compute security debt index measuring unprotected functions, weak protections, and coverage gaps |
| `--security-gates` | Enable security regression gates (Feature 146) |
| `--semantic-leakage` | Measure semantic leakage between original and obfuscated IR (Feature 152) |
| `--survivability` | Run protection survivability index measurement |
| `--synthesis` | Enable protection synthesis engine (auto-select protections) |
| `--synthesis-max-overhead SYNTHESIS_MAX_OVERHEAD` | Max allowed overhead percent (default: 50) |
| `--synthesis-max-size SYNTHESIS_MAX_SIZE` | Max allowed size multiplier (default: 3.0) |
| `--synthesis-output SYNTHESIS_OUTPUT` | Output path for synthesis report (default: build/synthesis_report.json) |
| `--synthesis-target-security SYNTHESIS_TARGET_SECURITY` | Target security score 0-100 (default: 70) |
| `--threat-coverage` | Map threats to features, metrics, and verifications; identify gaps (Feature 198) |
| `--update-baseline` | Save current metrics as new baseline for security gates |

### Other

| Option | What it does |
|---|---|
| `--ai-guided-diversity` | Enable AI-guided evolutionary diversity generation |
| `--apply-synthesis` | Apply synthesis plan flags to pipeline configuration |
| `--build-id BUILD_ID` | Stable build id: seeds the semantic-lowering kernel and is recorded in the signature sidecar, so two builds with the same --build-id lower identically. It does not by itself make the whole build reproducible (default: empty = random per build) **Lowering-kernel seed only.** Seeds the `--pytoc` semantic-lowering symbol map and is recorded in the manifest. It does not make the whole build reproducible, and a non-`--pytoc` build does not use it. |
| `--context-saturation` | Compute context window saturation metrics |
| `--cross-process` | Enable cross-process fragment binding (Item 111) |
| `--deobfuscation-threshold DEOBFUSCATION_THRESHOLD` | Minimum deobfuscation score (default: 0.7) |
| `--diagnostic` | Diagnostic build: per-stage timings + transform counts + NOT-FOR-RELEASE marker |
| `--dispersal-slices DISPERSAL_SLICES` | Number of payload slices (default: 3) |
| `--flow-entangle` | Enable whitebox-flow entanglement (crypto-state- dependent control flow) |
| `--function-intent` | Enable function intent obfuscation |
| `-h, --help` | show this help message and exit |
| `--kod` | [LOADER ONLY -- ignored by this pipeline] Arm loader kill-on-detect: the VM snippet reads NIXON_KOD env at runtime (default: report-only) |
| `--max-cpu-overhead MAX_CPU_OVERHEAD` | Max CPU overhead percentage (default: 20) |
| `--max-size-mult MAX_SIZE_MULT` | Max binary size multiplier (default: 3.0) |
| `--optimize` | Enable cost-aware protection optimizer |
| `--payload-dispersal` | Enable payload dispersal execution model (disjoint slice execution) |
| `--poly-engine` | Enable environmental poly-engine (environment-adapted code variants) |
| `--require-live-features N` | Fail the build unless at least N features are LIVE in the artefact |
| `--seed SEED` | seed the randomised transform order (reproducible builds) **Reproducibility seed.** Seeds the global `random` module, the AST transformer's RNG and its `secrets` patch, and several injectors. With the same payload, tool version and flags, the source emitter is byte-identical. It does **not** make the packed loader reproducible, and it is not key material. `--skip-obfuscate` is the copy path. |
| `--silent-fallback` | Detect silent fallbacks (try/except without logging) in codebase (Feature 191) |

<!-- END GENERATED CLI REFERENCE -->

## Generated reference: packed loader

<!-- BEGIN GENERATED LOADER REFERENCE -->

Every option `python3 -m obfuscator.core.pipeline build` accepts, generated from its own `--help` by
`scripts/gen_cli_reference.py` and checked by `tests/test_readme_matches_cli.py`,
so it cannot drift. Editorial notes are marked where a flag is inert or archived.

**69 options.**

### Input, output and build control

| Option | What it does |
|---|---|
| `--skip-cloud` | Skip the cloud build farm: build the artifact locally even if --compile/--auto would send it to the farm |

### Obfuscation ladder and AST transforms

| Option | What it does |
|---|---|
| `--lowering LOWERING` | Semantic-lowering families CSV (default: disabled) |
| `--no-anti-rea` | Skip the counter-REA shields |
| `--no-audit-hook-plant` | Omit the audit-hook plant detector |
| `--no-section-split` | Ship the payload as a single blob instead of N sealed sections (default: sections are on) |
| `--no-snapshot` | Omit the frozen-stdlib snapshot gate |
| `--no-stdlib-audit` | Omit the stdlib function-audit gate |
| `--opt-level OPT_LEVEL` | Protection ladder 0-5: resolve the 17 canonical transform flags from the level. Without it the loader build applies the full set |

### Anti-analysis, counter-REA and deception

| Option | What it does |
|---|---|
| `--anti-rea` | Counter-REA shields: architecture-mirage chaff, canary credentials, evidence-contract poison, a decoy call graph and high-salience bait procedures (ON by default) |
| `--anti-rea-level {stealth,balanced,maximum}` | How much decoy material the counter-REA shields emit |
| `--exclude-rea` | Exclude ALL classifier-directed bait layers (compliance notices, cognitive-armor canaries, fabricated classifier-bait corpus) from the counter-REA shields. The base shields (chaff, decoy call graph, canary credentials) stay on; use --no-anti-rea to skip those too |
| `--exclude-rea-bio` | Exclude only the fabricated classifier-bait corpus (BLA's keyword-only bio/chem/cyber trigger strings; inert, no actionable content). Exclusions combine: pass any of --exclude-rea-* together |
| `--exclude-rea-cognitive` | Exclude only the cognitive-armor layer (canary notices and in-band abort markers). Exclusions combine: pass any of --exclude-rea-* together |
| `--exclude-rea-compliance` | Exclude only the compliance-notice layer. Exclusions combine: pass any of --exclude-rea-* together |

### Runtime integrity, anti-tamper and attestation

| Option | What it does |
|---|---|
| `--driver-check` | Bake the kernel-driver gate into the loader |
| `--hostguard` | Prepend hostguard snippet to loader |

### Licensing, binding, watermarking and provenance

| Option | What it does |
|---|---|
| `--customer-salt CUSTOMER_SALT` | Bind the payload key to one customer (mixed as a domain-separated second mask; empty = no binding) |
| `--hwid HWID` | HWID string for macro expansion / HWID-locked fallback |
| `--hwid-lock` | HWID-lock the bytecode fallback blob (requires --hwid) |
| `--licence-token LICENCE_TOKEN` | Bind the payload key to a licence token (its key_material becomes the customer mask; the artefact then needs that token at run time) |
| `--name-gate` | Rewrite privileged call sites through per-build token map |
| `--rename-internal` | Rename proven-internal public methods/attributes |
| `--trial TRIAL` | Trial period spec, e.g. '7d' (parsed via obfuscator.macros.parse_trial) |
| `--watermark WATERMARK` | Embed an owner-supplied watermark message in the loader, HMAC-tagged and checked at load time: a stripped or edited watermark kills the artifact |

### Packaging, loaders, native backends and build farm

| Option | What it does |
|---|---|
| `--exclude-android` | Skip Android build in Nuitka cloud compilation |
| `--native` | Native Mode: Cloud Farm Cython Compilation (Hybrid - With Fallback) |
| `--native-only` | Strict Native Mode: Cloud Farm Cython Compilation (No Fallback) |
| `--platform {auto,github}` | Build farm platform. "auto" selects the only implemented farm, GitHub |
| `--public` | Public Repo Mode (Flash Mode) - Nukes repo after build |
| `--python PYTHON` | Python version for GitHub Actions (Defaults to local) |
| `--resume RESUME` | Resume waiting for a specific GitHub Run ID (skip upload) |
| `--section-count SECTION_COUNT` | Number of sealed sections when --section-split is used (default 4) |
| `--section-split` | Ship the payload as N independently sealed sections instead of one blob, so the whole encrypted payload is never resident in a single buffer. Needs a fallback payload to split, so it is not available with --native-only (default: on) |
| `--split-bootstrap` | Shamir (n=3,k=2) threshold key + fragmented decoder |
| `--tor` | Route build traffic through Tor (default 127.0.0.1:9050; override via --tor-proxy or NIXON_TOR_PROXY) |
| `--tor-proxy TOR_PROXY` | Tor SOCKS endpoint host:port (default 127.0.0.1:9050; env NIXON_TOR_PROXY) |
| `--vm-threshold VM_THRESHOLD` | VM-score verdict threshold (default: 50.0) |

### Other

| Option | What it does |
|---|---|
| `--allow-countries ALLOW_COUNTRIES` | Allowed country codes |
| `--allow-regions ALLOW_REGIONS` | Allowed regions |
| `--auto [AUTO]` | Automation: cf=Cloudflare, nk=Nuitka (Defaults to cf,nk if no value) |
| `--auto-deploy` | Auto deploy contract |
| `--bind BIND` | Bind files inside payload |
| `--bind-mac BIND_MAC` | Bind to MAC address |
| `--block-countries BLOCK_COUNTRIES` | Blocked country codes |
| `--block-regions BLOCK_REGIONS` | Blocked regions |
| `--cf-account CF_ACCOUNT` | Cloudflare Account ID (overrides the stored config) |
| `--cf-token CF_TOKEN` | Cloudflare API Token (overrides the stored config) |
| `--compile` | Compile FINAL loader with Nuitka (Creates EXE/ELF) |
| `--contract CONTRACT` | Contract address |
| `--debug-dump-raw` | Compile the plaintext-dump debug aid into the artifact (it writes the decrypted payload to a 0600 temp file when NIXON_DUMP_RAW=1). Off by default: a normal artifact has no such capability |
| `--deploy-rpc DEPLOY_RPC` | RPC URL for deployment |
| `--expire EXPIRE` | Expiration Date (YYYY-MM-DD) |
| `--explorer EXPLORER` | Blockscout URL |
| `--fast` | Build the reduced-protection profile: detections only warn, entropy noise and rdtsc pressure are lower. Faster builds and faster artefacts; weaker posture. |
| `--kod` | Arm the loader kill-on-detect response: the artifact terminates when a detection fires |
| `--layers LAYERS` | Recursive packaging layers (default 100) |
| `--lock-hwid LOCK_HWID` | Lock the build to a target HWID: registers a license for it and seeds the build deterministically **Not a whole-build seed.** Registers a licence for the target HWID and seeds the loader's polymorphic-map/VM RNG only; the blob and string keys remain random. The help text's 'seeds the build deterministically' is broader than the implementation. |
| `--net-url NET_URL` | Auth URL (if not using auto=cf) |
| `--one-shot` | Self-destruct |
| `--pin-structure` | Pin the EMITTER-ONLY draws (encoding order, slot picks, names, VM op-map) so two builds share a structure. Debugging aid; key material is not pinned, so artefacts are not byte-identical. **Structure only.** Pins emitter draws and the build timestamp; key material is not pinned, so artefacts are not byte-identical. |
| `--portable` | Skip the native core so one file runs on every OS. The FHE/ORAM layer falls back to pure Python with a small batch; every other protection is unchanged. |
| `--private-key PRIVATE_KEY` | Deployment key |
| `--rpc RPC` | RPC URL |
| `--shards SHARDS` | Key shard URLs |
| `--stego` | Steganography wrapping |
| `--strict-detections` | Make the loader's environment detections (sandbox, emulator, debugger frame, geo-fence, licence) terminate the artifact instead of only perturbing it (ON by default; use --fast to opt out) |
| `--tls-ca-bundle TLS_CA_BUNDLE` | PEM CA bundle for the emitted key fetch. The artifact verifies the certificate chain AND the hostname against the system trust store plus this CA (it never disables verification) |
| `--webhook WEBHOOK` | Alert Webhook URL |
| `--zips ZIPS` | Number of ZIP layers |

<!-- END GENERATED LOADER REFERENCE -->
