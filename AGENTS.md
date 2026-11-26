# Agent Notes

## Verification commands

- Focused pytest runs should use the fast local pytest installation and a writable temp directory:
  `TMPDIR=/home/nixon/absmax-tmp /home/nixon/.local/bin/pytest -q <tests> --tb=short -p no:cacheprovider`
- The full test tree is large. Use bounded partitions instead of a single serial run:
  `TMPDIR=/home/nixon/absmax-tmp TEST_PARTITION_PYTEST_RUNNER=/home/nixon/absmax-tmp/run_pytest.py python3 scripts/run_test_partitions.py --timeout 1800 --test-timeout 120 --out-dir <output-dir>`
- `scripts/run_pytest.py` is the spawn-safe pytest entry point used by the partition runner. It is untracked local test infrastructure and disappeared once during a long run; copy it to `/home/nixon/absmax-tmp/run_pytest.py` and set `TEST_PARTITION_PYTEST_RUNNER` for multi-partition runs.

## ABSOLUTE MAXIMUM benchmark evidence

- Do not modify the authoritative benchmark artifacts under `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds/`; benchmark validity depends on their fixed SHA-256 identities.
- Provider, timeout, harness, malformed-answer, and over-tool-limit records are invalid evidence, not resistance evidence.
- TokenHarbor and OpenCode/Hy4 benchmark lanes are separate model lanes. Authorised lanes are `opencode/hy4-flash-free`, `tokenharbor/deepseek-v4.1-flash:free`, and fallback `tokenharbor/deepseek-v4.1-flash-1017`; do not substitute unauthorized models. Use exactly one multi-lane resume watchdog.
- Benchmark secrets and licence-derived keys must remain outside agent sandboxes and must be redacted from provider-bound traffic.
- Evidence redaction verification uses `python3 re-bench/tools/redact_benchmark_credentials.py` followed by `python3 re-bench/tools/scan_secret_redaction.py`; the scanner covers raw results, live copied workspaces, OpenCode state, historical invalid/smoke roots, copied OpenCode home, action-verification output, scratch evidence, and proxy operational logs across exact/JSON/base64/hex representations and should report `credential_hits=0`.

## Local environment caveat

- `/tmp` has been full on this host because of pre-existing data. Tests that hard-code `/tmp` can fail with `ENOSPC`; use pytest `tmp_path` in tests and `TMPDIR=/home/nixon/absmax-tmp` in commands.
