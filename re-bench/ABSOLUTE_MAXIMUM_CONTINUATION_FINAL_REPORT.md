# ABSOLUTE MAXIMUM continuation final report


> **2026-11-27 status supersession:** this is historical pre-DeepSeek continuation
> evidence. Statements that the benchmark remains provider-blocked or incomplete
> are superseded for the operator-authorised replacement lane:
> `opencode-go/deepseek-v4.1-flash` completed 114/114 structurally valid
> diagnostic cells across 6 variants × 19 scenarios, one attempt per cell. That
> completion is diagnostic-only, not statistical acceptance or a release gate.
> Current authority: `re-bench/ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md` and
> `re-bench/ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md`.

Date: 2026-11-26. This report covers the continuation work only. It does not overwrite the prior audit and it does not claim externally blocked work is complete.

## Executive outcome

The continuation closed several concrete implementation and evidence gaps: real local EVM execution through a full emitted artifact, emitted-loader expiry enforcement, strict chain transport parsing, benchmark-control gating for AI-RE-003, build fatal-error visibility, release/provenance acceptance defects, dependency-lock enforcement, EVM dependency locking, credential scanning, and evidence documentation. The benchmark itself remains externally provider-blocked and no production signing/notarisation result is claimed.

## New continuation reports

- `re-bench/ABSOLUTE_MAXIMUM_CONTINUATION_STATUS_MATRIX.md`
- `re-bench/ABSOLUTE_MAXIMUM_RUNTIME_SECRET_BOUNDARY.md`
- `re-bench/ABSOLUTE_MAXIMUM_CROSS_PLATFORM_SIGNING_STATUS.md`
- `re-bench/ABSOLUTE_MAXIMUM_BENCHMARK_METHODOLOGY_STATUS.md`
- `re-bench/CONTINUATION_PROGRESS_20261126.md`

## Important verified results

| Verification | Result | Evidence |
|---|---:|---|
| Runner attestation regressions | 21 passed | `test_outputs/pytest-runner-attest-continuation.log` |
| Xfail regression lane | 8 passed | `test_outputs/xfix-regression-continuation.log` |
| Benchmark-control gate | 17 passed | `test_outputs/benchmark_control_gate.log` |
| Build error visibility | 7 passed | `test_outputs/build_error_visibility.log` |
| Real local EVM contract + full emitted artifact | 5 passed in 58.57s | `test_outputs/chain_real_evm_full_artifact_continuation.log` |
| Workflow/dependency regressions after release changes | 80 passed in 14.38s | `test_outputs/workflow_regressions_continuation.log` |
| Independent fix/regression lane | 67 passed in 2.95s | `test_outputs/independent_fix_regressions_continuation.log` |
| Secret scan after continuation edits | credential_hits=0 across 64,229 files | `test_outputs/secret_redaction_scan_continuation.log` |
| Capture benchmark timeout fix | 1 passed in 55.43s | `test_outputs/bench_capture_time_fix.log` |
| Final verification summary regeneration | success | `ABSOLUTE_MAXIMUM_RAW_RESULTS/final_verification_summary.json` |

Full-suite partition evidence is in `test_outputs/full_partitions_continuation/`. At the time this report was drafted, completed partitions included `vm-ir-llvm` 774 passed and `crypto-container` 405 passed, 1 skipped. The run was a bounded continuation run and must be interpreted with its generation caveat: the full emitted-artifact EVM test was added after that run had started and was verified separately. The security-licensing partition initially exposed `test_bench_capture_time` exceeding its 180-second budget; the benchmark timeout was corrected and the focused rerun passed.

## Real EVM evidence

`tests/test_chain_real_evm.py` compiles the actual Solidity licence contract with `solcx` 0.8.20, deploys it to an in-process py-evm/eth-tester chain, exposes it through the repository JSON-RPC bridge, and validates ownerOf behavior. It covers valid ownership, transferred licence enforcement, burned/unminted token refusal, wrong-chain refusal, response manipulation, malformed token/refund semantics, and expiry behavior. The full artifact test builds a real protected artifact, runs it successfully before transfer, transfers the token on-chain, and verifies the next artifact execution fails closed with `licence chain owner mismatch`.

This is real local EVM execution, not mocked RPC. It is not public-chain evidence.

## Supply-chain and release-integrity fixes

- CI no longer sets `NIXON_REQUIRE_PROVENANCE=1` without the required manifest trust anchor.
- CI/release acceptance compare embedded provenance pins against independently generated publisher key material rather than artifact-derived pins.
- CI/release acceptance now compare exact dependency-lock digest, workflow identity, run identity, and commit identity rather than merely checking field presence.
- Release dependency drift is fatal in the release lane through `NIXON_REQUIRE_DEP_LOCK=1`.
- Release upload includes the signed build-manifest sidecar.
- Publish verification now checks the accepted artifact digest, manifest digest, manifest signature, and acceptance verdict.
- `scripts/build.py` exits nonzero after logged phase errors rather than printing success and returning 0.
- Debug protected artifacts are included in manifest generation coverage.

## Security-boundary conclusions

AM-001 remains an architectural limitation, not a fixable local coding oversight. The customer-controlled machine has the licence file, licence key material, and operator shard material needed for legitimate execution. A direct import of an already extracted native object can bypass loader-mediated licence/chain/host/provenance enforcement. True confidentiality requires server-side execution, remote key release, or a hardware/trust boundary; software obfuscation cannot provide cryptographic confidentiality against the host operator.

## Remaining externally blocked or incomplete items

1. Benchmark completion is externally blocked: Hy4 free lane is in provider-specified cooldown; TokenHarbor `:free` resets 2 Dec 2026 15:07 UTC; TokenHarbor paid fallback returns HTTP 402.
2. Windows public certificate-chain trust, Authenticode timestamping, and strict shadow-stack enforcement need external certificate/Windows validation.
3. Apple Developer ID signing, Hardened Runtime, notarisation, stapling, and Gatekeeper validation need Apple/macOS infrastructure.
4. Linux ARM64 and Windows ARM64 native payloads are unsupported/unmeasured.
5. Persistent release publisher identity and protected production environment configuration are operator-side requirements.
6. Rollback machinery and tests exist, but production emitted-artifact wiring remains incomplete; it must not be represented as deployed anti-rollback protection.
7. Rollback machinery and tests exist, but production emitted-artifact wiring remains incomplete; it must not be represented as deployed anti-rollback protection.

## Exact operator actions still required

- Rotate any host/provider credentials exposed before credential isolation.
- Restore authorised benchmark quota or wait for the provider reset.
- Configure persistent publisher signing identity and protected production environment rules.
- Obtain/configure Windows and Apple signing credentials and run platform-native validation.
- Decide whether rollback protection is a supported product feature; if yes, implement and verify production wiring as a separate controlled change.

## Key files changed or added in this continuation

### Runtime/build/product logic
- `obfuscator/licensing.py`
- `obfuscator/core/pipeline.py`
- `obfuscator/core/utils.py`
- `obfuscator/build_manifest.py`
- `scripts/build.py`
- `scripts/common.py`
- `scripts/benchmark/score_control.py`
- `scripts/phases/phase07_phase2.py`

### Tests and dependency locks
- `tests/test_chain_real_evm.py`
- `tests/test_evm_dependency_lock.py`
- `tests/test_benchmark_control_gate.py`
- `tests/test_build_error_visibility.py`
- `tests/test_ai_benchmark_harness.py`
- `tests/test_licence_binding.py`
- `tests/test_chain_transport_policy.py`
- `tests/bench_attack_replay.py`
- `requirements-evm.txt`
- `requirements-evm.lock`

### Workflows
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- workflow action-pin updates across `.github/workflows/*.yml`

### Continuation evidence/reports
- `re-bench/ABSOLUTE_MAXIMUM_CONTINUATION_STATUS_MATRIX.md`
- `re-bench/ABSOLUTE_MAXIMUM_RUNTIME_SECRET_BOUNDARY.md`
- `re-bench/ABSOLUTE_MAXIMUM_CROSS_PLATFORM_SIGNING_STATUS.md`
- `re-bench/ABSOLUTE_MAXIMUM_BENCHMARK_METHODOLOGY_STATUS.md`
- `re-bench/ABSOLUTE_MAXIMUM_CONTINUATION_FINAL_REPORT.md`
- `re-bench/CONTINUATION_PROGRESS_20261126.md`

This is the high-confidence continuation list, not a claim that these are the only dirty files. The working tree contains extensive prior-session modifications outside this continuation.

## Final bounded full-suite evidence

The first full partition run completed the large build/security partitions but the runner copy inside TMPDIR was deleted by tests, causing five partitions to exit before collection. The affected partitions were rerun with the runner outside TMPDIR. Results:

- vm-ir-llvm: 774 passed
- crypto-container: 405 passed, 1 skipped
- build-native-loader: 557 passed, 4 skipped
- security-licensing rerun: 832 passed
- unit-static-1: 483 passed
- unit-static-2: 25,634 passed, 1 skipped
- unit-static-3 corrected rerun: 948 passed, 3 skipped
- unit-static-4: 979 passed
- distributed-network: 161 passed

Aggregate across corrected partition evidence: **30,773 passed, 9 skipped, 0 failed**. This is partition-combined evidence rather than one single pytest process; it also carries the generation caveat documented above. Evidence directories: `test_outputs/full_partitions_continuation/`, `test_outputs/full_partitions_missing_rerun/`, and `test_outputs/unit_static_3_rerun/`.

Two documentation/escape-hatch defects found during final verification were corrected without editing `docs/MAXIMUM_SECURITY.md`: the experimental unvalidated-benchmark override was removed entirely, and failed farm attestation is now always refused rather than bypassable through an undocumented environment variable.


## Commits created

- `89a6527` — `Harden security controls and validation evidence` (263 files; scoped source/test/workflow/config commit; excluded evidence trees and `docs/MAXIMUM_SECURITY.md`)
- `fb4f7af` — `Add hash-locked native farm dependency manifest` (`requirements-farm.lock`)

The large evidence directories `re-bench/` and `audit/` remain local evidence, not committed bulk artifacts. `docs/MAXIMUM_SECURITY.md` remains externally modified and was deliberately excluded.
