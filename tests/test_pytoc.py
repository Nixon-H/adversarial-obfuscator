"""Batch-2: REAL --pytoc Cython path — all tests graceful, never fail build."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_pytoc_flag_exists():
    r = subprocess.run(
        [sys.executable, "scripts/build.py", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    out = r.stdout + r.stderr
    assert "--pytoc" in out
    assert "--pytoc-out" in out


def test_pytoc_helper_importable():
    from scripts.phases.phase_pytoc import cythonize_obfuscated, phase_pytoc
    assert callable(cythonize_obfuscated)
    assert callable(phase_pytoc)


def test_pipeline_helper_importable():
    from obfuscator.core.pipeline import compile_payload_to_cython
    assert callable(compile_payload_to_cython)


def test_build_with_pytoc_does_not_crash(tmp_path):
    """Tiny payload through phase_pytoc: either .so appears or skip logged."""
    from scripts.phases.phase_pytoc import phase_pytoc
    src = tmp_path / "tiny.py"
    src.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    out = str(tmp_path / "tiny_pytoc.so")
    built, msg = phase_pytoc(str(src), out)
    assert isinstance(msg, str) and msg
    if built is not None:
        assert os.path.isfile(built)
        assert os.path.getsize(built) > 0
    else:
        assert "skip" in msg.lower()


def test_skip_if_no_compiler_handled(monkeypatch, tmp_path):
    """Missing toolchain degrades to (None, reason) instead of raising."""
    import shutil as _shutil
    from scripts.phases.phase_pytoc import phase_pytoc as _phase_pytoc
    monkeypatch.setattr(_shutil, "which", lambda *a, **k: None)
    src = tmp_path / "tiny2.py"
    src.write_text("x = 1\n", encoding="utf-8")
    built, msg = _phase_pytoc(str(src), str(tmp_path / "o.so"))
    assert built is None
    assert "skip" in msg.lower()


def test_missing_source_graceful(tmp_path):
    from scripts.phases.phase_pytoc import phase_pytoc
    built, msg = phase_pytoc(str(tmp_path / "nope.py"), str(tmp_path / "o.so"))
    assert built is None
    assert "skip" in msg.lower()
