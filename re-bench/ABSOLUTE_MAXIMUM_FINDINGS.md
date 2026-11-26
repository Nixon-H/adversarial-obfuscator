# ABSOLUTE MAXIMUM findings register

> **2026-11-27 status supersession:** benchmark status statements in this historical document may refer to incomplete Hy4/TokenHarbor/Kern lanes. The current completed diagnostic lane is `opencode-go/deepseek-v4.1-flash`: 114/114 active records structurally valid across 6 variants × 19 scenarios, one attempt per cell. Treat this document as historical context unless it explicitly cites the DeepSeek final report. Current status: `re-bench/ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md`.

Audit date: 2026-11-25/26. Severity reflects exploitability in the stated attacker model, not generic CVSS. Evidence is under `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/`.

## AM-001 — Customer-machine attacker can directly execute an extracted native payload

Status: **confirmed, unresolved architectural limitation**
Severity: **high** in the legitimate-runtime-secrets attacker model; not a secrets-withheld external-attacker result by itself

Evidence:

* The native object extracted with legitimate runtime secrets is a valid ELF64 shared object.
* Direct import without the seal shard fails closed (`string KEK unavailable`).
* Direct import with only `NX_SEAL_SHARD` executes and prints `SEALED 8771940273853809a401795ec7699cdc`, without licence, chain, host, or provenance enforcement.
* Final artifact evidence: `native_final_lowering/direct_import_boundary.json`; final extracted objects are under `native_final_lowering/*/linux.so`. Earlier strict dependency-lock evidence remains under `native/*/strict_dep_lock/`.

Root cause: enforcement is loader-mediated, while payload execution occurs in native-module initialisation. Once the object is extracted, the loader is outside the execution boundary.

Impact: a customer-machine attacker with legitimate runtime secrets can extract and execute/redistribute the payload with only the seal shard. Because the licence token carries static key material, chain burn/transfer or later licence revocation cannot rotate keys already used for extraction; loader-mediated chain failure does not protect an already extracted native object.

Remediation direction: move enforcement into native code and require an authenticated loader/native handshake before payload initialisation. A superficial environment-variable presence check would not be a fix.

## AM-002 — Artifact-only known-plaintext recovery of the pre-fix native blob

Status: **confirmed in pre-fix artifact; fixed and regression-tested in post-fix build**
Severity: **high** for secrets-withheld static analysis of the pre-fix native-only artifact

Pre-fix evidence:

* The pre-fix native blob was encrypted with repeating-key XOR.
* A valid x86-64 ELF has a predictable first 32 bytes. XORing those bytes with the ciphertext recovered the effective key:
  `<redacted-license-bound-effective-native-key>`.
* The reconstructed native object exactly matched the legitimately extracted object byte-for-byte: SHA-256 `76637eb7f1eb7bddbf12d8abb663f99478853ea42a87cc34968a5fd8d5070e93`; `cmp` returned 0.
* Raw evidence: `crypto_validation/known_plaintext_recovery.json` and `crypto_validation/known_plaintext_extracted_linux.so`.
* Exact-artifact validation was repeated against the preserved pre-fix comparison artifacts without any runtime secret (`crypto_validation/prefix_postfix_exact_artifact_known_plaintext.json`):
  * `absolute-native-only` pre-fix artifact SHA-256 `1b98683b749bec36b7d3016a18f471359bedc77493e33966cfb9912bdff69776`: the attack recovered an ELF with dynamic-symbol evidence for both exported payload/protection functions whose SHA-256 `76637eb7f1eb7bddbf12d8abb663f99478853ea42a87cc34968a5fd8d5070e93` exactly matches the legitimate extracted object.
  * `absolute` pre-fix artifact SHA-256 `c587cc56ec2a532b7b0ea4cb877c456fc65ce699d4b957445b2747d2ab68b0ff`: the same artifact-only attack recovered an ELF (`e6fe9a6148ca76fee31f46afd2b321982b47fed49519abfddf514612618c3d91`) with `readelf -h` success and dynamic-symbol evidence for both exported `PyInit_payload` and `nx_apply_protections` functions.
  * Recovered evidence files are preserved under `crypto_validation/prefix_exact_recovered/` because they are artifact-only recoverable and therefore not secret.

Root cause: repeating-key XOR makes known plaintext directly reveal key bytes. The ELF header is public and fixed, so licence key material was not necessary for static blob recovery even though it remained necessary for the ordinary loader path.

Fix implemented:

* Added `NXS1` stream-envelope packing in `obfuscator/core/utils.py`: magic, deterministic per-message nonce, and a SHA-256 counter-mode keystream.
* Updated hybrid and packed native/fallback packing paths in `obfuscator/core/pipeline.py`.
* Loader `_xor_decrypt` now opens `NXS1` envelopes and retains legacy repeating-XOR support only for backwards compatibility with old artifacts.
* Updated `re-bench/tools/extract_native_with_secrets.py` for both formats.

Post-fix validation:

* Post-fix native blobs begin `NXS1` and carry distinct nonces.
* Repeating the old attack only forces the first 32 bytes to look like an ELF header by construction; it does not reconstruct the actual plaintext. Exact-match validation is recorded in `crypto_validation/strict_dep_lock_known_plaintext_validation.json` and `crypto_validation/prefix_postfix_exact_artifact_known_plaintext.json`. For both final artifacts, neither offset-0 nor post-`NXS1`-header offset-20 reconstruction matches the actual extracted plaintext hash or contains the payload marker pair.
* Regression test: `tests/test_native_path_live.py::test_native_blob_packing_is_not_recoverable_by_repeating_xor_known_plaintext`.
* Post-fix artifacts execute successfully and fail closed as before.

Limit: this is still stdlib-only packing protection, not a substitute for authenticated encryption or a solution to the customer-machine attacker boundary.

## AM-003 — Geolocation/country gate creates network dependency and unreliable behavior

Status: **confirmed; excluded from final ABSOLUTE MAXIMUM configuration**
Severity: medium reliability/privacy weakness; low as a security boundary because the network adversary controls the signal

Evidence: an initial candidate using country restrictions caused outbound DNS/connect activity to public geolocation services and approximately ten seconds of runtime overhead. The implementation intentionally does not fail closed for block-only lists when location is unknown, because doing so kills offline customers.

Final decision: country/region restrictions were excluded. Post-fix valid-run strace shows zero inet/inet6 connect calls.

## AM-004 — EVM test harness initially misclassified reverted transactions

Status: **fixed in audit harness; regression evidence produced**
Severity: high test-integrity issue; no product impact after correction

Evidence: eth-tester transaction reverts can return receipts with `status=0` rather than raising. The bridge now checks receipt status. All eight local ERC-721 licence-contract tests passed on a real py-evm/eth-tester backend. No public-chain claim is made.

## AM-005 — OpenCode/free-provider instability limited AI benchmarking

Status: **confirmed measurement limitation**
Severity: benchmark blocker/invalid-attempt source

Evidence:

* OpenCode `opencode/hy4-flash-free` quota was exhausted before analysis (`provider.free-limit`, HTTP 429); those attempts are unavailability evidence only.
* Per operator policy the strict benchmark starts with `tokenharbor/deepseek-v4.1-flash:free`. The harness falls back to `tokenharbor/deepseek-v4.1-flash-1017` only when that free quota returns a free-limit/429 error; no other DeepSeek flash models are used.
* Earlier non-standalone or insufficiently isolated attempts were archived under `results_invalid_*` / `workspaces_invalid_*` and are not scored.
* The first matrix had to be interrupted because post-fix artifacts replaced the artifact files mid-campaign, making the run mixed-version. It is archived as `results_interrupted_mixed_artifact` / `workspaces_interrupted_mixed_artifact` and excluded from comparative scoring.

Provider failure, timeout, malformed output, or missing `answer.json` is never evidence of resistance.

## AM-006 — Strict-xfail protocol defects fixed in current source; authoritative artifacts still expose the old decoy-key derivation

Status: **source-level fixed; authoritative-artifact exposure remains open until a separately identified rebuild**

Fixed and unmarked after passing regression tests:

* malformed section-pack integer/framing handling;
* section-pack state digest verification;
* anti-rollback MAC verification and fail-closed writes;
* build-manifest signer fingerprint binding;
* atomic SQLite-backed replay ledger behavior;
* revocation rollback/high-water wiring;
* operator-keyed honey/decoy-key derivation (AI-CRYPTO-004 in the current source tree).

Current focused result: `tests/test_ai_findings_regressions.py`: **7 passed in 0.14s** (`ABSOLUTE_MAXIMUM_RAW_RESULTS/test_outputs/ai_findings_current_source_rerun.log`). No test in that file remains xfailed.

Artifact-specific boundary: the authoritative benchmark artifact pair predates the operator-keyed decoy hardening. Both artifacts still emit `_NX_HONEY_HINT`, and the pre-fix public derivation `sha256(b"nx-honey-decoy:" + build_id)` reproduces that hint in both variants. The derived key also passes the section-pack state/key checks and decompresses a plausible 2,012-byte Python decoy plaintext for each variant; it does not contain the real hidden secret:

* `absolute-native-only`: emitted hint `c9b35579a8e85f4d`, exact match; recovered decoy plaintext SHA-256 `48e63a707b1c6ba48057552d1463ec5265a7fd3e8e8896bd7df5cee4fbdf9a77`;
* `absolute`: emitted hint `f456c7daeba248f7`, exact match; recovered decoy plaintext SHA-256 `1deab89a1de5a899b63d5e040bb5795f3ea6812b7213d8a717822f3246f2eeda`.

Evidence: `ABSOLUTE_MAXIMUM_RAW_RESULTS/crypto_validation/authoritative_artifact_honey_key_derivation_check.json`. The current source keys the decoy with operator-held `NX_HONEY_SECRET` and omits the optional decoy when no suitable secret is configured, but no rebuilt artifact, runtime probe, static analysis, or AI benchmark yet exists for that later source state. Do not mix the current-source regression pass into the authoritative artifact benchmark; closing the artifact exposure requires a new artifact identity and campaign.

## AM-007 — GitHub Actions pinning rechecked: no effective unpinned upstream reference

Status: **corrected/closed after YAML-aware recheck**

Initial textual scanning counted a commented example line (`.github/workflows/codeql.yml:69`, `#   uses: actions/setup-example@v1`) as a live use. Effective YAML parsing found 123 `uses` references: 107 external upstream references, all pinned to full 40-character commit SHAs, plus 16 local reusable workflow references. Evidence: `github_actions_effective_uses.json`.

## AM-008 — Public/platform production trust properties remain unverified

Status: **not tested / blocked by external requirements**

Includes Authenticode public-CA trust, Apple Developer ID signing/notarisation, Windows strict shadow-stack enforcement on supported hardware, production release administration, and lowering-shim packaging on every target platform. Only Linux x86-64 local artifacts were built and measured.

## AM-009 — Benchmark harness initially omitted artifact identity and reused stale extracted-native evidence

Status: **fixed in audit harness**

The harness now records artifact SHA-256/size in every result and copies the variant-specific strict dependency-lock extracted native object when available. The mixed-version campaign was stopped and archived rather than scored.

## AM-010 — HTTPS licence-chain verification could use a stale CA bundle after unrelated urllib use

Status: **confirmed and fixed; regression evidence produced**
Severity: medium client-side verification reliability/security weakness

Evidence: running `tests/test_chain_transport_policy.py` before `tests/test_chain_gate_local.py` initially produced two certificate-verification failures even though the test fixture set `SSL_CERT_FILE`. Root cause: Python's module-level `urllib.request.urlopen` caches a global opener, so an earlier HTTPS request can fix the TLS context before a later CA-bundle configuration is applied.

Fix: `obfuscator/licensing.py::chain_owner_of` now builds a per-call HTTPS opener with a fresh `ssl.create_default_context()` instead of using module-level `urlopen` for HTTPS RPC calls.

Regression evidence: `tests/test_chain_transport_policy.py tests/test_chain_gate_local.py`: **24 passed** (`ABSOLUTE_MAXIMUM_RAW_RESULTS/test_outputs/chain_transport_postfix_fixed.txt`). The transport tests include ordinary HTTP rejection and lookalike-host cases such as `127.evil.com`.


## AM-011 — Build dependency lock initially drifted from the system Python environment

Status: **fixed for authoritative artifacts by strict lock-compliant rebuild**
Severity: medium supply-chain/reproducibility weakness

Evidence: the system environment initially had Cython 3.2.1 and requests 2.34.2 while the lock required Cython 3.0.12 and requests 2.33.0. Build logic now records drift and can fail closed with `NIXON_REQUIRE_DEP_LOCK=1`.

Authoritative strict artifacts were rebuilt using `re-bench/build-venv/bin/python` with locked versions: Cython 3.0.12, requests 2.33.0, certifi 2026.11.20, charset-normalizer 3.5.3, idna 3.20, urllib3 2.8.0, cryptography 50.0.0, setuptools 84.2.1. Strict artifact hashes are in `ABSOLUTE_MAXIMUM_BUILD_MANIFEST.json`.

## AM-012 — Native white-box ABI test failure was a stale build artifact, not current source behavior

Status: **confirmed; resolved by rebuilding the native test library**
Severity: medium test-validity/supply-chain hygiene issue; no evidence that the stale object affected the ABSOLUTE Python-native payload artifacts

Evidence: the initially tested `build/wb.so` dated 2026-11-13 predated native source changes. `native/test_core_abi.py` failed 5 tests, including missing `WBC_encrypt_ex`/`WBC_decrypt_ex` and C++ `std::length_error` crossing child-process ABI probes. Rebuilding with `make wb` produced a current `build/wb.so`; the same test now reports **7 passed, 5 subtests passed** (`test_outputs/native_core_abi_after_rebuild.txt`).

This is not claimed as proof that the white-box construction is cryptographically strong; it only establishes that the current native ABI source passes its regression contract when the correct artifact is built.

## AM-013 — `--lowering` was accepted but omitted from native builds

Status: **confirmed, fixed, rebuilt, and regression-tested**
Severity: **high integrity/implementation mismatch** because the strongest profile appeared to accept a protection that the shipped native blob did not receive

Evidence:

* `prepare_obfuscated_source()` supported lowering, and `--lowering` was parsed by the CLI, but the small `_native_ast_opts` dictionary passed to `build_local_cython()` omitted the key.
* Consequently, native compilation did not receive the requested lowering families even when the fallback/bytecode path did.
* The defect was found after artifacts that appeared to be “post-lowering” had already been built; those artifacts are preserved under `builds/*/cipher/post_lowering_native_unwired/` and are not authoritative.

Fix:

* `obfuscator/core/pipeline.py` now forwards `'lowering': str(getattr(args, 'lowering', '') or '')` in `_native_ast_opts`.
* `tests/test_lowering.py::test_native_build_option_subset_forwards_lowering` guards the wiring.
* The strict dependency-lock artifacts were rebuilt after the fix.

Post-fix verification:

* `tests/test_lowering.py`: 9 passed in the focused wiring run; the final combined lowering/kernel suite reports 183 passed.
* Final artifacts are `28630cc945e883151761b4752db1d9a7e59a7dbb29bc9e93b381e75ba2898032` (`absolute-native-only`) and `5382e72af5cce267fa2ec0379b6c3910b0bc33f7ac645a5ad2c88bc011ce0fbe` (`absolute`).
* Final extracted native objects contain `_nxk_len`/`nxk` strings and do not contain the top-level `lowering_shim` module name.

Residual limitation: visible public `_nxk_*` aliases remain in the extracted native object. The per-build implementation-symbol/native-kernel separation described by the design is therefore only partially verified. This does not negate the wiring fix, but it is not evidence of perfect semantic hiding.

## AM-014 — Final-matrix first launch was invalid as a benchmark because provider retry behavior hid quota exhaustion

Status: **confirmed benchmark-methodology issue; corrected before scoring**
Severity: high for benchmark validity; no product-security impact

Evidence:

* `opencode/hy4-flash-free` immediately returned `provider.free-limit`/HTTP 429.
* `tokenharbor/deepseek-v4.1-flash:free` returned `provider.rate-limit`/`free_tier_limit_reached`/HTTP 429, but OpenCode scheduled an internal retry minutes later instead of exiting. The harness timeout would therefore produce timeouts rather than reaching the authorized 1017 fallback.
* The first final-matrix launch was stopped before any TokenHarbor result completed. Its 10 invalid hy4/free-limit records are archived as `results_final_aborted_free_retry` and are not scored.

Correction:

* Because both free lanes were already proven exhausted, the authoritative matrix was restarted directly with the operator-authorized `tokenharbor/deepseek-v4.1-flash-1017` fallback.
* No other DeepSeek Flash model was substituted.


## AM-015 — Benchmark workspaces initially received pre-extracted native plaintext in secrets-withheld scenarios

Status: **confirmed benchmark-methodology defect; corrected before final scoring**
Severity: high for benchmark validity; no product-security impact

Evidence: several secrets-withheld scenarios, including `runtime-secrets-withheld`, `native-module-extraction`, `ghidra-static`, and `semantics-hidden-vectors`, copied `extracted_linux.so` and a Ghidra probe into the agent workspace. That evidence was produced using legitimate licence key material. Supplying it to a secrets-withheld attacker would circularly bypass the extraction/key-derivation boundary being measured and would conflate the essential secrets-available and secrets-withheld attacker models.

Correction: `re-bench/tools/ai_bench.py` now withholds pre-extracted native plaintext and precomputed Ghidra reports from all secrets-withheld scenarios. Agents may use Ghidra or other tools on artifacts they can lawfully materialize inside the workspace. Only the legitimate-runtime-secrets scenario receives pre-extracted native evidence as a customer-machine attacker convenience. The four binary-only results completed before this correction are archived as `results_archived_pre_evidence_boundary_fix` and excluded from the authoritative matrix; the full matrix is rerun cleanly.

## AM-016 — Scoring harness required two validity/calibration corrections

Status: **corrected before final scoring**
Severity: medium benchmark-methodology issue; no product-security impact

Corrections made in `re-bench/tools/score_ai_benchmark.py` before final aggregation:

* `answer.json` must parse as JSON and contain all required top-level keys. A syntactically valid but incomplete answer is malformed, not a valid reverse-engineering attempt.
* The unsupported-secret-claim penalty no longer triggers on accurate negative statements such as “secret unrecovered” or “key material withheld.” It is limited to positive recovered-secret claims not independently confirmed.
* Scenarios that prohibit execution cannot earn the dynamic-execution subscore merely by paraphrasing loader exit paths; they remain able to earn static platform-protection and host-gate identification credit.
* Payload/crypto credit was recalibrated after inspection showed that every early valid attempt reached the maximum merely by naming the format. The final scorer reserves three payload/crypto points for independently observed payload plaintext recovery and two points for exact artifact-public base-key recovery validated against the artifact. Merely naming `NXS1`, Shamir, or licence-mask mechanics is therefore not scored as full cryptographic recovery.
* Required answer-key names are no longer treated as evidence. The scorer flattens answer values only, so the mere presence of required keys such as `licence_chain`, `native_blob`, `provenance`, or `evidence` cannot satisfy keyword checks.
* Dynamic execution evidence recognizes `run_valid.sh` invoked directly or through `sh`/`bash`, but only when the observable OpenCode shell-event log contains the execution command and corroborating valid-sealed or fail-closed output.
* The secrets-withheld `run_valid.sh` stub is not counted as artifact execution; only the real legitimate-secrets wrapper that execs `artifact.py` counts. Merely observing the valid output vector is not payload-plaintext recovery. Pre-supplied `extracted_linux.so` evidence in legitimate-runtime-secrets workspaces is excluded from extraction-recovery credit because the harness provided it.

These corrections do not change the artifact, prompt, tool access, hidden vectors, or independent `solution.py` execution. All raw attempts are rescored under the same final scorer; raw results remain recalculable. The remaining reconstruction dimensions still use transparent keyword/structure checks and must be interpreted as reconstruction-content measurements, not as standalone proof of exploitation.

## AM-017 — Twelve-way provider parallelism caused mass timeouts and was reverted

Status: **confirmed benchmark-execution limitation; corrected before final scoring**
Severity: medium benchmark-validity/performance issue; no product-security impact

A variant-sharded experiment running 12 concurrent OpenCode invocations caused the first batch to hit the 360-second timeout en masse, including otherwise simple binary-only scenarios. Thirteen invalid records and copied workspaces were archived as `results_invalid_parallel12_experiment` and `workspaces_invalid_parallel12_experiment`, then excluded from authoritative scoring. The benchmark was reverted to six total concurrent invocations (two variant shards with three workers each), matching the concurrency level that had already produced completed valid attempts. Parallelism is an execution parameter only; artifact content, prompts, scenario inputs, and scoring conditions are unchanged.

## AM-018 — Benchmark sandbox initially inherited host/provider credential environment variables

Status: **confirmed benchmark-infrastructure vulnerability; stopped, archived, redacted, and corrected before authoritative scoring**
Severity: **critical credential-handling failure** for benchmark infrastructure; no evidence of a product artifact weakness

Evidence:

* The first corrected final-matrix harness invoked bubblewrap without scrubbing the parent environment. As a result, agent shell commands inherited host/provider variables such as API keys and authentication tokens.
* Observable `opencode.events.jsonl` records showed that some agents ran `env`-like commands and could see credential variable names and values inside the sandbox. The harness also copied the operator's full OpenCode configuration into the sandbox state; that configuration contained credential material or credential references outside the nominal workspace boundary.
* Because tool output is part of model context, any credential values printed by agents must be treated as potentially transmitted to the remote model provider. Exact values are not reproduced in this register.

Immediate containment:

1. The running campaign was stopped before completion.
2. Thirty-eight raw attempt records and their copied workspaces were archived under `ai_benchmark/archived_credential_env_exposure_20261125T202432Z/` and are permanently excluded from scoring.
3. Exact-match redaction was applied across the archived evidence, live benchmark workspaces, and per-attempt OpenCode state for 17 sensitive environment variables. `credential_redaction_report.json` records 121 files changed and subsequent verification found zero exact matches for those values outside byte-identical `artifact.py` copies.
4. No exact host environment credential was found in `artifact.py` copies.

Correction:

* `re-bench/tools/ai_bench.py` no longer copies the operator's full OpenCode configuration. It generates a minimal TokenHarbor-only configuration.
* The sandbox now runs with `--unshare-net` and `--unshare-pid` and a scrubbed environment containing only `PATH`, `HOME`, `USER`, `LOGNAME`, locale, `TMPDIR`, and `PYTHONUNBUFFERED`.
* A host-side Unix-socket proxy (`re-bench/tools/tokenharbor_unix_proxy.py`) holds the TokenHarbor credential outside the sandbox and accepts only the authorized `deepseek-v4.1-flash-1017` model. Inside the sandbox, `re-bench/tools/sandbox_tokenharbor_bridge.py` exposes only a loopback bridge to that Unix proxy.
* A second Unix-socket endpoint exposes the local py-evm endpoint at loopback port 8545 so licence-chain execution remains possible without general network access; after AM-023 hardening that endpoint is itself a read-only filtering proxy rather than a raw relay.
* Smoke validation confirmed: model bridge status 200; EVM bridge status 200; no sensitive environment names inside the sandbox; external network connection attempts fail with `OSError`.
* Initially corrected attempts record `sandbox_profile=credential-isolated-unshare-net-pid-v1`; after AM-028 endpoint minimisation, new attempts record `credential-isolated-unshare-net-pid-v2-minimal-endpoints`. The scorer treats any detected host-credential leak as structurally invalid.

Residual requirement: because the pre-containment agents may have transmitted printed environment values to the remote model provider as tool output, the exposed credentials should be rotated by the operator. This audit cannot rotate those credentials. Continued use of the current TokenHarbor key is limited to the host-side proxy until rotation occurs.

AM-018 addendum: after the credential-isolated lane was validated, the host-side proxy was additionally upgraded to redact exact benchmark runtime-licence material, licence key material/nonce/HWID, and `NX_SEAL_SHARD` values from provider-bound requests and provider responses before forwarding. This prevents the remote model provider from receiving those test secrets even if a legitimate-secrets agent prints them into tool output. The proxy logs only redaction counts, not values. The upgrade was deployed by zero-downtime Unix-socket replacement; the pre-redaction proxy process was then killed. The redacting proxy passed a live `deepseek-v4.1-flash-1017` smoke request with upstream status 200.

AM-018 second addendum: before the legitimate-runtime-scenarios portion of the matrix, the proxy was further upgraded to compute and redact licence-derived customer masks and effective native-blob keys in hex, uppercase-hex, and base64 forms. This closes the derived-secret bypass in which an agent could transform the provided licence material and print a derivative that exact literal redaction would miss. The upgrade was deployed by renaming the old Unix socket, starting the patched proxy on the authoritative socket, waiting until the old process had no active worker threads, and then terminating it. Model-listing validation returned HTTP 200, subsequent upstream chat completions returned HTTP 200, and no proxy-error records were observed in the restart validation window. Post-completion evidence redaction was also extended to the same derived values without storing them.

## AM-019 — Licence-bound effective native-key material was initially preserved in audit evidence

Status: **confirmed evidence-handling defect; corrected by exact-match redaction**
Severity: high evidence-handling issue for the old licence-bound build; no evidence that the current licence key was exposed

During review of the crypto validation evidence, the audit found that `crypto_validation/known_plaintext_recovery.json` and several archived invalid benchmark workspaces contained the full licence-bound effective native-blob key in hexadecimal form. That value is not merely an artifact-public share: it incorporates licence customer key material and therefore must not be preserved as reusable audit evidence, even though the pre-fix repeating-XOR weakness already made the old native blob recoverable artifact-only.

Correction performed:

* Exact-match redaction of both the corrected and initially miscalculated effective-key hex values across `re-bench/`, excluding byte-identical `artifact.py` copies.
* Seventeen files changed; verification found zero remaining exact matches.
* Only SHA-256 fingerprints of the redacted values are retained in `ABSOLUTE_MAXIMUM_RAW_RESULTS/crypto_key_redaction_report.json`.
* Artifact-public base shares remain visible in invalid benchmark evidence because they are part of the attacker-visible artifact and are necessary to evaluate what agents reconstructed; they do not include the licence customer mask.

Residual interpretation: redaction does not undo any provider transmission that occurred in the invalid pre-isolation campaigns. Those campaigns remain excluded. The current authoritative lane uses the redacting host-side proxy, so exact runtime licence/key/shard values are not forwarded to the provider even if printed by an agent.

## AM-020 — Copied benchmark artifact evidence was redacted instead of remaining byte-identical

Status: **confirmed benchmark-evidence defect; corrected for preserved copies and post-processing**
Severity: medium evidence-integrity issue; no effect on what the agents analyzed live

Review of the copied workspaces showed that `sanitize_copied_workspace()` redacted the licence-bound HWID string inside copied `artifact.py` files. The live agent workspaces received the correct byte-identical artifact before sanitisation, so model behavior and result validity were not affected. However, the preserved copies no longer matched the SHA-256 recorded in the result metadata, violating the benchmark requirement that artifact versions remain identical and independently re-analysable.

Correction performed:

* `ai_bench.py` now exempts `artifact.py` from all copied-workspace redaction. The artifact is attacker-visible input; any HWID embedded in it is part of that input rather than a separate runtime secret.
* Added `re-bench/tools/repair_copied_artifacts.py`, which restores each copied `artifact.py` from the exact artifact source matching the result-recorded SHA-256 and verifies the repaired hash.
* Initial repair covered 28 copied artifacts, changed 28, and ended with zero mismatches or errors; evidence is `ABSOLUTE_MAXIMUM_RAW_RESULTS/copied_artifact_repair_report.json`.
* Post-completion processing now reruns the repair before precision analysis and redaction because the already-running shard processes use the earlier harness code.

Interpretation: runtime licence files, seal shards, licence key material, customer masks, and derived effective keys remain redacted from non-artifact evidence. The artifact itself must remain byte-identical even though it contains attacker-visible build/host binding metadata.

## AM-021 — Authoritative artifacts predate later concurrent source hardening; exact current-source reproducibility is limited

Status: **confirmed reproducibility/scope limitation; benchmark evidence remains valid only for the hash-defined artifact pair**
Severity: medium audit-scope limitation; no evidence of benchmark-artifact tampering

Evidence:

* The authoritative artifact hashes and build-time manifest are fixed and all authoritative benchmark result records match those hashes.
* After the build, concurrent audit/remediation work under `audit/2026-11-25` modified source/tests/docs, including `obfuscator/key_emit.py`, `obfuscator/core/pipeline.py`, `tests/test_native_path_live.py`, and `docs/MAXIMUM_SECURITY.md`.
* The later source includes operator-held `NX_SEAL_SHARD`/`NX_TABLE_SHARD` blob-key masking that was not present in the authoritative artifact build.
* The repository was already extensively dirty at baseline, and no complete build-time source snapshot was captured.

Impact:

* The benchmark measures the exact hash-defined artifact pair, not the later working-tree source.
* The exact command, dependency lock, artifact bytes, hashes, runtime behavior, and benchmark evidence are reproducible as evidence, but rebuilding the same bytes from the current working tree is not guaranteed.
* Any rebuild incorporating operator-shard blob-key masking requires a new artifact-identity boundary and new benchmark campaign before stronger-current-source claims can be made.

Constraints:

* The concurrent work was preserved and not reverted, as required.
* No artifact rebuild or replacement is performed while the authoritative benchmark is active.

## AM-022 — Live sandbox bridge source mutation invalidated 90 initial benchmark jobs before model invocation

Status: **confirmed benchmark-infrastructure defect; fixed and regression-tested**
Severity: high for benchmark validity; no product-security impact

Evidence:

* During the authoritative credential-isolated matrix, `re-bench/tools/sandbox_tokenharbor_bridge.py` was edited while initial jobs were still being launched. The first edit transiently left a Python `SyntaxError` in the live source file.
* Because bubblewrap bound that live source file directly into each new sandbox, 90 initial jobs exited in about 0.03 seconds before OpenCode or the model started. Their stderr contains the bridge `SyntaxError`; their result records contain no answer and no provider response.
* These records are invalid infrastructure evidence only. They are not timeouts, model failures, or artifact resistance.

Correction:

* `re-bench/tools/ai_bench.py` now copies an immutable per-attempt bridge snapshot into the per-attempt OpenCode state directory and bind-mounts that snapshot as `/opt/sandbox_tokenharbor_bridge.py`.
* Results now include `harness_error` when the bridge fails before model invocation.
* `re-bench/tools/score_ai_benchmark.py` classifies these records as `harness-bridge-syntax-error` rather than generic missing-answer failures.
* Regression coverage: `tests/test_ai_benchmark_harness.py::test_bridge_snapshot_is_per_attempt_copy`; result `2 passed` for the new harness regression file.

Residual impact: the 90 affected initial jobs were not rerun because the authorised provider quota was exhausted before the infrastructure defect was fully reconciled. They remain missing evidence, not successful resistance.

## AM-023 — Shared local EVM endpoint initially permitted state-changing RPCs inside concurrent agent sandboxes

Status: **confirmed benchmark-design risk; corrected before any chain-scenario model execution**
Severity: medium benchmark-validity risk; no product-security impact

Evidence:

* The credential-isolated sandbox exposes the local py-evm chain through a loopback Unix relay so licence validation can execute without external networking.
* The first version of the in-sandbox bridge relayed JSON-RPC traffic without method filtering. A chain-focused agent could therefore have attempted `eth_sendTransaction`/`eth_sendRawTransaction` and mutated shared chain state, potentially contaminating concurrent attempts.
* Observable workspace scans found no `eth_sendTransaction`, `eth_sendRawTransaction`, `mint(`, or `burn(` use before the correction. No chain-state contamination was identified.

Correction:

* `re-bench/tools/sandbox_tokenharbor_bridge.py` now permits only read-only JSON-RPC methods needed for chain inspection and licence validation, including `eth_call`, `eth_chainId`, block/transaction/code/balance queries, gas estimation, and sync status.
* State-changing methods receive a JSON-RPC error and HTTP 403 inside agent sandboxes. Contract mint/burn/revocation behavior remains covered by the independent local-EVM test harness rather than by concurrent agents mutating the shared chain.
* Regression coverage: `tests/test_ai_benchmark_harness.py::test_agent_chain_bridge_is_read_only`.
* Manual bridge validation after the correction returned HTTP 200 for `eth_chainId` and `eth_blockNumber`, and HTTP 403 for `eth_sendTransaction`.

Post-correction containment addendum (2026-11-26): a later infrastructure audit found that the raw host-side `evm.sock` relay itself was still visible inside the sandbox filesystem namespace. Agents therefore could have bypassed the in-sandbox loopback filter by opening the Unix socket directly, even though no preserved event log referenced that socket path. The raw relay has now been replaced by `re-bench/tools/evm_readonly_unix_proxy.py`, which enforces the same read-only JSON-RPC allowlist at the host-side Unix socket boundary. Live validation evidence is `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/evm/evm_readonly_unix_proxy_validation.json`: `eth_chainId` returned HTTP 200 with a result, `eth_sendTransaction` and `eth_sendRawTransaction` returned HTTP 403 / JSON-RPC `-32601`, and the block number remained unchanged after the blocked write attempts. Regression coverage now includes `tests/test_ai_benchmark_harness.py::test_host_evm_unix_proxy_enforces_read_only_at_socket`.

Retrospective preserved-evidence scan after this hardening found zero references to `/run/absmax-tokenharbor/evm.sock` in benchmark evidence. Two Hy4 agents did probe `eth_sendTransaction` or related state-changing methods through the filtered loopback endpoint; both received HTTP 403 and did not mutate the chain. A subsequent `ownerOf(1)` query against the runtime licence contract still returned the expected customer address, recorded in `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/evm/evm_owner_state_after_readonly_proxy.json`. Because direct-socket access was technically possible before hardening, this remains a containment correction rather than proof that no bypass was theoretically possible; no preserved evidence indicates actual chain contamination.

Impact boundary: no valid chain-scenario benchmark attempts exist in the current partial matrix, so this correction has no measured effect on benchmark scores. It is a preventive validity control for any resumed run.

## AM-024 — Authoritative benchmark matrix is incomplete because authorised provider quota was exhausted

Status: **external benchmark blocker; partial results preserved exactly and not overstated**
Severity: high for benchmark completeness; no product-security impact and no resistance inference

Final reconciliation of the 290 preserved result records:

* 58 structurally valid scored attempts, all from the initial 160-job matrix.
* 90 `harness-bridge-syntax-error` records (AM-022), all initial jobs that never reached the model.
* 134 `provider-quota-exhausted` records: 4 initial and all 130 supplemental jobs.
* 7 timeout records.
* 1 static-scenario execution-policy violation.

The TokenHarbor `deepseek-v4.1-flash-1017` lane returned `provider.quota` / `plan_allowance_exhausted` with HTTP 402. The already-probed `opencode/hy4-flash-free` lane remained limited by `provider.free-limit`/HTTP 429, and the TokenHarbor free lane had already been exhausted. Per the operator policy, no other DeepSeek Flash model was substituted.

Coverage consequence:

* Only 6 of 32 variant/scenario/model groups meet the target of five valid attempts.
* 14 of 32 groups have at least one valid attempt.
* 18 of 32 groups have zero valid attempts, including the essential `legitimate-runtime-secrets`, `runtime-secrets-withheld`, `crypto-construction`, `chain-licence-path`, `provenance-signatures`, `host-runtime-gates`, `pack-layout-sections`, `loader-initialization-order`, and `semantics-hidden-vectors` groups.
* The targeted pre-fix AI comparison did not start; zero pre-fix rows means missing evidence, not resistance.

Supplementation was stopped deliberately after quota exhaustion because every supplemental job was failing before model invocation and generating only invalid evidence. The exact blocker is external quota availability. The benchmark cannot be represented as complete until the deficient groups are rerun under the same artifact hashes and evidence boundaries.

## AM-025 — Initial Hy4 legitimate-runtime-secrets probe used opaque TLS before redacting-proxy containment

Status: **confirmed benchmark-infrastructure secret-transmission incident; contained; replacement redacting lane validated**
Severity: high for benchmark fixture-secret confidentiality; no host/provider credential exposure identified; no valid benchmark evidence produced

Evidence:

* Before the OpenCode Hy4 lane had a TLS-terminating redaction path, a manual `legitimate-runtime-secrets` smoke attempt was launched through an opaque HTTPS `CONNECT` tunnel.
* The sandbox itself still had no host/provider API credentials and no general network access, but the remote model request stream could include exact runtime fixture material printed into tool output because the tunnel was opaque to the host-side redactor.
* The attempt was terminated before completion. It produced no valid `answer.json`, no passing `solution.py`, and no countable benchmark attempt.
* Exact-match local evidence assessment found licence key material twice, licence nonce six times, licence HWID eight times, and `NX_SEAL_SHARD` twice in the generated OpenCode event log. Those counts are evidence that the values entered model request/response history; because the TLS tunnel was opaque at that time, the pre-containment transmissions must be treated as provider-visible.
* The generated event log was redacted locally. Redacted generated-output evidence, without recopying the input secret fixture files, is preserved under `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/archived_hy4_unredacted_tls_attempt11_20261125T2257Z/`; assessments are under `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/hy4_legitimate_secret_exposure_*.json`.

Correction and validation:

* Added `re-bench/tools/opencode_mitm_addon.py`, a host-side mitmproxy addon that allows only `opencode.ai` and `models.opencode.ai` and exact-match-redacts runtime licence material, licence key material/nonce/HWID, seal shard, licence-derived customer mask, effective native key, encoded hex/base64 variants, and host/provider credential values before upstream transmission. It logs counts and metadata only, never secret values.
* The dedicated mitmproxy CA private key remains outside the benchmark sandbox boundary. Only the public CA certificate/combined bundle is visible inside sandboxes.
* Upgraded `re-bench/tools/opencode_connect_relay.py` so even already-running sandbox bridge snapshots that use the compatibility relay now synthesize their `CONNECT` through the redacting MITM proxy rather than creating opaque direct TLS tunnels.
* Updated `re-bench/tools/sandbox_tokenharbor_bridge.py` and `re-bench/tools/ai_bench.py` so new Hy4 sandboxes use the redacting MITM socket when available, use the combined CA bundle, remain network-namespace isolated, and do not require user-namespace root or port-443 capability experiments.
* Added a fail-closed guard in `ai_bench.py`: Hy4 `legitimate-runtime-secrets` attempts are not started unless `/home/nixon/absmax-tokenharbor-proxy/opencode-mitm.ready` exists. If the MITM path is unavailable, HTTPS egress fails closed rather than falling back to general networking.
* Certificate validation through the proxy succeeded with `ssl_verify_result=0`. A non-sensitive canary was redacted exactly once before upstream transmission. Live inference requests then showed exact-match redaction of licence key material, nonce, HWID, seal shard, and effective native key. Machine-readable counts are in `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/opencode_mitm_validation.json`; at the validation checkpoint there were 212 proxied requests and zero blocked-host entries, with redaction counts including 116 key-material, 101 nonce, 111 seal-shard, and 15 effective-native-key replacements.

Residual impact:

* The pre-containment fixture licence/seal material must be treated as disclosed to the OpenCode inference provider. These values must not be reused as production secrets. If they correspond to anything outside the benchmark fixture boundary, the operator must rotate/reissue them and rebuild affected artifacts; the agent cannot perform that rotation.
* Redaction changes what the remote model receives even though the local sandbox tool output contains the original values. This is deliberate confidentiality enforcement, but it means Hy4 legitimate-runtime results measure model performance under a redacted-remote-context boundary. They must not be compared one-to-one with an unredacted lane.
* The incident invalidates only the terminated pre-containment smoke attempt. It does not invalidate later attempts that used the validated redacting MITM lane.

## AM-026 — JSON-escaped licence representations and licence signatures were initially outside exact redaction coverage

Status: **confirmed redaction-coverage gap; corrected, validated, and locally re-redacted**
Severity: high for fixture-licence confidentiality defence-in-depth; key material/nonce/shard were already redacted, but licence signatures must be treated as provider-visible for pre-correction Hy4 traffic

Evidence:

* The first redacting MITM implementation matched exact raw runtime-licence text, individual key material/nonce/HWID fields, seal shard, customer masks, effective native keys, and simple encoded variants.
* OpenCode event payloads are JSONL. A licence file embedded in tool output is JSON-escaped rather than byte-identical to the raw file, so the raw full-licence literal did not match nested tool output.
* The licence top-level signature field was not initially included as a separate redacted value. Pre-correction copied Hy4 legitimate-runtime evidence contained exact licence-signature matches: 10 occurrences in two files for `absolute-native-only` and 8 occurrences in three files for `absolute` at the measurement checkpoint.
* Because model providers receive tool output as part of inference requests, pre-correction licence signatures and non-redacted licence metadata must conservatively be treated as provider-visible. Exact key material, nonce, seal shard, customer masks, and effective keys were already redacted by the earlier lane; this finding does not imply that those already-redacted values were transmitted after the first MITM containment.

Correction and validation:

* `re-bench/tools/redact_benchmark_credentials.py` now expands secrets into exact literal, JSON-escaped, hexadecimal, and base64 representations without logging values, and includes the licence signature as `licence-sig`.
* `re-bench/tools/opencode_mitm_addon.py` uses the expanded representation set. At validation it carried 139 exact representations. In-memory validation confirmed that nested JSON-escaped runtime-licence output and the licence signature are redacted; no values were written. Evidence: `ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/opencode_mitm_expanded_redaction_validation.json`.
* The MITM process was restarted as PID 2057476 so the expanded addon is active. `/home/nixon/absmax-tokenharbor-proxy/opencode-mitm.ready` records the validation and restart metadata.
* `re-bench/tools/ai_bench.py` copied-workspace sanitisation now applies the same expanded representations and preserves the runtime-licence replacement label rather than overwriting it with a less-specific derived label.
* Existing copied evidence, live workspaces, and per-attempt OpenCode state were re-redacted. Machine-readable reports: `expanded_secret_redaction_targeted_report.json`, `expanded_secret_redaction_live_state_report.json`, and `expanded_secret_representation_scan.json` under `ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/`.
* The post-redaction scan found zero exact or expanded secret-representation matches outside byte-identical `artifact.py` copies in the copied workspaces, live workspaces, and OpenCode state roots. `artifact.py` is intentionally excluded because it is attacker-visible input and must remain byte-identical.
* Regression coverage: `tests/test_ai_benchmark_harness.py::test_copied_workspace_redacts_json_escaped_licence_and_signature`; current harness regression suite result is `38 passed`.
* Latest independent scan hardening: `re-bench/tools/scan_secret_redaction.py` now scans the raw-results root, live copied workspaces, OpenCode state, historical invalid/smoke workspace roots, copied OpenCode home, action-verification output, scratch evidence, and proxy operational logs (53,545 files at the latest checkpoint) against 139 exact/JSON/base64/hex representations, including host/provider environment credential values. The ripgrep fixed-string prefilter is multiline-aware, and regression coverage verifies that a multiline test secret is prefetched and matched only as a complete value. This broadened scan found the separate copied-OpenCode-home credential residual documented as AM-031; after redaction the latest result is zero credential hits. Expected non-credential matches are licence-HWID host-binding metadata in artifact/build/benchmark-state metadata and the two invalid forged-licence runtime fixtures. Those forged fixtures reuse a public signature but have different key material and nonce, cannot authorise execution alone, and are retained as negative-test evidence. Evidence: `ABSOLUTE_MAXIMUM_RAW_RESULTS/secret_redaction_scan.json`.
* Regression coverage also includes `tests/test_ai_benchmark_harness.py::test_secret_candidate_prefilter_supports_multiline_values`.

Residual impact:

* Pre-correction licence signatures cannot be withdrawn from any provider-side logs. They are benchmark fixture material and must not be reused as production secrets. If they protect anything outside the benchmark fixture boundary, the operator must rotate/reissue them and rebuild affected artifacts.
* The current lane is validated after correction. Later attempts use the expanded redaction set, but all pre-correction traffic remains conservatively disclosed.

## AM-027 — The pre-registered 20-tool-call benchmark limit was not enforced by the initial scorer

Status: **confirmed benchmark-methodology defect; scorer corrected; prior valid-attempt counts downgraded**
Severity: high for benchmark validity and comparability; no product-security impact

Evidence:

* The benchmark prompt instructs agents to use at most 20 tool calls and then write `answer.json` even if partial.
* The initial harness recorded `tool_event_count` but did not treat over-limit runs as invalid. Event inspection showed unique `tool_use` identifiers, so the count is a real count of tool invocations rather than duplicated start/end events.
* Strict recalculation with the corrected scorer shows the impact:
  * TokenHarbor lane: 332 records, only 1 strict structurally valid attempt; 57 otherwise relevant attempts are now classified as `tool-call-limit-exceeded`, alongside 176 provider-quota records, 90 bridge-syntax infrastructure records, 7 timeouts, and 1 static-policy violation.
  * Initial Hy4 strict checkpoint: 118 records, 5 strict structurally valid attempts. Current model-separated Hy4 lane: 166 records, 28 strict structurally valid attempts; 42 are `tool-call-limit-exceeded`, 84 are provider free-usage-limit records, 2 are timeouts, 7 are static-policy violations, 2 are fail-closed harness records, and 1 is a generic malformed/nonzero record.
* The earlier statements of 58 valid TokenHarbor attempts and 27 valid Hy4 attempts were therefore valid only under the older non-enforcing scorer. They must not be used as strict benchmark coverage. They remain preserved as security-relevant raw evidence but not valid scored attempts.

Correction:

* `re-bench/tools/score_ai_benchmark.py` now counts unique tool invocations from the preserved `opencode.events.jsonl` evidence (falling back to result metadata only if the log is absent) and treats more than 20 invocations as a structural validity failure with category `tool-call-limit-exceeded`.
* `re-bench/tools/render_benchmark_report.py` reports that category explicitly as non-resistance evidence.
* `re-bench/tools/resume_absmax_benchmark_when_quota.py` uses the real scorer when choosing supplemental jobs, so future scheduling automatically counts only strict compliant attempts.
* Future prompts now state explicitly that exceeding 20 tool invocations makes the attempt structurally invalid and instruct agents to begin finalising by call 15. Earlier attempts remain governed by the original limit but are scored strictly under the corrected scorer.
* Regression coverage: `tests/test_ai_benchmark_harness.py::test_scorer_rejects_attempts_over_twenty_tool_calls`; current harness regression suite result is `38 passed`. A separate regression verifies that copied-artifact repair skips fail-closed no-workspace records instead of reporting them as missing-copy corruption.

Current security interpretation:

* Over-limit successful reconstructions remain important attacker evidence. For example, the `absolute-native-only` legitimate-runtime-secrets attempt that recovered the fixture secret and passed all hidden vectors used 30 tool calls, so it is not strict valid evidence; the `absolute` legitimate-runtime-secrets attempt that recovered the fixture secret and passed all hidden vectors used exactly 20 tools and remains strict valid evidence at the current checkpoint.
* Aggregate machine-checked over-limit evidence at the current checkpoint: Hy4 has 42 over-limit records, of which 34 recovered the artifact-public base key and 20 reported the correct NXS1 nonce; 3 contain raw ELF hits, but all such hits were pre-supplied legitimate-runtime evidence and excluded from extraction credit; 2 contain exact fixture-secret appearances and 1 passed all independent hidden vectors. TokenHarbor has 57 over-limit records, all 57 recovered the artifact-public base key and 40 reported the correct NXS1 nonce, but none recovered the exact secret, output vector, payload plaintext excluding supplied evidence, or an independently passing implementation. No over-limit attempt recovered a payload ELF when pre-supplied legitimate-runtime evidence is excluded.
* These are customer-machine attacker results because runtime secrets were intentionally supplied. They are not evidence that artifact-only analysis recovered the secret.
* The strict benchmark matrix is substantially less complete than previously reported. Zero or deficient strict-valid groups remain missing evidence, not resistance.

## AM-028 — Benchmark proxy operational directory was overexposed inside agent sandboxes

Status: **confirmed containment weakness; corrected before post-hardening Hy4 continuation**
Severity: low-to-medium benchmark-hygiene and operational-metadata exposure; no credential or artifact-analysis content identified in the exposed log files

Evidence:

* Earlier versions of `re-bench/tools/ai_bench.py` bind-mounted the whole host directory `/home/nixon/absmax-tokenharbor-proxy` at `/run/absmax-tokenharbor` so the sandbox bridge could reach the Unix endpoints.
* In addition to the required Unix sockets, that directory contained proxy logs, MITM metadata, relay logs, PID files, readiness files, and public CA material. Those files were read-only, but they were not part of the intended attacker input set.
* The exposed proxy logs are operational metadata rather than reverse-engineering evidence: they record endpoint, status, timing, response sizes, redaction counts, and host/path metadata. A targeted assessment found zero occurrences of representative artifact-analysis terms (`cipher-master-K_77`, `NXS1`, `keystream`, `extracted_linux.so`, `PyInit_payload`, `nx_apply_protections`, `answer.json`, and `solution.py`) in the potentially exposed log files. Evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/proxy_operational_log_metadata_assessment.json`.
* A scan of preserved benchmark workspaces found zero references to the proxy log/statistics filenames. One event log contains the host proxy directory path because the agent observed the outer `bwrap` command line; that is not evidence of reading the logs. No direct evidence of agent exploitation was found.
* The exposure still violated least-privilege input boundaries: future log formats could have contained more useful metadata, and benchmark agents should receive only workspace inputs plus explicitly intended service endpoints.

Correction and validation:

* `ai_bench.py` now maintains model-separated subdirectories under `/home/nixon/absmax-sandbox-endpoints`. Hy4 sandboxes expose only `evm.sock`, `opencode-mitm.sock`, and `opencode-connect.sock`; TokenHarbor sandboxes expose only `evm.sock` and `tokenharbor.sock`. The synchroniser verifies device/inode identity, tolerates concurrent link creation, fails closed on unexpected entries, and never exposes proxy logs or PID files. This also prevents an agent in one model lane from using the other model provider as an oracle.
* New result records use sandbox profile label `credential-isolated-unshare-net-pid-v2-minimal-endpoints`; earlier records retain their original v1 labels as historical evidence.
* A direct sandbox inspection confirmed that only the model-appropriate sockets are visible and that `proxy.log` and `opencode-mitm-stats.jsonl` are absent. Model-separation validation is preserved at `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/model_endpoint_separation_validation.json`: the Hy4 endpoint directory can establish CONNECT tunnels to the redacting OpenCode lane but has no TokenHarbor socket backend, while the TokenHarbor endpoint directory has no OpenCode CONNECT backend. The probe did not invoke a model or consume inference quota.
* Both authoritative artifacts were re-executed through both model-separated endpoint directories and the hardened read-only EVM proxy. All four executions exited 0 and produced the expected sealed output; no secret files were preserved. Evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/evm/per_model_endpoint_runtime_smoke.json`.
* Regression coverage: `tests/test_ai_benchmark_harness.py::test_sandbox_endpoint_exposure_contains_only_required_socket_links` and `test_benchmark_binds_minimal_endpoint_directory_not_proxy_log_directory`; current harness regression suite result is **38 passed**.

Impact boundary:

* No pre-hardening log read or artifact-analysis disclosure was identified, and the exposed logs do not contain the hidden secret or solution content. The already preserved v1 attempts are therefore not reclassified solely because of this theoretical metadata exposure.
* New attempts use the stricter v2 endpoint boundary. This is a containment improvement, not evidence about artifact resistance, and it does not change the incomplete status of the benchmark matrix.

## AM-029 — Independent validation initially executed model-written `solution.py` on the host

Status: **confirmed benchmark-infrastructure containment weakness; corrected during the Hy4 continuation; no exploitation evidence identified by retrospective static scan**
Severity: high benchmark-infrastructure containment weakness in principle; no evidence of host-path, network, or destructive behavior in preserved candidate files at the checkpoint

Evidence:

* Before correction, `ai_bench.py::validate_workspace` imported and executed candidate `solution.py` directly with the host Python interpreter while validating hidden vectors. Although the model's OpenCode process was bubblewrap-isolated, this validation step ran after the attempt outside that sandbox.
* A malicious or compromised model-written file could therefore have used host filesystem paths, network access, or process execution during validation. This did not require modifying `artifact.py` and was not blocked by the benchmark sandbox.
* The first three post-resume Hy4 worker batches were already in flight or started before the correction boundary and therefore used the legacy host-validation path. New worker batches started after the correction use the isolated implementation.
* Retrospective scan evidence is `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/orchestrator/solution_validation_host_execution_retrospective_scan.json`. At the latest checkpoint it scanned 175 live/copied `solution.py` path instances (including duplicate live/raw copies), representing 90 unique file hashes and 11 unique flagged file hashes. Twenty-two instances used generic `open` or dynamic-import/execution capability; the scan found zero host-path, network, or destructive-pattern flags. This scan is not proof of benign behavior because host execution had already occurred and static patterns are incomplete.

Correction:

* `ai_bench.py` now copies only `solution.py` into a fresh temporary directory and executes hidden-vector validation inside a separate bubblewrap namespace with no network, an isolated PID namespace, read-only candidate workspace binding, a small isolated `/tmp`, a cleared environment, and no host home/repository bindings.
* The implementation is `run_solution_validation_isolated`; validation records carry `execution_isolation='bubblewrap-unshare-net-pid-readonly-workspace'` when the corrected path is used.
* Manual validation confirmed that a correct hidden-vector implementation still passes all four vectors under the isolated validator, while a probe asserting that the repository secrets path is absent loads successfully inside the namespace.
* Regression coverage: `tests/test_ai_benchmark_harness.py::test_solution_validation_runs_inside_isolated_bwrap_workspace` and `test_solution_validation_source_does_not_execute_candidate_on_host`; harness regression suite result is now **38 passed**.

Impact boundary:

* This is a benchmark-host containment weakness, not a weakness in the protected artifacts and not evidence of artifact-only reverse-engineering success.
* Because the legacy execution already happened for earlier attempts, the absence of suspicious preserved content cannot retroactively prove that no validation-time code accessed the host. No credential exposure, host-path access pattern, network use, destructive behavior, or persistence mechanism was identified in the scanned candidate files.
* The correction changes benchmark-infrastructure containment only. It does not invalidate model answers, and it is not counted as product resistance or product weakness.

## AM-030 — Static execution policy was enforced by the scorer but under-specified in several scenario prompts

Status: **confirmed benchmark-methodology defect; prompt corrected during the Hy4 continuation**
Severity: medium for benchmark validity efficiency; no product-security impact

Evidence:

* The benchmark design treats scenarios whose harness `dynamic` flag is false as static-analysis scenarios. The scorer invalidates attempts that execute `artifact.py` in those scenarios.
* Several static scenario descriptions did not explicitly tell the model that execution, import, tracing, debugging, or invoking `run_valid.sh` was prohibited. Descriptions for scenarios such as `crypto-construction`, `pack-layout-sections`, `loader-initialization-order`, `provenance-signatures`, and `semantics-hidden-vectors` focused on the analysis target without a clear execution prohibition.
* Post-resume evidence showed avoidable `static-scenario-execution-policy-violation` records in static groups. Those attempts remain invalid under the pre-registered scenario boundary, but the under-specified prompt made violations more likely and wasted authorised free-lane requests.

Correction:

* `ai_bench.py::prompt_for` now derives the execution boundary from the scenario table. Dynamic scenarios explicitly permit only bounded local execution/tracing/debugging. Static scenarios explicitly state: do not execute, import, trace, debug, or invoke `artifact.py` or `run_valid.sh`; use only non-executing inspection.
* The correction does not change the scorer, the artifact pair, or the scenario definitions. It aligns the prompt with the pre-existing execution policy.
* Regression coverage: `tests/test_ai_benchmark_harness.py::test_static_scenario_prompt_explicitly_forbids_execution`; harness regression suite result is **38 passed**.

Impact boundary:

* Attempts launched before the prompt correction remain governed by the original static/dynamic execution policy and are not reclassified. The prompt defect is infrastructure/methodology evidence, not resistance evidence and not artifact weakness evidence.
* Attempts launched after the correction are more explicit but still measure the same scenario boundary. Any residual executions remain invalid.

## AM-031 — Residual host/provider credentials remained in copied/generated OpenCode config evidence

Status: **confirmed benchmark-evidence hygiene defect; local redaction completed and structurally audited; operator rotation still required**
Severity: high for host/provider credential hygiene; no evidence that the current credential-isolated matrix uses these copied legacy configs

Evidence:

* The strengthened independent scanner was extended beyond the raw-results root, live copied workspaces, and OpenCode state to include historical invalid-workspace roots, smoke roots, the copied OpenCode home, action-verification output, scratch evidence, and proxy operational logs.
* At the first positive checkpoint it scanned 53,121 files against 139 exact/JSON/base64/hex secret representations and reported one credential hit: `env-KERN_API_KEY` in `/home/nixon/absmax-opencode-home/.config/opencode/opencode.json`. The value itself was never written to the scan report.
* A follow-up structural audit of the copied config found additional literal credential-like values that exact environment matching could not know: a Mistral `apiKey`, a local-proxy `apiKey`, and an OpenCode organisation identifier duplicated into two provider entries. The copied-home TokenHarbor `apiKey` was only an environment-variable reference, not a literal secret.
* Preserved pilot commands bind-mounted `/home/nixon/absmax-opencode-home/.config/opencode` and `/home/nixon/absmax-opencode-home/.local/share/opencode` into pre-containment OpenCode sandboxes. Even without proof that an agent printed the file, the keys/identifier were present inside the sandbox boundary and must conservatively be treated as potentially provider-visible from pre-containment use.
* Incident evidence is `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/opencode_home_residual_credential_incident.json`; the pre-repair redaction report copy is `credential_redaction_report_extra_root_initial_pass.json`.

Correction and validation:

* The exact `KERN_API_KEY` representation was redacted locally. The structural pass then redacted the Mistral key, local-proxy key, and organisation identifier in 19 copied/generated config files. Aggregate replacements were 19 Mistral-key occurrences, 19 local-proxy-key occurrences, and 38 organisation-identifier occurrences. Those counts correspond to the affected config files and did not indicate additional copies in event logs or other scanned evidence. No secret value was printed.
* The first broadened redaction pass also replaced artefact-public licence-HWID strings in 42 non-authoritative scratch/invalid-workspace evidence files. Because HWID is host-binding metadata embedded in attacker-visible artifacts rather than key material, that over-redaction was reversed exactly where introduced: 100 occurrences restored, recorded in `extra_root_hwid_overredaction_repair.json`. The credential redactions were not reversed.
* `redact_benchmark_credentials.py` now covers the extra evidence roots but preserves artefact-public `licence-hwid` there while still redacting true runtime secrets and host/provider credentials. Regression coverage includes `tests/test_ai_benchmark_harness.py::test_extra_evidence_redaction_preserves_public_hwid_but_redacts_secret`.
* `audit_opencode_config_secret_fields.py` now independently audits copied/generated OpenCode config structure without printing values. Latest result: 516 config files with sensitive-looking fields; 497 intentional `credential-isolated-local-proxy` dummy values used by the corrected local-proxy harness; 95 redacted placeholders; 19 environment-variable references; **0 literal sensitive values**. Evidence: `ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark/opencode_config_secret_field_audit.json`.
* The broadened scanner now classifies all remaining representation matches. Latest checkpoint: 53,545 files scanned; 1,207 representation-match files; zero uncategorised non-artifact hits; `credential_hits=0`. Expected matches are licence-HWID host-binding metadata in artifact/build/benchmark-state evidence and invalid forged-licence negative-test fixtures. Evidence: `ABSOLUTE_MAXIMUM_RAW_RESULTS/secret_redaction_scan.json`.
* Harness regression suite after the new coverage: **38 passed in 0.55 s** (`test_outputs/benchmark_harness_regression.txt`).

Residual impact:

* Local redaction cannot withdraw provider-side logs or model context. The operator must rotate the affected host/provider credentials if they are still in use, and should rotate any other credentials exposed through the pre-containment copied configuration as previously required by AM-018. If the organisation identifier is sensitive operationally, treat it as disclosed as well.
* The current authoritative matrix remains credential-isolated and does not use the copied full OpenCode home. Generated post-containment TokenHarbor configs use the documented non-credential dummy value `credential-isolated-local-proxy`; the host-side proxy injects authorisation outside the sandbox. This finding does not invalidate post-containment benchmark records, but it reinforces that pre-containment records are excluded.

## AM-032 — Historical non-standalone calibration used non-authorised OpenCode model lanes and is excluded

Status: **confirmed preserved invalid calibration evidence; excluded from the authorised benchmark**
Severity: medium for benchmark-methodology transparency; no product-security impact and no valid resistance evidence

Evidence:

* Preserved invalid calibration roots contain 35 records in `results_invalid_nonstandalone` and 11 records in `results_invalid_nonstandalone_round2` for `opencode/beam-free` and `opencode/iceman-free`.
* Their file timestamps predate the authoritative model-separated matrix: the invalid non-standalone records span 2026-11-25 23:49–23:57 IST, while the current authoritative `results` root starts at 2026-11-26 02:07 IST.
* These models are not part of the operator-authorised lane set now in force (`opencode/hy4-flash-free`, `tokenharbor/deepseek-v4.1-flash:free`, and fallback `tokenharbor/deepseek-v4.1-flash-1017`). The records are outside the authoritative 498-record model-separated set and are not scored.
* Many records are timeout/terminated/provider-incomplete calibration artifacts. Even completed rows are invalid because the execution mode and model lanes are outside the authoritative benchmark design.

Correction and boundary:

* The invalid records and workspaces are preserved rather than deleted, but they are excluded from scoring, precision analysis, benchmark tables, resistance claims, and pre/post comparison.
* The current harness invokes OpenCode with `run --standalone`, uses only the authorised model lanes, separates model-specific endpoints, and records artifact/model identity in every authoritative result.
* The broadened credential scan includes these historical roots only to verify evidence hygiene. Their inclusion in the scan does not make them benchmark evidence.
