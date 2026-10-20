"""The Rust relay binary.

The relay is a Rust crate: these tests need ``build/orbital-relay``,
which only exists after ``make relay`` (a cargo build).  They are skipped
when it has not been built, like the other toolchain-gated tests in this
suite -- a missing build artifact is not a defect, and failing on it
made the suite red for anyone who had not run ``make relay`` first.
"""
import subprocess
import os
import pytest

RELAY_BIN = os.path.join(os.path.dirname(__file__), "..", "build", "orbital-relay")


def _relay_bin():
    if not os.path.exists(RELAY_BIN):
        pytest.skip("relay binary not built (run `make relay`)")
    return RELAY_BIN


def test_relay_binary_exists():
    _relay_bin()  # skips with a clear message when `make relay` was not run
    assert os.path.exists(RELAY_BIN), f"Binary not found: {RELAY_BIN}"


def test_relay_help():
    result = subprocess.run([_relay_bin(), "--help"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "Usage:" in result.stdout or "Usage" in result.stdout


def test_relay_version():
    result = subprocess.run([_relay_bin(), "--version"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
