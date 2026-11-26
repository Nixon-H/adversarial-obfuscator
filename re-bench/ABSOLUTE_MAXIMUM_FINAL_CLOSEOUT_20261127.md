# ABSOLUTE MAXIMUM DeepSeek benchmark closeout — 2026-11-27

This closeout supersedes stale in-progress status notes for the OpenCode Go DeepSeek lane.

## Final executed matrix

- model lane: `opencode-go/deepseek-v4.1-flash`
- variants: 6
- scenarios: 19
- planned cells: 114
- structurally valid active records: 114/114
- active invalid records: 0
- attempts per cell: 1
- aggregate evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/deepseek_benchmark_aggregate.json`
- final report: `re-bench/ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md`

## Statistical acceptance resolution

The original release-oriented evidence-sufficiency target remains five structurally valid attempts per group. That target was **not** met: this campaign has one valid attempt per cell. The campaign is therefore formally classified as **broad diagnostic evidence only**, not statistical benchmark completion and not a release gate.

This is not a retroactive claim that one attempt is statistically sufficient. If statistical benchmark acceptance is required later, a separate repeat campaign must obtain five structurally valid attempts for each variant/scenario/model/artifact-hash group under unchanged artifact identities.

## Exploitability conclusion

No full non-source external-attacker break was validated. Source-assisted recoveries are expected controls. The significant confirmed weakness is the customer-controlled runtime-secret boundary, evidenced by partial native-object extraction in `maximum-local / legitimate-runtime-secrets` without exact master-secret recovery or independent semantic reconstruction.

## AM-001 resolution

AM-001 is formally accepted as an architectural limitation rather than falsely marked fixed. The decision record is `re-bench/ABSOLUTE_MAXIMUM_AM001_ARCHITECTURAL_DECISION_20261127.md`.


## Final partitioned test evidence

A single fresh post-closeout nine-partition run completed successfully. No corrective partition substitution is used in the final aggregate:

- **30,853 passed**
- **9 skipped**
- **0 failed**
- all 9 partitions rc 0

Machine-readable aggregate: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/final_partition_test_aggregate_20261127.json`. The run started after the benchmark closeout fixes; subsequent intervening commits were documentation-only historical-status supersession notices and did not change product or test code. The earlier corrected-composite aggregate remains in git history only as interim evidence.

## Evidence hygiene

Final redaction scan after closeout: `credential_hits=0` across 83,518 scanned files; evidence copy: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/final_closeout_redaction_scan_20261127.json`. Provider-key material was held only by host-side proxy processes and was not present in benchmark sandboxes.

## Push state

Benchmark closeout work is committed locally. No push is authorised or performed unless the operator explicitly requests it.
