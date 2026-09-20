import subprocess
import os
import pytest

RELAY_BIN = os.path.join(os.path.dirname(__file__), "..", "build", "orbital-relay")


def test_relay_binary_exists():
    assert os.path.exists(RELAY_BIN), f"Binary not found: {RELAY_BIN}"


def test_relay_help():
    result = subprocess.run([RELAY_BIN, "--help"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "Usage:" in result.stdout or "Usage" in result.stdout


def test_relay_version():
    result = subprocess.run([RELAY_BIN, "--version"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
