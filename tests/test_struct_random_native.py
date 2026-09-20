"""Tests that native/struct_random.c compiles cleanly."""

import os
import subprocess
import pytest

MAKEFILE_DIR = os.path.join(os.path.dirname(__file__), "..")


def test_struct_random_c_compiles():
    result = subprocess.run(
        ["make", "struct-random-c"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"struct-random-c failed:\n{result.stderr}"
