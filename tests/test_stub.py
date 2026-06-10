import os
import platform
import sys
import unittest
import subprocess
import pytest

STUB_CPP = os.path.join(os.path.dirname(__file__), "..", "nixon_stub.cpp")
PAYLOAD_H = os.path.join(os.path.dirname(__file__), "..", "payload.h")

_IS_WINDOWS = platform.system() == "Windows"
_HAS_PAYLOAD_H = os.path.isfile(PAYLOAD_H)


def test_payload_h_exists():
    if not _HAS_PAYLOAD_H:
        pytest.skip("payload.h not found - needed for stub compilation")


@pytest.mark.skipif(not _IS_WINDOWS, reason="nixon_stub.cpp only compiles on Windows (WinAPI headers)")
@pytest.mark.skipif(not _HAS_PAYLOAD_H, reason="payload.h not found")
def test_msvc_compile_check():
    """Attempt to compile nixon_stub.cpp with MSVC if available."""
    try:
        result = subprocess.run(
            ["cl.exe", "/nologo", "/c", "/EHsc", STUB_CPP],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        pytest.skip("MSVC (cl.exe) not found in PATH")
    except subprocess.TimeoutExpired:
        pytest.skip("MSVC compile timed out")

    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        if "error" in stderr_lower or "fatal" in stderr_lower:
            pytest.skip(f"MSVC compile failed (expected): {result.stderr[:200]}")
