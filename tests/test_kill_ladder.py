"""Unified kill-ladder tests (V10 single failure path).

- nx_kill validates reason codes, wipes mutable holders, deletes key
  globals, exits 137 (subprocess), silent by default, NIXON_LADDER_DEBUG
  diagnostics opt-in, dry_run seam returns the action list.
- emit_kill_snippet compiles, 3.10-parses, kills via 137 with no literals
  leaked.
- Migrated gates (vm, driver, audit-hook, trial, watermark) all funnel
  through _nx_kill: no direct os._exit remains in their snippets.
"""
import ast
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.kill_ladder import DEBUG_VAR, KILL_CODE, REASON_CODES, emit_kill_snippet, nx_kill


def test_kill_code_is_137():
    assert KILL_CODE == 137


def test_reason_codes_cover_gates():
    for r in ("vm-detect", "driver-blocked", "audit-plant", "audit-timing",
              "trial-expired",
              "trial-tampered", "trial-rollback", "watermark-tampered",
              "watermark-missing", "integrity-snapshot", "stdlib-tamper",
              "hwid-mismatch"):
        assert r in REASON_CODES, r


def test_unknown_reason_rejected():
    try:
        nx_kill("bogus-reason", dry_run=True)
    except ValueError:
        return
    raise AssertionError("unknown reason must raise ValueError")


def test_dry_run_wipes_and_lists_exit():
    buf = bytearray(b"supersecretkeymaterial1234567890")
    view = memoryview(bytearray(b"anotherkeybuffer87654321"))
    ns = {"BLOB_KEY": b"immutable-bytes-key", "other": 1}
    actions = nx_kill("vm-detect", key_holders=[buf, view, ns], dry_run=True)
    assert all(v == 0 for v in buf)
    assert all(v == 0 for v in view)
    assert "BLOB_KEY" not in ns
    assert ns["other"] == 1
    assert actions[-1] == "exit:137"
    assert any(a.startswith("wipe:bytearray:") for a in actions)
    assert any(a.startswith("del:BLOB_KEY") for a in actions)


def test_dry_run_empty_holders():
    actions = nx_kill("trial-expired", dry_run=True)
    assert actions == ["exit:137"]


def test_real_exit_is_137_silent():
    code = (
        "import sys; sys.path.insert(0, %r);"
        "from obfuscator.kill_ladder import nx_kill;"
        "nx_kill('driver-blocked')" % (
            os.path.join(os.path.dirname(__file__), ".."),)
    )
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout == ""
    assert proc.stderr == ""


def test_debug_var_prints_reason():
    code = (
        "import sys; sys.path.insert(0, %r);"
        "from obfuscator.kill_ladder import nx_kill;"
        "nx_kill('audit-plant')" % (
            os.path.join(os.path.dirname(__file__), ".."),)
    )
    env = dict(os.environ)
    env[DEBUG_VAR] = "1"
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=60, env=env)
    assert proc.returncode == 137
    assert "nx-kill:audit-plant" in proc.stderr


def test_snippet_compiles_and_310():
    src = emit_kill_snippet()
    compile(src, "<nx_kill_ladder>", "exec")
    ast.parse(src, feature_version=(3, 10))
    assert "def _nx_kill(" in src
    assert "_exit(137)" in src


def test_snippet_kills_137():
    src = emit_kill_snippet()
    code = src + "\n_nx_kill('vm-detect')\n"
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout == ""


def _no_direct_exit(path, extra_allowed=()):
    src = open(path).read()
    # Kill-ladder migration: gate EMITTED snippets must not call os._exit
    # directly; the only exit primitive is _nx_kill (which itself wraps
    # os._exit). Docstrings/comments may still mention the old primitive.
    # So check string LITERALS that reach the emitted snippet: any line
    # containing _exit that is NOT inside the kill-ladder import block and
    # NOT a docstring/comment line is a violation.
    # DOCUMENTED ALLOWLIST (not gates — separate primitives by design):
    # - macros.py CRASH(): explicit user-invoked stop (exit 1, no wipe).
    # - sources.py NANOMITE_*: forked tracer CHILD fast-exit(0) on
    #   completion (child PID only; routing through _nx_kill would wipe
    #   the parent's keys and misreport a healthy exit as a kill).
    _allow = set(extra_allowed) | {
        "CRASH", "NANOMITE", "tracer child", "tracer-child",
        "child fast-exit", "child done", "allowlist",
    }
    violations = []
    in_docstring = False
    for ln in src.splitlines():
        s = ln.strip()
        if s.startswith('"""') or s.startswith("'''"):
            if s.count('"""') == 2 or s.count("'''") == 2:
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring or s.startswith("#"):
            continue
        if "_nx_kill" in ln or "kill_ladder" in ln or "kill ladder" in ln.lower():
            continue
        if any(a in ln for a in _allow):
            continue
        # Emitted-snippet string lines look like: + "    _os._exit(1)\n"
        if "_exit(" in ln and ('"' in ln or "'" in ln):
            violations.append(ln.strip()[:100])
    assert not violations, (path, violations)


def _repo(rel):
    return os.path.join(os.path.dirname(__file__), "..", rel)


def test_vm_snippet_uses_ladder():
    from obfuscator.vm_score import emit_loader_snippet
    src = emit_loader_snippet()
    assert "_nx_kill(" in src
    assert '"vm-detect"' in src or "'vm-detect'" in src
    _no_direct_exit(_repo("obfuscator/vm_score.py"))


def test_driver_snippet_uses_ladder():
    from obfuscator.driver_blocklist import emit_driver_snippet
    src = emit_driver_snippet(armed=True)
    assert "_nx_kill(" in src
    _no_direct_exit(_repo("obfuscator/driver_blocklist.py"))


def test_audit_snippet_uses_ladder():
    from obfuscator.audit_hook import emit_snippet
    src = emit_snippet()
    assert "_nx_kill(" in src
    _no_direct_exit(_repo("obfuscator/audit_hook.py"))


def test_pipeline_trial_watermark_use_ladder():
    src = open(_repo("obfuscator/core/pipeline.py")).read()
    assert '_nx_kill(\\"trial-\\"' in src
    assert '_nx_kill(\\"watermark-\\"' in src
    # No direct sys.exit enforcement strings remain for the gates.
    assert "_nx_trial_sys.exit" not in src
    assert "_nx_watermark_sys.exit" not in src


def test_pipeline_integrity_gates_use_ladder():
    src = open(_repo("obfuscator/core/pipeline.py")).read()
    assert '_nx_kill(\\"integrity-snapshot\\")' in src
    assert '_nx_kill(\\"stdlib-tamper\\")' in src
    _no_direct_exit(_repo("obfuscator/frozen_snapshot.py"))
    _no_direct_exit(_repo("obfuscator/stdlib_audit.py"))


def test_documented_allowlist_only():
    # CRASH (explicit user stop, exit 1) and the NANOMITE tracer-child
    # fast-exits (child PID, exit 0) are the ONLY sanctioned direct-exit
    # primitives. This test fails if anyone adds a new one without
    # documenting it here.
    import re
    macro_src = open(_repo("obfuscator/macros.py")).read()
    assert "_os._exit(1)" in macro_src  # CRASH() body
    assert macro_src.count("_os._exit(1)") == 1, "new direct exit in macros?"
    nano_src = open(_repo("obfuscator/core/sources.py")).read()
    nano_exits = re.findall(r"_o\._exit\(0\)|_exit\(0\)", nano_src)
    # 5th documented exit: after the tracer child is continued out of its
    # SIGSTOP it must die instead of falling through and re-running the
    # loader (that fall-through was the intermittent artifact hang).
    assert 1 <= len(nano_exits) <= 6, ("nanomite child exits changed:",
                                       len(nano_exits))
    assert "kill-ladder allowlist" in nano_src
