# ABSOLUTE MAXIMUM Continuation Goal Plan

> **2026-11-27 status supersession:** this document contains historical Hy4/TokenHarbor/Kern continuation state. It is not the current benchmark status. The completed operator-authorised replacement lane is `opencode-go/deepseek-v4.1-flash`: 114/114 active records are structurally valid across 6 variants × 19 scenarios after retry. That campaign is diagnostic-only because it has one attempt per cell. Use `re-bench/ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md` and `re-bench/ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md` as the current authoritative status.

Created: 2026-11-26
Repository HEAD at start: `b571b18a79b76ee351f307ced793c6e66c7f22ce`
Branch at start: `master...origin/master [ahead 2]`
Initial worktree state: extensively dirty (253–254 status entries); no reset/cleanup/revert is authorised. `docs/MAXIMUM_SECURITY.md` has pre-existing/external modifications and must not be modified by this continuation.

## Execution constraints

- Execute concrete work; do not produce another planning-only report.
- Do not overwrite previous-session raw evidence.
- Do not modify authoritative benchmark artifact copies under `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds/`.
- Do not substitute benchmark model identity. Devin subagents may perform local audit/research work, but their output is not Hy4/TokenHarbor benchmark evidence.
- Authorised benchmark provider lanes only: `opencode/hy4-flash-free`, `tokenharbor/deepseek-v4.1-flash:free`, fallback `tokenharbor/deepseek-v4.1-flash-1017`.
- Do not push without explicit authorisation.
- Do not expose credentials in files, logs, reports, or output.

## P0 reconstruction and verification

1. Build the continuation status matrix from actual files, source, logs, workflows, test output, and raw benchmark evidence.
2. Reconcile previously reported outstanding items against verified evidence rather than document claims.
3. Classify every item as one of: COMPLETED AND VERIFIED, IMPLEMENTED BUT NOT VERIFIED, PARTIALLY COMPLETED, NOT STARTED, BLOCKED BY EXTERNAL DEPENDENCY, NO LONGER APPLICABLE.

## P1 concrete workstreams

- GitHub Actions immutable pinning: inventory, resolve upstream SHAs, pin with comments, validate, produce machine-readable inventory.
- Xfail investigation: identify exact xfailed tests, reproduce, fix underlying defects where real, remove markers only after independent verification.
- Actual local EVM licence-contract testing: real local EVM deployment and client/loader path coverage, distinct from mocked RPC evidence.
- Cross-platform build/packaging: inventory actual executed evidence and platform gaps; do not claim unexecuted platforms.
- Signing/trust: implement safe repository-side validation where missing; document external certificate/account/admin steps exactly.
- Dependency/build/release/provenance integrity: verify pins, exceptions, manifests, signatures, rollback/replacement detection, fatal logs, and payload usability gates.
- Customer-controlled runtime-secret boundary: map exposure/reuse/isolation and document feasible architectural improvements without unsupported confidentiality claims.
- Benchmark methodology/acceptance: validate scorer, invalid evidence treatment, model/artifact identity, hidden evaluation, and AI-RE-003 gate decision.
- Independent review of prior fixes: reproduce, verify remediation, search adjacent bypasses, negative tests, regression tests, artifact/native identity checks.

## P2 provider-bound workstream

- Keep exactly one benchmark resume watchdog.
- Resume deficient post-fix groups and targeted pre-fix comparison only through authorised lanes.
- If no lane becomes available, preserve the blockage as external and do not fabricate completion.

## Verification gates

- Focused tests must use: `TMPDIR=/home/nixon/absmax-tmp /home/nixon/.local/bin/pytest -q <tests> --tb=short -p no:cacheprovider`.
- Full-suite evidence must use bounded partitions, not a single resource-heavy serial run.
- After any benchmark-record change run copied-artifact repair, precision analysis, scoring, report rendering, credential redaction, expanded secret scanning, config audit, and final verification.
- Secret scan must report `credential_hits=0`; OpenCode config audit must report `literal_sensitive_field_count=0`.
- Final report must state exact files, commits, tests, EVM results, platform evidence, action pins, xfail statuses, signing requirements, security limitations, and unavailable-environment blockers.
