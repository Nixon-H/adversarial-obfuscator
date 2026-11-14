"""The injected integrity check must be valid LLVM IR."""
import shutil
import subprocess

import pytest

from llvmgen.integrity import inject_integrity_check

MODULE = """target datalayout = "e-m:e-p270:32:32"
target triple = "x86_64-pc-linux-gnu"
define i32 @main() {
entry:
  ret i32 3
}
"""


def test_integrity_injection_keeps_the_preamble_first():
    out = inject_integrity_check(MODULE)
    assert "@__shadow_ir_blob" in out
    assert "@llvm.global_ctors" in out
    # `target triple` must stay above the injected functions.
    assert out.index("target triple") < out.index(
        "define void @__shadow_integrity_check")


@pytest.mark.skipif(shutil.which("llc") is None, reason="llc not installed")
def test_integrity_injection_assembles(tmp_path):
    out = inject_integrity_check(MODULE)
    path = tmp_path / "module.ll"
    path.write_text(out)
    proc = subprocess.run(["llc", str(path), "-o", str(tmp_path / "m.o")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
