"""Batch-3 SKIP scoping: the version-check bypass requires BOTH vars.

``NIXON_VERIFY_SKIP_VERSION_CHECK`` alone must HOLD the gate (prod-safe);
SKIP + (``NIXON_CI`` or ``NIXON_ALLOW_SKIP``) passes. Covers the emitted
``emit_version_gate`` snippet (obfuscator/py_matrix.py), the obfuscated
LOADER_HEAD gate (obfuscator/core/sources.py), and the hybrid loader gate
(``_nx_ci_bypass_ok`` in pipeline.py's loader template).
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import py_matrix  # noqa: F401 (this line binds a name used by an embedded template)
from obfuscator.py_matrix import CURRENT, emit_version_gate

_WRONG = (2, 7) if CURRENT != (2, 7) else (1, 0)


def _run_snippet(required, env_extra=None):
    snippet = emit_version_gate(required)
    env = dict(os.environ)
    for var in ("NIXON_VERIFY_SKIP_VERSION_CHECK", "NIXON_CI", "NIXON_ALLOW_SKIP"):
        if not (env_extra and var in env_extra):
            env.pop(var, None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True, text=True, env=env, timeout=30,
    )


def _loader_gate_expr(src):
    """Extract the _load_native bypass predicate calls from the template."""
    tpl = re.search(r"loader_template = r'''(.*?)'''", src, re.DOTALL).group(1)
    assert "_nx_ci_bypass_ok" in tpl
    return tpl


def test_snippet_compiles_and_mentions_both_vars():
    snippet = emit_version_gate(CURRENT)
    compile(snippet, "<version_gate>", "exec")
    assert "NIXON_VERIFY_SKIP_VERSION_CHECK" in snippet
    assert "NIXON_CI" in snippet
    assert "NIXON_ALLOW_SKIP" in snippet


def test_gate_holds_with_only_skip_set():
    proc = _run_snippet(_WRONG, {"NIXON_VERIFY_SKIP_VERSION_CHECK": "1"})
    assert proc.returncode != 0
    assert "mismatch" in proc.stderr.lower()


def test_gate_passes_with_skip_plus_ci():
    proc = _run_snippet(
        _WRONG, {"NIXON_VERIFY_SKIP_VERSION_CHECK": "1", "NIXON_CI": "1"})
    assert proc.returncode == 0, proc.stderr
    proc2 = _run_snippet(
        _WRONG, {"NIXON_VERIFY_SKIP_VERSION_CHECK": "1", "NIXON_ALLOW_SKIP": "yes"})
    assert proc2.returncode == 0, proc2.stderr


def test_gate_passes_on_version_match_regardless():
    proc = _run_snippet(CURRENT)
    assert proc.returncode == 0, proc.stderr


def test_obfuscated_loader_head_gate_requires_both():
    src = open("obfuscator/core/sources.py").read()
    assert "_NX_SKIP_ON and _NX_CI_ON" in src or "(_NX_SKIP_ON and _NX_CI_ON)" in src
    assert "NIXON_ALLOW_SKIP" in src


def test_hybrid_loader_gate_requires_both():
    src = open("obfuscator/core/pipeline.py").read()
    tpl = _loader_gate_expr(src)
    # helper definition requires both vars; all five call sites use it
    assert "NIXON_VERIFY_SKIP_VERSION_CHECK" in tpl
    assert "NIXON_CI" in tpl
    assert "NIXON_ALLOW_SKIP" in tpl
    assert tpl.count("_nx_ci_bypass_ok()") >= 5
    assert "environ.get('NIXON_VERIFY_SKIP_VERSION_CHECK')" not in tpl.replace(
        "_e.get('NIXON_VERIFY_SKIP_VERSION_CHECK')", "")
