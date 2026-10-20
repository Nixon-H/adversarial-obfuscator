"""
test_pipeline.py

Tests for the main build pipeline (scripts/build.py).

Test coverage:
- Positive tests verify obfuscation-only and full pipeline execution
- Negative tests verify graceful handling of missing payload
"""
import subprocess
import sys
import os
import tempfile

PIPELINE = os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")


def test_pipeline_obfuscate_only():
    """Run pipeline with --skip-relay on a trivial payload."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("print('hello')\n")
        payload = f.name

    result = subprocess.run(
        [sys.executable, PIPELINE, "--payload", payload, "--skip-relay",
         "--skip-llvmgen", "--skip-encrypt",
         "--no-cfg-flatten", "--no-opaque-predicates", "--no-bogus-exceptions",
         "--no-mba-subs", "--no-fragment-strings", "--no-unicode-ids"],
        capture_output=True, text=True, timeout=30,
    )
    os.unlink(payload)
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
    if result.stdout or result.stderr:
        assert "DONE" in result.stdout or "DONE" in result.stderr


def test_pipeline_with_obfuscation():
    """Run full obfuscation pipeline (LLVM/encrypt skipped — known WIP)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("x = 1\ny = x + 2\nprint(y)\n")
        payload = f.name

    result = subprocess.run(
        [sys.executable, PIPELINE, "--payload", payload, "--skip-relay",
         "--skip-llvmgen", "--skip-encrypt",
         "--fragment-strings"],
        capture_output=True, text=True, timeout=30,
    )
    os.unlink(payload)
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"


def test_pipeline_missing_payload():
    """Pipeline should fail gracefully on missing input."""
    result = subprocess.run(
        [sys.executable, PIPELINE, "--payload", "/nonexistent.py", "--skip-relay"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
