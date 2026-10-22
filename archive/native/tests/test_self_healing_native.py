"""Tests that native/self_healing.c compiles cleanly."""

import os
import subprocess

MAKEFILE_DIR = os.path.join(os.path.dirname(__file__), "..")


def test_self_healing_c_compiles():
    result = subprocess.run(
        ["make", "self-healing-c"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"self-healing-c failed:\n{result.stderr}"
