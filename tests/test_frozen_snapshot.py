"""Frozen stdlib file snapshots (runtime integrity, additive).

Build-time records {module: sha256(origin file bytes)} on the BUILD host;
runtime re-hashes on the TARGET and fails closed via
_nx_kill("integrity-snapshot") on mismatch. Version-bound: enforced only
on tag match, else DISABLED/report-only. Missing files skipped (frozen/
zipimport-safe). Opt-outs: NIXON_SNAPSHOT_OFF (runtime) + --no-snapshot
(build flag, snapshot_off=True).
"""
import ast
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.frozen_snapshot import (
    CRITICAL_MODULES,
    OPT_OUT_VAR,
    build_snapshot_context,
    build_tag,
    emit_snapshot_snippet,
    is_opted_out,
    verify_snapshot,
)
from obfuscator.kill_ladder import REASON_CODES, nx_kill

BUILD_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")
_BLANK_BLOBS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))


def test_reason_registered():
    assert "integrity-snapshot" in REASON_CODES
    assert nx_kill("integrity-snapshot", dry_run=True) == ["exit:137"]


def test_build_tag_recorded_and_shaped():
    ctx = build_snapshot_context()
    assert ctx["tag"] == build_tag()
    assert ctx["tag"].count(".") >= 2 and "-" in ctx["tag"]
    assert isinstance(ctx["files"], dict) and isinstance(ctx["skipped"], list)
    # Builtin/frozen stdlib (sys, os, io, marshal) can never be file-hashed.
    assert "sys" in ctx["skipped"]
    # The enforcement surface is the file-backed subset.
    assert len(ctx["files"]) >= 5
    for name, entry in ctx["files"].items():
        assert len(entry["sha256"]) == 64
        bytes.fromhex(entry["sha256"])


def test_critical_list_sane():
    assert len(CRITICAL_MODULES) >= 10
    for name in ("hashlib", "hmac", "json", "base64", "socket",
                 "subprocess", "threading", "traceback"):
        assert name in CRITICAL_MODULES, name


def test_same_version_match_passes():
    ctx = build_snapshot_context()
    assert verify_snapshot(ctx["files"], ctx["tag"]) == "ok"


def test_tampered_file_detected(tmp_path):
    victim = tmp_path / "victim_mod.py"
    victim.write_text("X = 1\n", encoding="utf-8")
    import hashlib
    good = hashlib.sha256(b"X = 1\n").hexdigest()
    files = {"victim_mod": {"path": str(victim), "sha256": good}}
    assert verify_snapshot(files, build_tag()) == "ok"
    victim.write_text("X = 2  # swapped stdlib\n", encoding="utf-8")
    assert verify_snapshot(files, build_tag()) == "mismatch"


def test_version_mismatch_report_only_never_kills():
    ctx = build_snapshot_context()
    assert verify_snapshot(ctx["files"], "0.0.0-none") == "version-mismatch"
    # Even a would-be mismatch is masked by the version gate.
    bad = dict(ctx["files"])
    if bad:
        first = sorted(bad)[0]
        bad[first] = {"path": bad[first]["path"], "sha256": "0" * 64}
    assert verify_snapshot(bad, "0.0.0-none") == "version-mismatch"


def test_missing_file_skipped_not_failed(tmp_path):
    ghost = str(tmp_path / "no_such_stdlib.py")
    files = {"ghost_mod": {"path": ghost, "sha256": "0" * 64}}
    assert verify_snapshot(files, build_tag()) == "ok"


def test_opt_out_helper():
    assert is_opted_out({}) is False
    assert is_opted_out({OPT_OUT_VAR: "1"}) is True
    assert is_opted_out({OPT_OUT_VAR: "yes"}) is True
    assert is_opted_out({OPT_OUT_VAR: "0"}) is False


def test_snippet_compiles_and_310():
    ctx = build_snapshot_context()
    src = emit_snapshot_snippet(ctx["files"], ctx["tag"])
    compile(src, "<nx_snapshot_gate>", "exec")
    ast.parse(src, feature_version=(3, 10))
    assert "def _nx_snapshot_gate(" in src
    assert OPT_OUT_VAR in src
    assert "version-mismatch" in src


def test_snippet_same_version_ok():
    ctx = build_snapshot_context()
    src = emit_snapshot_snippet(ctx["files"], ctx["tag"])
    ns = {}
    exec(compile(src, "<nx_ss_ok>", "exec"), ns)
    assert ns["_nx_snapshot_gate"]() == "ok"


def test_snippet_tamper_mismatch_and_kill(monkeypatch):
    import hashlib
    target = os.path.join(os.path.dirname(__file__), "fixtures",
                          "test_payload.py")
    if not os.path.isfile(target):
        target = os.path.join(os.path.dirname(__file__), "..",
                              "obfuscator", "frozen_snapshot.py")
    good = hashlib.sha256(open(target, "rb").read()).hexdigest()
    files = {"victim": {"path": target, "sha256": good}}
    src = emit_snapshot_snippet(files, build_tag())
    # Corrupt the expectation (simulate a swapped stdlib on target).
    src = src.replace(good, "0" * 64, 1)
    code = ("import os as _os\n"
            "import sys as _sys\n"
            "def _nx_kill(_reason='', _holders=None):\n"
            "    _sys.stdout.write('KILLED:' + str(_reason))\n"
            "    _sys.exit(137)\n"
            + src +
            "\n_r = _nx_snapshot_gate()\n"
            "print('GATE:' + str(_r))\n"
            "if _r == 'mismatch':\n"
            "    _nx_kill('integrity-snapshot')\n")
    env = dict(os.environ)
    env.pop(OPT_OUT_VAR, None)
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr)
    assert "GATE:mismatch" in proc.stdout
    assert "KILLED:integrity-snapshot" in proc.stdout


def test_snippet_version_mismatch_report_only():
    ctx = build_snapshot_context()
    src = emit_snapshot_snippet(ctx["files"], "0.0.0-none")
    code = src + "\nprint('GATE:' + str(_nx_snapshot_gate()))\n"
    env = dict(os.environ)
    env.pop(OPT_OUT_VAR, None)
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "GATE:version-mismatch" in proc.stdout


def test_snippet_opt_out_honored():
    ctx = build_snapshot_context()
    src = emit_snapshot_snippet(ctx["files"], ctx["tag"])
    code = src + "\nprint('GATE:' + str(_nx_snapshot_gate()))\n"
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
                                              build_id="ss-on-01")
    compile(src, "<ss_on>", "exec")
    assert "def _nx_snapshot_gate" in src
    assert "_NX_SNAPSHOT_TAG" in src
    assert "_NX_SNAPSHOT_FILES" in src
    assert '_nx_kill("integrity-snapshot")' in src
    assert '_NX_SNAPSHOT_GATE = "DISABLED"' not in src


def test_loader_opt_out_disabled():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _, _ = generate_hybrid_loader_script(dict(_BLANK_BLOBS), b"",
                                              _RAW_KEY.hex(),
                                              build_id="ss-off-01",
                                              snapshot_off=True)
    compile(src, "<ss_off>", "exec")
    assert "_NX_SNAPSHOT_GATE = \"DISABLED\"" in src
    assert "def _nx_snapshot_gate" not in src


def test_loader_signature_default_on():
    import inspect
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    assert inspect.signature(
        generate_hybrid_loader_script).parameters["snapshot_off"].default is False


def test_loader_default_gate_ok_in_process():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _, _ = generate_hybrid_loader_script(dict(_BLANK_BLOBS), b"",
                                              _RAW_KEY.hex(),
                                              build_id="ss-e2e-01")
    ns = {"__name__": "ss_e2e_loader"}
    exec(compile(src, "<ss_e2e>", "exec"), ns)
    assert ns.get("_NX_SNAPSHOT_GATE") == "ok"


def test_build_flag_present():
    out = subprocess.run([sys.executable, BUILD_PY, "--help"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "--no-snapshot" in (out.stdout + out.stderr)


def test_gate_names_survive_rename_passes():
    from obfuscator.core.sources import apply_ast_mutation
    probe = ("def _x():\n"
             "    a = _nx_snapshot_gate\n"
             "    b = _NX_SNAPSHOT_GATE\n"
             "    c = _NX_SNAPSHOT_TAG\n"
             "    d = _NX_SNAPSHOT_FILES\n"
             "    e = _nx_stdlib_gate\n"
             "    f = _NX_STDLIB_GATE\n"
             "    return (a, b, c, d, e, f)\n")
    out, _ = apply_ast_mutation(
        probe, {"symbol_rename": True, "unicode_ids": True})
    for name in ("_nx_snapshot_gate", "_NX_SNAPSHOT_GATE",
                 "_NX_SNAPSHOT_TAG", "_NX_SNAPSHOT_FILES",
                 "_nx_stdlib_gate", "_NX_STDLIB_GATE"):
        assert name in out, name
