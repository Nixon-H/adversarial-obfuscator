# Archive — non-core / generated material (2026-09-04)

Moved out of the repo root during folder organization. Nothing here is
part of the obfuscator pipeline. All paths below are relative to `archive/`.

## demo_unrelated/
- `Love.py` — manim heart-animation demo (284 lines, imports `manim`/`numpy`).
  Unrelated to obfuscation; was only ever used as a sample payload.
- `Love_adaptive.py` — 3.6 MB obfuscated output of `Love.py` (build artifact).

## bench_outputs/
Generated benchmark / adversarial-loop outputs (regenerable via
`benchmark_ai_resistance.py` / `adversarial_loop.py`):
- `benchmark_output/`, `benchmark_output_v2/` … `benchmark_output_v7/`,
  `benchmark_output_fresh/` — per-run model results (`report.html/pdf`,
  `summary.json`, `*_result.txt`)
- `deobf_results/` — 3 deobfuscation sample outputs
- `adversarial_output/` (`round_001`–`round_003`) + `adversarial_state.json`
  — adversarial training loop state (target achieved: 3/3 PROOF rounds)

## artifacts/
Large / stale one-off artifacts:
- `invariant_engine_report.json` (~79 MB) — invariant-engine dump
- `pipeline*.prof` (4 files) — profiler dumps
- `build.log`, `build_error.log` — stale build logs
- `error_codes.json` — placeholder (`{"E0001": "Invalid input"}`)
- `task_plan.md` — stale adversarial-loop task plan (status: Phase 1)

## originals_backup/
Backups of obfuscator core modules predating the adversarial loop
(`attention_poison.py`, `dataflow.py`, `decoy_apis.py`,
`reasoning_traps.py`, `transforms.py`). Kept for diffing only.

## Related files intentionally LEFT at repo root
`adversarial_loop.py`, `benchmark_ai_resistance.py`, `ai-obfuscator.py`,
`sample_ai_proof.py`, `test_ai_proof.py`, `test_deobf_models.py` are the
AI-resistance eval harness and ARE obfuscator-related. They stay at root
because `adversarial_loop.py` resolves sibling paths via
`Path(__file__).parent` — moving them into a subdir would break
`BENCHMARK_SCRIPT`, `SOURCE_PAYLOAD`, `BUILD_SCRIPT`, `TRANSFORMS`, etc.

## Other moves in the same cleanup
- `attack_report.md`, `claim_validation.md`, `runtime_verification.md`
  → `docs/reports/` (related documentation, not archive)
- `run_all_flags.sh` → `scripts/run_all_flags.sh` (pipeline runner; note it
  hardcodes `cd /home/nixon/Desktop/2` and `--payload Love.py`, so it needs
  path updates before reuse)
- Deleted 21× `.build_tmp_*_obfuscated.py` temp files (gitignored regenerables)
  and top-level `__pycache__/`.
