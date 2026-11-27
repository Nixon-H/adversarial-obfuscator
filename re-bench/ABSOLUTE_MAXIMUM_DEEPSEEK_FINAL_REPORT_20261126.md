# ABSOLUTE MAXIMUM OpenCode Go DeepSeek benchmark final report

Date: 2026-11-26
Model lane: `opencode-go/deepseek-v4.1-flash`
Prompt/harness: cache-aware stable-prefix prompt with explicit two-turn session continuation
Evidence roots:

- `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark_profile_matrix_deepseek-local-v12/`
- `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark_profile_matrix_deepseek-cloud-v13/`
- `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark_profile_matrix_go-v12/`
- aggregate: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/deepseek_benchmark_aggregate.json`
- cache telemetry: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/opencode_go_cache_summary.json`

## Completion status

Benchmark execution is complete.

| Matrix | Planned | Structurally valid after retry | Invalid active records |
|---|---:|---:|---:|
| Core local, 4 key/source scenarios | 16 | 16 | 0 |
| Core validated-cloud, 4 key/source scenarios | 8 | 8 | 0 |
| Extended 15-scenario slice | 90 | 90 | 0 |
| Combined aggregate | 114 | 114 | 0 |

Four initially invalid extended-scenario records were archived as invalid evidence and retried. Replacement records are valid:

| Variant | Scenario | Original failure | Retry result | Score |
|---|---|---|---|---:|
| absolute-native-only | ghidra-dynamic | timeout | valid | 60 |
| absolute-native-only | unprivileged-local | timeout | valid | 57 |
| absolute | host-runtime-gates | malformed answer | valid | 61 |
| absolute | source-assisted-static | static execution-policy violation | valid | 83 |

Original invalid bytes were preserved with `.invalid-*.retry1.evidence` suffixes rather than deleted.

## Cache-hit telemetry

The lane was explicitly optimized for cache reuse by using a stable instructional prompt prefix, moving variant/scenario metadata to the end, using stable explicit OpenCode session IDs, and preserving `x-opencode-session` routing metadata.

Provider metadata summary:

| Metric | Value |
|---|---:|
| proxy log records | 1,321 |
| successful model requests | 1,298 |
| weighted cache-hit rate | 70.94% |
| mean per-request cache-hit rate | 71.33% |
| maximum per-request cache-hit rate | 99.96% |
| provider-bound request redactions | 1,486 |
| provider-bound response redactions | 0 |
| provider-reported allowance total | 1.43068717 units |

The allowance value is provider metadata, not an invoice. Proxy errors are early transport/cancellation records from the pre-streaming and duplicate-runner period; active benchmark evidence was judged only from structurally valid completed attempts.

## Score distribution

The score is a reconstruction/attack-progress score, not a release pass/fail grade. Higher means the attacker reconstructed more.

| Variant | Valid records | Mean | Min | Max |
|---|---:|---:|---:|---:|
| absolute | 19 | 60.53 | 43 | 83 |
| absolute-cloud | 19 | 65.63 | 42 | 90 |
| absolute-native-only | 19 | 61.79 | 50 | 78 |
| maximum-cloud | 19 | 66.32 | 58 | 88 |
| maximum-local | 19 | 65.00 | 56 | 82 |
| maximum-packed | 19 | 29.58 | 7 | 68 |
| **all** | **114** | **58.14** | **7** | **90** |

## Recovery and exploitability findings

### External non-source attacker boundary

No active record showed a full external-attacker break in the non-source scenarios:

- no exact hidden master-secret recovery in non-source secrets-withheld scenarios;
- no independently passing semantic reconstruction in non-source secrets-withheld scenarios;
- no fix-requiring exploit marker in the aggregate;
- no validated solution.py in non-source secrets-withheld scenarios.

Source-assisted recoveries are expected controls because `original_source.py` was intentionally provided. They verify that the scorer and independent validation can detect real reconstruction; they are not counted as product vulnerabilities.

### Source-assisted control recoveries

Exact secret recovery occurred only in source-assisted scenarios:

- `source-assisted-static`: 5 records
- `source-assisted-secrets-withheld`: 3 records
- `source-assisted-runtime-secrets`: 2 records

Independent semantic solution validation passed only in source-assisted scenarios:

- `source-assisted-secrets-withheld`: 5 records
- `source-assisted-runtime-secrets`: 4 records
- `source-assisted-static`: 4 records

These results are control evidence, not release-blocking vulnerabilities.

### Confirmed customer-machine native extraction

One non-source recovery marker remains important: in `maximum-local / legitimate-runtime-secrets`, the agent recovered a native payload object:

- file name in evidence: `native_linux.bin`
- size: 190,024 bytes
- SHA-256: `95388ca4790f9e02718b31a62852ac4f994c2d2446889f7dc59b5a5a024c959e`

The same attempt did not recover the exact hidden master secret and did not pass independent semantic reconstruction. This is therefore partial native-material recovery, not a complete semantic break.

It confirms the documented customer-controlled runtime-secret boundary: when the attacker controls the customer machine and has legitimate runtime secrets, native payload material can be extracted for offline analysis. This is a real architectural limitation of client-side protection. It cannot be completely fixed by more obfuscation.

Detailed boundary analysis and remediation ordering are in `re-bench/ABSOLUTE_MAXIMUM_RUNTIME_SECRET_BOUNDARY.md`. The formal decision record is `re-bench/ABSOLUTE_MAXIMUM_AM001_ARCHITECTURAL_DECISION_20261127.md`. At the time of this benchmark report, AM-001 was accepted as an architectural limitation rather than falsely marked fixed; the later opt-in server-side split remediation is validated separately in `re-bench/ABSOLUTE_MAXIMUM_AM001_REMOTE_SPLIT_VALIDATION_20261127.md` and does not retroactively change these benchmark artifacts.

## `maximum-packed` provenance anomaly resolution

The anomaly is resolved as **not a product defect**.

Direct runtime probes of the authoritative `maximum-packed` artifact showed:

| Probe | Result |
|---|---|
| correct provenance pin | rc 0, expected runtime output |
| wrong provenance pin | rc 137, fail-closed: pin does not match signing key |
| missing provenance pin | rc 137, fail-closed: pin missing under release policy |

The empty embedded provenance prefix observed by the earlier AST diagnostic is expected for the recursive packed control: the outer recursive packer hides the inner signed loader. Runtime evidence proves the inner provenance enforcement is present and effective.

## Cloud artifact validity

The benchmarked cloud artifacts are the validated `cloud-final4` artifacts:

- `maximum-cloud`: `f9c5256d796c57fccc81e0eff0064b5743a1768e2dc203dfa3fc91651965a395`
- `absolute-cloud`: `9bfdadef9414f9f79b0529f16bfa9591423f6f93bc53a5f9dbea83e1e6330dc0`

Validation evidence is `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/CLOUD_FINAL4_VALIDATION.json`. The validated properties included manifest hash agreement, Windows/Linux/Darwin native-blob presence, positive runtime control, missing-secret fail-closed control, and all per-runner attestation validation.

## Security conclusion

1. The benchmark is complete with 114/114 structurally valid active records.
2. DeepSeek did not demonstrate a full non-source external-attacker break.
3. Source-assisted recovery is expected control evidence.
4. The significant confirmed weakness remains the customer-controlled runtime-secret boundary, now independently confirmed through native-object extraction in `maximum-local / legitimate-runtime-secrets`.
5. No complete client-side fix exists for that boundary. The correct remediation for genuinely confidential operations is server-side execution, remote key release, short-lived wrapped keys, per-customer isolation, or hardware-backed execution where available.
6. Native handshake hardening and memory-only loading may be useful defense-in-depth but must not be represented as cryptographic confidentiality against the customer-machine attacker.

## Verification and evidence hygiene

- Final focused harness/provenance/build-farm/failure-mode regression lane: 127 passed.
- Final post-closeout partitioned suite: 30,853 passed, 9 skipped, 0 failed; all 9 partitions rc 0 in one direct run (`re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/final_partition_test_aggregate_20261127.json`).
- `make lint`: passed.
- Python compilation of the benchmark tooling: passed.
- `git diff --check` over the intended commit paths: clean.
- Final credential-redaction scan after closeout: 83,518 files scanned, 479 secret representations checked, `credential_hits=0` (`re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/final_closeout_redaction_scan_20261127.json`).
- Staged-diff scan found no provider-key prefixes or private-key material.
- Invalid original records were archived outside active result globs rather than deleted.

## Remaining limitations

- One attempt per cell in this lane; the results are broad evidence, not statistical resistance estimates. The statistical acceptance amendment in `re-bench/ABSOLUTE_MAXIMUM_BENCHMARK_ACCEPTANCE.md` formally classifies this campaign as diagnostic-only and preserves the five-valid-attempt standard for any future release-oriented statistical campaign.
- The scoring rubric measures reconstruction progress and independently validated recovery; it is not a release gate by itself.
- No SGX/TEE execution, public-chain execution, production signing/notarisation, or credentialed remote deployment was performed.
- Client-side artifacts still cannot guarantee confidentiality against a fully hostile customer-controlled host with legitimate runtime secrets.
