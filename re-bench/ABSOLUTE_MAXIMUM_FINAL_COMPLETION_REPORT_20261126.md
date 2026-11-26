# ABSOLUTE MAXIMUM final completion report

Date: 2026-11-26. This report supersedes the earlier continuation-only status rows for the final rollback/rebuild verification. It is evidence-bound: paths are local evidence, not claims of external CI, public-chain, provider benchmark, Windows, or macOS completion.

## Final result

The repository-side remediation and local verification work is complete to the maximum extent possible in this environment. The final source state is `6008a6d362551cf7b486267db18e10f719a4aa9c` plus this documentation update. No remote push was performed.

The final post-remediation partition evidence is assembled from bounded partitions run after the relevant final edits:

| Partition | Result |
|---|---:|
| vm-ir-llvm | 779 passed |
| crypto-container | 405 passed, 1 skipped |
| security-licensing | 843 passed |
| build-native-loader | 560 passed, 4 skipped |
| distributed-network | 161 passed |
| unit-static-1 | 483 passed |
| unit-static-2 | 25,638 passed, 1 skipped |
| unit-static-3 | 951 passed, 3 skipped |
| unit-static-4 | 979 passed |
| **Total** | **30,799 passed, 9 skipped, 0 failed** |

Aggregate machine-readable evidence: `/home/nixon/absmax-scratch/final-partition-aggregate.json`. Partition logs are under `/home/nixon/absmax-scratch/final-partitions-postfix/`, `/home/nixon/absmax-scratch/final-partitions-remaining/`, and `/home/nixon/absmax-scratch/final-review/full-partitions-v3/` for unit-static-2/3. The latter two partitions ran after the final product-source rollback commits; the only later change was the unit-static-1 benchmark-watchdog test correction, which is outside those partitions.

## Final focused verification

- `make lint`: rc 0; Ruff clean; 0 undefined globals; generated core facade up to date. Log: `/home/nixon/absmax-scratch/final-lint.log`.
- `pytest -q tests/test_rollback.py -x`: 19 passed in 0.85s, including emitted-loader rollback refusal, no payload execution after refusal, unwritable-mark fail-closed behavior, no contiguous embedded payload key, and payload-key rotation with a stable lineage root.
- `pytest -q tests/test_rollback.py tests/test_runner_attest.py tests/test_dependency_locking.py tests/test_invariant_engine.py`: 76 passed in 37.39s.
- `pytest -q tests/test_chain_real_evm.py`: 5 passed in 58.43s. Log: `/home/nixon/absmax-scratch/final-evm/chain_real_evm.log`.
- Xfail rescan: 0 active pytest xfail decorators. Evidence: `/home/nixon/absmax-scratch/final-xfail-scan.json`.
- `git diff --check 24f75f4..HEAD`: clean.
- Gitleaks over `24f75f4..HEAD`: 4 commits scanned, no leaks. Gitleaks over the remaining worktree diff: no leaks. Evidence: `/home/nixon/absmax-scratch/final-secret-scan/`.
- Targeted private-key/AWS/GitHub/Slack/64-hex-assignment scan over the same commit range: 0 hits.

## Final ABSOLUTE rebuild from current source

The two variants were rebuilt after the rollback lineage fix with `re-bench/tools/build_absolute.py` into `/home/nixon/absmax-scratch/rebuild-final-review-v7/`. Redacted public evidence was copied to `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/final_rebuild_post_rollback/`; secret inputs remained only in the 0700 scratch secrets tree and were not copied.

| Variant | Artifact SHA-256 | Size | Build rc |
|---|---|---:|---:|
| absolute | `5e4a44e5bfa999252b3d739cae33a6cf3de5bffcf782194bb06ae73f15f6389f` | 1,736,530 | 0 |
| absolute-native-only | `692f00282e1518ba2b37b49dad11d63cb4838af5de5ec24419451292aacbc21c` | 1,039,250 | 0 |

Signed build manifests carry monotonic `protection_level` values `1795679084961158667` and `1795679134499846308` respectively. Runtime first-run marks exist with schema `nx-rollback/v1` and 64-hex HMACs.

Runtime controls:

| Case | absolute | absolute-native-only |
|---|---:|---:|
| valid runtime secrets | 0, expected output | 0, expected output |
| missing licence | 137, no payload output | 78, no payload output |
| missing seal shard | 137, no payload output | 78, no payload output |
| wrong seal shard | 137, no payload output | 78, no payload output |
| missing all runtime secrets | 137, no payload output | 78, no payload output |
| one-byte tamper | 137, no payload output | 137, no payload output |
| forged licence payload | 1, no payload output | 1, no payload output |
| wrong licence token | 1, no payload output | 1, no payload output |

Exit 78 in the native-only missing-secret cases is the deliberate native-only no-fallback refusal (`[FATAL] native-only artefact ... exit 78`), not successful execution. It is fail-closed and emits no payload output.

Native extraction with legitimate runtime secrets produced valid Linux ELF objects for both variants. Both extracted objects have GNU RELRO, non-executable GNU_STACK, `nx_apply`, and Python initialization exports. Extracted object hashes begin `dde69f59d301b906` (absolute) and `016601725cb492ed` (absolute-native-only).

Exact-match scans found zero occurrences of the runtime licence, licence key material, seal shard, honey secret, issuer seed, manifest signing key, or provenance signing key in the artifacts, runtime output, extracted native objects, or copied public evidence. `_NX_ROLLBACK_KEY_HEX` is absent; rollback uses the domain-separated runtime/lineage derivation.

## Rollback security outcome

The final implementation is client-side high-water-mark enforcement, not server-authoritative anti-rollback. It now:

1. carries the same integer `protection_level` in the signed manifest and emitted loader;
2. checks the mark before payload execution;
3. fails closed when the mark cannot be written;
4. does not embed the payload key as a contiguous rollback secret;
5. derives a domain-separated rollback key at runtime;
6. prefers a customer/licence lineage root so payload-key rotation does not by itself invalidate rollback continuity;
7. is regression-tested for downgrade refusal, upgrade acceptance, invalid input, unwritable state, payload non-execution, and key rotation.

Residual limitation: deleting the mark or running in a clean directory bypasses this client-side mechanism. Cross-build continuity also requires stable customer/licence binding material; freshly re-keyed artefacts start a new lineage. Strong rollback security requires issuer/server-side refusal.

## Benchmark and subagent status

The required one-at-a-time local subagent replacement evidence is complete as qualitative validation: all 8 expected lanes exist, all answers are schema-valid, controlled exact-secret matches total 0, artifact integrity controls pass, positive controls return 0, and secret-withheld controls fail closed without output. Evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/subagent_benchmark_validation_final.json`.

This is not external statistical benchmark completion. TokenHarbor paid remains HTTP 402; TokenHarbor free reported reset on 2 Dec 2026 15:07 UTC. A duplicate detached continuation process restarted Hy4 watchdogs despite the subagent replacement instruction; that duplicate process tree was terminated, and no ABSMAX Hy4/watchdog process is active now. Those supplemental external records are not used as release evidence.

## GitHub Actions and dependency state

- Active workflow inventory: 123 effective `uses` rows; 107 external rows; all 107 external rows pinned to immutable upstream SHAs; 0 mutable external references; 16 local reusable workflow references. Evidence: `re-bench/GITHUB_ACTION_PIN_INVENTORY.json`.
- Artifact dependency installation is hash-locked through the maintained lock files. Unused unverified UPX installation was removed from CI/release artifact jobs.
- Intentional exceptions remain informational/non-artifact-producing only, such as latest-ruff comparison and pip bootstrap itself.

## Commits and files

Relevant final continuation commits:

```text
89a6527 Harden security controls and validation evidence
fb4f7af Add hash-locked native farm dependency manifest
937b301 Exclude evidence trees from invariant scanning
8fc40b2 Honor TMPDIR in native payload header tests
d1e2520 Correct partition runner recovery guidance
a11b649 Remove unused UPX supply-chain exception
7d122b2 Wire client-side rollback enforcement into emitted loaders
24f75f4 Cover farm attestation verification failure closure
ebdaf6d Avoid embedding payload keys for rollback marks
e0086d1 Update continuation status evidence and benchmark boundaries
78050f9 Preserve rollback lineage across payload-key rotation
6008a6d Align benchmark watchdog regression with lane error handling
```

The narrow final commit-range file list is `/home/nixon/absmax-scratch/final-scoped-changed-files.txt` (19 files). The broader continuation range touches 272 files because it includes the pre-existing audit remediation base; its list is `/home/nixon/absmax-scratch/final-changed-files.txt`.

`docs/MAXIMUM_SECURITY.md` remains externally modified and deliberately uncommitted. Bulk `audit/` and `re-bench/` evidence trees remain uncommitted; secret-bearing subtrees must not be committed. Branch is local-only and ahead of `origin/master`; no push was authorized or performed.

## Remaining external blockers and honest limitations

1. External statistical benchmark completion requires explicit authorized provider availability/quota; local subagent evidence is qualitative only.
2. Local EVM evidence is real in-process py-evm contract execution, not public-chain evidence.
3. Windows Authenticode public trust, strict shadow-stack validation, Apple Developer ID signing, Hardened Runtime, notarisation, stapling, and Gatekeeper validation require external certificates/accounts/runners.
4. ARM64 native builds are unverified.
5. Live GitHub Actions validation requires an authorized CI run/push.
6. Client-side artifacts cannot guarantee cryptographic confidentiality against an attacker who controls the customer machine and possesses legitimate runtime secrets. Stronger confidentiality requires server-side execution, remote key release, or hardware-backed custody.
7. Client-side rollback marks can be deleted or bypassed in a clean directory; issuer/server enforcement is required for authoritative anti-rollback.
8. Production release signing still requires persistent operator-controlled publisher identity, protected environment rules, and independent pin distribution.
