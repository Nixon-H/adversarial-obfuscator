# Nixon Adversarial Obfuscator (shadow-compiler)

Python-source obfuscator + loader-hardening pipeline. `scripts/build.py`
(version `shadow-compiler 2.0.0`, per `python3 scripts/build.py --version`)
takes a Python payload and emits an obfuscated `.py` artifact into `build/`
plus loader gates (anti-VM, trial/HWID, watermark, snapshot/stdlib-audit,
audit-hook plant detection, optional kernel-driver gate).

> Scope note: this repo also contains research/experimental flags (FHE-VM,
> iO, ZK, GPU/TEE/SGX, distributed execution, red-team). This README covers
> only the paths verified by the test-suite and by the commands below.
> Every flag is documented below. Where one is inert or superseded, the reference says so.

## Requirements

Python dependencies are installed from a **hash-pinned lock**
(`requirements.lock`): every artefact, including the transitive
closure, carries its SHA-256, and CI installs with `--require-hashes`,
so a substituted artefact fails the install rather than landing.
`requirements.txt` states the wanted versions; regenerate the lock with
`make lock` after changing it.

- Python **3.10–3.14** for builder **and** payloads
  (`obfuscator/nyser.py: SUPPORTED_MINORS`,
  `obfuscator/py_matrix.py: SUPPORTED`, builder floor
  `sys.version_info < (3, 10)` in `scripts/build.py`). Verified on 3.13.5.
- No dependencies needed for the quick-start below (stdlib only).
  Full pipeline stages need `cargo`, `g++`, `llc` (checked at startup).

## Quick-start (verified 2026-11-10, Python 3.13.5, Linux x86_64)

A minimal build with no external toolchain: AST obfuscation only.

```bash
echo 'print("hello-nixon")' > /tmp/hello.py

NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/qs_hello.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras

# [11:45:26] [   OBFUSCATE] /tmp/hello.py → /tmp/qs_hello.py
# [11:45:26] [   OBFUSCATE] Done: 14.0KB (was 0.0KB)
# [11:45:27] [     PACKAGE] Packaging build artifacts...
#  Build artifacts: build/

NIXON_LOG_REDIRECT=0 timeout 60 python3 build/hello_obfuscated.py
# hello-nixon
```

About a second, and the artefact is ~15 KB from a 21-byte source. Measured on the
default `--opt-level 4`; level 0 produces a byte-identical copy of the source.

### What each `--skip-*` buys you

The five skips keep the build to the AST stage. Without them the pipeline also runs
IR generation, LLVM codegen, post-link encryption and the Rust relay, which is where
`cargo`, `g++` and `llc` become mandatory (checked at startup).

| Skip | Stage removed | Needs |
|---|---|---|
| `--skip-irgen` | IR construction | — |
| `--skip-llvmgen` | LLVM codegen | `llc` |
| `--skip-encrypt` | post-link encryption | — |
| `--skip-relay` | Rust relay build | `cargo` |
| `--skip-extras` | optional native extras | — |

Drop them only when the toolchain is present; a full build is minutes, not seconds.

### Two behaviours that surprise people

**`-o` is a staging path, not the output.** The final artefact is always packaged as
`build/<payload>_obfuscated.py`. Writing outside the build directory is refused:

```text
$ python3 scripts/build.py --payload /tmp/hello.py -o /tmp/nope.py --skip-extras
[ERROR] Refusing -o outside build dir: /tmp/nope.py (use --force-output to override)
```

`--force-output` exists because silently overwriting an arbitrary path is a bad
default for a local tool, not because the guard is optional.

**Logging differs between the two entry points.** `scripts/build.py` sets
`NIXON_LOG_REDIRECT=0` itself, so it prints to the console. The loader CLI
(`python3 -m obfuscator.core.pipeline build`) *does* write `build.log` in the current
directory unless you set `NIXON_LOG_REDIRECT=0`. There is no import-time redirect:
`enable_log_redirect()` is called explicitly by the loader entry point, so merely
importing `obfuscator.core` writes nothing.

### If you use `--lowering`

`--lowering io,scalar` rewrites covered call sites to `from lowering_shim import ...`.
That artefact only runs when `obfuscator/` is importable:

```text
$ python3 build/hello_obfuscated.py
ModuleNotFoundError: No module named 'lowering_shim'

$ PYTHONPATH=$PWD/obfuscator python3 build/hello_obfuscated.py
hello-nixon
```

The default build (no `--lowering`) runs anywhere. This is the one flag that changes
the deployment requirement of the artefact, so decide it deliberately.

### The loader CLI

`python3 -m obfuscator.core.pipeline build` is the second entry point and has its own
options (counter-REA, section splitting, loader switches — 69 of them, listed in the
[loader reference](#the-loader-cli) below).

```bash
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
  python3 -m obfuscator.core.pipeline build /tmp/hello.py --skip-cloud

python3 dist/hello_protected.py     # hello-nixon
```

It writes `dist/hello_protected.py` (plus a `_dbg` variant), not `build/`: the two
entry points have different output conventions. Its flags do not overlap with
`build.py`'s — there is no `--skip-extras` here, the equivalent is `--skip-cloud`.

## What it does

The tool takes a Python payload and emits an artefact that is harder to read,
harder to re-run under instrumentation, and — where a stage supports it — able to
refuse to run when it detects it has been altered. Layers are independent: you can
use any one of them alone.

Each area below names the flags that switch it on. The **complete** flag list, with
the parser's own description for every option, is in the [CLI reference](#cli-reference)
further down.

### 1. Obfuscation ladder — `--opt-level 0..5`

One dial, default **4**, which turns on 14 of the 17 base transforms: cfg-flatten,
opaque predicates, bogus exceptions, MBA substitution, string fragmentation,
unicode identifiers, variable splitting, constant unfolding, metadata stripping,
code checksums, dynamic code, enhanced junk, symbol renaming and decompiler breaks.

The ladder is the only way to switch a transform **on**. Individual transforms are
switched **off** with the `--no-` form — `--no-cfg-flatten`, `--no-opaque-predicates`,
`--no-bogus-exceptions`, `--no-mba-subs`, `--no-fragment-strings`,
`--no-unicode-ids` — so you can drop one rung without leaving the ladder. There is
no `--mba-subs`; it is on at level ≥ 1 and disabled by its inverse.

Level 0 is a **byte-for-byte no-op** (asserted by `tests/test_pipeline_wiring.py` and
`tests/test_opt_enforcement.py`), so you can diff a build against its source.

Beyond the ladder: `--ssa-mutation`, `--cfg-mutation`, `--class-dispatch`,
`--struct-randomization`, `--branch-entangle`, `--multicore-entangle`,
`--speculation-obfuscation`, `--data-obfuscation`, `--micro-fragment`,
`--fragment`, `--per-exec-recompile`, `--self-healing`.

### 2. Semantic lowering — `--lowering`

Rewrites covered call sites to `_nxk_*` kernel calls across **20 families / 140
kernel ops**. The generated artefacts need `obfuscator/lowering_shim.py` importable;
the default build (no `--lowering`) runs anywhere. Measured shim overhead is
1.46x–3.84x per family — see the numbers below, which are the in-repo ones.

### 3. Counter-REA shields — on by default (`--anti-rea`)

Ported from [BLA](https://github.com/qybaihe/bla), in `obfuscator/anti_rea.py`:
architecture-mirage chaff, canary credentials and URL parser differentials,
evidence-contract poison, a decoy call graph woven into real functions, a BPE token
amplifier, shadow business logic, an aliasing illusion, crash-trace decoys and
diagnostic rabbit holes.

Classifier-directed bait layers are also on by default. Each is individually
removable via the **loader** CLI (`python3 -m obfuscator.core.pipeline build`):
`--exclude-rea` (all of them), `--exclude-rea-compliance`,
`--exclude-rea-cognitive`, `--exclude-rea-bio`; `--anti-rea-level` sets intensity
and `--no-anti-rea` turns the whole subsystem off. Every combination is built **and
run** in CI (`portable-deep-matrix.yml`, the `flags` job).

### 4. Deception against automated and human analysts

`--poison-apis` · `--poison-imports` · `--poison-call-graph` · `--poison-paths` ·
`--poison-protocols` · `--poison-all` · `--decoy-apis` · `--honey-functions` ·
`--reasoning-traps` · `--trap-depth` · `--prompt-resistance` · `--attention-poison` ·
`--llm-resilient` · `--multi-agent-deception` · `--storyline-count` ·
`--provenance-poison` · `--manipulation-detector` · `--false-confidence-audit` ·
`--self-critique` · `--red-team`

### 5. Runtime integrity and anti-tamper

| Gate | Default | Off switch |
|---|---|---|
| Frozen-stdlib snapshot | **on** | `NIXON_SNAPSHOT_OFF` at run time, `--no-snapshot` at build |
| Stdlib function audit | **on** | `NIXON_STDLIB_AUDIT_OFF`, `--no-stdlib-audit` |
| Audit-hook plant detector | **on** | `--no-audit-hook-plant` |
| Loader traceback suppression | **on** | — |
| BYOVD driver check | off (`--driver-check`) | read-only; never loads a driver |

Modules: `obfuscator/frozen_snapshot.py`, `stdlib_audit.py`, `audit_hook.py`,
`driver_blocklist.py`, `kill_ladder.py`, `hostguard.py`. Kill primitives exit the
process and are silent unless `NIXON_LADDER_DEBUG=1`.

Structural anti-tamper: `--section-split` on the **loader** CLI (Shamir n=3,k=2
threshold with a fragmented decoder), and on `build.py`: `--rolling-keys`,
`--temporal-keys`
(**inert — see the note in the CLI reference**), `--history-bound-decryption`,
`--state-isa`, `--attestation`, `--challenge-response`, `--crypto-binding`
(build-time validation only; the chain secret is not written to the artefact).

### 6. Licensing, binding and provenance

`--hwid` + `--hwid-lock` · `--trial` (formats `90s 1m 1h 1d 1w 1mo`) ·
`--watermark` + `--verify-watermark` · `--verify-watermark-survivability` ·
`--name-gate` · `--rename-internal` · `--licence-token` · `--customer-salt` ·
`--sign-key-env` · `--embed-proof` · `--zk-state` · `--remote-unlock` ·
`--dist-watermark` · `--provenance-replace`

A licence token carries a SHA-256 of the issuer seed, not the seed; the payload key
is masked with it, so **an artefact without its token decrypts to garbage**
(`tests/test_licence_binding.py`, and the derivation is documented in
`obfuscator/licensing.py`).

### 7. Packaging and loaders

`--pytoc` (Cython) · `--pyinstaller-spec` · `--simd-vm` (C VM; the SSE path only on
x86, the scalar fallback elsewhere) · `--fhe-vm` · `--oram` · `--rop` · `--sgx` ·
`--tee` · `--cross win,linux,macos,linux-arm` · `--payload-dispersal` ·
`--split-bootstrap` · `--generate-payload-h` · `--rust-exe` · `--python-dll`

`--pytoc` and `--pyinstaller-spec` are best-effort and never fail the build.

### 8. Verification you can run

`--validate` · `--validate-fail` · `--verify-preservation` ·
`--verify-preservation-formal` · `--verify-mutations` · `--verify-jit` ·
`--verify-mba` · `--prove-vm` · `--prove-fragments` · `--proof-coverage` ·
`--proof-soundness` · `--verification-bundle` · `--evidence-ledger` ·
`--confidence-interval`

A build now **fails** if its own phase-3 table reports a variant mismatch
(`match == MISMATCH`); a variant that merely could not be run is reported as
inconclusive and does not fail the build. That distinction is deliberate: a gate
that fires when it cannot check is a gate people learn to ignore.

### 9. Research and evaluation

`scripts/` carries the measurement programme behind the claims: `benchmark/`,
`evaluation/` (analyst time, cost model, survivability probes), `attack_replay/`,
`adversarial_bench/`, `proofs/`, `zk_state/`, `distributed/`, `gpu/`, `fhe_vm/`.
Their flags are in the CLI reference under *Research, evaluation and reporting*.


Measured numbers (host-specific, reproducible in-repo):

- Phase-1 lowering-shim overhead: per-family geomeans **1.46x–3.84x** vs
  plain CPython — `obfuscator/lowering_DESIGN.md` table
  (`NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py`;
  finite-ratio/parity assertions in `tests/test_lowering_perf.py`).
- Vendor-native claims (**0.19x–1.56x**) describe a native kernel and are
  **NOT reproduced in-repo** (stated in `scripts/benchmark/lowering_perf.py`
  header and `obfuscator/lowering_DESIGN.md`).

## CLI reference

Complete: every option `scripts/build.py` accepts, generated from the parser's own
`--help`. The block below is machine-generated and checked in CI
(`tests/test_readme_matches_cli.py`), so it cannot drift from the code again —
it previously listed 42 of 271 options under a heading claiming to be from `--help`.

<!-- BEGIN GENERATED CLI REFERENCE -->

Every option `scripts/build.py` accepts, generated from its own `--help` by
`scripts/gen_cli_reference.py` and checked by `tests/test_readme_matches_cli.py`,
so it cannot drift. Editorial notes are marked where a flag is inert or archived.

**268 options.**

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
| `--branch-entangle` | Enable branch predictor entanglement (Item 125) **Archived** — logs and continues; no entanglement is emitted. |
| `--cfg-mutation` | Enable live CFG mutation (variant basic-block ordering) |
| `--cfg-mutation-variants CFG_MUTATION_VARIANTS` | Number of CFG orderings per function (default: 4) |
| `--class-dispatch` | Enable execution-path-specific JIT codegen |
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
| `--multicore-entangle` | Enable multi-core timing entanglement (Item 126) **Archived** — logs and continues; no entanglement is emitted. |
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
| `--per-exec-recompile` | Enable per-execution recompilation |
| `--phase2-extras` | Enable optional extras (antidbg APIs, packing, timing checks, etc.) |
| `--randomization-level {1,2,3}` | Randomization level 1-3 (default: 3) |
| `--randomization-seed RANDOMIZATION_SEED` | Deterministic seed for structure randomization (also read from SEED/NIXON_SEED env when flag is absent) |
| `--self-healing` | Enable self-healing runtime (redundant code copies) |
| `--speculation-obfuscation` | Enable AST-level speculation obfuscation (Item 123) |
| `--ssa-mutation` | Enable SSA mutation (variant instruction ordering) |
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
| `--state-isa` | Enable state-dependent opcode mapping |
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
| `--hpc-detect` | Enable emulator detection via HPC (Item 122) **Archived** — the native backend has no call path; logs and continues. |
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
| `--build-id BUILD_ID` | Stable build id: seeds the semantic-lowering kernel and is recorded in the signature sidecar, so two builds with the same --build-id lower identically. It does not by itself make the whole build reproducible (default: empty = random per build) |
| `--cache-bound` | Enable cache-bound execution (Item 124) **Archived** — the native backend has no call path; logs and continues. |
| `--context-saturation` | Compute context window saturation metrics |
| `--cross-process` | Enable cross-process fragment binding (Item 111) |
| `--deobfuscation-threshold DEOBFUSCATION_THRESHOLD` | Minimum deobfuscation score (default: 0.7) |
| `--diagnostic` | Diagnostic build: per-stage timings + transform counts + NOT-FOR-RELEASE marker |
| `--dispersal-slices DISPERSAL_SLICES` | Number of payload slices (default: 3) |
| `--flow-entangle` | Enable whitebox-flow entanglement (crypto-state- dependent control flow) |
| `--function-intent` | Enable function intent obfuscation |
| `-h, --help` | show this help message and exit |
| `--hw-entropy` | Enable hardware entropy loop (Item 123) **Archived** — the native backend has no call path; logs and continues. |
| `--kod` | [LOADER ONLY -- ignored by this pipeline] Arm loader kill-on-detect: the VM snippet reads NIXON_KOD env at runtime (default: report-only) |
| `--max-cpu-overhead MAX_CPU_OVERHEAD` | Max CPU overhead percentage (default: 20) |
| `--max-size-mult MAX_SIZE_MULT` | Max binary size multiplier (default: 3.0) |
| `--optimize` | Enable cost-aware protection optimizer |
| `--payload-dispersal` | Enable payload dispersal execution model (disjoint slice execution) |
| `--poly-engine` | Enable environmental poly-engine (environment-adapted code variants) |
| `--require-live-features N` | Fail the build unless at least N features are LIVE in the artefact |
| `--seed SEED` | seed the randomised transform order (reproducible builds) |
| `--silent-fallback` | Detect silent fallbacks (try/except without logging) in codebase (Feature 191) |

<!-- END GENERATED CLI REFERENCE -->

### The loader CLI

`python3 -m obfuscator.core.pipeline build` is a second entry point with its own
option set — the counter-REA flags, section splitting and the loader-side switches
live here, not in `build.py`. Generated from that parser's `--help`, and checked by
the same test.

<!-- BEGIN GENERATED LOADER REFERENCE -->

Every option `scripts/build.py` accepts, generated from its own `--help` by
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
| `--lock-hwid LOCK_HWID` | Lock the build to a target HWID: registers a license for it and seeds the build deterministically |
| `--net-url NET_URL` | Auth URL (if not using auto=cf) |
| `--one-shot` | Self-destruct |
| `--pin-structure` | Pin the EMITTER-ONLY draws (encoding order, slot picks, names, VM op-map) so two builds share a structure. Debugging aid; key material is not pinned, so artefacts are not byte-identical. |
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

## Audit

The most recent full repository audit is [`docs/AUDIT-2026-10-19.md`](docs/AUDIT-2026-10-19.md) — 20 sections, the
vendor v1.1→V10 version matrix, and a completeness verdict. It also records
the two highest-severity findings of the year: the adversarial injection
corrupting the emitted ChaCha20 seal (~80% of default builds produced a dead
artifact) and a process-wide `mlockall(MCL_FUTURE)` leak. Both are fixed.

The follow-up rounds are in
[`docs/AUDIT-2026-10-19-followup.md`](docs/AUDIT-2026-10-19-followup.md)
(verified TLS, no import-time log file, `section_split` wired, an
enforceable lint gate) and
[`docs/AUDIT-2026-10-20.md`](docs/AUDIT-2026-10-20.md) (the CLI audit:
dropped flags, an unpinned lint gate, an untracked build config, a hard
`z3` dependency, and the documentation refresh). The current suite is
**4314 passed, 23 skipped, 0 failed** (plus 289 Rust runtime tests and
4 Rust relay tests).

### Which version numbers are which

| Numbering | Meaning |
|---|---|
| **2.0.0** | **this product's** version. One constant, in `obfuscator/version.py`; the CLI reports it and `config/default.json` carries the same value (a test checks they agree). See [`docs/CHANGELOG.md`](docs/CHANGELOG.md). |
| **v1.1 … V10** | the **vendor's** obfuscation-technique generations, tracked in the audit report's version matrix. They are NOT releases of this tool and must not be compared with 2.0.0. |

## Changelog

[`docs/CHANGELOG.md`](docs/CHANGELOG.md).

The suite is green. The live count is a moving number -- read it from
`python3 -m pytest tests/ -q` rather than from a doc; the dated
snapshots live in the audit reports.

## Security model + honest limitations

- Kernel-driver stance: **read-only BYOVD gate, no ring-0 loading.**
  `obfuscator/driver_blocklist.py` enumerates loaded-driver names only
  (Linux `/proc/modules`, Windows `EnumDeviceDrivers`) and compares stems
  against a ~20-entry public BYOVD blocklist (LOLDrivers-derived). No driver
  loading, no IOCTLs, no service installation, no writes. Disarmed (default)
  it enumerates and returns hits but never exits; armed it fails closed via
  `os._exit(1)` plus a best-effort 60 s daemon re-check thread.
- Kill primitives (`_nx_kill`) exit the process (exit 137 for audit-plant)
  and are silent unless `NIXON_LADDER_DEBUG=1` (`obfuscator/kill_ladder.py`).
- Limitations verified during doc writing:
  - Lowered artifacts (`--lowering`) need `lowering_shim` importable
    (run with `PYTHONPATH=.../obfuscator`); otherwise `ModuleNotFoundError`.
  - `--watermark` without IR stages logs a conflict hint
    (`skip_irgen <-> watermark (requires)`); the AST path still builds.
  - `--pytoc` / `--pyinstaller-spec` are best-effort and never fail the build.
  - Vendor-native perf claims (0.19x–1.56x) are not reproduced in-repo;
    measured Phase-1 shim overhead is 1.46x–3.84x per family.
- Full attacker-by-attacker breakdown: `THREAT_MODEL.md`.
- Policy, supported versions (3.10–3.14), and enforceable invariants: `SECURITY.md`.

## Repo layout

```text
scripts/build.py          Build pipeline entry point (+ scripts/phases/, scripts/benchmark/)
obfuscator/               AST obfuscation, lowering, loader-gate emitters (vm_score, trial_bind,
                          hwid_lock, watermark_gate, frozen_snapshot, stdlib_audit, audit_hook,
                          driver_blocklist, split_bootstrap, name_gate, internal_rename, nyser, py_matrix)
irgen/ llvmgen/ encrypt/  IR / LLVM / post-link encryption stages
vm/ runtime/ relay/       VM ISA + interpreters, Rust runtime, Rust relay binary
native/                   C/C++ extensions and stubs
tests/test_*.py           Per-feature test files (see table above)
docs/research/            Research programme: paper, benchmark, nine defect reports,
                          retraction record -- start at docs/research/README.md
docs/                     DEVELOPER.md, USER_GUIDE.md, PLATFORMS.md, ATTESTATION.md, ROADMAP.md, ...
examples/hello.py         Sample payload (print-based)
```

## Research programme

`docs/research/` holds a research programme that ran alongside this codebase and
produced **nine correctness defects** in it, all fixed and guarded, plus one
negative result written up as an instrument-validity note. Start at
[`docs/research/README.md`](docs/research/README.md).

Four independent checks back it:

| check | command | what it catches |
|---|---|---|
| test suite | `python3 -m pytest tests/ -q` | code drifting from its specification |
| artefact gate | `python3 scripts/transfer/artefact_gate.py --variants 2 --seeds 4242,7` | output that does not compile, import or run |
| reproduction | `python3 scripts/transfer/reproduce.py` | prose drifting from measurement |
| paper guards | `python3 -m pytest tests/test_research_docs_consistency.py -q` | prose drifting from its own tables |

The defects matter more than the paper. Six of the nine could not have been found
by this project's own tests: they needed code the project did not write (three
external libraries and a vendored package, 104 gated artefacts) or a check that
imports the artefact rather than compiling it. Two of the nine produced code that
**looked fine and was not obfuscated at all**.

## Testing

```bash
NIXON_LOG_REDIRECT=0 python3 -m pytest tests/ -q
```

That is the whole suite. It is large (a few hundred test files), so the
targeted subsets below are what to reach for while working:

```bash
NIXON_LOG_REDIRECT=0 python3 -m pytest tests/test_lowering.py \
  tests/test_opcount_truth.py tests/test_vm_subset.py tests/test_clock_bias.py -q
```

A broader verified subset (lowering parity, diagnostic, trial, hwid,
pytoc, spec, snapshot, stdlib, watermark, gates, split-bootstrap, driver):

```bash
NIXON_LOG_REDIRECT=0 python3 -m pytest tests/test_lowering_parity_141.py \
  tests/test_diagnostic.py tests/test_trial_bind.py tests/test_hwid_static.py \
  tests/test_hwid_lock.py tests/test_pytoc.py tests/test_pyinstaller_spec.py \
  tests/test_stdlib_audit.py tests/test_frozen_snapshot.py tests/test_watermark_gate.py \
  tests/test_name_gate.py tests/test_internal_rename.py tests/test_split_bootstrap.py \
  tests/test_driver_blocklist.py -q
```

Other gates:

```bash
make lint        # ruff + the runtime undefined-global check
make e2e         # every build must produce an artifact that RUNS
make audit-commit  # what the last commit removed, and which removals dropped a call
```

`NIXON_LOG_REDIRECT=0` keeps pytest output on the console instead of
`build.log`.

## Contributing

See `docs/DEVELOPER.md` (prereqs, `make` targets, project structure).
Do not commit docs or code without running the relevant tests above.
