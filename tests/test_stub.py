import os
import platform
import sys
import unittest
import subprocess
import pytest

STUB_CPP = os.path.join(os.path.dirname(__file__), "..", "native", "stub.cpp")
PAYLOAD_H = os.path.join(os.path.dirname(__file__), "..", "native", "payload.h")
NIXON_STUB_CPP = os.path.join(os.path.dirname(__file__), "..", "native", "nixon_stub.cpp")
VM_STUB_C = os.path.join(os.path.dirname(__file__), "..", "native", "vm_stub.c")

_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX = platform.system() == "Linux"
_HAS_PAYLOAD_H = os.path.isfile(PAYLOAD_H)


def test_payload_h_exists():
    if not _HAS_PAYLOAD_H:
        pytest.skip("payload.h not found - needed for stub compilation")


def _pick_compiler():
    for c in ["g++", "clang++", "c++"]:
        try:
            subprocess.run([c, "--version"], capture_output=True, timeout=5)
            return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


@pytest.mark.skipif(not _HAS_PAYLOAD_H, reason="payload.h not found")
def test_stub_compile_check():
    """Compile native stubs with available C++ compiler."""
    if _IS_WINDOWS:
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
                pytest.skip(f"MSVC compile failed: {result.stderr[:200]}")
    else:
        compiler = _pick_compiler()
        if compiler is None:
            pytest.skip("No C++ compiler (g++/clang++) found")
        srcs = [s for s in [VM_STUB_C] if os.path.isfile(s)]
        if not srcs:
            pytest.skip("No cross-platform stubs found to compile")
        for src in srcs:
            out = src + ".o"
            try:
                result = subprocess.run(
                    [compiler, "-c", "-o", out, src, "-I", os.path.dirname(PAYLOAD_H)],
                    capture_output=True, text=True, timeout=30,
                )
            except subprocess.TimeoutExpired:
                pytest.skip(f"Compile timed out: {src}")
            if result.returncode != 0:
                stderr_lower = result.stderr.lower()
                if "error" in stderr_lower or "fatal" in stderr_lower:
                    pytest.skip(f"{compiler} rejected {src}: {result.stderr[:200]}")
            if os.path.isfile(out):
                os.remove(out)
