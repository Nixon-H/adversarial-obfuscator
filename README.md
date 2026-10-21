# Nixon Adversarial Obfuscator (shadow-compiler)

Python-source obfuscator + loader-hardening pipeline. `scripts/build.py`
(version `shadow-compiler 2.0.0`, per `python3 scripts/build.py --version`)
takes a Python payload and emits an obfuscated `.py` artifact into `build/`
plus loader gates (anti-VM, trial/HWID, watermark, snapshot/stdlib-audit,
audit-hook plant detection, optional kernel-driver gate).

> Scope note: this repo also contains research/experimental flags (FHE-VM,
> iO, ZK, GPU/TEE/SGX, distributed execution, red-team). This README covers
> only the paths verified by the test-suite and by the commands below.
> Unlisted flags exist in `--help` but are out of scope here.

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

## Quick-start (verified 2026-09-23)

The `-o/--output` path is a staging path: the final artifact is always
packaged as `build/<payload>_obfuscated.py` (`scripts/phases/phase06_package.py`).
`-o` outside the build dir is refused unless `--force-output` is passed
(path-traversal guard: silent overwrites of arbitrary files are a
footgun for a local build tool).
Without `NIXON_LOG_REDIRECT=0`, stdout/stderr go to `build.log`
(`obfuscator/core/utils.py`; the default is `1`, and `scripts/build.py`
itself calls `setdefault("0")`, so plain `python3 scripts/build.py ...`
prints to the console — but any library import path without that
`setdefault` still redirects).

```bash
echo 'print("hello-nixon")' > /tmp/hello.py
NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/qs_hello.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras
# [   OBFUSCATE] Done: 1.1KB (was 0.0KB)
# [     PACKAGE]   Payload: /home/nixon/Projects/adversarial-obfuscator/build/hello_obfuscated.py
#   Build artifacts: /home/nixon/Projects/adversarial-obfuscator/build/

NIXON_LOG_REDIRECT=0 timeout 60 python3 build/hello_obfuscated.py
# hello-nixon
```

Notes:

- `--skip-*` keeps this to the AST-obfuscation stage. Without them the
  pipeline runs IR/LLVM/encrypt/relay stages (needs the toolchain above).
- `--lowering io,scalar` (no skips removed) rewrites call sites to
  `from lowering_shim import ...`; that artifact only runs with
  `obfuscator/` on `PYTHONPATH`, otherwise `ModuleNotFoundError:
  No module named 'lowering_shim'`. Default (no `--lowering`) runs anywhere.

## Features (each row has test evidence)

| Feature | What it does | Evidence |
|---|---|---|
| AST obfuscation ladder `--opt-level 0-5` (default 4, 14/17 flags on) | cfg-flatten, opaque predicates, MBA, string fragmentation, unicode ids, junk/decoys/minify/dataflow/provenance | `tests/test_opt_levels.py`, `tests/test_obfuscator.py` |
| Semantic lowering, 20 families / 140 kernel ops | rewrites covered call sites to `_nxk_*` kernel calls; op-count truth-locked | `tests/test_lowering.py`, `tests/test_opcount_truth.py`, `tests/test_lowering_parity_141.py` |
| Anti-VM loader snippet, 12 of 14 signals Linux-checkable incl `clock_bias` (`registry_keys`/`wmi_bios` are Windows-only) | weighted verdict vs `--vm-threshold` (default 50.0); report-only unless KOD armed | `tests/test_vm_subset.py`, `tests/test_vm_score.py`, `tests/test_clock_bias.py` |
| Frozen-stdlib snapshot gate (default ON) | refuse-to-run on stdlib tamper; runtime off via `NIXON_SNAPSHOT_OFF` | `tests/test_frozen_snapshot.py` |
| Stdlib function-audit gate (default ON) | audit of stdlib functions; runtime off via `NIXON_STDLIB_AUDIT_OFF` | `tests/test_stdlib_audit.py` |
| Audit-hook plant detector (default ON) | kills on site-packages `.pth`/sitecustomize plants; off via `--no-audit-hook-plant` / `NIXON_AUDITHOOK_PLANT_OFF` | `tests/test_sitepackages_hook.py` |
| Trial gate `--trial 7d` | composite-fallback expiry enforcement, formats `90s 1m 1h 1d 1w 1mo` combos (`m` = minute, `mo` = month) | `tests/test_trial_bind.py`, `tests/test_macros.py` |
| HWID binding `--hwid` + `--hwid-lock` | dynamic string (via `uuid.getnode()`) or static `HWID:<64 hex>` canonical fingerprint | `tests/test_hwid_static.py`, `tests/test_hwid_lock.py`, `tests/test_hwid_lock_integration.py` |
| Watermark `--watermark STR` (+ `--verify-watermark`) | semantic watermark embedded in IR + refuse-to-run gate when configured | `tests/test_watermark.py`, `tests/test_watermark_gate.py`, `tests/test_watermark_survivability.py` |
| Name gate `--name-gate` (opt-in) | rewrites privileged call sites through per-build token map | `tests/test_name_gate.py` |
| Internal rename `--rename-internal` (opt-in) | renames proven-internal public methods/attributes only | `tests/test_internal_rename.py` |
| BYOVD driver gate `--driver-check` (opt-in) | read-only blocklist check, fail-closed only when armed | `tests/test_driver_blocklist.py` |
| Split bootstrap `--split-bootstrap` (opt-in) | Shamir (n=3,k=2) threshold key + fragmented decoder in loader | `tests/test_split_bootstrap.py` |
| Diagnostic build `--diagnostic` | per-stage timings + transform counts + NOT-FOR-RELEASE marker | `tests/test_diagnostic.py` |
| `--pytoc` native extension (best-effort) | Cython compile of output; never fails the build | `tests/test_pytoc.py` |
| `--pyinstaller-spec` (best-effort) | writes `.spec` next to output; never fails the build | `tests/test_pyinstaller_spec.py` |
| Artifact signing `--sign-key-env VAR` | signs packaged payload to `<file>.sig.json` (best-effort) | `tests/test_artifact_sign.py` |
| Audit-timing enforcement (opt-in env) | `NIXON_AUDIT_TIMING` arms timing-kill in audit hook | `tests/test_audit_timing.py` |
| Loader traceback suppression (default ON) | `tracebacklimit=0` + quiet excepthook ("fatal error", no paths); diagnostics via `NIXON_TRACEBACKS=1` | `tests/test_traceback_suppression.py` |

Measured numbers (host-specific, reproducible in-repo):

- Phase-1 lowering-shim overhead: per-family geomeans **1.46x–3.84x** vs
  plain CPython — `obfuscator/lowering_DESIGN.md` table
  (`NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py`;
  finite-ratio/parity assertions in `tests/test_lowering_perf.py`).
- Vendor-native claims (**0.19x–1.56x**) describe a native kernel and are
  **NOT reproduced in-repo** (stated in `scripts/benchmark/lowering_perf.py`
  header and `obfuscator/lowering_DESIGN.md`).

## CLI reference (from `scripts/build.py --help`)

```text
--payload PAYLOAD     Python script to obfuscate (required)
-o, --output OUTPUT   Staging output path; final artifact lands in build/<name>_obfuscated.py
--force-output        Allow -o outside the build dir (default: refused)
--cross CROSS         Cross-compile targets: win,linux,macos,linux-arm
--skip-obfuscate | --skip-irgen | --skip-llvmgen | --skip-encrypt | --skip-relay | --skip-extras
--include-original    Include original payload in build/
--no-cfg-flatten | --no-opaque-predicates | --no-bogus-exceptions | --no-mba-subs
    | --no-fragment-strings | --no-unicode-ids
--opt-level {0,1,2,3,4,5}   Protection ladder, default 4 (recommended)
--lowering LOWERING   Family CSV (default '' = disabled). Bare names ADD to
                      the 15 defaults; -fam removes; none = empty; "all" = all 20
--diagnostic          Per-stage timings + transform counts + NOT-FOR-RELEASE marker
--pytoc [--pytoc-out PATH]  Cython native-extension compile (best-effort, never fails build)
--pyinstaller-spec    Write best-effort PyInstaller .spec (never fails build)
--watermark WATERMARK Embed semantic watermark string into IR
--verify-watermark     Verify watermark after embedding
--sign-key-env VAR    Env var holding hex key for .sig.json sidecars (default '' = disabled)
--name-gate           Per-build token map for privileged calls (default off)
--rename-internal     Rename proven-internal public methods/attributes (default off)
--build-id BUILD_ID   Seeds the lowering kernel and is recorded in the
                      signature sidecar. It does NOT by itself make the
                      whole build reproducible (default: empty = random)
--version             Prints e.g. 'shadow-compiler 2.0.0'
```

The flags below configure the **hybrid loader**. They are accepted by
`scripts/build.py` for backward compatibility, but this pipeline emits a
native binary and no hybrid loader, so they are **reported as ignored**
at run time. The loader build path is
`python3 -m obfuscator.core.pipeline build` (see below), where they
apply:

```text
--hwid HWID           Dynamic string, or static 'HWID:<64 hex>' fingerprint
--hwid-lock           HWID-lock the fallback blob (requires --hwid; default off)
--trial TRIAL         e.g. '7d', '1w2d' (parsed via obfuscator.macros.parse_trial; default '')
--vm-threshold FLOAT  VM-score verdict threshold in loader snippet (default 50.0)
--kod                 Arm loader kill-on-detect (runtime reads NIXON_KOD; default report-only)
--hostguard           Prepend hostguard snippet (default off)
--driver-check        Bake V10 kernel-driver gate into loader (default off; also NIXON_DRIVER_CHECK=1)
--split-bootstrap     Shamir (n=3,k=2) threshold key + fragmented decoder (default off)
--no-snapshot         Omit frozen-stdlib snapshot gate (default: gate ON)
--no-stdlib-audit     Omit stdlib function-audit gate (default: gate ON)
--no-audit-hook-plant Omit site-packages audit-hook plant detector (default: detector ON)
```

### The loader CLI (`python3 -m obfuscator.core.pipeline`)

A second, separate CLI. It emits the hybrid loader; `scripts/build.py`
compiles the payload to a native binary. They share the transform
implementation but not the flag set.

```text
build <script.py>          Obfuscate and compile a Python script
  --native | --native-only Cloud-farm Cython compilation (hybrid / no fallback)
  --auto [cf,nk]            Automation: cf=Cloudflare, nk=Nuitka (implies --native)
  --lock-hwid HWID          Lock the build to a target HWID (licence target)
  --watermark MSG          Embed an owner-supplied watermark message in the
                            loader, HMAC-tagged and checked at load time
  --debug-dump-raw          Compile the plaintext-dump debug aid into the
                            artifact (off by default)
  --compile                 Compile the final loader with Nuitka
  --skip-cloud              Build locally even if --compile/--auto would use the farm
  --platform {auto,github}  Build farm platform (GitHub is the only implemented farm)
  --section-split           Ship the payload as N sealed sections (needs a
                            fallback). ON by default: the whole encrypted
                            payload is never resident in one buffer
  --no-section-split        Ship it as a single blob instead (the escape hatch)
  --section-count N         Number of sealed sections (default 4)
  --opt-level 0-5           Protection ladder; without it the loader build
                            applies the full transform set
  --tls-ca-bundle PEM       Extra CA for the emitted key fetch; verification is never disabled
  --expire YYYY-MM-DD       Expiration date
  --hwid / --trial / --vm-threshold / --kod / --hostguard / --hwid-lock
  --driver-check / --split-bootstrap / --no-snapshot / --no-stdlib-audit
  --name-gate / --lowering / --rename-internal / --no-audit-hook-plant
auth --hwid HASH            Authorize a hardware ID (Cloudflare)
clean                       Remove the Cloudflare deployment
obfuscate <script.py>       Obfuscate a Python script (-o PATH, --opt-level 0-5)
build-farm --payload PATH   Trigger the cloud build farm
version                     Show the version
```

`--opt-level` (the 0-5 protection ladder) resolves the same 17 canonical
transform flags on all three CLIs now. Without it the loader build
applies the full transform set, as it always has; with it, the flags the
ladder controls follow the level.

The two CLIs' `--watermark` means different things, which is why the
loader CLI's flags say which is which: there `--lock-hwid` is the target
machine the build is licensed to, and `--watermark` is the
owner-supplied message the loader's watermark gate checks.
`scripts/build.py --watermark` embeds a semantic watermark in the IR.

Note: `--lowering`'s `--help` text lists the 9 node/call families
(`io,scalar,string,container,service,protocol,function,import,fusion`)
plus 5 opt-in node-kind families
(`arithmetic,truth,slice,format,augassign`); the registry in
`obfuscator/lowering.py` additionally defines per-type method families
(`list,dict,set,tuple,bytes,range`) for a total of 20, of which 15 are
default-ON when lowering is enabled (verified:
`python3 -c "from obfuscator import lowering; ..."` prints 20 / 15).
`--lowering` itself defaults to `''` = disabled.

Default-ON vs default-OFF matrix:

| Default ON | How to disable |
|---|---|
| Frozen-stdlib snapshot gate | `--no-snapshot` or `NIXON_SNAPSHOT_OFF=1` at runtime |
| Stdlib function-audit gate | `--no-stdlib-audit` or `NIXON_STDLIB_AUDIT_OFF=1` |
| Audit-hook plant detector | `--no-audit-hook-plant` or `NIXON_AUDITHOOK_PLANT_OFF=1` |
| `--opt-level 4` AST transforms | `--opt-level 0` / `--no-*` flags / `--skip-obfuscate` |
| Lowering default families (15/20, incl `range`) once `--lowering` is passed | `--lowering none`, or `-fam` removals |
| Watermark/trial/HWID gates | only when configured (`--watermark` on the native pipeline; `--watermark` / `--lock-hwid` / `--trial` / `--hwid` on the loader CLI) |

| Default OFF (opt-in) | How to enable |
|---|---|
| `--driver-check` kernel-driver gate | flag on the loader CLI, or `NIXON_DRIVER_CHECK=1` at runtime |
| `--rename-internal` | flag (both CLIs) |
| `--split-bootstrap` | flag on the loader CLI |
| KOD kill-on-detect (VM + audit-hook timing) | `NIXON_KOD=1` at runtime (report-only otherwise) |
| Audit timing enforcement | `NIXON_AUDIT_TIMING=<any non-"0" value>` arms at runtime |
| `--lowering` itself | `--lowering <csv>` |
| Opt-in lowering families (`arithmetic,truth,slice,format,augassign`) | `+fam` / bare names / `all` |
| Tor SOCKS endpoint for build-farm traffic | `NIXON_TOR_PROXY=<host:port>` (default `127.0.0.1:9050`); also read at runtime by the emitted Tor client. `--tor`/`--tor-proxy` belong to the `obfuscator/core/pipeline.py` CLI (`build`/`build-farm` subparsers) — `scripts/build.py` has no Tor flag |

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
**4303 passed, 23 skipped, 0 failed** (plus 289 Rust runtime tests and
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
docs/                     DEVELOPER.md, USER_GUIDE.md, PLATFORMS.md, ATTESTATION.md, ROADMAP.md, ...
examples/hello.py         Sample payload (print-based)
```

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
