"""Stdlib function auditing (runtime integrity, additive).

Build-time records {qualified_name: sha256} (source hash + bytecode
hash; runtime enforces the bytecode subset only — fast, no source
reads). A monkeypatched stdlib function changes co_code -> mismatch ->
_nx_kill("stdlib-tamper"). Version-bound: enforced only on tag match,
else DISABLED/report-only. Opt-outs: NIXON_STDLIB_AUDIT_OFF (runtime)
+ --no-stdlib-audit (build flag, stdlib_audit_off=True).
"""
import ast
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.stdlib_audit import (
    CRITICAL_FUNCTIONS,
    OPT_OUT_VAR,
    build_audit_context,
    build_tag,
    emit_audit_snippet,
    fingerprint_of,
    is_opted_out,
    verify_audit,
)
from obfuscator.kill_ladder import REASON_CODES, nx_kill

BUILD_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")
_BLANK_BLOBS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))


def test_reason_registered():
    assert "stdlib-tamper" in REASON_CODES
    assert nx_kill("stdlib-tamper", dry_run=True) == ["exit:137"]


def test_build_tag_recorded():
    ctx = build_audit_context()
    assert ctx["tag"] == build_tag()
    assert isinstance(ctx["funcs"], dict) and isinstance(ctx["runtime"], dict)
    assert len(ctx["funcs"]) >= 20
    assert len(ctx["runtime"]) >= 5


def test_critical_list_sane():
    names = [p for (p, _h) in CRITICAL_FUNCTIONS]
    assert len(names) >= 20
    for name in ("builtins.eval", "builtins.exec", "builtins.compile",
                 "builtins.__import__", "builtins.open",
                 "importlib.import_module", "marshal.loads", "marshal.dumps",
                 "json.loads", "base64.b64decode", "hashlib.sha256",
                 "hmac.new", "subprocess.Popen", "socket.socket"):
        assert name in names, name
    # Our own audit-hook wrapper target must NOT be audited (self-flag).
    assert "sys.addaudithook" not in names


def test_source_preferred_bytecode_fallback():
    pure = fingerprint_of("json.loads", "func")
    assert pure["kind"] == "source+bytecode"
    assert len(pure["sha256"]) == 64 and len(pure["co_sha256"]) == 64
    cfunc = fingerprint_of("os.urandom", "func")
    assert cfunc["kind"] == "identity"
    assert cfunc["co_sha256"] == ""


def test_same_version_match_passes():
    ctx = build_audit_context()
    assert verify_audit(ctx["runtime"], ctx["tag"]) == "ok"


def test_tampered_func_detected():
    import json
    ctx = build_audit_context()
    real = json.loads
    try:
        json.loads = lambda *a, **k: real(*a, **k)  # noqa: E731
        assert verify_audit(ctx["runtime"], ctx["tag"]) == "mismatch"
    finally:
        json.loads = real
    assert verify_audit(ctx["runtime"], ctx["tag"]) == "ok"


def test_version_mismatch_report_only_never_kills():
    ctx = build_audit_context()
    assert verify_audit(ctx["runtime"], "0.0.0-none") == "version-mismatch"
    bad = dict(ctx["runtime"])
    if bad:
        first = sorted(bad)[0]
        bad[first] = "0" * 64
    assert verify_audit(bad, "0.0.0-none") == "version-mismatch"


def test_unresolvable_skipped_not_failed():
    table = {"no.such.module.func": "0" * 64}
    assert verify_audit(table, build_tag()) == "ok"


def test_opt_out_helper():
    assert is_opted_out({}) is False
    assert is_opted_out({OPT_OUT_VAR: "1"}) is True
    assert is_opted_out({OPT_OUT_VAR: "TRUE"}) is True
    assert is_opted_out({OPT_OUT_VAR: "0"}) is False


def test_snippet_compiles_and_310():
    ctx = build_audit_context()
    src = emit_audit_snippet(ctx["runtime"], ctx["tag"])
    compile(src, "<nx_stdlib_gate>", "exec")
    ast.parse(src, feature_version=(3, 10))
    assert "def _nx_stdlib_gate(" in src
    assert OPT_OUT_VAR in src
    assert "version-mismatch" in src


def test_snippet_same_version_ok():
    ctx = build_audit_context()
    src = emit_audit_snippet(ctx["runtime"], ctx["tag"])
    ns = {}
    exec(compile(src, "<nx_sa_ok>", "exec"), ns)
    assert ns["_nx_stdlib_gate"]() == "ok"


def test_snippet_tamper_mismatch_and_kill():
    import hashlib
    import json as _json
    co = _json.loads.__code__
    good = hashlib.sha256(bytes(co.co_code)).hexdigest()
    table = {"json.loads": good}
    from obfuscator.frozen_snapshot import build_tag as _tag
    src = emit_audit_snippet(table, _tag())
    src = src.replace(good, "0" * 64, 1)  # simulate patched stdlib
    # Real kill ladder (single failure path), not a hand-rolled stub.
    from obfuscator.kill_ladder import emit_kill_snippet
    code = (emit_kill_snippet()
            + "\n" + src +
            "\n_r = _nx_stdlib_gate()\n"
            "print('GATE:' + str(_r), flush=True)\n"
            "if _r == 'mismatch':\n"
            "    _nx_kill('stdlib-tamper')\n")
    env = dict(os.environ)
    env.pop(OPT_OUT_VAR, None)
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr)
    assert "GATE:mismatch" in proc.stdout
    assert proc.stderr == ""  # silent kill


def test_snippet_version_mismatch_report_only():
    ctx = build_audit_context()
    src = emit_audit_snippet(ctx["runtime"], "0.0.0-none")
    code = src + "\nprint('GATE:' + str(_nx_stdlib_gate()))\n"
    env = dict(os.environ)
    env.pop(OPT_OUT_VAR, None)
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "GATE:version-mismatch" in proc.stdout


def test_snippet_opt_out_honored():
    ctx = build_audit_context()
    src = emit_audit_snippet(ctx["runtime"], ctx["tag"])
    code = src + "\nprint('GATE:' + str(_nx_stdlib_gate()))\n"
    env = dict(os.environ)
    env[OPT_OUT_VAR] = "1"
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "GATE:disabled" in proc.stdout


def test_loader_default_on_has_gate():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _, _ = generate_hybrid_loader_script(dict(_BLANK_BLOBS), b"",
                                              _RAW_KEY.hex(),
                                              build_id="sa-on-01")
    compile(src, "<sa_on>", "exec")
    assert "def _nx_stdlib_gate" in src
    assert "_NX_STDLIB_TAG" in src
    assert "_NX_STDLIB_FUNCS" in src
    assert '_nx_kill("stdlib-tamper")' in src
    assert '_NX_STDLIB_GATE = "DISABLED"' not in src


def test_loader_opt_out_disabled():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _, _ = generate_hybrid_loader_script(dict(_BLANK_BLOBS), b"",
                                              _RAW_KEY.hex(),
                                              build_id="sa-off-01",
                                              stdlib_audit_off=True)
    compile(src, "<sa_off>", "exec")
    assert "_NX_STDLIB_GATE = \"DISABLED\"" in src
    assert "def _nx_stdlib_gate" not in src


def test_loader_signature_default_on():
    import inspect
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    assert inspect.signature(
        generate_hybrid_loader_script).parameters["stdlib_audit_off"].default is False


def test_loader_default_gate_ok_in_process():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _, _ = generate_hybrid_loader_script(dict(_BLANK_BLOBS), b"",
                                              _RAW_KEY.hex(),
                                              build_id="sa-e2e-01")
    ns = {"__name__": "sa_e2e_loader"}
    exec(compile(src, "<sa_e2e>", "exec"), ns)
    assert ns.get("_NX_STDLIB_GATE") == "ok"


def test_build_flag_present():
    out = subprocess.run([sys.executable, BUILD_PY, "--help"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "--no-stdlib-audit" in (out.stdout + out.stderr)


def test_gate_names_survive_rename_passes():
    from obfuscator.core.sources import apply_ast_mutation
    probe = ("def _x():\n"
             "    a = _nx_stdlib_gate\n"
             "    b = _NX_STDLIB_GATE\n"
             "    c = _NX_STDLIB_TAG\n"
             "    d = _NX_STDLIB_FUNCS\n"
             "    e = _nx_snapshot_gate\n"
             "    f = _NX_SNAPSHOT_GATE\n"
             "    return (a, b, c, d, e, f)\n")
    out, _ = apply_ast_mutation(
        probe, {"symbol_rename": True, "unicode_ids": True})
    for name in ("_nx_stdlib_gate", "_NX_STDLIB_GATE",
                 "_NX_STDLIB_TAG", "_NX_STDLIB_FUNCS",
                 "_nx_snapshot_gate", "_NX_SNAPSHOT_GATE"):
        assert name in out, name
