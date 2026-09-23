"""Loader traceback suppression (V10 v6.0 parity).

Suppression lives at the TOP of the hybrid-loader template
(pipeline.py loader_template): sys.tracebacklimit = 0 + quiet
excepthook ("fatal error" + exit 1, no paths). Opt-out via
NIXON_TRACEBACKS=1 (full tracebacks for diagnostics).
"""
import ast
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _head_frag():
    import ast as _ast
    tree = _ast.parse(open("obfuscator/core/pipeline.py").read())
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for t in node.targets:
                if getattr(t, "id", "") == "loader_template":
                    return node.value.value[:1500]
    raise AssertionError("loader_template not found")


def test_suppression_installed_first():
    frag = _head_frag()
    ns = {"__name__": "tb_head"}
    exec(compile(frag, "<frag>", "exec"), ns)
    try:
        assert sys.tracebacklimit == 0, sys.tracebacklimit
        assert getattr(sys.excepthook, "__name__", "") == \
            "_nx_quiet_excepthook", sys.excepthook
    finally:
        sys.tracebacklimit = 1000


def test_loader_failure_is_silent_by_default():
    frag = _head_frag()
    code = (frag + "\nraise ValueError(\"secret-path-should-not-appear\")\n")
    env = dict(os.environ)
    env.pop("NIXON_TRACEBACKS", None)
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert proc.returncode == 1, (proc.returncode, proc.stderr[-500:])
    assert proc.stdout == ""
    assert "secret-path-should-not-appear" not in proc.stderr
    assert "Traceback" not in proc.stderr
    assert "fatal error" in proc.stderr


def test_opt_out_restores_tracebacks():
    frag = _head_frag()
    code = (frag + "\nraise ValueError(\"visible-diagnostic\")\n")
    env = dict(os.environ)
    env["NIXON_TRACEBACKS"] = "1"
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert "visible-diagnostic" in proc.stderr
    assert "Traceback" in proc.stderr
