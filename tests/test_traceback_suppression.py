"""Loader traceback suppression (V10 v6.0 parity).

Suppression lives at the TOP of the hybrid-loader template
(pipeline.py loader_template): sys.tracebacklimit = 0 + quiet
excepthook ("fatal error" + exit 1, no paths). Opt-out via
NIXON_TRACEBACKS=1 (full tracebacks for diagnostics).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _head_frag():
    """Return the loader template's head, cut at a COMPLETE STATEMENT.

    A fixed character window is fragile: every loader change shifts the
    content and a slice can land mid-token. Measured 2026-11-18 -- after the
    earliest-anti-dump prctl was added, a 1500-char window cut `importlib.util`
    to `i` and then `_nx_licenc` mid-def, and the resulting SyntaxError looked
    exactly like a suppression regression. The cut is now made at the last
    statement boundary before the limit, so the fragment is always executable.
    """
    import ast as _ast
    template = None
    tree = _ast.parse(open("obfuscator/core/pipeline.py").read())
    for node in _ast.walk(tree):
        # skip the later `loader_template = loader_template.replace(...)`
        # rebindings: only the raw-string literal assignment carries the
        # template text
        if isinstance(node, _ast.Assign) and isinstance(node.value, _ast.Constant):
            for t in node.targets:
                if getattr(t, "id", "") == "loader_template":
                    template = node.value.value
    if template is None:
        raise AssertionError("loader_template not found")
    head = _cut_at_statement_boundary(template)
    # The template's first lines carry the identity-gate and self-check
    # MARKERS (the generator replaces them with real text); the raw
    # markers are not executable, so resolve them exactly as the
    # generator does -- gate text stripped (this fragment exec IS a
    # non-main exec) and the self-check markers emptied (its call reads
    # __file__). __NX_ANTI_DUMP__ (2026-11-19) is substituted by the
    # generator with a per-build anti-dump block; its CONTENT has its own
    # tests -- this file's subject is the suppression ORDER, so the marker
    # is dropped like the others rather than duplicating the block here.
    while "__NX_" in head:
        head = head.replace("__NX_IDENTITY_GATE__\n", "")
        head = head.replace("__NX_SELF_CHECK_DEFS__\n", "")
        head = head.replace("__NX_SELF_CHECK_CALL__\n", "")
        head = head.replace("__NX_ANTI_DUMP__\n", "")
        if "__NX_" in head:
            raise AssertionError("unknown __NX_ marker in the loader head")
    return head


def _cut_at_statement_boundary(template, limit=2600):
    """Longest prefix of `template` (<= limit) that parses as Python.

    Walks back line by line from the limit, stripping the marker lines the
    generator replaces. The first prefix that compiles is returned; that is a
    complete sequence of statements by construction.
    """
    lines = template.splitlines(keepends=True)
    total = 0
    end = 0
    for i, line in enumerate(lines):
        total += len(line)
        if total > limit:
            break
        end = i + 1
    for cut in range(end, 0, -1):
        candidate = "".join(lines[:cut])
        candidate = (candidate
                     .replace("__NX_IDENTITY_GATE__\n", "")
                     .replace("__NX_SELF_CHECK_DEFS__\n", "")
                     .replace("__NX_SELF_CHECK_CALL__\n", "")
                     .replace("__NX_ANTI_DUMP__\n", ""))
        if "__NX_" in candidate:
            continue
        try:
            compile(candidate, "<frag>", "exec")
        except SyntaxError:
            continue
        return candidate
    raise AssertionError("could not find an executable prefix of the template")
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
