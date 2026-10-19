# Threat Model — shadow-compiler

Scope: the build-time obfuscation pipeline (`scripts/build.py`,
`obfuscator/`, `irgen/`, `native/`) and the loader gates it emits into
artifacts (anti-VM, trial/HWID, watermark, frozen-stdlib snapshot,
stdlib-audit, audit-hook plant detector, BYOVD driver gate, kill ladder).
Out of scope: research/experimental flags (FHE-VM, iO, ZK, GPU/TEE/SGX,
distributed execution) unless stated.

## How to read this table (evidence taxonomy)

Every row carries a **Status** — the strongest claim the in-tree evidence
supports — plus an **Evidence** cite. Documentation must never claim above
the evidence. When in doubt, the row is downgraded.

- `UNIMPLEMENTED`: no detection code found in the tree (or the control is
  impossible by design, e.g. resisting root). Residual risk is accepted or
  future work — never coverage.
- `IMPLEMENTED`: detection code exists (cited `file:line`) but no test
  executes it.
- `TESTED`: a unit/integration test executes the detection path (cited
  `tests/file:line`). Happy-path-only execution lands here, never higher.
- `ADVERSARIAL_TESTED`: a test forces the hostile condition (tampered
  input, transplant, replay, malformed bytes, planted hook/symlink/driver)
  and asserts fail-closed (kill / `mismatch` / `tampered` / `False`).
  Mere happy-path tests do NOT qualify.
- `ENVIRONMENT_VALIDATED`: the control was exercised in (or against a
  faithful replica of) the deployment environment — requires a CI job or a
  documented hosted run. Local-only `pytest` runs do NOT qualify, and
  neither does CI running unit tests in-process on a Linux dev runner when
  the gate ships in a Windows artifact or a deployed loader.

`UNVERIFIED` in an Evidence cell means no in-tree evidence was found —
treat the row as residual risk, not as coverage.

Note: the five previously-`UNVERIFIED` cells were re-checked
against code and the test files below — four keep their status and one
(malicious config) has since been promoted to `ADVERSARIAL_TESTED` via
schema validation (see "UNVERIFIED cross-check").

| Threat | Attack surface | Detection (file:line) | Mitigation | Residual risk | Status | Evidence |
|---|---|---|---|---|---|---|
| Malicious local admin (root / Administrator) | Whole host: artifact memory, key material, state files | None — UNVERIFIED (no detector can run above its attacker) | None; admin reads `BLOB_KEY` from process memory regardless of wipe-on-kill | **HIGH**. Accepted: tool raises analyst cost, does not resist root. | UNIMPLEMENTED | None by design — no code can detect a reader above it. |
| Unprivileged attacker (same user / other local user) | Loader gates, trial state files, `build/` artifacts | Gates below (trial, watermark, snapshot, stdlib-audit) | Fail-closed kill ladder: wipe + `os._exit(137)` (`obfuscator/kill_ladder.py:44`, `obfuscator/kill_ladder.py:188`) | Medium: attacker can still copy artifacts offline and attack statically. | TESTED | Kill path executed in subprocess, silent 137 (`tests/test_kill_ladder.py:68`, `tests/test_kill_ladder.py:105`). Direct kill invocation only — no hostile input forced at this aggregate level; per-gate adversarial tests live in the gate rows below. |
| BYOVD attacker (vulnerable signed driver) | Kernel via known-vulnerable drivers (WinRing0, etc.) | `obfuscator/driver_blocklist.py:36` (blocklist), `obfuscator/driver_blocklist.py:246` (`is_armed`), native gate `native/stub_win.cpp:643`, `native/stub_win.cpp:681`, `native/stub_win.cpp:719` | Read-only enumeration + blocklist compare; when armed (`--driver-check` / `NIXON_DRIVER_CHECK=1`), `_nx_kill("driver-blocked")`. No loading, no IOCTLs (`obfuscator/driver_blocklist.py:1`, `native/stub_win.cpp:647`) | Medium: gate is opt-in (default disarmed); enumeration is point-in-time + 60 s re-check thread only. | ADVERSARIAL_TESTED | Armed gate + planted bad-driver name → 137 in-process (`tests/test_driver_blocklist.py:226`), end-to-end via real ladder in subprocess (`tests/test_driver_blocklist.py:247`), env-only arming variant (`tests/test_driver_blocklist.py:265`). Native `.cpp` gate itself is compile-only (see DLL row). |
| Tampered binaries / artifacts (swapped payload, patched loader) | `build/<payload>_obfuscated.py`, sidecar configs, farm zips | Artifact HMAC signing `scripts/artifact_sign.py:47` (`sign_file`), `scripts/artifact_sign.py:57` (`verify_file`, constant-time `hmac.compare_digest`), plus metadata-bound `sign_artifact` (`scripts/artifact_sign.py:134`, MAC over bytes + repo/commit/build-id/platform) / `verify_artifact` (`:156`, legacy bytes-only sigs still verify but can never satisfy a metadata pin) | Sign at build with binding (`--sign-key-env`, `scripts/phases/phase06_package.py:59`), opportunistic upload sidecars (`obfuscator/core/utils.py:598`, `:920`); farm download verifies sidecars BEFORE extract, mismatch raises fail-closed (`:843`, `:1480`); no key → auditable `ARTIFACT-AUTH` warning, never silent | Medium-high: package signing still opt-in; farm-runner binaries are unsigned by design (runners never hold the key — ADR-0005), so the download gate enforces only where sidecars exist; shared secret (any verifier can forge), no per-farm identity / rotation versioning / replay expiry. | ADVERSARIAL_TESTED | Swapped bytes → `False` (`tests/test_artifact_sign.py:23`), wrong key → `False` (`:31`), malformed sig shape rejected (`:38`), CLI `FAIL` nonzero (`:46`); bound roundtrip/pin/tamper/metadata-tamper/legacy-pin-refusal/wrong-key (`tests/test_artifact_signing.py:50-95`), zip-gate tamper/wrong-key → `SignatureMismatchError`, no-sig zip → 0, bad sidecars (`:139-183`), no-key paths warn via `caplog` (`:210-226`), package-step bound sidecar incl. tamper-closed (`:236-262`). Stays `ADVERSARIAL_TESTED`: CI runs the suite in-process on Linux runners (`.github/workflows/ci.yml:29`), which the taxonomy counts as testing, not deployment validation. |
| Malicious config (poisoned `config/*.json`, build flags) | `config/default.json`, `config/relay.json`, phase JSON sidecars | Fail-closed schema gate on the `default.json` load path: per-key rules for all 97 keys (`scripts/config_schema.py`), wired into `load_advanced_protection_config` (`scripts/phases/phase02_config.py`), clean abort (`ERROR` + `sys.exit(1)`) in `scripts/build.py` | Poisoned/malformed `default.json` aborts instead of silently weakening; unknown keys dropped + warned; `atomic_write` still prevents torn reads (`scripts/common.py:55`, `scripts/common.py:82`) | Low-medium for `default.json`: explicit `False` posture choices still allowed (now logged via conflict warnings); **remainder:** `config/relay.json` and phase JSON sidecars have no schema gate — a writer there can still change posture silently. | ADVERSARIAL_TESTED | Poisoned threshold/gate/cipher types, out-of-range security values, missing required fields, nested-bomb and giant-list inputs forced through `validate_config`/`load_config_file`, all assert `ConfigError` (`tests/test_config_schema.py`); poisoned + malformed files forced through the real loader, assert `ConfigError` (loader tests + `tests/test_failure_modes.py::test_corrupted_config_fails_closed`). Scope: `default.json` load path only. |
| Compromised dependencies (`requests`, `urllib3`, `numpy`, toolchain) | Build host: `pip install -r requirements.txt`, `cargo`, `g++`, `llc` | UNVERIFIED — `requirements.txt` pins versions (`requests==2.33.0`, `urllib3==2.7.0`, `numpy==2.2.4`) but no `--require-hashes` lockfile or vendoring found (re-confirmed 2026-09-28). Partial control only: `pip-audit` hard gate in CI (`.github/workflows/ci.yml:43`) scans pins against advisories but does not prevent silent substitution at install time. | Version pins only | Medium: pin without hash allows silent substitution at install time. Hash-pinned lockfile is future work. | UNIMPLEMENTED | No hash pinning; no test installs from a hostile index. `pip-audit` is advisory detection, not substitution prevention. |
| TOCTOU — trial state (concurrent runs race read-modify-write) | Sealed last-seen dotfile (`~/.local/state/nixon-trial/`) | Build-time path takes POSIX `LOCK_EX` (`obfuscator/trial_bind.py:97`, `obfuscator/trial_bind.py:329`); emitted runtime snippet takes **no** lock by design (`obfuscator/trial_bind.py:467`) | Monotonic HMAC-sealed writes: worst case one stale rollback window, absolute deadline still holds (`obfuscator/trial_bind.py:331`) | Low. Accepted by design; documented at `obfuscator/trial_bind.py:467`. | TESTED | `check_and_update` (which takes the lock on POSIX) is executed (`tests/test_trial_bind.py:149`), but no test runs concurrent writers, so mutual exclusion itself is unproven — rollback/tamper adversarial tests belong to the Replay/Corrupted-state rows, not this one. |
| TOCTOU — build outputs (torn artifact reads) | `build/` artifacts, phase sidecars | `atomic_write` temp-then-`os.rename` (`scripts/common.py:55`, `scripts/common.py:82`) | Readers never see partial files | Low. | TESTED | `atomic_write` is executed by report-write paths (`tests/test_reachability.py:257`, `tests/test_retirement.py:291`) — happy-path writes only; no concurrent reader/writer torn-read test on an artifact path. |
| DLL / shared-lib hijack (Windows loader search order) | `stub_win` DLL resolution, pipeline reflective loader | Reflective import resolution + `GetModuleHandleA` verification (`native/stub_win.cpp:581`, `native/stub_win.cpp:602`); pipeline loader source (`obfuscator/core/pipeline.py:2701`) | Reflectively-loaded DLL has no OS module entry so `GetModuleHandle` cannot be tricked into blessing a planted DLL on disk; system DLLs resolved via guarded `LoadLibraryA`/`GetProcAddress` (`native/stub_win.cpp:285`, `native/stub_win.cpp:725`) | Medium: second resolution site (`native/stub_win.cpp:1955`) and search-order hardening beyond reflective load are not exhaustively audited. | IMPLEMENTED | Detection code exists, but `tests/test_stub_win_contract.py` asserts only source properties (poison registries, bounds, read-only imports) — no test executes the `GetModuleHandle` verification, and Linux CI cannot load a PE. `stub-win-msvc` (`.github/workflows/cross-platform.yml:109`) compiles the stub on Windows but never runs a gate. |
| Path traversal (`-o` / payload paths) | `-o/--output` staging path, payload path | Guard refuses `-o` outside build dir unless `--force-output` (`obfuscator/core/pipeline.py:386`, `obfuscator/core/pipeline.py:390`; CLI flag `scripts/build.py:366`) | `realpath` containment check; silent overwrite of arbitrary files refused | Low when default used; `--force-output` explicitly re-opens the footgun (operator opt-in). | ADVERSARIAL_TESTED | Outside-root source path forced through `process_file_safe`, write asserted confined to `build_dir` (`tests/test_adversarial_security.py:359`). Caveat: the `--force-output` refusal branch itself (`scripts/build.py:1001`) has no direct test. |
| Symlink attacks — trial state file | State-file write swaps link target | `O_NOFOLLOW` on state write (`obfuscator/trial_bind.py:382`) and in emitted snippet (`obfuscator/trial_bind.py:620`) | Symlinked state path fails instead of following | Low. | ADVERSARIAL_TESTED | Symlinked (dangling + live-target) state paths forced; gate degrades to `ok` without writing through the link, target bytes asserted unchanged (`tests/test_adversarial_security.py:383`). |
| Symlink attacks — temp files | `secure_temp` build artifacts | `O_EXCL \| O_CREAT \| O_RDWR` + mode `0o600` + `fchmod` (`obfuscator/secure_temp.py:26`, `obfuscator/secure_temp.py:221`); snippet counterpart same flags | Exclusive create defeats pre-planted symlinks at that path | Low-medium: `O_NOFOLLOW` is NOT set on temp writes (verified absent) — an attacker who can pre-create the exact random name is still blocked by `O_EXCL`, but symlink hardening is partial. | TESTED | Write path executed (roundtrip `tests/test_secure_temp.py:16`, mode `0o600` `tests/test_secure_temp.py:27`, snippet flags `tests/test_secure_temp.py:82`) — but no pre-planted-symlink hostile test forces the `O_EXCL`-vs-symlink outcome. |
| Env manipulation (`NIXON_*` vars) | Every gate reads env at runtime | `obfuscator/vm_score.py:417` (`NIXON_KOD` default `"0"` = report-only), `obfuscator/kill_ladder.py:247` (`NIXON_LADDER_DEBUG` default `"0"` = silent), `obfuscator/driver_blocklist.py:292` (`NIXON_DRIVER_CHECK` default disarmed), `obfuscator/audit_hook.py:361` (`NIXON_AUDIT_TIMING` default `"0"` = off) | Fail-safe defaults: tamper *detection* gates default ON (snapshot, stdlib-audit, audit-hook plant); *kill-on-detect actions* and diagnostics default OFF, so a scrubbed env degrades to report-only, never to silent-pass-with-kill-disabled on integrity verdicts (verdicts still return `mismatch`/`tampered`) | Medium: `NIXON_SNAPSHOT_OFF` / `NIXON_STDLIB_AUDIT_OFF` / `NIXON_AUDITHOOK_PLANT_OFF` are explicit opt-outs — anyone controlling the runtime env can disable gates (documented operator escape hatches, not stealth). | TESTED | Opt-out helpers and default-ON wiring asserted (`tests/test_frozen_snapshot.py:92`, `tests/test_frozen_snapshot.py:200`, `tests/test_stdlib_audit.py:101`, `tests/test_kill_ladder.py:82`) — but no test scrubs the env and asserts tamper verdicts still return `mismatch`/`tampered`. |
| Forged telemetry (fake attestations / gate reports) | Gate verdict strings, relay attestation channel | UNVERIFIED for loader gates — verdicts are in-process strings with no authentication envelope; relay attestation uses an incrementing nonce (`relay/src/attestation.rs:35`) | Trial/watermark/snapshot bindings are HMAC-keyed so forgery needs the build key; verdicts feed `_nx_kill` locally, not a remote trust decision | Medium: no consumer should treat a loader's self-report as proof of integrity. | UNIMPLEMENTED | No envelope code for loader verdicts; no test forges one. Relay nonce is transport-level, not a loader-gate authenticator. |
| Replay — trial last-seen rollback (`date -s`) | Trial state dotfile | Sealed last-seen stamp `seal_last_seen` / `unseal_last_seen` (`obfuscator/trial_bind.py:222`, `obfuscator/trial_bind.py:235`); `now < last_seen - tolerance` → `rollback` (`obfuscator/trial_bind.py:370`); tampered seal → fail-closed (`obfuscator/trial_bind.py:364`) | Rollback detected within 300 s tolerance (`ROLLBACK_TOLERANCE_S`); deleting the dotfile restarts `last_seen` at now (documented, `obfuscator/trial_bind.py:44`) | Low-medium: clock jumps inside tolerance + fresh dotfile extend the window; absolute deadline still bounds it. | ADVERSARIAL_TESTED | Rewound clock → `rollback` (`tests/test_trial_bind.py:149`), emitted-snippet clock rewind → `rollback` (`tests/test_trial_bind.py:228`), tolerance-boundary battery (`tests/test_trial_bind.py:455`), token reuse advances `last_seen` without bypass (`tests/test_adversarial_security.py:418`), cross-machine state transplant → `tampered` (`tests/test_adversarial_security.py:437`). |
| Replay — nonce reuse (section crypto, proofs) | Split-bootstrap sections, ledger proofs | Per-section fresh `os.urandom(16)` nonce (`obfuscator/section_split.py:69`); distinct HMAC domain separators for trial vs last-seen (`obfuscator/trial_bind.py:60`) — **but `section_split.py` is not wired into any build/pipeline/loader path (library-only, referenced only by its own tests), so no shipped artifact is section-split** | Nonces never reused across builds/sections; seals are domain-separated | Low. | NOT WIRED (library-only) | `section_split.py` has zero non-test references, so this control is not active in any shipped artifact; its hostile-case tests (tampered section → `ValueError` `tests/test_section_split.py:28`, dropped section → `ValueError` `tests/test_section_split.py:42`) exercise the module in isolation only — and no test asserts nonce uniqueness across sections/builds or domain separation, which is this row's actual claim. |
| Corrupted state (truncated/edited dotfiles, torn JSON) | Trial dotfile, config sidecars | `unseal_last_seen` raises `ValueError` on tamper (`obfuscator/trial_bind.py:242`, `obfuscator/trial_bind.py:250`) → verdict `tampered`, never `ok` (`obfuscator/trial_bind.py:254`); torn `config/default.json` refused fail-closed via the schema gate (`scripts/config_schema.py`, `ConfigError` on malformed JSON) | Fail-closed: corrupt state kills instead of passing; corrupt default config aborts the build instead of degrading to empty | Low. Note: vacuous-empty contexts (`files={}` → `"ok"`) are possible only when the build baked nothing — pipeline always bakes a non-empty set. | ADVERSARIAL_TESTED | Forged seal → `tampered` (`tests/test_trial_bind.py:180`), garbage/empty variants → `tampered`/`ok`-first-run (`tests/test_trial_bind.py:504`), garbage state file → `tampered` (`tests/test_adversarial_security.py:206`); torn/poisoned `default.json` → `ConfigError` via loader (`tests/test_config_schema.py`, `tests/test_failure_modes.py::test_corrupted_config_fails_closed`). |
| Compromised update mechanism | Self-update / auto-download path | No auto-update mechanism found in tree — UNVERIFIED as absent-by-inspection (the `urllib.request.urlopen` calls in `obfuscator/core/pipeline.py:720,865,896,983` are cloud-deploy calls, not self-update; re-confirmed 2026-09-28) | Nothing to exploit if nothing phones home for code; verify before relying | Low-medium: absence-by-inspection is not a control; any future updater must require artifact-signature verification (`scripts/artifact_sign.py:31`) before execution. | UNIMPLEMENTED | Absence cannot be tested by a gate test; no tree-scan test (cf. `test_no_driver_loading_ioctl` pattern) pins the absence. |
| Frozen-stdlib snapshot tamper (swapped stdlib file on target) | Target `site-packages`/stdlib files hashed at build | Build-time `{module: sha256}` context + runtime re-hash, tag-bound (`obfuscator/frozen_snapshot.py:207`, `obfuscator/frozen_snapshot.py:211`) | Mismatch → `_nx_kill("integrity-snapshot")`; version-gated (tag mismatch = report-only); missing files skipped | Low-medium: version skew disables enforcement (report-only); opt-outs (`NIXON_SNAPSHOT_OFF`, `--no-snapshot`) are operator escape hatches. | ADVERSARIAL_TESTED | Swapped file bytes → `mismatch` (`tests/test_frozen_snapshot.py:64`), corrupted expectation + real ladder in subprocess → 137 with `GATE:mismatch` (`tests/test_frozen_snapshot.py:117`), tamper-never-downgrades invariant (`tests/test_security_invariants.py:98`, `tests/test_security_invariants.py:109`). |
| Stdlib function patch (monkeypatched `json.loads`, etc.) | Runtime stdlib function bytecode (`co_code`) | Build-time bytecode-hash table + runtime compare (`obfuscator/stdlib_audit.py:247`, `obfuscator/stdlib_audit.py:294`) | Mismatch → `_nx_kill("stdlib-tamper")`; version-gated; unresolvable names skipped | Low-medium: version skew disables enforcement; C-identity functions (`os.urandom`) fingerprinted by identity only. | ADVERSARIAL_TESTED | Live monkeypatch of `json.loads` → `mismatch`, restore → `ok` (`tests/test_stdlib_audit.py:74`), corrupted table + real ladder in subprocess → 137 (`tests/test_stdlib_audit.py:126`), invariant (`tests/test_security_invariants.py:133`). |
| Watermark strip / tamper (marker removed, message edited, key swapped) | Emitted loader watermark literals | HMAC tag over message + marker-presence check (`obfuscator/watermark_gate.py:72`, `obfuscator/watermark_gate.py:82`) | `tampered`/`missing` → `_nx_kill("watermark-tampered"/"watermark-missing")`; unmarked builds stay `DISABLED` | Low: no watermark configured = no gate (documented); strip detected only when a watermark was baked. | ENVIRONMENT_VALIDATED | Stripped marker in built artifact → 137 e2e (`tests/test_watermark_gate.py:127`), edited message → 137 (`tests/test_watermark_gate.py:149`), swapped key → 137 (`tests/test_watermark_gate.py:185`), corrupt tag/message units (`tests/test_adversarial_security.py:227`). Hosted: strip + message-tamper probes on built artifacts (production hybrid-loader builder, fresh subprocess, real 137 silent) on ubuntu-24.04 × py 3.11/3.13 (`.github/workflows/security-artifact.yml`, `scripts/ci_security_artifact.py`). |
| Audit-hook plant / timing manipulation (hostile `sys.addaudithook`, blocked canary, inflated latency) | Runtime `sys.addaudithook` / `sys.audit` | Wrapper + `_nx_audit_verify` replacement check (`obfuscator/audit_hook.py:164`, `obfuscator/audit_hook.py:38`); canary + latency gates, timing kill opt-in (`obfuscator/audit_hook.py:116`, `obfuscator/audit_hook.py:361`) | Plant/replacement → `_nx_kill("audit-plant")`; inflated latency → `_nx_kill("audit-timing")` only when armed | Low-medium: timing kill defaults OFF (report-only); `NIXON_AUDITHOOK_PLANT_OFF` is an operator escape hatch. | ADVERSARIAL_TESTED | Wrapper replacement → 137 in subprocess (`tests/test_audit_timing.py:100`), plant via fake site path → 137 (`tests/test_audit_timing.py:208`), preinstalled foreign hook → kill path (`tests/test_audit_timing.py:136`), inflated latency armed → 137 (`tests/test_audit_timing.py:182`). |
| Anti-VM detection (hypervisor/sandbox timing signals) | Loader VM-score signals incl. clock-bias | Clock-bias detector + weighted score, kill only if `NIXON_KOD` armed (`obfuscator/vm_score.py:417`, `obfuscator/clock_bias.py` thresholds) | Report-only by default (`NIXON_KOD` default `"0"`); score feeds verdict, kill is opt-in | Medium: default posture detects-but-continues; live verdicts are host-noise-dependent and never asserted. | TESTED | Synthetic VM-like vectors flag via both verdict and timer seams (`tests/test_clock_bias.py:73`, `tests/test_clock_bias.py:346`); live-timer tests assert structure only, never the verdict value — no live-VM validation exists. |

## Residual-risk summary

- **HIGH / accepted:** malicious local admin (no software control helps).
- **Require operator discipline:** opt-in gates left disarmed (driver-check,
  artifact signing), `--force-output`, `NIXON_*_OFF` escape hatches.
- **UNVERIFIED (future work):** hash-pinned dependencies, authenticated
  gate telemetry, updater signature policy, schema gates for
  `config/relay.json` and phase JSON sidecars (only `config/default.json`
  is gated).

## Coverage summary (2026-09-28 evidence pass)

Counts over 23 rows: `UNIMPLEMENTED` 4 (admin, dependencies,
forged telemetry, updater) · `IMPLEMENTED` 1 (DLL hijack) ·
`TESTED` 7 (unprivileged aggregate, TOCTOU-trial, TOCTOU-build,
symlink-temp, env manipulation, nonce replay, anti-VM) ·
`ADVERSARIAL_TESTED` 10 (BYOVD, artifact signing, malicious config,
path traversal,
symlink-trial, trial replay, corrupted state, snapshot, stdlib-audit,
audit-hook) · `ENVIRONMENT_VALIDATED` 1 (watermark).

Only the watermark row qualifies for `ENVIRONMENT_VALIDATED`, via the
hosted real-artifact job (`.github/workflows/security-artifact.yml`):
strip + message-tamper probes on built artifacts from the production
hybrid-loader builder, executed as fresh processes on ubuntu-24.04 × py
3.11/3.13 with real silent-137 kills. The same job also collects hosted
evidence that promotes NO row, strictly: expired-trial refusal (no
expiry-specific row exists -- the Replay row covers rollback, the
Corrupted-state row covers tamper) and the KOD kill with a
forced (`vm_threshold=0.0`) verdict, which validates the armed kill path
in the deployment environment, not genuine VM detection. What CI
otherwise runs (`.github/workflows/ci.yml:29` `pytest tests/ -v` on
ubuntu-latest × py 3.10–3.14; same full-suite step in `build.yml:29` and
`cross-platform.yml:30`): every security test file executes, but
in-process on a Linux dev runner — the gates are never probed inside a
built artifact on a target host. Native Windows gates are compiled
(`stub-win-msvc`, `cross-platform.yml:109`) but never executed; the
shadow-build workflow builds the pipeline without running any gate test.
Hosted unit-test execution is (adversarial) testing, not deployment
validation — hence the cap at `ADVERSARIAL_TESTED` on current evidence
for every row except watermark.

## UNVERIFIED cross-check (the 5 previously-unverified cells)

Re-checked 2026-09-28 against code and the named test files; one
promoted (malicious config, see below), four keep their status, with
reasons:

- Malicious local admin: unpromotable by construction — no detector can
  run above its attacker. Keep `UNIMPLEMENTED`, risk accepted.
- Malicious config: PROMOTED 2026-09-28 — `scripts/config_schema.py`
  validates all 97 `default.json` keys on the phase02 load path and
  `tests/test_config_schema.py` forces poisoned configs (wrong types,
  out-of-range security values, missing required fields, nested-bomb and
  giant-list inputs) asserting `ConfigError`; `tests/test_failure_modes.py`
  (`test_corrupted_config_fails_closed`) pins the loader abort. Now
  `ADVERSARIAL_TESTED` for the `default.json` load path; `relay.json` and
  phase sidecars remain ungated (see row residual).
- Compromised dependencies: pins without hashes confirmed; the
  `pip-audit` CI hard gate (`ci.yml:43`) detects known advisories but
  does not stop silent substitution at install time. Keep
  `UNIMPLEMENTED` with the partial control noted.
- Forged telemetry: loader verdicts remain unauthenticated in-process
  strings; relay nonce is transport-level. No forgery test exists. Keep
  `UNIMPLEMENTED` for the loader-gate claim.
- Compromised update mechanism: absence-by-inspection re-confirmed
  (`urlopen` sites are cloud-deploy, not self-update). No tree-scan test
  pins the absence. Keep `UNIMPLEMENTED`.

## Gaps — what test would promote each row below ADVERSARIAL_TESTED

- DLL hijack (`IMPLEMENTED` → `ADVERSARIAL_TESTED`): run the MSVC-built
  stub on `windows-latest` with a planted DLL on the search path; assert
  the `GetModuleHandle` verification refuses it.
- TOCTOU trial-state (`TESTED` → `ADVERSARIAL_TESTED`): concurrent-writer
  test (threads/processes racing `check_and_update`); assert serialized
  monotonic seals, no lost-update pass.
- TOCTOU build outputs (`TESTED` → `ADVERSARIAL_TESTED`): concurrent
  reader/writer test over an artifact path; assert readers see old or new
  bytes, never torn content.
- Symlink temp (`TESTED` → `ADVERSARIAL_TESTED`): pre-plant a symlink at
  the (mocked) temp name; assert `O_EXCL` refuses instead of following.
- Env manipulation (`TESTED` → `ADVERSARIAL_TESTED`): scrub all `NIXON_*`
  vars, then feed tampered snapshot/stdlib inputs; assert verdicts still
  `mismatch` (detection survives a scrubbed env).
- Nonce replay (`TESTED` → `ADVERSARIAL_TESTED`): assert per-section
  nonces are unique across packs/builds and trial/last-seen domain
  separators differ; assert cross-domain seal replay fails.
- Anti-VM (`TESTED` → `ADVERSARIAL_TESTED` → `ENVIRONMENT_VALIDATED`):
  fixed-vector tests already force the signal; add a hosted run on a
  known-VM runner asserting the flag fires (and a bare-metal control).
- Unprivileged aggregate (stays `TESTED` by design): covered via the
  per-gate `ADVERSARIAL_TESTED` rows; no separate promotion needed.
- `UNIMPLEMENTED` four: `--require-hashes` lockfile; authenticated verdict
  envelope (or documented "local-only" trust boundary + test pinning it);
  updater absence tree-scan test (extend the
  `test_no_driver_loading_ioctl` pattern in
  `tests/test_security_invariants.py:71`); admin stays accepted.
- `ENVIRONMENT_VALIDATED` (general): `.github/workflows/security-artifact.yml`
  (+ `scripts/ci_security_artifact.py`) is the first such job: it builds
  artifacts with gates armed and probes the *built artifact files* as
  fresh processes on hosted runners (ubuntu-24.04 × py 3.11/3.13) —
  currently watermark strip/tamper (promoted), plus hosted evidence for
  expired-trial refusal and the KOD armed kill path (forced verdict; no
  promotion, see Coverage summary). Still missing for the remaining
  rows: rewound-clock rollback and transplanted-state probes executed
  hosted (still pytest-only), and `windows-latest` execution for the
  native driver/DLL gates. No other row may claim this level until its
  gate is probed the same way.
