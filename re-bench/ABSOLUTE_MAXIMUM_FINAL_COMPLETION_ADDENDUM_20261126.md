# ABSOLUTE MAXIMUM final completion addendum — 2026-11-26

> **Authoritative correction — 2026-11-27.** This is retained as historical
> pre-DeepSeek remediation evidence. Its commit/branch/full-suite status is stale
> and is superseded by `ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md` and
> `ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md`. The rebuild hashes below
> were current-source validation artifacts for that pass only; they are not the
> fixed DeepSeek benchmark artifact identities. Do not use the “Commit decision”
> or “Full-suite status” sections below as current state.

This addendum continues, rather than replaces, `ABSOLUTE_MAXIMUM_CONTINUATION_FINAL_REPORT.md`. It covers the final remediation pass performed after the internal subagent review and the final ABSOLUTE MAXIMUM rebuild. No raw licence token, fixture secret, hidden plaintext, private key, shard, or credential value is recorded here.

## Final remediation results

| ID | Finding | Final status | Evidence |
|---|---|---|---|
| ABSMAX-FR-001 | Generated farm installed Cython/setuptools/wheel without hash locking | FIXED | `requirements-farm.lock`; `obfuscator/core/utils.py:935,2108-2116`; `tests/test_dependency_locking.py:129-157`; pip dry-run rc 0 in `ABSOLUTE_MAXIMUM_RAW_RESULTS/farm-lock-pip-dryrun.log` |
| ABSMAX-FR-002 | Farm attestation compared the original source rather than the exact uploaded post-AST source | FIXED | `obfuscator/core/pipeline.py:5701`; regression `tests/test_runner_attest.py:248-264` |
| ABSMAX-FR-003 | Cloud licence private-key sampling was reducible to a 32-bit PRNG seed | FIXED | `obfuscator/core/pipeline.py:8266` now uses `secrets.SystemRandom()`; regression `tests/test_phantom_worker_auth.py:107-121` |
| ABSMAX-FR-004 | Cloudflare `SECRET_KEY` and `NTRU_PRIV` were deployed as visible `plain_text` bindings | FIXED | `obfuscator/core/pipeline.py:1927` uses `secret_text`; behavioral multipart test `tests/test_phantom_worker_auth.py:67-104` |
| ABSMAX-FR-005 | One-shot cleanup trusted `NX_ORIGIN` as an arbitrary file-deletion path | FIXED for generated sectioned and packed loaders | sectioned emitter `obfuscator/core/pipeline.py:2608-2638`; packed paths `obfuscator/core/sources.py:7251,7469`; tests `tests/test_access_gates_sectioned.py:117-216` |
| ABSMAX-FR-006 | Local `.nixon_key_*` creation had a permissions/symlink race | FIXED | atomic 0600 helper `obfuscator/core/pipeline.py:45-73`, use at `pipeline.py:6132`, test `tests/test_phantom_worker_auth.py:124-136` |
| ABSMAX-FR-007 | Farm runner attestation is self-asserted, not independent proof of correct compilation | DOCUMENTED LIMITATION / PARTIALLY MITIGATED | attestation is now fail-closed (`pipeline.py:5731`) and binds exact bytes/artifacts, but a malicious runner can still lie consistently; independent trusted-runner, reproducible-build, or hardware attestation is required |

## Post-fix verification

- Focused post-remediation regression lane: **226 passed, 1 skipped, 0 failed in 48.98s**. Evidence: `/home/nixon/absmax-scratch/final-review/final-focused-regression.log`.
- `make lint`: **passed**; Ruff clean, 0 undefined globals, generated core facade current. Evidence: `/home/nixon/absmax-scratch/final-review/make-lint.log`.
- `git diff --check`: **clean**. Evidence: `/home/nixon/absmax-scratch/final-review/git-diff-check.rc` = 0.
- Gitleaks scans of final touched source/test/workflow/evidence files: **0 leaks**. Evidence summary: `/home/nixon/absmax-scratch/final-review/gitleaks/summary.txt`.
- Generated farm lock validation: `python3 -m pip install --dry-run --ignore-installed --require-hashes -r requirements-farm.lock` returned **0** and resolved exactly `Cython-3.0.12 packaging-26.4 setuptools-84.2.1 wheel-0.48.0`. Evidence: `audit/2026-11-25/farm-lock-pip-dryrun.log` and `.rc`.

## Final ABSOLUTE MAXIMUM rebuild

Both current-source variants rebuilt successfully with `re-bench/build-venv/bin/python re-bench/tools/build_absolute.py` into `/home/nixon/absmax-scratch/rebuild-final-review/`:

| Variant | rc | artifact SHA-256 | size |
|---|---:|---|---:|
| absolute | 0 | `2e513b3ad77f62132cbed8f9b0c002a3610094350cf27810faaf35fcfa078911` | 1,811,992 |
| absolute-native-only | 0 | `cc9f55c08caee571d565c837a4bd136be105580705c7875d7c4714811ec29ede` | 1,145,137 |

These are new current-source artifacts. They do not overwrite the older committed benchmark artifacts or their hashes.

Extracted Linux native objects:

| Variant | native SHA-256 | size | ELF | RELRO | NX stack | required exports |
|---|---|---:|---|---|---|---|
| absolute | `45483fac3f590933389139f5bb1c1b800c81d8eb441dc54601858e857aa57141` | 731,168 | yes | yes | yes | `nx_apply_protections`, `PyInit_payload` |
| absolute-native-only | `21e45447d4d0ddb3cb0316817c839115f0d8b8c07eea9f4725ee41823eacc345` | 751,640 | yes | yes | yes | `nx_apply_protections`, `PyInit_payload` |

Runtime controls on the final artifacts:

| Case | rc | stdout SHA-256 | stderr length |
|---|---:|---|---:|
| absolute, secrets available | 0 | `d9d34b5c820045756b0bd7eb21a72540e6575744efd01a3dd307a72df1f0c623` | 0 |
| absolute, secrets withheld | 137 | empty stdout | 106 |
| absolute-native-only, secrets available | 0 | same stdout hash | 0 |
| absolute-native-only, secrets withheld | 137 | empty stdout | 106 |

A byte scan confirmed none of the positive/negative stdout/stderr files contained the licence token, seal shard, or honey secret.

Machine-readable copies are in `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/final_rebuild_results.json`, `final_rebuild_runtime_controls.json`, and `final_rebuild_native_hardening_readelf.json`.

## Subagent replacement benchmark status

The Hy4 resume watchdog was stopped after the user directed that subagents replace the Hy4 lane. The internal subagent benchmark is complete as qualitative evidence, not as an external statistical benchmark:

- all 8 expected lanes present;
- all 8 `answer.json` files schema-valid;
- controlled exact-secret matches: **0**;
- artifact integrity and positive/negative controls: passed;
- machine evidence: `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/subagent_benchmark_validation_final.json`.

AI-RE-003 remains resolved as: unvalidated benchmark scores must not drive pass selection or release gates. Internal subagent evidence supplements direct controls but does not replace independent external-model validation.

## Previously requested accounting

- GitHub Actions: 123 effective `uses`; 107 active external uses; 107 pinned to immutable SHAs; 0 active mutable external uses; 16 local reusable workflow references; 0 verification failures. Evidence: `re-bench/GITHUB_ACTION_PIN_INVENTORY.json` and `ABSOLUTE_MAXIMUM_RAW_RESULTS/github_actions_pin_inventory.json`.
- Current AST inventory of pytest `xfail` decorators: **0**. The historical seven strict xfails were already resolved; the earlier “six xfailed tests” wording is superseded by the authoritative seven-item historical inventory and the current zero-marker state.
- Real local EVM evidence remains py-evm/eth-tester evidence, including full emitted-artifact execution and transfer-induced loader refusal (`tests/test_chain_real_evm.py`, 5 passed in prior continuation evidence). It is not public-chain evidence.
- Docker authoritative evidence remains the earlier clean tester run: 30,703 passed, 0 failed, 19 skipped, 1 xfailed, image `sha256:a62ac26993bdbc955e7a79ac2f4e6f76ff9d8a166b4f86f0de9ecbf14c05ab78`. Docker was not rebuilt after this final small remediation pass; current-source verification is the focused lane, lint, final rebuild/runtime controls, and the partition run recorded in the progress report.
- Cross-platform signing remains externally blocked: no public Windows Authenticode trust, no Apple Developer ID/Hardened Runtime/notarisation/stapling, no hardware-backed Windows shadow-stack validation, and no verified ARM64 native build.
- Customer-machine confidentiality remains impossible to guarantee in software when the host operator controls the machine and possesses legitimate runtime secrets. Server-side execution, remote key release, or hardware-backed key custody is required for that stronger guarantee.
- Markdown cleanup was already completed only after reading all then-existing Markdown files; only the two stale untracked scratch files were deleted. No additional Markdown deletion was performed in this final pass.

## Commit decision

No new commit was created and nothing was pushed. The working tree still contains extensive mixed pre-existing changes: 217 tracked modified files, 2 tracked deletions, and 51 untracked top-level paths in the final status snapshot. Committing now would mix unrelated prior-session work with this remediation. Existing local branch state remains `master...origin/master [ahead 2]`; no additional continuation commit was added.

## Full-suite status

A fresh final partition run was started with isolated `TMPDIR` at `/home/nixon/absmax-scratch/final-review/full-partitions`. Its final machine-readable result is `/home/nixon/absmax-scratch/final-review/full-partitions/results.json` when complete. Until that file exists, the only current-post-fix full-suite claim is the focused 226-test lane; do not treat this addendum as hiding that distinction.
