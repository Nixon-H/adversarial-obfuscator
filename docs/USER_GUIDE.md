# User Guide

Practical walkthrough for `scripts/build.py` (`shadow-compiler 2.0.0`).
Every command below was run on 2026-09-23 (CPython 3.13.5); outputs are
pasted verbatim. For the flag table and test-evidence matrix see
`README.md`.

## Two CLIs

| CLI | Produces | Use it for |
|---|---|---|
| `python3 scripts/build.py --payload P` | a **native** binary (obfuscate → IR → LLVM → encrypt → Rust relay) | shipping a compiled artifact |
| `python3 -m obfuscator.core.pipeline build P` | the **hybrid Python loader** | the loader-level gates (trial, HWID lock, KOD, driver check, split-bootstrap) |

The loader gates only exist in the loader: `scripts/build.py` accepts
those flags for backward compatibility and now says plainly that it
ignored them. Sections 3, 4 and 8 below therefore use the loader CLI.

## 1. Minimal build (verified)

`-o/--output` is a staging path; the final artifact is packaged as
`build/<payload>_obfuscated.py`. `NIXON_LOG_REDIRECT=0` keeps logs on the
console (otherwise stdout/stderr go to `build.log`; note `scripts/build.py`
itself calls `setdefault("0")`, so a plain build prints to the console —
but library import paths without that `setdefault` still redirect).

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

Remove `--skip-*` to run the full IR/LLVM/encrypt/relay stages (needs
`cargo`, `g++`, `llc`).

## 2. Semantic lowering (`--lowering`)

Default `''` = disabled. Value is a CSV with three forms
(`obfuscator/lowering.py: resolve_families`):

- bare names ADD to the 15 defaults; `-fam` removes; `none` = empty:
  `--lowering io,scalar` == defaults (io,scalar already default-ON)
- `+fam` / `-fam` = add/remove vs the 15 default-ON families
- `all` = all 20 families, `none` = empty

```bash
NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/out3.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras \
  --lowering io,scalar
# [         OPT] Semantic lowering families: io,scalar
# [    LOWERING] Semantic lowering: 15 families, 11 call sites
# [   OBFUSCATE] Done: 3.4KB (was 0.0KB)
```

The 20 families (`tests/test_lowering.py`, `obfuscator/lowering.py:
FAMILIES`): `io scalar string container service protocol range function
import fusion list dict set tuple bytes` (default-ON once lowering is
enabled) plus opt-in `arithmetic truth slice format augassign`
(node-kind rewrites, Phase-2, no runtime functions yet — excluded from the
benchmark per `scripts/benchmark/lowering_perf.py` header).

Caveat (verified): a lowered artifact imports `lowering_shim`
(`from lowering_shim import _nxk_...`, emitted by `emit_shim_import`), so
it only runs with `obfuscator/` on the path:

```bash
timeout 60 python3 build/hello_obfuscated.py
# ModuleNotFoundError: No module named 'lowering_shim'
NIXON_LOG_REDIRECT=0 timeout 60 env PYTHONPATH=$PWD/obfuscator python3 build/hello_obfuscated.py
# hello-nixon
```

Overhead reference: Phase-1 shim per-family geomeans **1.46x–3.84x** vs
plain CPython (`obfuscator/lowering_DESIGN.md`, reproduced with
`NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py`).
Vendor-native 0.19x–1.56x figures are not reproduced in-repo.

## 3. Trial gate (`--trial`)

```bash
NIXON_LOG_REDIRECT=0 timeout 300 python3 -m obfuscator.core.pipeline build \
  /tmp/hello.py --trial 7d
```

Spec format (`obfuscator/macros.py: parse_trial`): number+unit pairs such
as `90s`, `1w2d`, `1mo1hr`. Units: `s m h d w mo` — **`m` = minute,
`mo` = month**. Empty string = disabled. Garbage raises `ValueError`
(`tests/test_macros.py`, `tests/test_trial_bind.py`).

This is a LOADER gate. `scripts/build.py --trial 7d` is accepted but
ignored by that pipeline, and it now says so:

```text
[        WARN] These flags configure the HYBRID LOADER and are ignored by this native pipeline: trial period
[        WARN] Use `python3 -m obfuscator.core.pipeline build` for the loader build path.
```

## 4. HWID binding (`--hwid` + `--hwid-lock`)

> These are LOADER gates: they apply to
> `python3 -m obfuscator.core.pipeline build`, not to
> `scripts/build.py` (which emits a native binary and no hybrid loader).
> The native pipeline reports them as ignored.

Two modes (`obfuscator/hwid_lock.py`):

- dynamic (default): any opaque string; the loader collects
  `format(uuid.getnode(), 'x')` at runtime.
- static (GAP #33): canonical `HWID:<64 hex chars>` fingerprint
  (case-insensitive, lowercased) binding the artifact to a known value.

```bash
NIXON_LOG_REDIRECT=0 timeout 300 python3 -m obfuscator.core.pipeline build \
  /tmp/hello.py \
  --hwid HWID:9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c \
  --hwid-lock
```

These are LOADER gates: the native pipeline ignores them and reports
that it did (see the warning in section 3).

Malformed `HWID:`-prefixed values raise `ValueError`
(`tests/test_hwid_static.py`, `tests/test_hwid_lock.py`).

## 5. Watermark (`--watermark`)

> On the native pipeline `--watermark` embeds a semantic watermark in the
> IR.  On the loader CLI it is the owner-supplied message the loader's
> watermark gate checks at load time: a stripped or edited watermark
> kills the artifact.

```bash
NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/stage_hw.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras \
  --watermark testmark-123
#  1. skip_irgen <-> watermark (requires)
#     Semantic watermarking operates on IR; --skip-irgen disables IR
#     Fix: Remove --skip-irgen to use --watermark, or accept watermark on AST only
# [   WATERMARK] Embedding semantic watermark: 'testmark-123'
# [   WATERMARK] Watermarked IR written to .../build/program_wm.ir
```

The conflict hint is informational: the build still completes and the AST
path proceeds. With IR stages enabled the semantic watermark plus the
refuse-to-run gate (`obfuscator/watermark_gate.py`,
`tests/test_watermark_gate.py`) are baked in. `--verify-watermark`
verifies after embedding (`tests/test_watermark.py`).

## 6. Diagnostic build (`--diagnostic`)

```bash
NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/out2.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras \
  --diagnostic
# [         OPT] DIAGNOSTIC BUILD (not for release)
# [  PROVENANCE] Provenance removal loaded for 20 bytes (diagnostic only)
```

Adds per-stage timings + transform counts and stamps a NOT-FOR-RELEASE
marker (`tests/test_diagnostic.py`). Never ship a `--diagnostic` artifact.

## 7. `--pytoc` and `--pyinstaller-spec` (best-effort)

Both are best-effort and never fail the build
(`scripts/build.py --help`, `tests/test_pytoc.py`,
`tests/test_pyinstaller_spec.py`):

```bash
NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/stage_hw.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras \
  --pyinstaller-spec
# [         OPT] PyInstaller .spec generation requested (best-effort)
# build/hello_obfuscated.spec   (alongside the packaged payload)
```

`--pytoc [--pytoc-out PATH]` compiles the obfuscated output to a native
extension via Cython (default output: alongside `-o` as
`<out>_pytoc.<so/pyd>`); missing toolchain = skipped, build continues.

## 8. Opt-in hardening: `--name-gate`, `--rename-internal`, `--driver-check`, `--split-bootstrap`

`--name-gate` and `--rename-internal` are transform-level and work on
BOTH CLIs:

```bash
# Per-build token map for privileged call sites (default off; tests/test_name_gate.py)
--name-gate
# Rename proven-internal public methods/attributes only (default off; tests/test_internal_rename.py)
--rename-internal
```

`--driver-check` and `--split-bootstrap` are LOADER gates: they take
effect in `python3 -m obfuscator.core.pipeline build`, and the native
pipeline reports them as ignored.

```bash
# Bake the read-only BYOVD driver gate into the loader (default off; tests/test_driver_blocklist.py)
--driver-check
# Shamir (n=3,k=2) threshold key + fragmented decoder in the loader
# (opt-in until battle-tested; default off; tests/test_split_bootstrap.py)
--split-bootstrap
```

`--driver-check` on the loader build logs:

```text
[OPT] Kernel-driver gate baked into loader (--driver-check; also armable via NIXON_DRIVER_CHECK=1)
```

## 9. Environment-variable reference

Each var verified by grep against the tree (sources + tests):

| Variable | Effect | Default | Source |
|---|---|---|---|
| `NIXON_LOG_REDIRECT` | `1` redirects stdout/stderr to `build.log`; `0` keeps console | `1` (but `scripts/build.py` calls `setdefault("0")`, so a plain build prints to console) | `obfuscator/core/utils.py`, `scripts/build.py` |
| `NIXON_KOD` | Anything but `"0"` arms kill-on-detect for the VM verdict (`os._exit`); unset or `"0"` = report-only, while even `""` (empty string) arms. It does NOT arm the audit-hook timing gate -- that one is `NIXON_AUDIT_TIMING` | report-only | `obfuscator/vm_score.py`; `tests/test_vm_score.py`, `tests/test_vm_subset.py` |
| `NIXON_DRIVER_CHECK` | Arms the BYOVD driver gate at runtime (fail-closed `_nx_kill("driver-blocked")`, exit 137, + 60 s daemon re-check); disarmed = enumerate-only, never exits (Python loader snippet; the native `CheckBYOVDDrivers` gate returns immediately without enumerating when disarmed) | disarmed | `obfuscator/driver_blocklist.py`, `obfuscator/core/pipeline.py`; `tests/test_driver_blocklist.py` |
| `NIXON_AUDIT_TIMING` | Arms timing-kill in the audit hook; unset or `"0"` = disarmed, any other value (including `""`) arms | disarmed | `obfuscator/audit_hook.py`; `tests/test_audit_timing.py` |
| `NIXON_SNAPSHOT_OFF` | Truthy (`1/true/True/TRUE`, see `frozen_snapshot.py`) disables the frozen-stdlib snapshot gate at runtime | gate ON | `obfuscator/frozen_snapshot.py`, `obfuscator/core/pipeline.py`; `tests/test_frozen_snapshot.py` |
| `NIXON_STDLIB_AUDIT_OFF` | Same truthy set; disables the stdlib function-audit gate at runtime | gate ON | `obfuscator/stdlib_audit.py`, `obfuscator/core/pipeline.py`; `tests/test_stdlib_audit.py` |
| `NIXON_AUDITHOOK_PLANT_OFF` | Disables the site-packages plant detector at runtime | detector ON | `obfuscator/audit_hook.py`, `obfuscator/core/pipeline.py`; `tests/test_sitepackages_hook.py` |
| `NIXON_LADDER_DEBUG` | `1` prints kill reasons to stderr (kills are silent otherwise) | silent | `obfuscator/kill_ladder.py`; `tests/test_kill_ladder.py` |
| `NIXON_FARM_ID` | The farm identity bound into the signed artifact sidecar. The download path pins it, so a sidecar minted by a different farm is a mismatch, not a pass | unset (no pin) | `scripts/artifact_sign.py`, `obfuscator/core/utils.py`; `tests/test_artifact_sidecar_binding.py` |
| `NIXON_ARTIFACT_TTL` | How long a signed sidecar stays valid, in seconds. The MAC covers `expires_at`, so it cannot be edited forward; `0` means no expiry | 30 days | `scripts/artifact_sign.py`; `tests/test_artifact_sidecar_binding.py` |

Runtime examples:

```bash
# Fail-closed on VM detection (default is report-only)
NIXON_KOD=1 python3 build/hello_obfuscated.py
# Arm the driver gate without rebuilding
NIXON_DRIVER_CHECK=1 python3 build/hello_obfuscated.py
# See why a gate killed the process
NIXON_LADDER_DEBUG=1 python3 build/hello_obfuscated.py
# Disarm integrity gates at runtime (not recommended for release)
NIXON_SNAPSHOT_OFF=1 NIXON_STDLIB_AUDIT_OFF=1 python3 build/hello_obfuscated.py
```

## 10. Kernel-driver stance (why read-only)

`obfuscator/driver_blocklist.py` is deliberately narrow and defensive-only:
pure enumeration + blocklist comparison. Read-only sources (Linux
`/proc/modules` first column; Windows `EnumDeviceDrivers` +
`GetDeviceDriverBaseName` in `try/except`; `[]` elsewhere), case-insensitive
stem matching against ~20 LOLDrivers-derived vulnerable/malicious stems.
No driver loading, no ring-0, no IOCTLs, no service installation, no writes.
Rationale: a userland obfuscator shipping ring-0 code would be a supply-chain
liability and a false-positive availability bug; detection-with-fail-closed
covers the BYOVD threat without it. Legit AV and hypervisor-guest drivers are
deliberately excluded from the blocklist.
