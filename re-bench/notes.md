# Notes: ABSOLUTE MAXIMUM Audit and Benchmark

> **2026-11-27 status supersession:** benchmark status statements in this historical document may refer to incomplete Hy4/TokenHarbor/Kern lanes. The current completed diagnostic lane is `opencode-go/deepseek-v4.1-flash`: 114/114 active records structurally valid across 6 variants × 19 scenarios, one attempt per cell. Treat this document as historical context unless it explicitly cites the DeepSeek final report. Current status: `re-bench/ABSOLUTE_MAXIMUM_FINAL_CLOSEOUT_20261127.md`.

## Baseline observations
- Branch/commit: see `baseline/initial-state.txt`.
- Worktree was already extensively modified before this session; no pre-existing change may be discarded.
- `re-bench/` did not exist at session start.

## Evidence separation legend
- OBS: direct observation/tool output.
- CLAIM: model or documentation claim requiring validation.
- VERIFIED: independently reproduced or tested.
- BLOCKED: cannot execute in available environment.

## Session key facts checkpoint (2026-11-25 late)
- Initial HEAD b571b18a79b76ee351f307ced793c6e66c7f22ce, branch master, already dirty/ahead 2 before this session. Exact status in `baseline/initial-state.txt`.
- `re-bench/` was created by this session; no source file has been intentionally modified yet.
- `docs/MAXIMUM_SECURITY.md` is read-only reference; contradictions observed: CLOUD section says stego conflicts with cloud, ABSOLUTE section says conflict no longer applies and includes stego with `platform=github`.
- Parser surfaces measured by `tools/inventory_live.py`: 59 argparse rows in `obfuscator/core/pipeline.py` (45 distinct long flags including subcommands), 30 rows in `scripts/build.py`; 148 NIXON/NX-looking names found, but many are C macros/generated symbols/test fixtures rather than env reads. `tools/env_audit.py` is classifying them.
- Missing from MAXIMUM_SECURITY by simple string scan: 16 scripts.build flags; pipeline `--output`; loader transform keys data-level/remote/remote-bundle; 64 NIXON/NX names (many false-positive non-env names).
- Access parser verified live: field is `expire`, not `expiry`; boolean keys include hwid-lock, bind-mac, one-shot, kod, hostguard, driver-check, name-gate, rename-internal.
- `--licence` unified keys: token, salt, env-only, bootstrap-encrypted, chain. `--web3` keys: rpc, explorer, contract, shards, deploy, deploy-rpc. They are separate purposes.
- pydeobsbench profiles exist for max/absolute/absolute-native-only but do not include all documented ABSOLUTE additions (no lowering/bootstrap-encrypted/chain/platform=github/rename-internal/bind-mac/webhook/TLS bundle).
- No GitHub/GH token or Cloudflare credentials are configured. CLOUD build-farm execution is blocked; audit only. `--package native platform=github` now fails closed without token unless `--skip-cloud`.
- Host tools: Python 3.13.5, Cython 3.2.1, cargo 1.95, g++ 14.2, clang/llvm 19, gdb 16.3, strace/ltrace, file/readelf/objdump/nm, Ghidra at `/usr/local/bin/ghidra` symlink to `~/Tools/Ghidra/ghidraRun`; `analyzeHeadless` not on PATH but likely under `~/Tools/Ghidra/support/analyzeHeadless` (verify). Foundry anvil/forge/cast absent. web3 7.14, solcx and solc 0.8.20/0.8.26 installed; eth-tester/py-evm initially absent; isolated install in `re-bench/evm-venv` running.
- OpenCode v2.4.1 installed. `opencode run` supports `--model`, `--agent`, `--format json`, `--file`, `--auto`, `--standalone`. Providers/models listed: `kern/Qwen/Qwen3.8-27B-FP8`; `local-proxy/deepseek-v4-1-flash-1017`, `local-proxy/deepseek-v4.1-flash`, `local-proxy/zai-glm-5.2`, `local-proxy/zai-glm-5.3`, `local-proxy/zai-glm-5.3-flash`; many mistral/nvidia/openai IDs. OpenCode config shows kern has exactly one enabled model `Qwen/Qwen3.8-27B-FP8`; local-proxy 5 enabled; mistral 15 enabled. OPENAI_BASE_URL is loopback `http://127.0.0.1:8080/v1`; OPENAI_MODEL `mimo-v2.5-free`; KERN_API_KEY and OPENAI_API_KEY are present (values never recorded).
- ERC721 source exists only embedded in `scripts/deploy_erc721_licence.py` (no .sol file). `chain_owner_of` accepts plain HTTP only for literal loopback 127/8 or ::1 and rejects localhost/127.evil.com; tests cover this.
