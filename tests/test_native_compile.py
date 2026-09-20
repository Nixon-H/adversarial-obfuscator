import os
import subprocess
import pytest

MAKEFILE_DIR = os.path.join(os.path.dirname(__file__), "..")


def _has_mingw():
    try:
        subprocess.run(
            ["x86_64-w64-mingw32-gcc", "--version"],
            capture_output=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _has_python_h():
    try:
        subprocess.run(
            ["g++", "-E", "-x", "c++", "-"],
            input=b"#include <Python.h>\n",
            capture_output=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    result = subprocess.run(
        ["g++", "-E", "-x", "c++", "-"],
        input=b"#include <Python.h>\n",
        capture_output=True, timeout=5,
    )
    return result.returncode == 0


def test_stub_linux():
    result = subprocess.run(
        ["make", "stub-linux"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"stub-linux failed:\n{result.stderr}"


@pytest.mark.skipif(not _has_mingw(), reason="x86_64-w64-mingw32-gcc not available")
def test_stub_win():
    result = subprocess.run(
        ["make", "stub-win"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"stub-win failed:\n{result.stderr}"


def test_vm_stub():
    result = subprocess.run(
        ["make", "vm-stub"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"vm-stub failed:\n{result.stderr}"


@pytest.mark.skipif(not _has_mingw(), reason="x86_64-w64-mingw32-gcc not available")
def test_vm_stub_win():
    result = subprocess.run(
        ["make", "vm-stub-win"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"vm-stub-win failed:\n{result.stderr}"


@pytest.mark.skipif(not _has_python_h(), reason="Python.h not found")
def test_core_cpp():
    result = subprocess.run(
        ["make", "core-cpp"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"core-cpp failed:\n{result.stderr}"
