"""No module may reference a name it never binds.

The lint gate ignores F403/F405, because the package imports its own
modules with ``from .mod import *``.  The consequence is that a name
arriving through a star import is not existence-checked by the linter.

``scripts/lint/check_undefined_globals.py`` closes that gap at runtime:
every ``LOAD_GLOBAL`` in the live tree must resolve.  This test runs it,
so the gap cannot reopen.

It is a separate process on purpose: the check imports every module in
the tree, and some of them are CLI wrappers that touch global state.
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHECKER = os.path.join(REPO_ROOT, "scripts", "lint",
                       "check_undefined_globals.py")


def test_checker_exists():
    assert os.path.exists(CHECKER), "the undefined-globals checker is missing"


def test_no_undefined_globals_in_the_live_tree():
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    proc = subprocess.run([sys.executable, CHECKER], cwd=REPO_ROOT, env=env,
                          capture_output=True, text=True, timeout=900)
    assert proc.returncode == 0, (
        "undefined globals found:\n%s\n%s" % (proc.stdout[-4000:],
                                              proc.stderr[-2000:]))


def test_checker_detects_an_injected_undefined_global(tmp_path):
    """The checker must actually fail on a module with a missing name."""
    import importlib.util

    probe = os.path.join(str(tmp_path), "probe_undef_globals.py")
    with open(probe, "w", encoding="utf-8") as fh:
        fh.write("def f():\n    return definitely_not_defined_anywhere\n")

    spec = importlib.util.spec_from_file_location("probe_undef_globals", probe)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    spec2 = importlib.util.spec_from_file_location(
        "nixon_undef_checker", CHECKER)
    checker = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(checker)

    problems = checker._problems_for(module)
    assert any("definitely_not_defined_anywhere" in p for p in problems), (
        "the checker did not flag the injected undefined global: %r" % (problems,))
