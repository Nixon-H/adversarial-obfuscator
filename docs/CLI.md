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
  still run; add `advanced-protection only=LIST none` for the ladder alone.
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
  --skip irgen --skip llvmgen --skip encrypt --skip relay --skip extras

NIXON_LOG_REDIRECT=0 timeout 60 python3 build/hello_obfuscated.py
# hello-nixon
```

About one second; ~15 KB from a 21-byte source at the default `--opt-level 4`.
Level 0 disables the ladder but not the always-on passes; `--skip obfuscate`
is the byte-identical copy path.

The packed loader writes **next to the payload**, not to the current directory:
`<dirname(payload)>/dist/<name>_protected.py`. A build of `/tmp/hello.py`
therefore writes `/tmp/dist/hello_protected.py` (verified 2026-11-10).

## What the skips buy

| Skip | Stage removed | Needs |
|---|---|---|
| `--skip irgen` | IR construction | — |
| `--skip llvmgen` | LLVM codegen | `llc` |
| `--skip encrypt` | Post-link encryption | — |
| `--skip relay` | Rust relay build | `cargo` |
| `--skip extras` | Optional native extras | — |

Drop them only when the toolchain is present; a full build is minutes, not
seconds.

## Flags that need a warning

| Flag | Reality |
|---|---|
| `--research temporal-keys` | **Inert.** ~19 s of hashing to produce metadata nothing reads. |
| `--research crypto-binding` | **Build-time only.** Nothing decrypts at run time. |
| `--transforms seed=N` / `SEED` | Seeds part of the pipeline; does **not** make builds byte-reproducible. |
| `--research code-genome` | Real but expensive: 50 × 30 = 1,500 evaluations by default. Use `genome-generations=N 2 genome-population=N 4`. |

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

**30 options.**

### Input, output and build control

| Option | What it does |
|---|---|
| `--force-output` | Allow -o/--output outside the repo build dir (default: refuse absolute/escaping paths) |
| `--include-original` | Include original payload in build/ |
| `-o, --output OUTPUT` | Staging path for the obfuscated script (the final artifact is written to build/) |
| `--payload PAYLOAD` | Python script to obfuscate |
| `--version` | show program's version number and exit |

### Obfuscation ladder and AST transforms

| Option | What it does |
|---|---|
| `--lowering LOWERING` | Semantic-lowering families CSV (io,scalar,string,conta iner,service,protocol,function,import,fusion + opt-in: arithmetic,truth,slice,format,augassign); default '' = disabled |
| `--no-anti-rea` | Disable every counter-REA/deception layer |
| `--no-bogus-exceptions` | Disable fake exception handlers (default: on) |
| `--no-cfg-flatten` | Disable control-flow flattening (default: on) |
| `--no-fragment-strings` | Disable string fragmentation (default: on) |
| `--no-mba-subs` | Disable MBA expression substitution (default: on) |
| `--no-opaque-predicates` | Disable opaque-predicate insertion (default: on) |
| `--no-unicode-ids` | Disable Unicode symbol renaming (default: on) |
| `--opt-level {0,1,2,3,4,5}` | Optimization/protection ladder O0-O5 (default: 4, recommended) |
| `--validate [[fail]]` | Run SMT semantic validation; 'fail' also aborts the build when validation fails |

### Anti-analysis, counter-REA and deception

| Option | What it does |
|---|---|
| `--anti-rea-level {stealth,balanced,maximum}` | Counter-REA shields are ON by default at maximum: there is no enable flag. Pass this only to LOWER the intensity (stealth or balanced) |

### Licensing, binding, watermarking and provenance

| Option | What it does |
|---|---|
| `--sign-key-env SIGN_KEY_ENV` | Env var name holding hex key for artifact signing sidecars (.sig.json; default: '' = disabled) |
| `--watermark WATERMARK` | Embed semantic watermark string into IR |

### Other

| Option | What it does |
|---|---|
| `--access OPT [OPT ...]` | Loader-only access gates (hwid, trial, kod, ...). This native pipeline emits no packed loader, so --access is refused here; use 'python3 -m obfuscator.core.pipeline build --access ...' instead |
| `--audit NAME [NAME ...]` | Run report/verification phases. Names are the old flag names without '--' (e.g. reality-score, security- gates, proof-coverage, verify-preservation); 'all' runs every report. key=value tunes a phase, e.g. confidence-level=0.99 or gate-threshold=0.8 |
| `--build-id BUILD_ID` | Stable build id: seeds the semantic-lowering kernel and is recorded in the signature sidecar, so two builds with the same --build-id lower identically. It does not by itself make the whole build reproducible (default: empty = random per build) **Lowering-kernel seed only.** Seeds the `--package pytoc` semantic-lowering symbol map and is recorded in the manifest. It does not make the whole build reproducible, and a build without `--package pytoc` does not use it. |
| `--diagnostic` | Diagnostic build: per-stage timings + transform counts + NOT-FOR-RELEASE marker |
| `--exclude FAMILY [FAMILY ...]` | Skip shield families. 'rea' turns every counter-REA layer off; namespaced entries skip one: rea.poison, rea.honey, rea.decoy, rea.attention, rea.traps, rea.storyline, rea.llm-resilient, rea.red-team, rea.self-critique, rea.manipulation, rea.prompt, rea.false-confidence, rea.multi-agent, rea.adversarial |
| `-h, --help` | show this help message and exit |
| `--optimize` | Enable cost-aware protection optimizer |
| `--package OPT [OPT ...]` | Packaging. All options: pytoc = compile the result to a Cython .so; pytoc-out=PATH = where that .so goes; pyinstaller = write a PyInstaller spec; python- dll=PATH = embed a Python DLL in the payload header; rust-exe=PATH = embed a Rust EXE in the payload header; cross=TARGETS = cross-compile for win,linux,macos,linux-arm; all (or everything) = package with everything else: pytoc pyinstaller cross=all targets plus every --transforms pass and --validate fail |
| `--research NAME [NAME ...]` | Run experimental/sidecar phases (the ones that write build/ metadata but do not change the artefact), e.g. cfg-mutation, code-genome, tee, gpu-execution. 'all' runs every research phase |
| `--seed SEED` | seed the randomised transform order (reproducible builds) **Reproducibility seed.** Seeds the global `random` module, the AST transformer's RNG and its `secrets` patch, and several injectors. With the same payload, tool version and flags, the source emitter is byte-identical. It does **not** make the packed loader reproducible, and it is not key material. `--skip obfuscate` is the copy path. |
| `--skip STAGE [STAGE ...]` | Skip build stages: conflict, obfuscate, irgen, llvmgen, encrypt, relay, extras, generate-payload-h |
| `--transforms OPT [OPT ...]` | Extra protection passes (off by default). Options: data = obfuscate data layout, data-level=3 = 1-3 intensity; function-intent = rename functions by what they do; speculation = speculation-resistant code; struct = randomise stack/heap/register layout, struct- level=3 = 1-3 intensity; seed=N = pin the pass RNG for reproducible builds |

<!-- END GENERATED CLI REFERENCE -->

## Generated reference: packed loader

<!-- BEGIN GENERATED LOADER REFERENCE -->

Every option `python3 -m obfuscator.core.pipeline build` accepts, generated from its own `--help` by
`scripts/gen_cli_reference.py` and checked by `tests/test_readme_matches_cli.py`,
so it cannot drift. Editorial notes are marked where a flag is inert or archived.

**31 options.**

### Input, output and build control

| Option | What it does |
|---|---|
| `--skip-cloud` | Skip the cloud build farm: build the artifact locally even if --package compile/cloud would send it to the farm |

### Obfuscation ladder and AST transforms

| Option | What it does |
|---|---|
| `--lowering LOWERING` | Semantic-lowering families CSV (default: disabled) |
| `--no-anti-rea` | Skip the counter-REA shields |
| `--no-section-split` | Ship the payload as a single blob instead of N sealed sections (default: sections are on) |
| `--no-split-bootstrap` | Ship the bootstrap key as one string instead of the default Shamir (n=3,k=2) split key + fragmented decoder |
| `--opt-level OPT_LEVEL` | Protection ladder 0-5: resolve the 17 canonical transform flags from the level. Without it the loader build applies the full set |

### Anti-analysis, counter-REA and deception

| Option | What it does |
|---|---|
| `--anti-rea` | Counter-REA shields: architecture-mirage chaff, canary credentials, evidence-contract poison, a decoy call graph and high-salience bait procedures (ON by default) |
| `--anti-rea-level {stealth,balanced,maximum}` | Counter-REA shields are ON by default at maximum: there is no enable flag. Pass this only to LOWER the intensity (stealth or balanced) |

### Licensing, binding, watermarking and provenance

| Option | What it does |
|---|---|
| `--licence KEY=VALUE [KEY=VALUE ...]` | Licence configuration: one flag for the whole licence gate. Sub-options: token=FILE = require this signed token at run time; salt=STRING = bind the key to a customer without a token; env-only = read the token only from NIXON_LICENCE; bootstrap-encrypted = encrypt the loader string table with a token key; chain = verify the signed ERC-721 owner on-chain. Booleans may be bare or =true/=false |
| `--watermark WATERMARK` | Embed an owner-supplied watermark message in the loader, HMAC-tagged and checked at load time: a stripped or edited watermark kills the artifact |

### Packaging, loaders, native backends and build farm

| Option | What it does |
|---|---|
| `--exclude-android` | Skip Android build in Nuitka cloud compilation |
| `--public` | Public Repo Mode (Flash Mode) - Nukes repo after build |
| `--python PYTHON` | Python version for GitHub Actions (Defaults to local) |
| `--resume RESUME` | Resume waiting for a specific GitHub Run ID (skip upload) |
| `--section-count SECTION_COUNT` | Number of sealed sections when section splitting is on (default 4) |
| `--tor` | Route build traffic through Tor (default 127.0.0.1:9050; override via --tor-proxy or NIXON_TOR_PROXY) |
| `--tor-proxy TOR_PROXY` | Tor SOCKS endpoint host:port (default 127.0.0.1:9050; env NIXON_TOR_PROXY) |

### Other

| Option | What it does |
|---|---|
| `--access KEY=VALUE [KEY=VALUE ...]` | Access gates: one flag for HWID/trial/expiry, hostile-host gates, geofence and alerting. Sub-options: hwid=STR hwid-lock lock-hwid=STR trial=7d expire=YYYY-MM-DD bind-mac one-shot kod hostguard driver-check name-gate rename-internal allow-countries=US,DE block-countries=RU allow-regions=R1 block-regions=R2 webhook=URL net-url=URL vm-threshold=50 (the former per-knob spellings were removed 2026-11-12) |
| `--bind BIND` | Bind files inside payload |
| `--cf-account CF_ACCOUNT` | Cloudflare Account ID (overrides the stored config) |
| `--cf-token CF_TOKEN` | Cloudflare API Token (overrides the stored config) |
| `--debug-dump-raw` | Compile the plaintext-dump debug aid into the artifact (it writes the decrypted payload to a 0600 temp file when NIXON_DUMP_RAW=1). Off by default: a normal artifact has no such capability |
| `--exclude FAMILY [FAMILY ...]` | Skip shield families: "rea" turns every bait layer off; "rea.compliance", "rea.cognitive", "rea.bio" skip one; "integrity.snapshot", "integrity.stdlib-audit", "integrity.audit-hook" omit one default-on integrity gate |
| `--fast` | Build the reduced-protection profile: detections only warn, entropy noise and rdtsc pressure are lower. Faster builds and faster artefacts; weaker posture. |
| `--package OPT [OPT ...]` | Packaging and mode. All options: native = cloud Cython compile keeping the bytecode fallback; native-only = cloud Cython with no fallback; compile = wrap the final loader in a Nuitka EXE/ELF; cloud = auto-build (cf,nk); platform=github = build farm (the only implemented one); layers=N = recursive packaging layers; zips=N = ZIP wrapper count; stego = hide the payload inside an image; portable = no native core, run anywhere; all (or everything) = every LOCAL packaging option: layers=25 zips=3 stego. The cloud compile (native/compile/cloud) is NOT part of all: it needs build-farm credentials and conflicts with stego — add it explicitly for cloud builds |
| `--pin-structure` | Pin the EMITTER-ONLY draws (encoding order, slot picks, names, VM op-map) so two builds share a structure. Debugging aid; key material is not pinned, so artefacts are not byte-identical. **Structure only.** Pins emitter draws and the build timestamp; key material is not pinned, so artefacts are not byte-identical. |
| `--private-key PRIVATE_KEY` | Deployment key |
| `--strict-detections` | Make the loader's environment detections (sandbox, emulator, debugger frame, geo-fence, licence) terminate the artifact instead of only perturbing it (ON by default; use --fast to opt out) |
| `--tls-ca-bundle TLS_CA_BUNDLE` | PEM CA bundle for the emitted key fetch. The artifact verifies the certificate chain AND the hostname against the system trust store plus this CA (it never disables verification) |
| `--transforms OPT [OPT ...]` | Extra protection passes on the payload before packing (off by default). Options: data = data-layout obfuscation, data-level=N (1-3), function-intent = rename functions by what they do, speculation = speculation-resistant code. struct stays native-pipeline only (it configures the LLVM/IR flow) |
| `--web3 KEY=VALUE [KEY=VALUE ...]` | Web3 configuration: one flag for RPC, explorer, contract, deployment and key shards. Sub-options: rpc=URL explorer=URL contract=ADDR shards=URL1,URL2 deploy deploy-rpc=URL (the former per-knob spellings were removed 2026-11-12) |

<!-- END GENERATED LOADER REFERENCE -->
