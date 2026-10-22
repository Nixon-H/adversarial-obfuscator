"""Native compile checks for the sources the product actually builds.

The compile-test corpus (stub_linux, stub_win, vm_stub, microjit,
crypto_chain, key_evolution, gpu_stub, self_healing, struct_random,
cross_process, distributed_vm, fragment_migration) was archived on
2026-10-23 — see archive/native/README.md.  Its tests moved with it; a
test for code that does not ship proves nothing and keeps the dead
corpus alive.

What remains here is what the product builds: core.cpp (and, via
`make native-test`, simd_vm.c).
"""
import os
import subprocess

import pytest

MAKEFILE_DIR = os.path.join(os.path.dirname(__file__), "..")


def _has_python_h():
    try:
        result = subprocess.run(
            ["g++", "-E", "-x", "c++", "-"],
            input=b"#include <Python.h>\n",
            capture_output=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@pytest.mark.skipif(not _has_python_h(), reason="Python.h not found")
def test_core_cpp():
    result = subprocess.run(
        ["make", "core-cpp"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"core-cpp failed:\n{result.stderr}"


def test_simd_vm_c():
    result = subprocess.run(
        ["make", "simd-vm-c"],
        cwd=MAKEFILE_DIR, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"simd-vm-c failed:\n{result.stderr}"


def test_archived_targets_are_gone():
    """A stale target is how the corpus creeps back."""
    makefile = open(os.path.join(MAKEFILE_DIR, "Makefile")).read()
    for target in ("stub-linux:", "stub-win:", "vm-stub:", "microjit-so:",
                   "crypto-chain:", "gpu-stub-c:", "self-healing-c:",
                   "struct-random-c:"):
        assert target not in makefile, f"{target} still exists in the Makefile"
