# ABSOLUTE MAXIMUM continuation status — 2026-11-26

> **2026-11-27 status supersession:** this document contains historical Hy4/TokenHarbor/Kern continuation state. It is not the current benchmark status. The completed operator-authorised replacement lane is `opencode-go/deepseek-v4.1-flash`: 114/114 active records are structurally valid across 6 variants × 19 scenarios after retry. That campaign is diagnostic-only because it has one attempt per cell. Use `re-bench/ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md` and `re-bench/ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md` as the current authoritative status.

## Completed and verified

- Valid cross-platform cloud artifacts were built in the clean `cloud-final4` scratch lane and copied into additive `cloud-final4/` artifact subdirectories without overwriting historical artifacts.
- `maximum-cloud`: SHA-256 `f9c5256d796c57fccc81e0eff0064b5743a1768e2dc203dfa3fc91651965a395`, size 1,327,566.
- `absolute-cloud`: SHA-256 `9bfdadef9414f9f79b0529f16bfa9591423f6f93bc53a5f9dbea83e1e6330dc0`, size 4,416,391.
- `CLOUD_FINAL4_VALIDATION.json` records rc 0 validation for both: manifest/artifact hash match, all three NXS1 native-blob slots present, positive runtime control passes, no-secret control fails closed, and all three per-runner attestation records pass hardening verification.
- Linux native plaintexts were extracted with legitimate secrets for fair attacker-model benchmarking; both are valid ELF files.
- Focused regression lane: 212 passed, 1 skipped.
- Credential-pattern scan of reviewed benchmark tooling: no live key material; Gitleaks over `re-bench/tools`: 0 leaks.
- Commits created locally: `31065b0` and `8902634`. No push performed.

## Product/build integrity fixes

- Cloud farm use is serialized with an OS-held lock.
- Cloud build failure now fails closed instead of shipping a degraded single-OS artifact.
- Farm repository creation checks existence before POSTing, reducing GitHub secondary-rate-limit consumption and validating arbitrary 422 responses.
- Per-OS runner attestations are isolated instead of overwritten during zip extraction.
- Attestation is bound to the exact uploaded payload bytes and per-artifact native blob.
- Mach-O dylib/bundle hardening no longer requires executable-image-only PIE/no-heap-exec flags while still forbidding executable stacks.
- A duplicate builder race that caused provenance-pin/artifact-manifest mismatch was identified and builders were stopped; fresh final4 artifacts were then validated.
- Builder-lock protection was added to `build_absolute.py`.

## Benchmark harness/scoring fixes

- `answer.json` exact secret recovery is now field-specific. Incidental mention of input source material no longer counts as recovery.
- Scoring no longer crosses evidence-root boundaries when a same-named legacy workspace exists.
- Provider-invalid records are preserved with `.evidence` suffixes outside active `*.json` result globs.
- Cloud benchmark lane supports additive artifact subdirectories and alternate secret roots.
- A Kern watchdog resumes the local matrix and then the cloud matrix only when the lane probes healthy.

## Current blockage

Kern is externally unhealthy: the credential-isolated probe returns HTTP 502 Bad Gateway or timeout. The matrix watchdog is running, but no benchmark matrix runner is active while the provider is broken. This is invalid infrastructure evidence, not resistance evidence.

Current structurally valid local preliminary scores (single attempt): maximum-packed 21/16/44/39 across the four scenarios; maximum-local legitimate-runtime-secrets 33. These are preliminary and incomplete, not final resistance claims.


## Final superseding closeout

The Kern blockage above was resolved by operator-authorised lane replacement, not by Kern recovery. The final `opencode-go/deepseek-v4.1-flash` diagnostic matrix completed with 114/114 structurally valid active records across 6 variants × 19 scenarios. The preliminary local scores quoted above are obsolete. See `ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md` and `ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md`.
