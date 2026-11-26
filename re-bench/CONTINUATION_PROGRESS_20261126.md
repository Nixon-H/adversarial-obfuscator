# ABSOLUTE MAXIMUM continuation progress — 2026-11-26

This file records work performed in the current continuation. It is a progress log, not a final completion report.

## Completed in this continuation

### GitHub Actions pinning

- Reconciled AI-SC-002 count: the claimed 91 mutable refs included one inert commented example; active mutable refs at the original audit point were 90, plus 15 pre-existing SHA refs.
- All 107 active external action rows in `.github/workflows` are now SHA-pinned; 0 active mutable external refs remain.
- 16 local reusable workflow refs are not upstream actions and are not third-party pinning targets.
- YAML parse validation: 17/17 workflow files parse with PyYAML.
- Machine inventory: `re-bench/GITHUB_ACTION_PIN_INVENTORY.json`.
- Pin regression validation: `tests/test_audit_followup_regression.py::test_every_ci_action_is_sha_pinned` plus Dependabot tests: 6 passed.
- Generated build-farm workflow in `obfuscator/core/utils.py` is SHA-pinned and now uploads `runner-attestation.json` with payloads.
- Full runner-attestation suite after fix: **21 passed in 66.52s**, evidence `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/test_outputs/pytest-runner-attest-continuation.log`.

### Chain/licence enforcement fixes

Source changes:

- `obfuscator/licensing.py`
  - strict 20-byte hex validation for contract and owner addresses;
  - explicit `chain_id` required in `--chain` metadata rather than silently defaulting to mainnet;
  - integer validation for `chain_id`/`token_id`;
  - strict JSON-RPC envelope validation (`jsonrpc == "2.0"`, `id == 1`);
  - malformed/non-object JSON rejected;
  - 1 MiB response cap;
  - strict ABI ownerOf validation: exact 32-byte word, canonical zero padding, hex only.
- `obfuscator/core/pipeline.py`
  - emitted standard and hybrid loaders now fail closed on expired licences;
  - malformed licence expiry fails closed;
  - emitted chain gates require signed `chain_id` and use it directly rather than defaulting to 1;
  - build-manifest generation now includes `_protected_dbg.py` artifacts as well as `_protected.py`.

Tests added/updated in `tests/test_licence_binding.py` and `tests/test_chain_transport_policy.py`.

Focused validation:

- `tests/test_licence_binding.py tests/test_chain_transport_policy.py`: **42 passed in 56.96s**.
- This does not yet include a fresh real-EVM dependency-gated test.

### Xfail resolution evidence

- Current tree has zero pytest xfail markers.
- Historical seven strict xfails at HEAD were:
  - AI-CRYPTO-004 decoy-key derivation;
  - AI-PROTO-006 unwritable replay ledger;
  - AI-PROTO-007 replay-ledger race;
  - AI-PROTO-008 rollback mark write failure;
  - AI-PROTO-009 revocation rollback guard wiring;
  - AI-PARSE-010 manifest fingerprint re-attribution;
  - AI-PARSE-011 stream_join exception contract.
- Focused regression command result: **8 passed in 0.19s**, evidence `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/test_outputs/xfix-regression-continuation.log`.
- Important boundary: fixes are in the dirty working tree, not committed HEAD. Authoritative benchmark artifacts still predate AI-CRYPTO-004 and still expose old artifact-public decoy derivation; they must not be mutated.

### Release/provenance acceptance fixes

- `.github/workflows/ci.yml` now sets `NIXON_BUILD_MANIFEST_PUBKEY` from the independently generated ephemeral signing key when `NIXON_REQUIRE_PROVENANCE=1` is used, closing the static fail-closed mismatch.
- CI acceptance now asserts the artifact-embedded provenance pin matches the independently generated publisher key rather than circularly trusting an artifact-derived pin.
- `.github/workflows/release.yml` now asserts the same independent-pin equality.
- Release artifact upload now includes `accepted_artefact.py.build-manifest.json` with the accepted artifact, digest, and acceptance report.
- YAML parse validation passed for both edited workflow files after the edits.

## Subagent audit findings not yet fixed

High-priority unresolved supply-chain findings from the read-only re-audit:

1. Anti-rollback (`obfuscator/rollback.py`) is implemented and tested but not wired into emitted artifacts or release consumption.
2. Dependency drift remains warning-only by default; release workflow does not set `NIXON_REQUIRE_DEP_LOCK=1`.
3. `scripts/build.py` can log phase errors and still print success/exit 0; unlike the emitted hybrid loader, this driver can still mask unusable-output failure.
4. Manifest acceptance validates presence more than exact values; should compare commit, dependency-lock digest, CI identity, dependency drift status, platform matrix, pack version, and protection-level monotonicity.
5. CI/release signing keys are ephemeral. This proves mechanics but is not persistent publisher identity.
6. No SLSA/in-toto/Sigstore/GitHub artifact-attestation provenance exists; provenance is custom Ed25519/manifest provenance.
7. Pip bootstrap upgrades and ruff installs remain unhashed supply-chain exceptions.
8. Release artifacts are intentionally not byte-for-byte reproducible; only seeded transform-layer reproducibility is claimed.
9. Some action versions differ across workflows (`checkout` v4.4.0/v4.2.2/v7.0.1, `setup-python` v5.6.0/v5.3.0, upload-artifact v4.6.2/v4.4.3). They are pinned but should be normalized or explicitly justified.
10. `dtolnay` action code is pinned, but `stable`/`nightly` Rust toolchains remain floating channels.

EVM/native findings from subagents not yet fixed:

- No reproducible dependency-gated real-EVM pytest has been added yet; historical real EVM evidence lives outside the repo and used ad hoc dependencies.
- Dynamic revocation/transfer test through emitted artifact loader not yet implemented.
- Rollback/replay integration into emitted artifact loaders remains incomplete.
- macOS signing/notarization, Windows public trust, ARM64 native support, and protected release environments remain external/unimplemented.

## Verification caveats

- No full-suite rerun has been performed after the current continuation edits.
- No commit has been created in this continuation.
- `docs/MAXIMUM_SECURITY.md` remains untouched as required.
- The benchmark remains externally provider-limited. Devin subagents are audit assistants only and are not valid Hy4/TokenHarbor benchmark evidence.

Additional fixes just applied:

- `scripts/common.py` now counts `ERROR` log events and `scripts/build.py` exits nonzero if any phase error occurred, closing successful-exit-after-phase-failure masking in that driver.
- `.github/workflows/release.yml` release acceptance build now sets `NIXON_REQUIRE_DEP_LOCK=1`, making dependency drift release-fatal in that lane.
- Syntax validation passed for `scripts/common.py` and `scripts/build.py`; release workflow YAML parses.

### Real local-EVM integration progress

- Added `tests/test_chain_real_evm.py`, a dependency-gated integration test that compiles the repository Solidity licence contract with solc 0.8.20, deploys it in py-evm/eth-tester, and exercises the exact emitted loader helper over loopback JSON-RPC.
- The test covers valid ownership, transfer invalidating the original owner, burn/revocation failure, wrong chain ID, runtime expiry, wrong JSON-RPC id/version, malformed ABI words, and non-canonical ABI padding.
- Added `requirements-evm.txt` with exact optional dependency pins: `eth-tester==0.14.0b1`, `py-evm==0.12.1b1`, `py-solc-x==2.0.5`.
- The integration exposed a real emitted-loader defect: `_hex_address` existed in `obfuscator/licensing.py` but was not copied into emitted artifacts, causing chain-enabled loaders to fail with `NameError`. Fixed `obfuscator/core/pipeline.py` to emit the helper in both standard and hybrid chain loader paths.
- Validation: **4 passed in 1.25s**. Evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/test_outputs/chain_real_evm_continuation.log`.

### AI-RE-003 benchmark-control gate

- Added `scripts/benchmark/score_control.py` implementing a central control-plane gate for benchmark-derived pass selection.
- Unvalidated composite benchmark scores now remain diagnostics and cannot drive adaptive rewriting by default.
- Explicit experimental override remains available only through `NIXON_ALLOW_UNVALIDATED_BENCHMARK_CONTROL=1`.
- Validation metadata can enable control only if it records held-out recovery correlation, at least 30 independent samples, Spearman rho at least 0.5, and positive lower confidence bound when supplied.
- Wired the gate into both `scripts/build.py` adaptive rewrite paths and `scripts/phases/phase07_phase2.py`.
- Added `tests/test_benchmark_control_gate.py`.
- Validation: **17 passed in 0.33s**. Evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/test_outputs/benchmark_control_gate.log`.

### Full artifact real-EVM validation

- Extended `tests/test_chain_real_evm.py` with a full emitted-artifact integration test.
- The test issues a licence bound to token 3 on the real local py-evm contract, builds the real protected artifact, verifies the first run prints `REAL_EVM_ARTIFACT_RAN`, transfers the token on-chain, and verifies the second artifact execution fails with `licence chain owner mismatch`.
- Validation: **5 passed in 58.57s**. Evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/test_outputs/chain_real_evm_full_artifact_continuation.log`.
- Added `requirements-evm.lock`, generated with `uv pip compile --generate-hashes --python-version 3.13`, and `tests/test_evm_dependency_lock.py` validating exact pins and hash coverage.
- Corrected the partition-runner environment variable documented in `AGENTS.md` to `TEST_PARTITION_PYTEST_RUNNER`.
- Added `re-bench/ABSOLUTE_MAXIMUM_RUNTIME_SECRET_BOUNDARY.md`, documenting the AM-001 customer-controlled runtime-secret boundary and feasible architectural remediation classes without claiming client-side cryptographic confidentiality.

### Later continuation evidence

- Real EVM full emitted-artifact test: **5 passed in 58.57s** (`test_outputs/chain_real_evm_full_artifact_continuation.log`). This includes a real build, valid execution, on-chain transfer, and subsequent loader refusal.
- Workflow and dependency regression lane after release-publish verification changes: **80 passed in 14.38s** (`test_outputs/workflow_regressions_continuation.log`).
- Independent fix/regression lane: **67 passed in 2.95s** (`test_outputs/independent_fix_regressions_continuation.log`).
- Credential redaction scan after continuation edits: **credential_hits=0**, files scanned 64,229 (`test_outputs/secret_redaction_scan_continuation.log`).
- `final_verification_summary.json` regenerated successfully after the continuation edits.
- Release publish acceptance now carries the signed build-manifest sidecar and re-verifies it in the publish job against the accepted artifact digest and the public key recorded in the acceptance report.
- Added `ABSOLUTE_MAXIMUM_CONTINUATION_STATUS_MATRIX.md`, `ABSOLUTE_MAXIMUM_RUNTIME_SECRET_BOUNDARY.md`, `ABSOLUTE_MAXIMUM_CROSS_PLATFORM_SIGNING_STATUS.md`, and `ABSOLUTE_MAXIMUM_BENCHMARK_METHODOLOGY_STATUS.md`.
- Full-suite security-licensing partition exposed one benchmark-infrastructure timeout: `tests/bench_attack_replay.py::TestAttackReplayBenchmarks::test_bench_capture_time` exceeded its 180s per-test budget. The benchmark timeout was raised to 600s (the benchmark performs many capture rounds); focused rerun passed in 55.43s. Evidence: `test_outputs/bench_capture_time_fix.log`.

Final partition aggregate: 30,773 passed, 9 skipped, 0 failed across corrected partition evidence. No continuation commit created because of mixed pre-existing dirty tree.
- Post-commit full-suite review exposed an invariant-engine scalability defect: untracked `re-bench/` and `audit/` evidence trees were included in recursive source scans, causing `test_check_no_silent_fallback` to exceed the per-test timeout. Fixed the directory exclusion and added regression coverage; focused result: 23 passed in 37.81s.
- Commits created: `89a6527` hardening/validation evidence, `fb4f7af` farm dependency lock.
