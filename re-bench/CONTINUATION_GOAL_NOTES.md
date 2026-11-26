# Continuation Goal Notes

> **2026-11-27 status supersession:** this document contains historical Hy4/TokenHarbor/Kern continuation state. It is not the current benchmark status. The completed operator-authorised replacement lane is `opencode-go/deepseek-v4.1-flash`: 114/114 active records are structurally valid across 6 variants × 19 scenarios after retry. That campaign is diagnostic-only because it has one attempt per cell. Use `re-bench/ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md` and `re-bench/ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md` as the current authoritative status.

This file preserves key reconstruction facts gathered during the `/goal` continuation. It is a working evidence index, not the final report.

## Initial verified state

- HEAD: `b571b18a79b76ee351f307ced793c6e66c7f22ce`; branch `master...origin/master [ahead 2]`.
- Worktree: extensively dirty (about 253 entries). Do not reset/revert. `docs/MAXIMUM_SECURITY.md` must not be modified.
- Authoritative artifacts remain pinned:
  - `absolute-native-only` SHA-256 `28630cc945e883151761b4752db1d9a7e59a7dbb29bc9e93b381e75ba2898032`, 1,117,774 bytes.
  - `absolute` SHA-256 `5382e72af5cce267fa2ec0379b6c3910b0bc33f7ac645a5ad2c88bc011ce0fbe`, 1,794,213 bytes.
- Benchmark remains incomplete: 498 records, 29 strict valid, 0/32 groups at five valid attempts; all 29 valid model-separated groups have exactly one valid attempt. Hy4 28/166 valid; TokenHarbor 1017 1/332 valid; TokenHarbor free 0 records. Pre-fix comparison 0 rows.
- Exactly one watchdog was restarted after the prior PID disappeared: PID 2393295, `python3 re-bench/tools/resume_absmax_benchmark_when_quota.py --probe-interval 300`. Fatal logging was added. It must not be duplicated.
- Devin subagents may perform local analysis but cannot be represented as Hy4/TokenHarbor benchmark evidence.

## GitHub Actions pin reconstruction

- Original AI-SC-002 count reconciliation: the report said 106 third-party refs = 91 mutable +15 SHA. Actual HEAD scan shows 105 active external refs = 90 mutable +15 SHA, plus one commented inactive `actions/setup-example@v1` in `codeql.yml`. The 91st was an inert commented example.
- Current active workflow scan before final validation: 123 active `uses` rows = 16 local reusable workflow refs +107 external SHA-pinned refs, 0 active external mutable refs.
- Current external refs are pinned to upstream-verified tags/branches. Important exact mappings:
  - `actions/checkout@11d5960a326750d5838078e36cf38b85af677262`: v4/v4.4.0/releases-v4.
  - `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`: v4.2.2.
  - `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`: v7/v7.0.1.
  - `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`: v5/v5.6.0/releases-v5.
  - `actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b`: v5.3.0.
  - `actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830`: v4/v4.3.0.
  - `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02`: v4/v4.6.2.
  - `actions/upload-artifact@b4b15b8c7c6ac21ea08fcf65892d2ee8f75cf882`: v4.4.3.
  - `actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16`: v4.1.8.
  - `actions-rust-lang/setup-rust-toolchain@166cdcfd11aee3cb47222f9ddb555ce30ddb9659`: v1/v1.17/v1.17.0.
  - `dtolnay/rust-toolchain@6a52aad76a94a5fbc50d567bb5be24419801c1fb`: branch `nightly` head at verification time; action.yml default toolchain nightly.
  - `dtolnay/rust-toolchain@39008827e6b4319a349e9a42dfc90579dd25f1ca`: branch `stable` head at verification time; action.yml default toolchain stable.
  - `github/codeql-action/*@915412ff23e8b7659517e607487dbeae018f2934`: v4/v4.39.5/releases-v4.
  - `gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7`: v2/v2.3.9.
- Missing pin comments in `ci.yml`/`release.yml` were added. Static active SHA rows now all carry `pinned immutable;` comments.
- `portable-deep-matrix.yml` has two more external refs than HEAD because one additional checkout/setup-python pair was added in pre-existing worktree changes.
- Generated farm workflow in `obfuscator/core/utils.py` was separately vulnerable: it generated mutable `checkout@v3`, `setup-python@v4`, `upload-artifact@v4` and uploaded only payload objects, not `runner-attestation.json`. It was changed to upstream-verified SHAs and to upload both payload and attestation. Tests were added in `tests/test_runner_attest.py`.
  - generated checkout v3 pin `a37ce9120846195fa4ece8f58b268e6043cb2f26` = v3/v3.7.0.
  - generated setup-python v4 pin `7f4fc3e22c37d6ff65e88745f38bd3157c663f7c` = v4/v4.9.1.

## Cross-platform/signing reconstruction highlights

- Linux local native build is real; Windows/macOS native evidence is cloud-farm measured evidence, not locally reproducible on this host.
- Windows x86-64 farm object measured CFG/CET compatibility; strict hardware-backed shadow-stack enforcement is not proven.
- macOS farm object is effectively unsigned/incomplete for trust: no Developer ID, no Hardened Runtime, no notarization/stapling; arm64 ad-hoc signature only and x86-64 slice lacks signature load command.
- Pure-Python portable artifact CI coverage is not native ABI coverage. Native objects are interpreter/ABI-specific and farm-built with Python 3.11.
- Lowering shim/native kernel distribution is incomplete as a standalone multi-platform package; `--pytoc`/PyInstaller paths are best-effort.
- Smart launchers contain adverse trust bypasses: Windows self-signed root/Defender exclusion and macOS quarantine removal. These conflict with public trust and should be removed or replaced with instructions.
- Generated farm workflow attestation upload gap is being fixed as noted above.

## EVM reconstruction highlights

- Real local EVM execution exists only in re-bench evidence using py-evm/eth-tester, not Anvil; pytest uses mocks/stubs. EVM dependencies are absent from requirements/locks, so evidence is not reproducible in the normal dev environment.
- Local py-evm evidence covers valid ownership, wrong owner/token, wrong chain, burn/transfer, read-only proxy, and real loader enforcement. No public-chain evidence exists.
- Major implementation gaps:
  1. Runtime expiry is never enforced in emitted artifacts; expiry only checked build-side.
  2. `chain_id` is not mandatory in emitted loaders; missing chain ID silently means mainnet (`or 1`).
  3. contract/owner addresses are only `0x`+length checked, not hex validated.
  4. ownerOf result is truncated with `result[-40:]` without strict 32-byte ABI hex validation; JSON-RPC responses lack id/version/size validation.
  5. rollback/replay libraries exist but are not wired into emitted artifacts.
  6. no dynamic revocation-after-successful-run end-to-end test.
  7. legacy blockchain gate is fail-open (`try/except: pass`) but separate from ERC-721 licence-chain path.
- Smallest high-value fixes: runtime expiry enforcement, mandatory chain_id, strict hex/ABI validation, malformed RPC tests, then optional-deps real-EVM pytest.

## Benchmark/secret-boundary reconstruction highlights

- Scorer is useful for triage but not validated as a release-quality metric. Most points are evidence/keyword rubric; only hidden-vector execution is independent. No golden scorer corpus exists.
- Acceptance correctly rejects unvalidated benchmark scores as release gates, but AI-RE-003 is not fully fixed in product because opt-in adaptive rewriting still uses unvalidated benchmark metrics through `BenchmarkFeedbackAnalyzer` -> `AdaptiveRewriter`.
- AM-001 is confirmed: customer-machine attacker with legitimate runtime secrets can extract and directly execute native module with only `NX_SEAL_SHARD`, bypassing loader gates. No local client-side design can guarantee confidentiality against the machine owner.
- Plaintext native object is written to a filesystem tempfile before native enforcement and `bytes(blob_data)` creates an unwipable immutable copy. This is opportunistic-exposure surface; memory-only loading can reduce but not eliminate customer-machine attack risk.
- Licence `key_material` is plaintext in customer token and static across reissue; operator shard reuse can magnify compromise. Cross-customer isolation is pre-compromise only.
- Redaction scan is strong operational hygiene but exact-match scanning is not confidentiality proof. Fixture secrets must be treated as disclosed.
