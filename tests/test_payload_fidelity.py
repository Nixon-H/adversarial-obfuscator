"""Payload-fidelity regressions found by the 2026-11-17 edge-case benchmark.

Two functional defects, both with security-adjacent causes:

1. **Spawn multiprocessing was broken.**  A spawn child re-imports the
   artefact as ``__mp_main__`` and unpickles the parent's target function
   by name.  The loader ran the payload only under ``__main__``, so the
   child had no payload functions at all ("Can't get attribute ... on
   <module '__mp_main__'>").  The entry now runs for both names, and the
   identity gate applies the SAME ``__file__``/``argv[0]`` check to both —
   measured: a real spawn child has both, so nothing is weakened.

2. **The payload's exit code was rewritten to 1.**  ``except BaseException``
   around the payload exec also caught ``SystemExit``, so ``sys.exit(7)``
   exited 1 — a silent contract break for CI gates and ``--fail`` flags.
   ``SystemExit`` is control flow: the loader wipes and re-raises it.
"""
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script  # noqa: E402
from obfuscator.core.sources import IDENTITY_GATE_TOP  # noqa: E402

_BLANKS = {"native_blobs": "", "fallback_blob": ""}


def _loader(**kw):
    kw.setdefault("identity_gate", False)
    kw.setdefault("self_check", False)
    return generate_hybrid_loader_script(dict(_BLANKS), b"", "11" * 32, **kw)[0]


# --- 1. spawn multiprocessing ------------------------------------------------

def test_loader_entry_runs_for_mp_main():
    src = _loader()
    assert 'if __name__ in ("__main__", "__mp_main__"):' in src
    # and NOT the old main-only form
    assert 'if __name__ == "__main__":\n    _load_native()' not in src


def test_identity_gate_applies_the_same_check_to_both_names():
    """No weakening: __mp_main__ gets the file/argv agreement check too."""
    assert 'not in ("__main__", "__mp_main__")' in IDENTITY_GATE_TOP
    assert "_me != _av" in IDENTITY_GATE_TOP
    # the gate must not have a per-name exemption
    assert IDENTITY_GATE_TOP.count("_me = _nx_id_os.path.abspath") == 1
    assert IDENTITY_GATE_TOP.count("_av = _nx_id_os.path.abspath") == 1


def test_fake_mp_main_still_needs_a_matching_script():
    """A foreign exec claiming __mp_main__ without a file context dies."""
    ns = {"__name__": "__mp_main__"}
    with pytest.raises(SystemExit) as exc:
        exec(compile(IDENTITY_GATE_TOP, "<gate>", "exec"), ns)
    assert exc.value.code == 2


def test_real_spawn_child_passes_the_gate(tmp_path):
    """End-to-end: a genuine spawn child satisfies the gate."""
    script = tmp_path / "spawn_check.py"
    script.write_text(
        "import multiprocessing as mp, sys\n"
        "sys.path.insert(0, %r)\n"
        "from obfuscator.core.sources import IDENTITY_GATE_TOP\n"
        "def child(q):\n"
        "    try:\n"
        "        exec(compile(IDENTITY_GATE_TOP, '<g>', 'exec'), globals())\n"
        "        q.put('PASSED')\n"
        "    except SystemExit as e:\n"
        "        q.put('BLOCKED-%%s' %% e.code)\n"
        "if __name__ == '__main__':\n"
        "    ctx = mp.get_context('spawn')\n"
        "    q = ctx.Queue()\n"
        "    p = ctx.Process(target=child, args=(q,))\n"
        "    p.start(); p.join()\n"
        "    print(q.get())\n" % (REPO_ROOT,),
        encoding="utf-8")
    proc = subprocess.run([sys.executable, str(script)], cwd=str(tmp_path),
                          capture_output=True, text=True, timeout=180,
                          env=dict(os.environ, PYTHONPATH=REPO_ROOT,
                                   NIXON_LOG_REDIRECT="0"))
    assert proc.returncode == 0, proc.stderr[-800:]
    assert "PASSED" in proc.stdout, proc.stdout + proc.stderr


# --- 2. exit-code fidelity ---------------------------------------------------

def test_loader_preserves_payload_system_exit():
    src = _loader()
    assert "if isinstance(e, SystemExit):" in src
    assert "raise" in src


def test_system_exit_survives_the_wrapper(tmp_path):
    """A payload's sys.exit(N) must reach the shell unchanged."""
    probe = tmp_path / "p.py"
    probe.write_text(
        "import sys\n"
        "try:\n"
        "    sys.exit(7)\n"
        "except BaseException as e:\n"
        "    if isinstance(e, SystemExit):\n"
        "        raise\n"
        "    sys.exit(1)\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(probe)], capture_output=True,
                          text=True, timeout=60)
    assert proc.returncode == 7, proc.returncode


# --- 3. darwin blob importability --------------------------------------------

def test_darwin_blob_extracts_as_so_not_dylib():
    """CPython's macOS extension suffixes do not include .dylib.

    The loader extracted the darwin native blob as ``.dylib`` and then called
    ``spec_from_file_location`` with no explicit loader -- on macOS that
    returns None (.dylib is not in EXTENSION_SUFFIXES), so the darwin blob
    was dead weight and macOS silently fell back to bytecode.  The artefact
    must extract as ``.so`` AND pass an explicit ExtensionFileLoader.
    """
    src = _loader()
    assert 'ext = ".so"' in src, "darwin extraction must use the .so suffix"
    assert 'ext = ".dylib"' not in src, "the broken .dylib extraction is back"
    assert "ExtensionFileLoader" in src, (
        "the import must pass an explicit loader so any OS suffix works")


def test_windows_and_linux_blob_extracts_are_untouched():
    """The per-OS naming convention: windows .pyd, linux .so."""
    src = _loader()
    assert 'blob_key = "windows"' in src and 'ext = ".pyd"' in src
    assert 'blob_key = "linux"' in src and 'ext = ".so"' in src
