# Agent Notes

## Verification commands

- Focused pytest runs should use the fast local pytest installation and a writable temp directory:
  `TMPDIR=/home/nixon/absmax-tmp /home/nixon/.local/bin/pytest -q <tests> --tb=short -p no:cacheprovider`
- The full test tree is large. Use bounded partitions instead of a single serial run:
  `TMPDIR=/home/nixon/absmax-tmp TEST_PARTITION_PYTEST_RUNNER=/home/nixon/absmax-runner/run_pytest.py python3 scripts/run_test_partitions.py --timeout 1800 --test-timeout 120 --out-dir <output-dir>`
- `scripts/run_pytest.py` is the spawn-safe pytest entry point used by the partition runner. It is tracked test infrastructure; if a long-running environment loses the working-tree file, copy it to `/home/nixon/absmax-runner/run_pytest.py` outside the pytest temporary root and set `TEST_PARTITION_PYTEST_RUNNER` for multi-partition runs.

## ABSOLUTE MAXIMUM benchmark evidence

- Do not modify the authoritative benchmark artifacts under `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds/`; benchmark validity depends on their fixed SHA-256 identities.
- Provider, timeout, harness, malformed-answer, and over-tool-limit records are invalid evidence, not resistance evidence.
- Kern, OpenCode Go, and TokenHarbor benchmark lanes are separate model lanes. The operator-directed primary lane is `opencode-go/deepseek-v4.1-flash` with cache-hit telemetry. The prior Kern lane is `kern/inkling-2-mini`; TokenHarbor fallback lanes are `tokenharbor/deepseek-v4.1-flash`, `tokenharbor/deepseek-v4.1-flash:free`, and `tokenharbor/deepseek-v4.1-flash-1017`. The operator explicitly authorised the non-`:free` DeepSeek lane for cache-aware continuation on 2026-11-26; record cache-hit telemetry but never prompts, completions, or credentials. The retired OpenCode/Hy4 lane is not part of new benchmark campaigns unless the operator explicitly re-authorises it. Do not substitute unauthorized models. Use exactly one benchmark runner or multi-lane resume watchdog at a time.
- Benchmark secrets and licence-derived keys must remain outside agent sandboxes and must be redacted from provider-bound traffic.
- Evidence redaction verification uses `python3 re-bench/tools/redact_benchmark_credentials.py` followed by `python3 re-bench/tools/scan_secret_redaction.py`; the scanner covers raw results, live copied workspaces, OpenCode state, historical invalid/smoke roots, copied OpenCode home, action-verification output, scratch evidence, and proxy operational logs across exact/JSON/base64/hex representations and should report `credential_hits=0`.

## Local environment caveat

- `/tmp` has been full on this host because of pre-existing data. Tests that hard-code `/tmp` can fail with `ENOSPC`; use pytest `tmp_path` in tests and `TMPDIR=/home/nixon/absmax-tmp` in commands.

## Commit message convention

- Do NOT add "Generated with ..." tool attribution lines or "Co-Authored-By:" agent trailers to commit messages. History was rewritten on 2026-11-27 to remove them project-wide at the owner's request; keep all future commits free of them.
