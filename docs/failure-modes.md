# Failure-Modes Audit — adversarial-obfuscator

Failure-oriented audit: for each scenario the observed behavior on code
inspection (plus cheap executable proof where noted), classified as one of
`FAIL-OPEN` / `FAIL-CLOSED` / `DEGRADE` / `CRASH` / `RETRY` / `SILENT` /
`AUDITED`. Verdict is `ACCEPTABLE` or `NEEDS-FIX`. Rows marked
`UNVERIFIED` could not be confirmed by reading (platform-specific or
needs live infra).

Conventions: `file:line` pins evidence. "Fail-safe" = denies, degrades,
or stays inert; "fail-open" = protection silently lost while execution
continues as if protected.

## Scenario table

| # | Scenario | Behavior | Evidence | Verdict | Fix-or-accept note |
|---|----------|----------|----------|---------|--------------------|
| 1 | `cryptography` unavailable (pipeline encrypt) | `DEGRADE` (silent downgrade) | `obfuscator/core/pipeline.py:422-456`: `_check_aes_ctr()` tries `cryptography` → `Crypto` → `False`; `Nixon_Enc_AES_CTR` falls through to XOR `Nixon_Enc_blob` with no log | `ACCEPTABLE` | Downgrade is logged nowhere; recommend one `print`/log line in the final `except ImportError` fallthrough. Too small to matter for the threat model (build-host dep), so accepted with note. |
| 2 | `cryptography` unavailable (fragment bind/decrypt) | `FAIL-CLOSED` / `CRASH` | `scripts/binding/crypto_binding.py:361-388`: `encrypt_fragment` imports `AESGCM` unguarded → raises; `decrypt_fragment` catches all → `None` (reject) | `ACCEPTABLE` | Encrypt fails loudly, decrypt fails closed. Correct polarity. |
| 3 | `z3` unavailable | `DEGRADE` (build works; the proof path fails with a clear message) | **fix applied**: every `import z3` in the tree now goes through `scripts/z3_optional.py`, which returns the real module or a stand-in that raises `RuntimeError("z3-solver is required for the SMT proof paths...")` the moment anything uses it. The build CLI imports without z3; proven by `tests/test_failure_modes.py::test_z3_absence_does_not_break_the_build_import_closure` and `::test_z3_absence_raises_a_clear_error_at_the_proof_entry_point` | `ACCEPTABLE` | A proof-only dependency is no longer load-bearing for every build. |
| 4 | `Cython` unavailable | `DEGRADE` (audited skip) | `scripts/phases/phase_pytoc.py:36-45,86-99`: missing Cython/setuptools/compiler/cythonize-fail all return `(None, reason)`; `scripts/build.py:2411-2467` logs `PYTOC … (non-fatal)` and continues; in-pipeline `compile_payload_to_cython` returns `None` on non-zero exit (`obfuscator/core/pipeline.py:349-361`); proven by `test_pytoc_missing_cython_graceful_skip` | `ACCEPTABLE` | Best-effort native path degrades with a log line. Correct. |
| 5 | `torch` unavailable | `SILENT` (no-op) | No `import torch` anywhere under `obfuscator/ scripts/ relay/ vm/ irgen/ llvmgen/ encrypt/ runtime/` (grep); `import torch` fails on this host yet nothing breaks; `torch` appears only as classifier string labels (`scripts/classification/function_classifier.py:280,310`) | `ACCEPTABLE` | Not a dependency at all. No action. |
| 6 | `numpy` unavailable | `DEGRADE` | `obfuscator/core/utils.py:386-390`: `HAS_NUMPY` flag via guarded import; `scripts/phases/phase_assumptions.py:64` guards `import numpy`; `scripts/gpu/gpu_execution.py:8-10` guards `pyopencl` — pattern is degraded-pure-Python/fallback | `ACCEPTABLE` (`UNVERIFIED` for exact `HAS_NUMPY=False` downstream surface) | Guard pattern verified; full no-numpy build not exercised here. |
| 7 | Corrupted `config/default.json` (phase02) | `FAIL-CLOSED` (abort, clean error) | **fix applied**: `scripts/config_schema.py` validates on load; malformed JSON or security-critical violations raise `ConfigError`, `scripts/phases/phase02_config.py` propagates it, `scripts/build.py` logs `ERROR` + `sys.exit(1)`; proven by `test_corrupted_config_fails_closed` + `tests/test_config_schema.py` poison battery (was: `JSONDecodeError` → silent `{'features': {}}`) | `ACCEPTABLE` | Missing file still degrades to `{'features': {}}` with a `WARN` log (absence is not tampering); poisoned file now aborts. Correct polarity. |
| 8 | Missing driver metadata (enum `[]`) | `FAIL-OPEN` (no evidence → no kill, even armed) | `obfuscator/driver_blocklist.py:160-181,266-277`: enum failures → `[]`; `check_current` → `[]`; emitted `driver_check` returns `[]`, kills only `if _hits and armed` (`driver_blocklist.py:944`); proven by `test_missing_driver_metadata_yields_no_kill` | `ACCEPTABLE` | Cannot kill on zero evidence without bricking every restricted host (`/proc` hidden, ctypes blocked). Correct polarity; documented limitation strings (`LIMITATION_HIDDEN`, lines 318-332). Armed kill is `os._exit(137)` (`kill_ladder.py:254`), uncatchable by design — verified when the first version of the probe killed the test runner itself. |
| 9 | Contradictory evidence (stem hit + clean/fixed version) | `FAIL-CLOSED` | `obfuscator/driver_blocklist.py:717-720`: `vuln is False` appends `fixed_version_stem_only` but confidence stays `0.6`; `should_kill` (`781-797`) kills at `>= 0.6`; proven by `test_contradictory_driver_evidence_still_kills` | `ACCEPTABLE` | Stem hit always gates when armed, version signal only raises confidence. Documented ("stem match alone still reports at 0.6"). |
| 10 | Stale `driver_versions.json` | `SILENT` (+ now evaluable) | `obfuscator/driver_blocklist.py:338-368`: cached load, no mtime/age/hash check; `LIMITATION_VERSIONS` admits staleness (331-332); **fix applied**: `version_fingerprints_mtime()` / `version_fingerprints_stale(max_age_s=90d)` added (additive, unreadable ⇒ stale); proven by `test_fingerprint_staleness_flag` | `ACCEPTABLE` (was `NEEDS-FIX`) | Fixed <15 lines. Callers should warn (not gate) on `stale() is True`; version signal only ever raises confidence, so staleness cannot fail open the gate. |
| 11 | Malformed driver paths (None/empty/non-str) | `SILENT` (skip, never raise) | `obfuscator/driver_blocklist.py:111-127` (`_stem`: any input → `""` on failure), `136-157` (`check_names`: non-iterable → `[]`), `456-468` (`_path_suspicious(None)` → `None`); proven by `test_malformed_driver_paths_never_raise` | `ACCEPTABLE` | Fail-soft enumeration is the design (never brick on weird driver names). |
| 12 | Symlinked trial state path | `FAIL-CLOSED` (refuse to follow) | `obfuscator/trial_bind.py:381-391` + emitted snippet `618-626`: `O_NOFOLLOW`, `ELOOP`/`EMLINK` → build-time returns `"ok"` with degraded rollback window, snippet re-raises (refuses write); matches `THREAT_MODEL.md:26` | `ACCEPTABLE` | State write is symlink-hardened on both paths. |
| 13 | Symlinked `payload.h` inputs / relay inputs / temp writes | `WARNED` (follow, and say so) | **fix applied**: the build host is trusted, so the inputs are followed rather than refused — refusing would break legitimate setups that symlink a runtime. `scripts/generate_payload_h.py` now warns for every symlinked build input (payload / python-dll / rust-exe) and names the target; the trust boundary is stated in `THREAT_MODEL.md` ("Build-host trust boundary"). The RUNTIME side is still defended: the trial state file is opened `O_NOFOLLOW` and fails closed (`obfuscator/trial_bind.py`). Proven by `tests/test_build_input_symlinks.py` | `ACCEPTABLE` | The remaining open question (`obfuscator/secure_temp.py` has `O_EXCL` but no `O_NOFOLLOW`) is a temp-file concern on a trusted host, not a build-input one. |
| 14 | Snapshot file unreadable on target | `DEGRADE` (skip, fail-open) | `obfuscator/frozen_snapshot.py:193-205` + snippet `287-297`: missing/unreadable → `continue`; build-time `build_snapshot_context` (`163-167`) also skips unreadable into `skipped` | `ACCEPTABLE` | Documented frozen/zipimport behavior. An attacker with file-permission control over stdlib already owns the box; failing closed here would brick legit frozen layouts. |
| 15 | `secure_temp` write fails (permissions/ENOSPC) | `CRASH` (raise) | `obfuscator/secure_temp.py:36-38` (OSError → retry new name), `52-61` (write/fsync error → unlink + `raise`); after 100 collisions raises `OSError` (71); loader twin raises after 100 tries (`secure_temp.py:222-252`) | `ACCEPTABLE` | Loud abort beats silent artifact loss; fail-closed direction for a build tool. |
| 16 | `time.time`/`perf_counter` unavailable (trial gate) | `CRASH` (library) / `FAIL-CLOSED` (snippet) | Library `check_trial`/`check_and_update` call `time.time()` unguarded (`obfuscator/trial_bind.py:195,261,335`) → exception propagates (deny-by-crash); emitted snippet wraps clock read in try/except → `"tampered"` (`trial_bind.py:549-552`); `clock_bias_check` degrades via injected timer/try paths (`clock_bias.py:123-145`) | `ACCEPTABLE` | Enforcement path (snippet) is fail-closed; library raise also denies. No fix: wrapping library clock in `"tampered"` would conflate broken-host with attacker-tamper in diagnostics. |
| 17 | Clock jumps backwards | `FAIL-CLOSED` (`"rollback"`, audited) | `obfuscator/trial_bind.py:368-371` (+ snippet `605-610`): `now < last_seen - 300s` → `"rollback"`; already covered upstream (`tests/test_adversarial_security.py:263-280`); re-proven by `test_clock_rollback_detected` | `ACCEPTABLE` | Tolerance-tested boundary included. |
| 18 | Extremely large timestamps (2⁶³) | `DEGRADE` (correct verdict, no overflow) | Python ints: `compute_deadline`/`mint_token(str(int))`/`seal_last_seen(repr(float))`/`unseal_last_seen(float())` all handle 2⁶³ (`trial_bind.py:187-251`); proven by `test_huge_timestamps_no_overflow` (`ok` before deadline, `expired` after, seal round-trip) | `ACCEPTABLE` | No C `time_t`/struct packing in the trial path (contrast `struct.pack(">I")` fragment IDs in `crypto_binding.py:354`, which is a separate bounded domain). |
| 19 | Partial state (half-written trial file) | `FAIL-CLOSED` (`"tampered"`) | `obfuscator/trial_bind.py:353-365`: `unseal_last_seen` raises `ValueError` on bad split/MAC → `check_and_update` returns `"tampered"`; snippet mirrors (`trial_bind.py:586-604`); proven by `test_half_written_trial_state_is_tampered` | `ACCEPTABLE` | HMAC seal makes torn writes indistinguishable from tamper — and treated as tamper. Correct. |
| 20 | Interrupted writes (fsync coverage) | `DEGRADE` (torn-write-tolerant by construction) | `scripts/common.py:78-86` (`atomic_write`: no fsync, rename-only atomicity); `scripts/generate_payload_h.py:266-269` (tmp+rename, no fsync); trial state `os.write`+`close` with no fsync (`trial_bind.py:395-413`); vs `secure_temp.py:51` and `macros.py:199,241` which DO fsync | `ACCEPTABLE` | Rename-atomicity prevents torn *reads*; a crash may lose the *last* write — benign everywhere: trial state is monotonic HMAC (rewritten each run), build artifacts are regenerable. No fix. |
| 21 | Disk exhaustion (ENOSPC) | `CRASH` (artifacts) / `DEGRADE` (trial state) | `atomic_write` cleanup-then-raise (`common.py:83-86`); `secure_write_temp` unlink-then-raise (`secure_temp.py:52-61`); trial `check_and_update` swallows write errors → returns `"ok"` with stale rollback window (`trial_bind.py:414-415`, documented "write failure does not fail the run") | `ACCEPTABLE` | Split is deliberate and documented: build fails loudly, runtime keeps the absolute deadline (which never depends on the state write). |
| 22 | Memory exhaustion (10MB+ string paths) | `SILENT`-safe (no crash, no hang) for gates; `CRASH` for bulk encoders | Driver `_stem`/`check_names` are linear string ops, never raise (`driver_blocklist.py:111-157`); proven with a 10MB string by `test_malformed_driver_paths_never_raise`; `generate_payload_h` instead materialises `payload_len` words + full header string in RAM (`generate_payload_h.py:232,256-264`) → `MemoryError` propagates (loud, no partial artifact since rename happens last) | `ACCEPTABLE` | Gate path proven allocation-safe; bulk path fails loudly rather than truncating. `UNVERIFIED` for true OOM-killer conditions (not simulable cheaply). |
| 23 | Subprocess failure (`run()` non-zero) | `CRASH` (abort) for core phases; `DEGRADE` (logged continue) for optional phases | Core: `scripts/common.py:136` raises on non-zero with `check=True`; `phase_generate_payload_h` calls `run(cmd)` unwrapped (`phase05_payload_h.py:50`), as do IR/encrypt stages (`build.py:1528,1545,1776`) → abort. Optional: optimizer catches, logs `ERROR`, continues (`build.py:1072-1075`); `--pytoc`/kernel-swap/spec are `try/except` + `PYTOC … (non-fatal)` (`build.py:2457-2467`) | `ACCEPTABLE` | Correct split: corrupting phases abort, advisory/best-effort phases degrade with a log line. The optimizer-continue path is the one to watch (build proceeds unoptimized, silently weaker — but logged as ERROR). |
| 24 | Network failure (DoH / GitHub farm) | `DEGRADE` (bounded) | **fix applied**: every `requests` call in the farm now carries a timeout (`_GITHUB_REQUEST_TIMEOUT`), so a stalled socket cannot hang the build; `trigger_and_wait` has an overall deadline (`_GITHUB_WAIT_DEADLINE`) instead of polling `while True` forever, and it reports the timeout plus the `--resume` hint; `download_artifacts` checks the status code instead of parsing an error page as an artifact list. Proven by `tests/test_build_farm_network.py` | `ACCEPTABLE` | The DoH→direct fallback still drops Tor posture silently; that is a *posture* question, not an availability one, and the farm is opt-in. |
| 25 | GitHub rate limiting (429) | `RETRY` (honours the server) | **fix applied**: `_github_retry_after()` reads `Retry-After` (seconds) and `X-RateLimit-Reset` (a unix timestamp), capped at `_GITHUB_MAX_BACKOFF`; `upload_file` treats 403/429 as a rate limit and waits as long as the server says; `download_artifacts` retries once after the wait. Other statuses keep the capped exponential backoff. Proven by `tests/test_build_farm_network.py` | `ACCEPTABLE` | Opt-in path only. |
| 26 | Corrupted downloaded artifact | `DEGRADE` (warned) / `FAIL-CLOSED` (keyed) | `GitHubBuildFarm.download_artifacts` (`core/utils.py:819-843`): timeouts (30s/120s), `raise_for_status`, ZipSlip confinement, plus verify-before-extract over `*.sig.json` sidecars (`_verify_download_zip`, `utils.py:493`) — mismatch raises, zip deleted, no extract; `GitHubNuitkaFarm.download_artifacts` (`utils.py:1429-1490`): same gate, tamper aborts without retry (`:1487`). No key → auditable `ARTIFACT-AUTH` warning + proceed; key + no sidecars → `info` + proceed (runner binaries unsigned by design) | `ACCEPTABLE` | Enforced where configured; keyless default warns (grep-able) instead of breaking existing users — explicit ADR-0005 protocol decision. Residual: runner-origin binaries have no HMAC (TLS + provenance only); Nuitka path still lacks ZipSlip confinement; shared-secret limits (no per-farm identity/rotation/replay expiry). Proven by `tests/test_artifact_signing.py::test_zip_gate_tamper_fail_closed`, `::test_enforce_dir_no_key_warns_loudly` (helper level; `utils.py` glue is `py_compile` + review — ADR-0005 risk 7). |
| 27 | Invalid C-extension output (cythonize fail) | `DEGRADE` (graceful skip) | Same as #4 plus in-pipeline `build_native_vm` returns `""` on non-zero (`core/pipeline.py:283-291`) and `compile_payload_to_cython` returns `None` with printed error (`349-361`); never raises | `ACCEPTABLE` | All Cython entry points degrade to pure-Python artifacts. |
| 28 | Incompatible Python/Cython versions | `CRASH` (early, loud) | Floor `sys.version_info < (3, 10)` → `ERROR` + `ok=False` → `sys.exit(1)` (`scripts/build.py:288-291,342-343`); NYSER loader enforces exact `(major, minor)` match → `ValueError("version mismatch — rebuild required")` (`core/pipeline.py:1610-1611`); farm pins `python-version: '3.11'` (`core/utils.py:563`) | `ACCEPTABLE` | Version mismatch fails at startup with a message, never as silent miscompilation. |
| 29 | Concurrent execution (trial flock vs build outputs) | `AUDITED` (trial) / `SAFE` (build outputs) | Trial read-modify-write holds blocking `LOCK_EX` (`trial_bind.py:91-107,346-351`), snippet deliberately lock-free with documented benign race (`trial_bind.py:466-474`); **fix applied**: `atomic_write` no longer uses a FIXED `path + ".tmp"` name — the temp file now carries the pid and a random suffix, so two concurrent builds of the same target cannot clobber each other (with the old name, one build's rename moved the file out from under the other, and the second rename raised `FileNotFoundError`). Proven by `tests/test_atomic_write_concurrency.py` | `ACCEPTABLE` | Trial side is fine. |
| 30 | Replay (trial token reuse) | `AUDITED` (`ok`, advances state) | Trial tokens are multi-use licenses, not nonces: reuse returns `"ok"` and advances sealed `last_seen` (`trial_bind.py:314-418`); covered upstream (`tests/test_adversarial_security.py:418-429` `test_trial_token_reuse_advances_not_bypass`) and re-proven by `test_trial_token_reuse_advances`; cross-machine replay fails via fingerprint binding; old-`last_seen` replay only shrinks the attacker's own rollback window (monotonic rewrite) | `ACCEPTABLE` | Documented limitation (state-file deletion resets the window; absolute deadline still holds). Correct for a license token. |
| 31 | Attacker-controlled env vars (all `NIXON_*`) | `AUDITED` (defaults fail-safe; table below) | Defaults verified in code + `test_env_defaults_fail_safe`; runtime effect of each var enumerated below | `ACCEPTABLE` | See env table. Two arming-on-empty-string quirks (`NIXON_KOD`, `NIXON_AUDIT_TIMING`: `!= "0"` means even `""` arms) err fail-closed; accepted deliberately. |

### `NIXON_*` env-var register (all vars found by grep over `*.py` + docs)

| Var | Default (unset) | Set effect | Fail-safe? |
|-----|-----------------|------------|-----------|
| `NIXON_LOG_REDIRECT` | `1` (redirect to build.log); `scripts/build.py:341` forces `0` for builds | `0` keeps console | Yes — observability only |
| `NIXON_KOD` | `0` = report-only (`obfuscator/vm_score.py:417`) | anything `!= "0"` (incl. `""`) arms kill-on-detect | Yes — default disarmed; quirk arms on empty (fail-closed) |
| `NIXON_DRIVER_CHECK` | disarmed, enumerate-only (`obfuscator/driver_blocklist.py:246-264,812`) | `1/true/yes` (any case) arms fail-closed gate + 60s daemon | Yes — default disarmed |
| `NIXON_AUDIT_TIMING` | disarmed (`obfuscator/audit_hook.py:117-119`) | any non-`"0"` (incl. `""`) arms timing-kill | Yes — same empty-string quirk as KOD, fail-closed |
| `NIXON_SNAPSHOT_OFF` | gate ON (`obfuscator/frozen_snapshot.py:97-106`) | `1/true/True/TRUE/yes/Yes/YES` disables gate | Yes — exact-match allowlist; `""`/typos keep gate ON |
| `NIXON_STDLIB_AUDIT_OFF` | gate ON (`obfuscator/stdlib_audit.py:29,45`) | same truthy set disables | Yes — same |
| `NIXON_AUDITHOOK_PLANT_OFF` | detector ON (`obfuscator/audit_hook.py:19,71`) | truthy disables plant detector | Yes — default armed |
| `NIXON_LADDER_DEBUG` | silent kills (`obfuscator/kill_ladder.py:47,179`) | `1` prints kill reasons to stderr | Yes — debug only |
| `NIXON_TRACEBACKS` | `0` = suppress loader tracebacks (`obfuscator/core/pipeline.py:1475`) | `1` enables diagnostics | Yes — default hides paths |
| `NIXON_TOR_PROXY` | `127.0.0.1:9050` (`obfuscator/core/utils.py:440-460`) | explicit endpoint; malformed → default | Yes — malformed falls back, never raises |
| `NIXON_VERIFY_SKIP_VERSION_CHECK` | gate holds (`obfuscator/py_matrix.py:101-180`) | bypasses version gate ONLY with `NIXON_CI`/`NIXON_ALLOW_SKIP` also set | Yes — dual-key; SKIP alone holds the gate |
| `NIXON_CI` / `NIXON_ALLOW_SKIP` | unset (gate holds) | second key for the skip-gate above | Yes — inert alone |
| `NIXON_SEED` / `SEED` | None (nondeterministic) (`scripts/build.py:897-906`) | deterministic `--randomization-seed` fallback | Yes — reproducibility only |
| `NIXON_DUMP_RAW` | `0` (no dump) (`obfuscator/core/pipeline.py:2791`) | `1` dumps raw material | Yes — default keeps material out of disk |
| `NIXON_SIGN_KEY` | unset → CLI errors (`scripts/artifact_sign.py:50-62`) | hex key for artifact HMAC | Yes — refuses to run without a key |
| `NIXON_ANALYST_COST` / `NIXON_AI_TOOL_COST` | `150.0` / `50.0` (`scripts/benchmark/hybrid_bench.py:56-57`) | benchmark cost inputs | Yes — metrics only |
| `NIXON_PROTECTED` | absent (source marker; `obfuscator/core/pipeline.py:2368`) | loader template marker, not env-read at runtime | N/A — not an env var |
| `NIXON_LICENSES` | KV namespace name (`obfuscator/core/pipeline.py:857`) | Cloudflare KV namespace for license deploy | N/A — deploy-time label, not a gate |

## Fixes applied (this audit)

1. `obfuscator/driver_blocklist.py`: added `version_fingerprints_mtime()` /
   `version_fingerprints_stale(max_age_s=90d)` — additive, no behavior change
   to the gate; unreadable/missing counts as stale (flag, don't trust).
   Proven by `tests/test_failure_modes.py::test_fingerprint_staleness_flag`.

## Deferred findings and their current state

One entry per finding, each marked. The list used to carry duplicate
entries (D24/D25 and D29 appeared twice, once as a recommendation and
once as a resolution) and D13 was still listed as unimplemented after
it had been resolved.

- **D3 — z3 hard dependency**: **RESOLVED**. Every `import z3` now
  goes through `scripts/z3_optional.py`; a build without z3 works and
  the proof path fails with a message that says what to install.
  Proven by `tests/test_failure_modes.py`.
- **D13 — build-input symlinks**: **RESOLVED** as an explicit trust
  statement. The build host is trusted (stated in `THREAT_MODEL.md`),
  so a symlinked input is followed and **warned about** with its
  target, rather than refused -- refusing would break legitimate
  setups that symlink a runtime. The runtime side was already
  `O_NOFOLLOW` and fails closed. Proven by
  `tests/test_build_input_symlinks.py`.
- **D24 / D25 — build-farm network robustness**: **RESOLVED**. Every
  `requests` call in the farm has a timeout, both farm classes have an
  overall deadline, `download_artifacts` checks the status code and
  retries once on a rate limit, and `Retry-After` /
  `X-RateLimit-Reset` are honoured with capped backoff. Proven by
  `tests/test_build_farm_network.py`. One residual remains open and
  is stated in the table: the DoH-to-direct fallback still drops Tor
  posture silently.
- **D26 — farm artifact integrity**: **DONE per ADR-0005**, residuals
  noted. The package step signs metadata-bound sidecars
  (`scripts/artifact_sign.py:sign_artifact`,
  `scripts/phases/phase06_package.py:59`); both `download_artifacts`
  paths verify-before-extract and fail closed on mismatch; no key
  means an auditable `ARTIFACT-AUTH` warning and proceed (fail-open by
  operator choice, never silent). ZipSlip confinement is now applied on
  **every** extraction path -- both farm download paths and the tool
  download -- through the shared `_extract_zip_confined()` /
  `_extract_tar_confined()` helpers, checked on the RESOLVED
  destination (proven by `tests/test_archive_confinement.py`).
  **Still open:** farm-runner binaries
  are unsigned by design (runners are keyless -- TLS plus provenance
  only); and a shared secret has no per-farm identity, rotation or
  replay expiry (`docs/adr/0005-artifact-authenticity.md`).
- **D29 — `atomic_write` temp-name collision**: **RESOLVED**. The temp
  name now carries the pid and a random suffix, so concurrent builds of
  the same target no longer share it. Proven by
  `tests/test_atomic_write_concurrency.py`.

## Behavior / verdict counts

- By behavior (31 scenarios): `DEGRADE` 10; `FAIL-CLOSED` 6; `CRASH` 5;
  `SILENT` 3; `AUDITED` 3; `FAIL-OPEN` 1; `WARNED` 1; `SILENT-safe` 1;
  `RETRY` 1. Mixed rows are counted under their primary label; the
  table carries the dual label. Four rows changed behavior when they
  were fixed: #3 `CRASH` → `DEGRADE` (the z3 import became optional),
  #13 `SILENT` → `WARNED` (a symlinked build input is now announced),
  #24 `DEGRADE` → bounded `DEGRADE` (timeouts and a deadline), and #25
  `SILENT` → `RETRY` (a rate limit is now waited out, not misreported).
- By verdict: `ACCEPTABLE` 31, `NEEDS-FIX` 0. #10 moved after the
  staleness-flag fix; #26 moved per ADR-0005 (enforced where configured,
  warned elsewhere); #3, #13, #24, #25 and #29 moved when the z3
  dependency was made optional, the build-input symlink warning landed,
  the farm timeouts/deadline and the rate-limit backoff landed, and the
  `atomic_write` temp-name fix landed.
