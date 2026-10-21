"""c_core_build.py

Purpose:
    Build the C core (``nixon_core.so``) that the FHE/ORAM bootstrap
    loads at run time.

Architectural Role:
    The loader loads ``nixon_core.so`` from the directory of its own
    file -- the artifact's directory.  Nothing used to build it there,
    so the loader always fell back to the pure-Python path, where
    ``encrypt_batch``/``dec_batch`` are no-ops: the FHE bootstrap
    verified nothing while the build report counted FHE and ORAM as
    enabled.

    One helper, so both build paths (the loader CLI and the native
    pipeline) put the library where the loader will look for it.

Security Relevance:
    The C backend is the FHE/ORAM bootstrap's real implementation.  The
    pure-Python fallback stays -- a host without a compiler must still
    run the artifact -- but it is a no-op, so the build says which one
    is in play.
"""

from __future__ import annotations

import os
import subprocess
import sysconfig

LIB_NAME = "nixon_core.so"

SOURCES = ("native/core.cpp", "native/whitebox_feistel.cpp")

#: The symbols the LOADER looks for.  ``FHE_*`` and ``ORAM_*`` are not
#: implemented in the C sources, so the loader's FHE/ORAM bootstrap
#: always takes its pure-Python fallback -- where encrypt_batch and
#: dec_batch are no-ops.  The build reports which of these are present
#: rather than implying the accelerated backend is in play.
LOADER_SYMBOLS = ("FHE_new", "FHE_encrypt_batch", "FHE_dec_batch",
                   "ORAM_new", "ORAM_access")


def _exported_symbols(path: str) -> set:
    """The dynamic symbols the library exports (best effort)."""
    try:
        import subprocess as _sp
        out = _sp.run(["nm", "-D", "--defined-only", path],
                      capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return set()
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] in ("T", "W", "D", "B"):
            names.add(parts[2])
    return names


def _root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_c_core(output_dir: str, root: str | None = None) -> str | None:
    """Compile the C core into ``output_dir``; return the path, or None.

    None means the library could not be built (no compiler, no
    sources, a build error).  The caller decides what to do about it;
    the loader's pure-Python fallback covers the gap.
    """
    base = root or _root()
    sources = [os.path.join(base, s) for s in SOURCES]
    if not all(os.path.exists(s) for s in sources):
        return None
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError:
        return None
    out_path = os.path.join(output_dir, LIB_NAME)
    try:
        include = sysconfig.get_paths()["include"]
    except Exception:
        include = ""
    libdir = sysconfig.get_config_var("LIBDIR") or ""
    ldversion = sysconfig.get_config_var("LDVERSION") or ""
    libname = ("python" + ldversion) if ldversion else "python3"
    cmd = (["g++", "-O2", "-fPIC", "-shared", "-std=c++17",
            "-DCORE_HAVE_PYTHON_H", "-o", out_path] + sources +
           ["-I" + include, "-L" + libdir, "-l" + libname, "-ldl", "-lm"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return out_path if os.path.exists(out_path) else None


def missing_loader_symbols(path: str) -> list:
    """Which of the loader's symbols the library does NOT export.

    An empty list means the loader's FHE/ORAM backend can be used.
    A non-empty list means the loader will fall back to its
    pure-Python path, where the FHE encrypt/decrypt are no-ops.
    """
    exported = _exported_symbols(path)
    if not exported:
        # nm unavailable: say nothing rather than guess.
        return []
    return [s for s in LOADER_SYMBOLS if s not in exported]
