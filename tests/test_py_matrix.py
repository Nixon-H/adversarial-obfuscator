"""Tests for obfuscator/py_matrix.py."""
import os
import subprocess
import sys

import pytest

from obfuscator import py_matrix
from obfuscator.py_matrix import (
    CURRENT,
    FEATURES,
    SUPPORTED,
    emit_version_gate,
    gate,
    matrix_table,
    supports,
)


def test_supported_matrix_shape():
    assert SUPPORTED == [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14)]
    assert isinstance(CURRENT, tuple) and len(CURRENT) == 2
    assert CURRENT[0] == sys.version_info[0]
    assert CURRENT[1] == sys.version_info[1]
    assert CURRENT in SUPPORTED or CURRENT[0] == 3


def test_features_have_required_keys():
    expected = {
        "nyser_exceptiontable", "exceptiontable_rebuild", "linetable",
        "per_opcode_cache", "co_positions", "adaptive_specialization",
        "type_params", "fstring_tokens", "marshal_version", "annotation_scope",
        "deferred_annotations", "template_strings", "code_qualname",
    }
    assert expected <= set(FEATURES)
    for name, info in FEATURES.items():
        assert set(info) == {"min", "added", "note"}, name
        assert isinstance(info["min"], tuple) and len(info["min"]) == 2
        assert isinstance(info["added"], str) and info["added"].startswith("3.")
        assert isinstance(info["note"], str) and info["note"]


def test_supports_logic_monotonic():
    # linetable (3.10) must be supported on any SUPPORTED interpreter
    assert FEATURES["linetable"]["min"] == (3, 10)
    # type_params (3.12) supported iff CURRENT >= (3,12)
    assert supports("type_params") == (CURRENT >= (3, 12))
    with pytest.raises(KeyError):
        supports("no_such_feature")


def test_gate_raises_and_passes():
    gate("linetable")  # min 3.10: passes on all supported interpreters
    with pytest.raises(KeyError):
        gate("no_such_feature")
    # Simulate an old interpreter by monkeypatching CURRENT
    old = py_matrix.CURRENT
    try:
        py_matrix.CURRENT = (3, 9)
        with pytest.raises(RuntimeError, match="type_params"):
            gate("type_params")
    finally:
        py_matrix.CURRENT = old


def test_matrix_table_contains_all_features():
    table = matrix_table()
    for name in FEATURES:
        assert name in table
    assert "feature" in table.splitlines()[0]
    assert "yes" in table or "no" in table


def test_snippet_compiles():
    snippet = emit_version_gate(CURRENT)
    compile(snippet, "<version_gate>", "exec")
    assert "sys.exit(1)" in snippet or "_sys.exit(1)" in snippet
    assert "NIXON_VERIFY_SKIP_VERSION_CHECK" in snippet


def _run_snippet(required, env_extra=None):
    snippet = emit_version_gate(required)
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    # Ensure bypass/CI vars absent unless explicitly set
    for _var in ("NIXON_VERIFY_SKIP_VERSION_CHECK", "NIXON_CI", "NIXON_ALLOW_SKIP"):
        if env_extra is None or _var not in (env_extra or {}):
            env.pop(_var, None)
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True, text=True, env=env, timeout=30,
    )
    return proc


def test_snippet_passes_on_match():
    proc = _run_snippet(CURRENT)
    assert proc.returncode == 0, proc.stderr


def test_snippet_exits_nonzero_on_mismatch():
    wrong = (2, 7) if CURRENT != (2, 7) else (1, 0)
    proc = _run_snippet(wrong)
    assert proc.returncode != 0
    assert "mismatch" in proc.stderr.lower()


def test_snippet_bypass_env_honored():
    # Batch-3 CI scope: SKIP alone holds the gate; SKIP + CI gate passes.
    wrong = (2, 7) if CURRENT != (2, 7) else (1, 0)
    proc = _run_snippet(wrong, {"NIXON_VERIFY_SKIP_VERSION_CHECK": "1"})
    assert proc.returncode != 0
    proc = _run_snippet(
        wrong, {"NIXON_VERIFY_SKIP_VERSION_CHECK": "1", "NIXON_CI": "1"})
    assert proc.returncode == 0, proc.stderr
    proc = _run_snippet(
        wrong, {"NIXON_VERIFY_SKIP_VERSION_CHECK": "1", "NIXON_ALLOW_SKIP": "1"})
    assert proc.returncode == 0, proc.stderr


def test_314_features_gated():
    # 3.14-only features must be gated, not assumed: on <3.14 supports()
    # is False; on 3.14+ the gate passes. Either way gate() never lies.
    for name in ("deferred_annotations", "template_strings"):
        assert FEATURES[name]["min"] == (3, 14)
        assert supports(name) == (CURRENT >= (3, 14))
    assert FEATURES["code_qualname"]["min"] == (3, 11)
