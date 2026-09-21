# Nyami V10 — feature pages + changelog (recorded 2026-09-20, full paste)

Source: full nyami.cc feature/changelog paste (user message 2026-09-20):
Semantic Lowering + Core Obfuscation + Security Features + Developer
Tools + Support + How-It-Works pipeline + Version 10.0 + Version 9.0
changelogs. Recorded here because the paste is the primary source for
the V10 feature set. Vendor claims below are NOT independently verified.

## V10 headline: Semantic Lowering

"Call sites for Python's own builtins are replaced with native
implementations that live in the protection kernel rather than in your
file. 14 families in total, including I/O. The builtins are not hidden,
they are gone."

- Enabled by default: I/O, scalar, string, container, service, protocol,
  function, import, fusion (9 families).
- Opt-in per family: arithmetic, truth-test, slice, format,
  augmented-assignment (5 families). Each trades per-call cost for depth.
- Family notes: I/O routes print/input/open to kernel routines; scalar +
  container (numeric conversions, str handling, list/tuple/dict/set/
  frozenset) measure "at or below plain Python speed"; import lowering
  (kernel-resolved imports) is "the fastest family we measure"; fusion
  collapses chains of lowered calls into one kernel dispatch.
- Operator/format lowering: arithmetic, comparisons, truth tests, slicing,
  f-strings/format calls, augmented assignment each lowerable, so "the
  operation stops being a recognisable Python instruction".
- Per-build kernel symbols: every kernel op renamed each build.
- Operation registry drives lowering (add/disable per family).

## V10 changelog (Version 10.0, "Semantic Lowering")

Lowering core:
- Kernel exposes native replacements for **141 lowered operations**.
- Nested lowered calls fused into single kernel dispatch; dedicated fast
  paths for fusion and f-strings.
- Dead tamper-guard wrapper stripped from pure-compute lowered calls —
  operator families went from 2x–6x overhead into 1.2x–1.6x.
- Measured 0.19x–1.56x of plain CPython 3.12 across families — import
  0.37x, container 0.86x–0.94x, scalar 0.81x–0.82x.
- Per-family lowering opt-outs, including I/O; opt-in renaming of
  proven-internal public methods/attributes.

Correctness fixes (each with a dedicated regression test):
- Keyword-argument binding on 3.10 (renamed internals broke f(1, c=2),
  dict(a=1), keyword-only args, **kwargs).
- Exception-table validator reading little-endian instead of big-endian
  on 3.11–3.14 (silently reverted a decompiler-breaker layer).
- Zero-argument super() in obfuscated class methods (per-method
  compilation stripped implicit __class__).
- PYTOC constant negative indexing reading adjacent memory; min()/max()
  wrong type on mixed int/float.

Failure path + self-corruption:
- Single failure path in kernel: any tamper trigger wipes key material,
  exits on first strike.
- On-tamper artifact self-corruption REPLACED self-delete (opt-out
  available); runs from detached child that waits for parent exit, then
  overwrites artifact with same-length garbage.
- Byte-tamper sweep: 12 single-byte mutations × 2 randomized builds, all
  fail-closed, 8–9 hitting kernel kill ladder (exit 137).

Sections + memory:
- Payload split into individually sealed sections, streamed one at a time
  (full code object never resident in one readable buffer).
- Sealed sections placeable on guard pages trapping out-of-window access.
- Key + white-box pages pinned (mlock), sections re-protected read-only
  after load.
- Kernel bootstrap: split-secret key derivation + fragmented decoder
  (no single embedded key); compiled exports randomized per build;
  runtime op names resolved per-process (no literals).
- Native watchdog with heartbeat liveness pairing + timeout kill.
- Timing side-channel detector based on clock-interrupt bias.

Native + audit:
- Native anti-debug tier in kernel: debug register/port/toolchain checks.
- Audit-hook timing + hook-addition detection; site-packages hook-plant
  detection.
- Randomized fixed-literal residue across 8 token families.

Build/delivery:
- Diagnostic build mode (per-stage timings, transform counts, key-material
  freshness check; artifact visibly marked non-release).
- Optional private build manifest (build provenance).
- Cross-compile native protection layer for Windows from Linux.
- HWID locking accepts static fingerprint format alongside dynamic.
- Crash-dialog suppression (native kill exits cleanly).

## Other pages in the paste (delta vs our earlier docs-summary)

- Core list now names: Section Splitter, White-Box 8–12 rounds (was
  "8-round"; now a per-build range), Custom Code-Object Serializer,
  multi-encoding pipeline, PYTOC — all previously known.
- Security list now names: 11 anti-debug families, 12-method anti-VM
  (was "8 methods" in old docs — now 12, confidence-weighted), kernel
  driver detection (still off by default), HMAC anti-monkey-patch,
  layered integrity (secure serializer + frozen snapshots + bytecode-hash
  re-verify), Anti-Dump, page protection, **guard-page traps** (new),
  Hydra (high-frequency + background + kernel watchdog, single failure
  path wiping keys), anti-trace/profile, audit-hook protection, caller
  frame validation, **runtime API name gate** (new: privileged names via
  per-process mapping, no literals), native kernel hardening (import +
  interpreter code/export tables verified; mismatch poisons keys),
  PBKDF2 HWID, trials 1h–1y (MAC-bound deadline, rollback detected),
  **on-tamper self-corruption** (new, replaces self-delete),
  secure cleanup.
- Developer list: 3.10–3.14 support, full CLI, multiple outputs (.py /
  ZIP bytecode container / native ext / exe), **diagnostic builds**
  (new), PyInstaller automation, interconnectivity, stdlib auditing,
  full docs.

## Full-paste notes (verbatim details worth keeping)

- Semantic Lowering: 14 families total incl. I/O. Default ON: I/O, scalar,
  string, container, service, protocol, function, import, fusion. Opt-in:
  arithmetic, truth-test, slice, format, augmented-assignment (each trades
  per-call cost for depth). Import lowering "fastest family we measure";
  scalar/container "at or below plain Python speed". Fusion collapses
  lowered-call chains into one dispatch. Per-build kernel symbols; operation
  registry drives families.
- How-It-Works pipeline (V10 wording): string encryption is ChaCha20
  per-session keys; lite-function picks best codec per function; white-box
  is "8 to 12 rounds, randomised per build, SHA-256-expanded tables";
  anti-VM is "12 detection methods... confidence-weighted"; trials support
  "1h, 1d, 1w, 1mo, 1y", deadline MAC-bound, rollback detected; watermark
  refuses to run if removed; HWID = UUID+MAC+disk-serial via PBKDF2 into
  AES-GCM AAD; secure cleanup overwrites temp artifacts; bootstrap is
  version-locked (version check + audit hooks + env validation).
- V10 changelog numbers: 141 lowered ops; fusion + f-string fast paths;
  pure-compute calls dropped 2x–6x → 1.2x–1.6x overhead; measured
  0.19x–1.56x of CPython 3.12 (import 0.37x, container 0.86x–0.94x,
  scalar 0.81x–0.82x). Byte-tamper sweep 12 mutations × 2 builds, all
  fail-closed, exit 137 on kill ladder. Static HWID fingerprint format
  accepted alongside dynamic. Per-family opt-outs incl. I/O; opt-in
  renaming of proven-internal methods/attributes.
