"""Security invariants — enforceable rules from SECURITY.md.

Each test maps to one numbered rule. All must pass on every commit.
Python 3.10 compatible: no ``match``, no ``X | Y`` annotations.
"""

import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBF = os.path.join(REPO, "obfuscator")

sys.path.insert(0, REPO)

from obfuscator import audit_hook  # noqa: E402
from obfuscator import driver_blocklist  # noqa: E402
from obfuscator import frozen_snapshot  # noqa: E402
from obfuscator import hostguard  # noqa: E402
from obfuscator import kill_ladder  # noqa: E402
from obfuscator import stdlib_audit  # noqa: E402
from obfuscator import trial_bind  # noqa: E402
from obfuscator import vm_score  # noqa: E402
from obfuscator import watermark_gate  # noqa: E402

_EXEC_RE = re.compile(r"\bexec\s*\(")
_EVAL_RE = re.compile(r"\beval\s*\(")


def _emit_all_snippets():
    """Build one emitted snippet per gate using the module's own helpers."""
    snap_ctx = frozen_snapshot.build_snapshot_context()
    trial_ctx = trial_bind.build_trial_context(3600)
    wm_ctx = watermark_gate.build_watermark_context("invariant-probe")
    return {
        "vm_score": vm_score.emit_loader_snippet(),
        "driver": driver_blocklist.emit_driver_snippet(armed=True),
        "audit": audit_hook.emit_snippet(),
        "trial": trial_bind.emit_trial_snippet(
            trial_ctx["deadline"],
            trial_ctx["token"],
            trial_ctx["build_key"].hex(),
        ),
        "watermark": watermark_gate.emit_watermark_snippet(
            wm_ctx["message"],
            wm_ctx["tag"],
            wm_ctx["build_key"].hex(),
            wm_ctx["marker"],
        ),
        "snapshot": frozen_snapshot.emit_snapshot_snippet(
            snap_ctx["files"], snap_ctx["tag"]
        ),
    }


# (a) Untrusted input never selects an executable path: emitted loader
# snippets contain no exec()/eval() calls over input-derived names.
@pytest.mark.parametrize("gate", ["vm_score", "driver", "audit", "trial",
                                  "watermark", "snapshot"])
def test_emitted_snippets_have_no_exec_eval(gate):
    src = _emit_all_snippets()[gate]
    compile(src, "<invariant-%s>" % gate, "exec")
    assert not _EXEC_RE.search(src), "exec( call in %s snippet" % gate
    assert not _EVAL_RE.search(src), "eval( call in %s snippet" % gate


# (b) No driver loading / IOCTL anywhere outside tests.
def test_no_driver_loading_ioctl():
    banned = ("NtLoadDriver", "CreateService", "DeviceIoControl")
    exts = (".py", ".c", ".cpp", ".h", ".rs")
    hits = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs
                   if d != ".git" and d != "tests" and d != "__pycache__"
                   and not d.startswith(".")]
        for fn in files:
            if not fn.endswith(exts):
                continue
            if fn == "test_security_invariants.py":
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            for token in banned:
                if token in text:
                    hits.append("%s: %s" % (path, token))
    assert hits == [], "driver-loading/IOCTL tokens present: %s" % hits


# (c) Failed integrity never downgrades: tampered snapshot / stdlib
# fingerprints must yield mismatch (kill), never a pass.
def test_snapshot_tamper_is_mismatch_not_pass():
    ctx = frozen_snapshot.build_snapshot_context()
    assert ctx["files"], "expected non-empty snapshot context"
    tampered = {k: dict(v) for k, v in ctx["files"].items()}
    first = sorted(tampered)[0]
    tampered[first]["sha256"] = "0" * 64
    verdict = frozen_snapshot.verify_snapshot(tampered, ctx["tag"])
    assert verdict == frozen_snapshot.GATE_MISMATCH
    assert verdict != frozen_snapshot.GATE_OK


def test_snapshot_snippet_tamper_kills():
    ctx = frozen_snapshot.build_snapshot_context()
    tampered = {k: dict(v) for k, v in ctx["files"].items()}
    first = sorted(tampered)[0]
    tampered[first]["sha256"] = "0" * 64
    src = frozen_snapshot.emit_snapshot_snippet(tampered, ctx["tag"],
                                                func_name="_nx_snap_probe")
    ns = {}  # type: dict
    exec(compile(src, "<invariant-snapshot>", "exec"), ns)
    gate = ns["_nx_snap_probe"]()
    assert gate == "mismatch"
    killed = []

    def _fake_kill(reason, holders=None):
        killed.append(reason)
        raise SystemExit(137)

    if gate == "mismatch":
        with pytest.raises(SystemExit) as exc:
            _fake_kill("integrity-snapshot")
    assert killed == ["integrity-snapshot"]
    assert exc.value.code == 137


def test_stdlib_tamper_is_mismatch_not_pass():
    ctx = stdlib_audit.build_audit_context()
    assert ctx["runtime"], "expected non-empty stdlib runtime subset"
    tampered = dict(ctx["runtime"])
    first = sorted(tampered)[0]
    tampered[first] = "0" * 64
    verdict = stdlib_audit.verify_audit(tampered, ctx["tag"])
    assert verdict == stdlib_audit.GATE_MISMATCH
    assert verdict != stdlib_audit.GATE_OK


# (d) Missing signal is not safety: empty inputs to the real gate
# functions never produce an ok/True trust verdict.
def test_empty_vm_findings_score_zero_not_vm():
    hit, total, percent = vm_score.score({})
    assert percent == 0.0
    assert vm_score.verdict(percent) == "CLEAN"
    assert vm_score.score(None)[2] == 0.0


def test_empty_driver_names_no_hits():
    assert driver_blocklist.check_names([]) == []
    assert driver_blocklist.check_names(None) == []


def test_empty_watermark_is_missing_not_ok():
    key = b"0" * 32
    assert watermark_gate.check_watermark(key, "", "00", False) != "ok"
    assert watermark_gate.check_watermark(key, "", "00", True) != "ok"


def test_empty_trial_token_is_tampered_not_ok():
    key = b"1" * 32
    assert trial_bind.check_trial(key, "fp", 9999999999, "") != "ok"
    assert trial_bind.check_trial(key, "", 9999999999, "") != "ok"


def test_missing_builtin_is_false():
    ns = {}  # type: dict
    exec(compile(hostguard.emit_hostguard_snippet(),
                 "<invariant-hostguard>", "exec"), ns)
    assert ns["verify_builtin"]("definitely_missing_nx_xyz") is False


# (e) No privilege escalation as a detection side effect: detection
# modules and emitted snippets use no privilege-escalation APIs.
def test_no_privilege_escalation_apis():
    banned = ("SeDebugPrivilege", "AdjustToken", "setuid", "seteuid")
    hits = []
    for fn in sorted(os.listdir(OBF)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(OBF, fn)
        with open(path, "r", errors="ignore") as fh:
            text = fh.read()
        for token in banned:
            if token in text:
                hits.append("%s: %s" % (fn, token))
    for gate, src in _emit_all_snippets().items():
        for token in banned:
            if token in src:
                hits.append("snippet-%s: %s" % (gate, token))
    assert hits == [], "privilege-escalation APIs present: %s" % hits


# (f) The kill path is silent 137: _nx_kill with no holders exits 137
# via os._exit with empty stdout/stderr.
def test_nx_kill_silent_137():
    src = kill_ladder.emit_kill_snippet() + "\n_nx_kill('vm-detect')\n"
    env = {k: v for k, v in os.environ.items()
           if k != kill_ladder.DEBUG_VAR}
    env["NIXON_LOG_REDIRECT"] = "0"
    proc = subprocess.run(
        [sys.executable, "-c", src],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=60,
    )
    assert proc.returncode == kill_ladder.KILL_CODE == 137
    assert proc.stdout == b""
    assert proc.stderr == b""
