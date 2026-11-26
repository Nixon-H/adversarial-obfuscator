# ABSOLUTE MAXIMUM final security audit

> **2026-11-27 status supersession:** benchmark status statements in this historical document may refer to incomplete Hy4/TokenHarbor/Kern lanes. The current completed diagnostic lane is `opencode-go/deepseek-v4.1-flash`: 114/114 active records structurally valid across 6 variants × 19 scenarios, one attempt per cell. Treat this document as historical context unless it explicitly cites the DeepSeek final report. Current status: `re-bench/ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md`.

Audit date: 2026-11-25/26. Repository: `/home/nixon/Projects/adversarial-obfuscator`, branch/commit `b571b18a79b76ee351f307ced793c6e66c7f22ce`; initial status was `master...origin/master [ahead 2]`. The tree contained extensive pre-existing modifications before the audit; none were reset or discarded. `docs/MAXIMUM_SECURITY.md` was not edited.

## Executive summary

Completed and independently measured on Linux x86-64:

* Built the two ABSOLUTE MAXIMUM variants with the post-fix stream-envelope packing code **and strict dependency-lock enforcement** (`NIXON_REQUIRE_DEP_LOCK=1`, using the lock-compliant build virtual environment):
  * `absolute-native-only`: 1,117,774 bytes, SHA-256 `28630cc945e883151761b4752db1d9a7e59a7dbb29bc9e93b381e75ba2898032`.
  * `absolute`: 1,794,213 bytes, SHA-256 `5382e72af5cce267fa2ec0379b6c3910b0bc33f7ac645a5ad2c88bc011ce0fbe`.
* Both artifacts execute successfully with the correct licence, HWID-bound token, local-chain owner state, provenance pin, and `NX_SEAL_SHARD`, printing `SEALED 8771940273853809a401795ec7699cdc`.
* Strict-artifact negative runtime probes:
  * native-only: missing licence/seal/all secrets exit 78; one-byte tamper exit 137; forged/wrong licence exit 1;
  * hybrid: missing licence/all secrets exit 137; missing seal shard exit 79; one-byte tamper exit 137; forged/wrong licence exit 1.
* The strict extracted native payloads are genuine ELF64 shared objects:
  * native-only: 739,360 bytes, SHA-256 `ebd1f04def3f422a27dcaa7e9d223432454f270bd8af28371cdf9323a3a71515`;
  * hybrid: 731,160 bytes, SHA-256 `4b0b297aefb138c78944eb59adf90ac681fd5708cab9413bfa434a771dfa5cf6`.
* Ghidra analyzed both final native-lowering objects. Native-only: 566 functions, `nx_apply_protections` at `001a3eb0`, `PyInit_payload` at `00106980`. Hybrid: 565 functions, `nx_apply_protections` at `001a2100`, `PyInit_payload` at `00106990`. Both export `PyInit_payload` and `nx_apply_protections`; decompilation shows `prctl`, `setrlimit`, and `sigaction`.
* Controlled final-artifact `strace`: valid execution exits 0, successful `mlock` observed, `PR_SET_DUMPABLE` observed, and zero inet/inet6 connect calls in both variants. Refined traces recorded 22/24 `prctl` calls, 23/36 `prlimit64` calls, and 204/206 `rt_sigaction` calls for native-only/hybrid respectively; no exact secret values appeared in the traces.
* The actual Solidity ERC-721 licence contract was compiled with solc 0.8.20, deployed to local py-evm/eth-tester, minted, burned, and queried. Eight contract/client cases passed. This was real local EVM execution, not a mocked `ownerOf` RPC implementation. No public-chain deployment was performed.
* The pre-fix repeating-XOR native blob was recoverable artifact-only from the known ELF header. Exact validation against both preserved pre-fix artifacts recovered valid ELF objects with dynamic-symbol evidence for `PyInit_payload`/`nx_apply_protections` and without runtime secrets; the final `NXS1` artifacts are not reconstructed by the same procedure (`crypto_validation/prefix_postfix_exact_artifact_known_plaintext.json`).

Critical boundary that remains:

* A customer-machine attacker with legitimate runtime secrets can extract the native module and directly execute it with only `NX_SEAL_SHARD`, bypassing loader-mediated licence/host/chain/provenance gates. This is measured, not speculative, and remains an unresolved architectural limitation.
* The authoritative artifact pair still emits `_NX_HONEY_HINT` values exactly reproduced by the old artifact-public honey-key derivation. The current source tree has operator-keyed decoy derivation and passes its regression test, but that later source hardening is not part of the authoritative artifact identity. The old derivation fully recovered a plausible 2,012-byte Python decoy plaintext from each authoritative artifact (without recovering the real hidden secret); the artifact exposure remains open until a separately identified rebuild and campaign.

Not completed or not claimable:

* No public-chain licence deployment, Authenticode public-CA trust, Apple Developer ID/notarisation, hardware-backed Windows shadow-stack validation, production release administration, cloud build-farm artifact, or cross-platform lowering-shim validation.
* A single serial full-repository pytest invocation remains impractical in this tree, but all 496 inventoried test files now have passing bounded-partition reruns across the nine disjoint partitions: 30,745 pytest rows passed and 9 were skipped in the selected passing runs. This is partitioned completion evidence, not a byte-frozen clean-checkout CI run; earlier killed/failed attempts remain preserved.
* The authorised continuation lanes are `opencode/hy4-flash-free` through the validated redacting MITM path, `tokenharbor/deepseek-v4.1-flash:free`, and fallback `tokenharbor/deepseek-v4.1-flash-1017`; the multi-lane watchdog probes them in that order and never substitutes another model. At the latest strict-scoring checkpoint Hy4 had 166 records, 28 strict valid attempts, 28/32 groups with any strict-valid attempt, 0/32 groups meeting five valid attempts, and a provider free-limit cooldown; TokenHarbor free had zero records because it was quota-blocked before execution. The matrix remains incomplete and cannot support a finished resistance conclusion.
* The final native-lowering AI matrix is **incomplete**. Reconciliation of 498 model-separated records after the AM-027 strict tool-limit correction gives 29 strict valid scored attempts and 469 invalid/unscored attempts: 90 harness-bridge syntax infrastructure failures, 176 TokenHarbor provider-quota failures, 84 Hy4 provider-free-limit failures, 99 over-20-tool-call attempts, 9 timeouts, 8 static-only execution-policy violations, 2 fail-closed harness records, and 1 generic malformed/nonzero record. TokenHarbor is 1/332 strict valid; Hy4 is 28/166 strict valid. No variant/scenario/model group meets five valid attempts. The targeted pre-fix AI comparison did not start. These are missing-evidence and invalid-attempt results, not resistance evidence. Full details are in `ABSOLUTE_MAXIMUM_BENCHMARK.md` and `ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/score_summary.json`.

## Three-profile comparison

Important live-implementation clarification: the CLI does not define literal profiles named `LOCAL MAXIMUM` or `CLOUD MAXIMUM`. Those names describe build paths: local `--skip-cloud` versus cloud/build-farm generation. The benchmark harness in `pydeobsbench/run.py` defines `default`, `max`, `max-legacy`, `absolute`, `absolute-native-only`, and `absolute-licensed`; those harness profiles are not additional security tiers. The audit therefore compares build paths rather than inventing a fourth tier.

### LOCAL MAXIMUM

Live meaning: local packed/native build for the current host, normally `--skip-cloud` plus local packaging. It can enable loader protections, the local Cython blob, access gates, licence binding, transforms, lowering, sectioned payload, split bootstrap, strict detections, and self-checks.

Limits: only the current OS blob is produced; native compilation is ABI/Python dependent; `--package all` is local packaging, not cloud compile. It received configuration/build-path audit only, no AI attempts.

### CLOUD MAXIMUM

Live meaning: the same recipe plus platform-specific native blobs through the implemented GitHub build farm (`platform=github`) and optional Cloudflare deployment. The only implemented farm platform is GitHub. Missing farm/cloud credentials now fail loudly rather than silently producing a single-platform artifact.

No cloud artifact was built because remote credentials/infrastructure were unavailable. It received configuration/build-path audit only, no AI attempts.

### ABSOLUTE MAXIMUM

The strongest locally valid customer-bound configuration combines native compilation, licence-token binding and pinned issuer verification, HWID/MAC binding, trial/expiry, KOD/hostguard/driver/name gates, VM threshold, encrypted bootstrap, local chain identity, provenance signing and pinned verification, memory hardening, loader self-checks, native-only fail-closed execution where selected, transformations, lowering, and `NX_SEAL_SHARD`-bound string keys.

`absolute-native-only` removes the Python fallback and exits 78 if the native object cannot load. `absolute` retains the sectioned/hybrid path and is the correct comparison variant for pack-layout behavior. They are variants within ABSOLUTE MAXIMUM, not separate tiers.

## Live CLI and environment inventory

Machine-readable inventories:

* `ABSOLUTE_MAXIMUM_RAW_RESULTS/live_inventory.json`
* `ABSOLUTE_MAXIMUM_RAW_RESULTS/inventory_classification.json`
* `ABSOLUTE_MAXIMUM_RAW_RESULTS/inventory_classification_summary.json`
* `ABSOLUTE_MAXIMUM_RAW_RESULTS/env_classification.json`

Live CLI inventory: 89 rows; 57 implemented, 18 partially implemented, 11 unsafe, 2 redundant, 1 parsed but unreachable. Seventeen parser flags were absent from the preserved reference document. Thirty-six documented standalone flags were absent as live standalone parser flags: 32 had no live parser implementation and 4 were represented as unified suboptions rather than standalone flags. The historical “15 undocumented flags” statement does not match the live tree.

Environment scan: 148 textual `NIXON`/`NX` names; 76 actual environment reads; 7 indirect/emitted references; 22 macro/generated-symbol references; 37 unclassified symbol references; 6 written/test-fixture-only names with no live read found. Classification counts: 49 implemented, 31 partially implemented, 18 documented but absent, 11 unsafe, 3 redundant, 2 inert, and 34 not environment variables. The historical “68 variables” statement does not match the live textual inventory because many matches are generated symbols or non-environment identifiers.

These counts are parser/textual/reachability classifications, not proof that every feature is runtime-active.

## Final strict build configuration

Exact argv and redacted environment are recorded in:

* `ABSOLUTE_MAXIMUM_RAW_RESULTS/builds/absolute-native-only/cipher/build_command.json`
* `ABSOLUTE_MAXIMUM_RAW_RESULTS/builds/absolute/cipher/build_command.json`
* `ABSOLUTE_MAXIMUM_BUILD_MANIFEST.json`

The native-only build uses `--skip-cloud --package native-only layers=0 zips=0 --no-section-split`; hybrid uses `--section-count 8 --package native layers=25 zips=3 stego`. Common controls include opt level 5, data/function-intent/speculation transforms, `string-key-env=NX_SEAL_SHARD`, trial 45 days, expiry, HWID lock, KOD, hostguard, driver check, name gate, internal renaming, MAC binding, VM threshold 65, env-only encrypted-bootstrap licence token with chain enforcement, and lowering `all`.

Strict dependency-lock build environment: `re-bench/build-venv/bin/python`, Python 3.13.5, Cython 3.0.12, requests 2.33.0, certifi 2026.11.20, charset-normalizer 3.5.3, idna 3.20, urllib3 2.8.0, cryptography 50.0.0, setuptools 84.2.1. `requirements.lock` SHA-256: `ec429dd371daf43bc8076090c00caea2c5ac1a110fd65d0145733d59aa4c82a6`.

## Static and dynamic binary evidence

Final native objects were extracted using legitimate secrets solely for authoritative analysis. Ghidra evidence is stored under `ABSOLUTE_MAXIMUM_RAW_RESULTS/ghidra_final_lowering/`. Dynamic traces and summaries are under `ABSOLUTE_MAXIMUM_RAW_RESULTS/dynamic_final_lowering/`. The old repeating-XOR validation for these exact artifacts is `native_final_lowering/old_attack_validation.json`, and direct-import boundary evidence is `native_final_lowering/direct_import_boundary.json`.

Static Ghidra observations establish recovered function boundaries, exports, and decompiled enforcement semantics. They do not by themselves prove resistance to a privileged customer-machine attacker.

## Cryptographic recovery finding and fix

Pre-fix artifact-only attack:

1. Parse `NATIVE_BLOBS['linux']` from the artifact.
2. XOR the first 32 ciphertext bytes with the predictable ELF header.
3. Use the result as a repeating key.
4. Reconstruct a byte-for-byte identical ELF (`cmp_rc=0`).

Post-fix state: packing uses `NXS1` magic, a deterministic nonce derived from key/plaintext/context, and a SHA-256 counter-mode keystream. The old repeating-XOR reconstruction no longer recovers the plaintext object. Validation for the final artifacts: `ABSOLUTE_MAXIMUM_RAW_RESULTS/crypto_validation/prefix_postfix_exact_artifact_known_plaintext.json` (older supporting validation is preserved in `native_final_lowering/old_attack_validation.json` and `crypto_validation/`). Regression: `tests/test_native_path_live.py::test_native_blob_packing_is_not_recoverable_by_repeating_xor_known_plaintext`.

This is evidence against the exact pre-fix known-plaintext procedure, not a proof that no attacker can recover the blob.

## Semantic-lowering integration correction

A late integration audit found that `--lowering` reached the Python/fallback path but was omitted from the small `_native_ast_opts` subset passed to `build_local_cython()`. As a result, earlier “post-lowering” artifacts did not actually apply lowering inside native blobs. The defect was fixed in `obfuscator/core/pipeline.py`; `tests/test_lowering.py` now includes a wiring regression. The final artifacts in this audit were rebuilt after that fix.

Final extraction evidence confirms lowering is active in the native object: `_nxk_len`/`nxk` strings are present, while the top-level `lowering_shim` module name is absent. This is not treated as proof of the complete design goal. The generated-native-kernel/per-build implementation-symbol separation remains only partially verified; visible public `_nxk_*` aliases are a residual information-leak/design limitation rather than evidence that lowering is absent.

## Performance measurements

Final native-lowering runtime overhead was measured with 7 valid-artifact runs per variant and 7 unprotected-source runs (`dynamic_final_lowering/summary.json`):

* unprotected source median: 14.592 ms;
* `absolute-native-only` median: 422.719 ms, about 28.97x;
* `absolute` median: 537.666 ms, about 36.85x.

The increase versus earlier non-native-lowering artifacts is expected because the native blob now actually receives the lowering pass. It is measured evidence, not a per-family cost model.

Lowering-shim family overhead was measured directly with 10,000 iterations and 5 repeats per operation (`performance/lowering_family_perf.json`; older 2,000x3 evidence is retained as `performance/lowering_perf.json`): 132 operations across 15 runtime families passed parity. Geometric-mean shim/plain ratios were: `bytes` 2.076, `container` 2.041, `dict` 1.765, `function` 2.097, `fusion` 2.687, `import` 2.129, `io` 1.517, `list` 2.442, `protocol` 2.264, `range` 1.982, `scalar` 2.336, `service` 2.008, `set` 1.886, `string` 2.648, `tuple` 3.798. The five opt-in node-kind families (`arithmetic`, `truth`, `slice`, `format`, `augassign`) have no runtime shim functions to time in the Phase-1 harness; their cost is included only in end-to-end artifact measurements, not in per-op microbenchmarks. These are Python-shim microbenchmarks, not claims about the native blob's per-instruction cost.

## EVM evidence

* Bridge: `re-bench/tools/evm_rpc_bridge.py`
* Backend: py-evm/eth-tester, chain ID `131277322940537`. Foundry/31337 was not substituted because the artifact and licence chain metadata are pinned to this implementation-specific chain ID; using 31337 would test a different configuration rather than the shipped enforcement path.
* Runtime contract: `0x51a240271AB8AB9f9a21C82d9a85396b704E164d`
* Customer: `0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF`
* Passed cases: unminted `ownerOf` reverts; non-owner mint reverts; owner mint succeeds; `ownerOf(1)` returns customer; double mint reverts; non-holder burn reverts; runtime instance ownership succeeds; burn then `ownerOf` reverts.

Loopback-only HTTP behavior was audited as a client-side transport control. Additional live local-EVM client negative tests all passed: wrong chain id rejected, unminted token error propagated, non-contract address fails closed, RPC connection failure fails closed, malformed contract rejected, non-loopback HTTP rejected, and `127.evil.com` rejected (`evm/client_chain_negative_tests.json`). The contract ABI exposes mint/burn/ownerOf but no transfer or separate revocation entry point; burn is the only revocation-like state transition tested. Transfer semantics and any richer revocation policy are licence-layer concerns rather than contract-entry-point tests in this implementation. Public-chain behavior remains untested.

## Regression tests and fixes

Focused current results already re-run after the latest fixes:

* `tests/test_native_path_live.py`, `tests/test_build_id.py`, `tests/test_pack_state.py`, `tests/test_section_split_wiring.py`: **23 passed, 1 skipped**.
* `tests/test_ai_findings_regressions.py`: **7 passed in 0.14 s** in the current source tree (`test_outputs/ai_findings_current_source_rerun.log`). This is source-level evidence only; the authoritative artifacts predate the operator-keyed decoy hardening.
* Final targeted security suite (`test_licensing.py`, `test_unified_flags.py`, `test_crypto_fallback.py`, `test_failure_modes.py`, `test_native_harden.py`, `test_loader_boundary.py`, `test_adversarial_security.py`): **210 passed, 2 skipped in 203.58 s**.
* Final chain transport/local HTTPS gate suite: **24 passed in 2.07 s**. This includes ordinary non-loopback HTTP rejection and lookalike loopback hostnames such as `127.evil.com`.
* `native/test_core_abi.py` initially failed against a stale `build/wb.so`; after rebuilding the current native library with `make wb`, it reports **7 passed, 5 subtests passed**.
* Final lowering/kernel suite (`test_lowering.py`, `test_lowering_parity_141.py`, `test_kernel_gen.py`, `test_kernel_fast.py`, `test_opcount_truth.py`): **183 passed in 31.33 s**.
* Lowering performance harness contract (`tests/test_lowering_perf.py`): **5 passed in 0.13 s**.
* Later-source operator-shard masking suite (`tests/test_operator_blob_key.py`, `tests/test_key_emit.py`): **19 passed in 0.79 s**; source-level only, not evidence about the authoritative artifact pair.
* Benchmark-harness regression suite (`tests/test_ai_benchmark_harness.py`): **38 passed in 0.55 s**. This covers immutable per-attempt sandbox bridge snapshots, model-separated endpoint-only socket exposure, read-only chain RPC filtering in the in-sandbox bridge and at the host-side EVM Unix socket, resume-watchdog attempt-number/priority selection, authorised zero-record free-lane rendering, provider reset-time parsing, Hy4 legitimate-secrets fail-closed behavior, exact and JSON-escaped MITM redaction, multiline-secret prefiltering in credential redaction, compatibility-relay redacting backend, sandbox MITM preference, copied-workspace redaction precedence, multiline and extra-root redaction policy, structural OpenCode-config secret-field classification, missing-workspace scorer handling, artifact-execution detection, legitimate-wrapper/stub separation, pre-supplied-native-evidence exclusion, embedded-ELF scanning, model-aware comparison paths, and enforcement of the 20-tool-call validity limit using unique preserved-event invocation counts.
* Full-repository testing: a single serial pytest run was stopped after several minutes at roughly 1% because it is impractically large in this tree. The bounded partition strategy subsequently completed every one of the 496 inventoried test files across nine disjoint partitions. Selected passing reruns total **30,745 passed, 9 skipped, 0 failed**; earlier rc137/resource-killed and runner-missing attempts are preserved rather than hidden. Aggregate evidence: `test_outputs/partitioned_full_suite_completion_summary.json` and `.md`. This is not a byte-frozen clean-checkout CI run because the tree remained concurrently modified, but it is no longer correct to describe the suite as partition-incomplete.

AI-CRYPTO-004 is therefore no longer an xfailed current-source test, but the authoritative artifacts still carry the old public derivation exposure. The exact artifact-specific confirmation is `crypto_validation/authoritative_artifact_honey_key_derivation_check.json` (reproducible with `re-bench/tools/validate_authoritative_honey_key_derivation.py`), and the boundary is documented in `ABSOLUTE_MAXIMUM_FINDINGS.md`.

Benchmark chain-isolation addendum: the raw host-side EVM Unix relay was replaced with `re-bench/tools/evm_readonly_unix_proxy.py` after audit showed that direct socket access could bypass the in-sandbox read-only bridge filter. The host-side socket now rejects state-changing JSON-RPC methods itself. Validation evidence is `ABSOLUTE_MAXIMUM_RAW_RESULTS/evm/evm_readonly_unix_proxy_validation.json`; the runtime licence token owner still matches the expected customer in `evm_owner_state_after_readonly_proxy.json`. Retrospective scans found no preserved direct `/run/absmax-tokenharbor/evm.sock` use, but the pre-hardening theoretical bypass is documented under AM-023 rather than hidden.

Benchmark endpoint-exposure addendum: earlier sandboxes also bind-mounted the whole host proxy operational directory, exposing read-only logs/PID/metadata files in addition to required Unix endpoints. No preserved evidence shows agents reading those files, and a targeted assessment found no hidden-secret or artifact-analysis terms in them. Nevertheless, the harness now exposes only hard-linked, model-appropriate endpoint socket inodes from `/home/nixon/absmax-sandbox-endpoints/opencode` or `/home/nixon/absmax-sandbox-endpoints/tokenharbor` under profile `credential-isolated-unshare-net-pid-v2-minimal-endpoints`. This also prevents one model lane from using the other provider as an oracle; validation is `ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/model_endpoint_separation_validation.json`. Both artifacts were re-executed successfully through both model-separated endpoint boundaries; evidence is `ABSOLUTE_MAXIMUM_RAW_RESULTS/evm/per_model_endpoint_runtime_smoke.json`. The theoretical pre-hardening exposure is documented as AM-028.

Benchmark validation-isolation addendum: independent hidden-vector validation formerly imported model-written `solution.py` on the host after otherwise isolated attempts. No host-path, network, or destructive-pattern exploitation was identified in a retrospective scan, but static scanning cannot retroactively prove benign execution. The harness now validates a copied candidate inside a fresh bubblewrap namespace with no network, isolated PID namespace, cleared environment, read-only candidate workspace, and no host repository/home bindings. Validation records use `execution_isolation='bubblewrap-unshare-net-pid-readonly-workspace'` on the corrected path. The pre-correction exposure and boundary are documented as AM-029; regression evidence is `test_outputs/benchmark_harness_regression.txt` (**38 passed**). Static scenario prompts were also corrected to state the pre-existing execution prohibition explicitly; under-specified pre-correction prompts and invalid executions are documented as AM-030.

## Outstanding-work register, rechecked live

* GitHub Actions: effective YAML parsing found 123 `uses` references: 107 external upstream references, all pinned to full 40-character commit SHAs, plus 16 local reusable workflow references. The apparent `actions/setup-example@v1` in `codeql.yml` is commented out and is not an effective use. Raw textual grep counts that included the comment were corrected; evidence is `github_actions_effective_uses.json`.
* Unvalidated AI score: not used for pass/fail selection.
* Strict xfail inventory: current AST scan of `tests/` finds zero xfail-marked tests; machine-readable evidence is `xfail_inventory.json`. This reflects later source fixes and does not retroactively harden the authoritative artifact pair.
* Authenticode public-CA trust: not tested.
* Developer ID signing and Apple notarisation: not tested.
* Windows strict shadow-stack enforcement: not tested on supported hardware.
* Production environment administration/release controls: external, not verified.
* Lowering-shim packaging for every target platform: not verified.
* Actual EVM testing: completed locally; public chain intentionally not tested.
* Complete live flag/environment inventory: completed at machine-readable parser/textual/reachability level; runtime activation of every feature remains partially verified.
* Full Ghidra/dynamic AI campaign: strict-artifact Ghidra and dynamic analysis completed; the AI matrix remains incomplete. The TokenHarbor paid/pass lane is quota-blocked and, after strict AM-027 rescoring, has only 1/332 strict valid attempts. The TokenHarbor free lane has zero records because it is quota-blocked before execution. The operator-authorised `opencode/hy4-flash-free` continuation matrix is active but in provider free-limit cooldown; at the latest checkpoint it had 166 records and 28 strict valid attempts, with 28/32 groups having any strict-valid attempt but 0/32 groups complete. The multi-lane watchdog is running, but no full-matrix claim is made.
* Targeted pre-fix AI comparison: not run because the provider quota was exhausted before it started; mechanical pre/post crypto validation is completed and preserved.
* Customer-machine attacker with legitimate secrets: confirmed practical boundary.
* Post-build operator-shard blob-key masking present in later concurrent source edits: not incorporated into the authoritative artifact pair. Focused source-level validation now passes (`tests/test_operator_blob_key.py` + `tests/test_key_emit.py`: **19 passed in 0.79 s**), proving the edited source can bind hybrid/native blob decryption to `NX_SEAL_SHARD`/`NX_TABLE_SHARD` without embedding those shards. It still requires a separate artifact rebuild, runtime verification, Ghidra/dynamic analysis, and benchmark before any stronger-current-source claim. Architecturally, if the customer machine must receive the same shard(s) for legitimate execution, this does not by itself solve the AM-001 customer-machine attacker boundary.
* Benchmark credential exposure (AM-018/AM-031): containment and redaction are complete, and the authoritative lane is credential-isolated, but operator rotation of the pre-containment exposed host/provider credentials remains required because remote provider transmission cannot be ruled out. AM-031 additionally found and locally redacted residual host/provider credential material in copied/generated OpenCode config evidence; local redaction cannot withdraw provider-side logs.

## Moving-source and reproducibility boundary

The authoritative artifact pair is hash-defined and was built at the time recorded in the manifest. After that build, a separate audit/remediation flow under `audit/2026-11-25` continued modifying the working tree, including `obfuscator/key_emit.py`, `obfuscator/core/pipeline.py`, tests, and `docs/MAXIMUM_SECURITY.md`. Those later edits include operator-held `NX_SEAL_SHARD`/`NX_TABLE_SHARD` blob-key masking that is **not** part of the authoritative artifact pair or the running AI matrix. They are preserved as external/concurrent work and were not reverted. Their focused unit/integration tests pass at source level, but no artifact built from that exact later source state has been benchmarked.

Consequently, the benchmark is valid for the exact artifact hashes above, but exact current-source reproducibility is only partially claimable: the repository was already dirty at baseline, no complete build-time source snapshot was captured, and the source later moved. The exact command, redacted environment, dependency lock, artifact bytes, and artifact hashes are preserved. Rebuilding from the current working tree may produce a different artifact and must not be mixed into this benchmark without a new artifact-identity boundary and a new campaign.

## Latest evidence post-processing checkpoint

The non-provider post-processing chain was rerun after the latest scoring/rendering corrections: copied-artifact repair, precision analysis, scoring, rendering, comparison rendering, credential redaction, secret scanning, and final verification all returned 0. Current outputs remain 498 records / 29 strict valid attempts, 0 pre-fix AI rows / 95 targeted post-fix rows, and zero credential hits in the strengthened evidence scan. That scan now covers raw results, live copied workspaces, OpenCode state, historical invalid-workspace/smoke roots, the copied OpenCode home, action-verification output, scratch evidence, and proxy operational logs (53,545 files at the latest checkpoint), tests 139 exact/JSON/base64/hex secret representations with multiline-aware prefiltering, and independently includes host/provider environment credential values. Its 1,207 representation-match files are classified expected non-credential content: 1,172 artifact/tampered-artifact copies, 15 runtime-licence fixture metadata files, 11 benchmark/OpenCode state evidence files, 8 build-command metadata files, and 1 stale build-manifest metadata file, all licence-HWID/signature-fixture categories rather than key material or provider credentials. The two runtime fixtures are invalid forged-licence negative-test inputs whose signatures are public verification artifacts while key material and nonce differ from the valid licence; they cannot authorise execution alone. Before correction, this broadened scan found residual host/provider credential material in copied/generated OpenCode config evidence (AM-031): one environment-matched host key plus structural Mistral/local-proxy keys and an organisation identifier. They were redacted locally; the structural config audit now reports 516 sensitive-field-bearing configs with zero literal sensitive values (497 intentional local-proxy dummy values, 95 redacted placeholders, 19 environment references), and the rerun reports no key material, nonce, full licence, seal shard, honey secret, customer mask, effective native key, or provider/host credential representation hit. Machine-readable evidence: `ABSOLUTE_MAXIMUM_RAW_RESULTS/final_verification_summary.json` and `secret_redaction_scan.json`; the final verification now explicitly reports `artifact_hash_pins_match=true` and `native_hash_pins_match=true` for the two authoritative artifact files and two extracted final native objects.

## Bottom line

The strict post-fix ABSOLUTE MAXIMUM artifacts are real, runnable, licence-bound, host-bound, chain-bound, provenance-pinned artifacts with measured fail-closed behavior and a corrected native-blob packing construction. They do not solve the customer-machine attacker boundary. Claims outside the measured Linux x86-64/local-EVM environment are not made.

Under the corrected strict validity rules, the TokenHarbor portion of the AI reverse-engineering benchmark is no longer representable as the earlier 58-valid-attempt result. Only **1/332** TokenHarbor records are strict valid: `absolute/privileged-debugger` attempt 3 scored 60 and recovered the artifact-public base key, but did not recover the NXS1 nonce, payload plaintext, exact hidden secret, or a passing independent implementation. The earlier 58-valid count was produced before AM-027 enforcement of the pre-registered 20-tool-call limit and is preserved only as historical scoring evidence.

The separate operator-authorised OpenCode `hy4-flash-free` continuation lane has **28/166** strict valid records at the current incomplete checkpoint. The most important strict valid result is `absolute/legitimate-runtime-secrets` attempt 4: score 78, exact fixture-secret appearance, payload-plaintext credit, and a `solution.py` passing all four independent hidden-vector validations. This reinforces, rather than creates, the AM-001 customer-machine attacker boundary because the attacker was intentionally given legitimate runtime licence/shard material; its `solution.py` references the scenario-supplied `extracted_linux.so` and `NX_SEAL_SHARD`, so the attempt demonstrates reuse of attacker-available native material rather than independent artifact-only extraction by the model. A second strict valid `absolute-native-only/legitimate-runtime-secrets` row (attempt 4, score 66) also contains exact fixture-secret/payload-plaintext credit but no independently passing implementation; like the hybrid row, its ELF evidence is scenario-supplied. The remaining strict valid Hy4 rows reconstruct substantial public artifact structure across static, dynamic, chain, provenance, loader, crypto, and secrets-withheld scenarios but do not recover the hidden secret or payload plaintext. No strict valid secrets-withheld attempt has recovered the hidden secret or payload plaintext. Across all strict valid attempts, payload ELF recovery excluding scenario-supplied native evidence is 0/29. The Hy4 matrix remains incomplete and cannot support a finished resistance conclusion in either direction.
Over-limit invalid attempts remain security-relevant raw attacker evidence but not valid benchmark coverage. Across 99 over-20-tool attempts, TokenHarbor recovered the artifact-public base key in 57/57 and correct NXS1 nonce in 40/57 without exact secret/payload/independent implementation recovery; Hy4 recovered the artifact-public base key in 34/42 and correct nonce in 20/42, with two exact fixture-secret appearances and one independent hidden-vector success in legitimate-runtime scenarios. All raw ELF hits in those over-limit rows were pre-supplied legitimate-runtime evidence and are excluded from artifact-only extraction credit. No over-limit attempt recovered payload ELF plaintext once supplied native evidence is excluded.
