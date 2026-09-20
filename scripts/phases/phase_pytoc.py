"""phase_pytoc.py — REAL Cython PYTOC path (batch 2).

cythonize_obfuscated(source_path, out_path) compiles an obfuscated .py file
to a native extension (<out>_pytoc.<so/pyd>) via Cython.Build.cythonize +
setuptools in an isolated temp dir, then copies the built extension to
out_path.

Degrades gracefully: missing Cython/setuptools/compiler -> (None, reason),
never raises. Reuses obfuscator.core.pipeline.compile_payload_to_cython when
importable (its base64-blob path), else a small inline implementation that
writes the .so bytes directly.
"""

from __future__ import annotations

import glob
import os
import shutil as _shutil
import subprocess
import sys
import tempfile


def _compiler_available() -> bool:
    return _shutil.which("gcc") is not None or _shutil.which("cc") is not None


def cythonize_obfuscated(source_path: str, out_path: str) -> tuple[str | None, str]:
    """Compile *source_path* to a native extension at *out_path*.

    Returns (built_path, message). built_path is None when skipped
    (missing toolchain) — the caller must log the message and continue.
    """
    if not os.path.isfile(source_path):
        return None, f"pytoc skip: source not found: {source_path}"
    try:
        import Cython  # noqa: F401
    except Exception as e:
        return None, f"pytoc skip: Cython not installed ({e})"
    try:
        import setuptools  # noqa: F401
    except Exception as e:
        return None, f"pytoc skip: setuptools not installed ({e})"
    if not _compiler_available():
        return None, "pytoc skip: no C compiler (gcc/cc) found"

    # Fast path: reuse the pipeline helper (returns base64 of the .so).
    try:
        from obfuscator.core.pipeline import compile_payload_to_cython as _pipe_cython
    except Exception:
        _pipe_cython = None
    if _pipe_cython is not None:
        try:
            import base64

            b64 = _pipe_cython(source_path, os.path.dirname(os.path.abspath(out_path)))
            if b64:
                with open(out_path, "wb") as f:
                    f.write(base64.b64decode(b64))
                return out_path, f"pytoc built via pipeline helper: {out_path}"
        except Exception as e:
            return None, f"pytoc skip: pipeline helper failed ({e})"
        return None, "pytoc skip: pipeline helper produced no artifact"

    # Inline fallback: cythonize in an isolated temp dir.
    build_dir = tempfile.mkdtemp(prefix="pytoc_")
    try:
        with open(source_path, encoding="utf-8") as f:
            code = f.read()
        pyx_path = os.path.join(build_dir, "pytoc_mod.pyx")
        with open(pyx_path, "w", encoding="utf-8") as f:
            f.write("# cython: language_level=3\n" + code)
        setup_path = os.path.join(build_dir, "setup.py")
        with open(setup_path, "w", encoding="utf-8") as f:
            f.write(
                "from setuptools import setup\n"
                "from Cython.Build import cythonize\n"
                "setup(name='pytoc_mod', "
                "ext_modules=cythonize('pytoc_mod.pyx', "
                "compiler_directives={'language_level': 3}))\n"
            )
        res = subprocess.run(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=build_dir, capture_output=True, text=True, timeout=600,
        )
        if res.returncode != 0:
            tail = (res.stderr or res.stdout or "")[-2000:]
            return None, f"pytoc skip: cython build failed ({tail})"
        cands = sorted(
            glob.glob(os.path.join(build_dir, "pytoc_mod*.so"))
            + glob.glob(os.path.join(build_dir, "pytoc_mod*.pyd"))
        )
        if not cands:
            return None, "pytoc skip: no extension artifact produced"
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        _shutil.copy2(cands[0], out_path)
        return out_path, f"pytoc built: {out_path}"
    except Exception as e:
        return None, f"pytoc skip: {e}"
    finally:
        _shutil.rmtree(build_dir, ignore_errors=True)


def phase_pytoc(obfuscated_path: str, out_path: str | None = None) -> tuple[str | None, str]:
    """Best-effort wrapper used by build.py. Never raises."""
    try:
        if not obfuscated_path or not os.path.isfile(obfuscated_path):
            return None, "pytoc skip: obfuscated output missing"
        if out_path is None:
            base, _ = os.path.splitext(obfuscated_path)
            out_path = base + "_pytoc.so"
        return cythonize_obfuscated(obfuscated_path, out_path)
    except Exception as e:
        return None, f"pytoc skip: {e}"
