"""Wiring tests for Phase-4 tested-but-unwired modules.

Covers: build.py --help shows new flags; generate_hybrid_loader_script
defaults unchanged (no hostguard text when False); hostguard True includes
bind_host; loader always includes secure-temp + vm snippet markers; macros
apply no-op on clean source; hwid_lock kwargs accepted.
"""
import ast
import inspect
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script, prepare_obfuscated_source
from obfuscator.macros import apply_macros

BUILD_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_KEY = "00" * 32


def test_build_help_shows_new_flags():
    r = subprocess.run(
        [sys.executable, BUILD_PY, "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    out = r.stdout + r.stderr
    for flag in ("--hwid", "--trial", "--vm-threshold", "--kod",
                 "--hostguard", "--hwid-lock", "--sign-key-env"):
        assert flag in out, flag


def test_build_help_defaults():
    r = subprocess.run(
        [sys.executable, BUILD_PY, "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert "--opt-level" in out  # pre-existing default-4 ladder untouched


def test_loader_signature_defaults():
    sig = inspect.signature(generate_hybrid_loader_script)
    params = sig.parameters
    assert params["hwid"].default == ""
    assert params["trial_seconds"].default is None
    assert params["vm_threshold"].default == 50.0
    assert params["kod"].default is False
    assert params["hostguard"].default is False
    assert params["hwid_lock"].default is False


def test_loader_default_has_no_hostguard():
    src, _, _ = generate_hybrid_loader_script(_BLANKS, b"", _KEY)
    compile(src, "<t>", "exec")
    assert "bind_host" not in src
    assert "check_host" not in src
    assert "isolated_exec" not in src


def test_loader_hostguard_true_includes_bind_host():
    src, _, _ = generate_hybrid_loader_script(_BLANKS, b"", _KEY, hostguard=True)
    compile(src, "<t>", "exec")
    assert "def bind_host" in src
    assert "def check_host" in src
    assert "def isolated_exec" in src


def test_loader_always_includes_secure_temp_and_vm():
    src, _, _ = generate_hybrid_loader_script(_BLANKS, b"", _KEY)
    compile(src, "<t>", "exec")
    # secure-temp markers
    assert "_nx_secure_write" in src
    assert "_nx_purge_stale" in src
    assert "_nx_TRACKED" in src
    # vm snippet markers
    assert "vm_check" in src
    assert "_NX_VM_THRESHOLD" in src
    assert "NIXON_KOD" in src


def test_loader_vm_threshold_embedded():
    src, _, _ = generate_hybrid_loader_script(_BLANKS, b"", _KEY, vm_threshold=75.0)
    compile(src, "<t>", "exec")
    assert "_NX_VM_THRESHOLD = 75.0" in src


def test_loader_kod_and_trial_markers():
    src, _, _ = generate_hybrid_loader_script(
        _BLANKS, b"", _KEY, kod=True, trial_seconds=604800)
    compile(src, "<t>", "exec")
    assert "_NX_KOD_ARMED = True" in src
    assert "_NX_TRIAL_SECONDS = 604800" in src
    src2, _, _ = generate_hybrid_loader_script(_BLANKS, b"", _KEY)
    assert "_NX_KOD_ARMED = False" in src2
    assert "_NX_TRIAL_SECONDS = None" in src2


def test_loader_hwid_lock_flag():
    src, _, _ = generate_hybrid_loader_script(_BLANKS, b"", _KEY)
    assert "_NX_HWID_LOCK = 'DISABLED'" in src
    src2, _, _ = generate_hybrid_loader_script(_BLANKS, b"", _KEY, hwid_lock=True)
    assert "_NX_HWID_LOCK = 'ENABLED'" in src2
    assert "def _nx_hwid_unlock" in src2


def test_macros_noop_on_clean_source():
    src = "def f(a):\n    b = a + 1\n    return b\n"
    out = apply_macros(src)
    assert ast.dump(ast.parse(out)) == ast.dump(ast.parse(src))


def test_macros_apply_hwid():
    out = apply_macros("h = GET_HWID()\n", hwid="HW-1")
    assert "GET_HWID" not in out
    ns = {}
    exec(compile(out, "<t>", "exec"), ns)
    assert ns["h"] == "HW-1"


def test_prepare_obfuscated_source_applies_macros(tmp_path):
    target = tmp_path / "payload.py"
    target.write_text("if IS_OBFUSCATED:\n    x = GET_HWID()\n", encoding="utf-8")
    out = prepare_obfuscated_source(str(target), {"hwid": "HW-9"})
    assert "IS_OBFUSCATED" not in out
    assert "GET_HWID" not in out
    assert "HW-9" in out


def test_prepare_obfuscated_source_no_macros_unchanged_semantics(tmp_path):
    src = "def f(a):\n    return a + 1\n"
    target = tmp_path / "plain.py"
    target.write_text(src, encoding="utf-8")
    out = prepare_obfuscated_source(
        str(target),
        {"hwid": "", "cfg_flatten": False, "opaque_predicates": False,
         "exception_flow": False, "fragment_strings": False, "mba_subs": False,
         "obf_calls": False, "bogus_exceptions": False, "split_vars": False,
         "unfold_constants": False, "strip_meta": False, "unicode_ids": False,
         "code_checksums": False, "dynamic_code": False, "enhanced_junk": False,
         "symbol_rename": False, "break_decompiler": False},
    )
    assert ast.dump(ast.parse(out)) == ast.dump(ast.parse(src))
