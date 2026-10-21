"""The FHE/ORAM C backend must be reachable, and the build must be honest.

The loader loads ``nixon_core.so`` from the directory of its own file
-- the artifact's directory.  Nothing used to build it there, so the
loader always fell back to its pure-Python path, where ``encrypt_batch``
and ``dec_batch`` are NO-OPS: the FHE bootstrap verified nothing while
the build reported FHE and ORAM as enabled.

Two things are checked here:

* the library is built NEXT TO THE ARTIFACT, so the loader can find it;
* the build says which of the loader's symbols the library actually
  exports, so an unimplemented backend is not passed off as working.
"""

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.skipif(
    subprocess.run(["sh", "-c", "command -v g++ >/dev/null"],
                   capture_output=True).returncode != 0,
    reason="no C++ compiler")


def _build(tmp_path):
    source = os.path.join(str(tmp_path), "hello.py")
    with open(source, "w", encoding="utf-8") as fh:
        fh.write('print("C-CORE-WIRING")\n')
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build", source,
         "--net-url", "https://127.0.0.1:9443/"],
        cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-1000:]
    artifact = os.path.join(str(tmp_path), "dist", "hello_protected.py")
    assert os.path.exists(artifact), proc.stdout[-2000:]
    return artifact, proc.stdout


def test_the_c_core_is_built_next_to_the_artifact(tmp_path):
    """The loader looks beside its own file, so the library goes there."""
    artifact, _out = _build(tmp_path)
    core = os.path.join(os.path.dirname(artifact), "nixon_core.so")
    assert os.path.exists(core), (
        "the C core was not built next to the artifact, so the loader "
        "cannot load it: %s" % core)


def test_the_build_reports_the_loader_symbols_it_is_missing(tmp_path):
    """An unimplemented backend must not be reported as working.

    ``FHE_new``/``ORAM_new`` do not exist in the C sources, so the
    loader's FHE/ORAM bootstrap always falls back to no-ops.  The build
    has to say so.
    """
    from obfuscator.core.c_core_build import missing_loader_symbols

    artifact, out = _build(tmp_path)
    core = os.path.join(os.path.dirname(artifact), "nixon_core.so")
    missing = missing_loader_symbols(core)
    if missing:
        assert "does NOT export" in out, (
            "the build did not report the missing loader symbols %r" % (missing,))
        assert "no-ops" in out


def test_the_loader_symbols_are_not_in_the_c_sources():
    """The FHE/ORAM C backend is unimplemented; that is a known gap.

    This test records the fact rather than asserting a fix: if the
    symbols ever appear, it fails and points at the stale warning.
    """
    from obfuscator.core.c_core_build import LOADER_SYMBOLS

    found = set()
    for name in ("core.cpp", "whitebox_feistel.cpp"):
        path = os.path.join(ROOT, "native", name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        for symbol in LOADER_SYMBOLS:
            if symbol in text:
                found.add(symbol)
    assert not found, (
        "the C core now defines %r -- the build's \"FHE/ORAM fallback is "
        "a no-op\" warning is stale" % (sorted(found),))
