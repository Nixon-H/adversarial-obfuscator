"""The lint cleanup scripts must not remove load-bearing constructs.

Two classes of statement look dead to a linter but are not:

* a **validation probe** -- a call inside a ``try`` whose handler
  catches an exception.  The exception it raises *is* the test:
  ``float(name)`` in a ``try/except ValueError`` answers "is this a
  number?", and deleting it makes the check answer "always yes".
* an **availability probe** -- an import that is the only statement in a
  ``try/except ImportError``.  Deleting it leaves the ``except`` branch
  unreachable and turns the probe into a lie.
* a **method call on an unknown receiver** -- ``p.join(timeout=1)``
  waits for a worker; ``hp.partition(ops)`` mutates its argument.  A
  method *name* is not evidence of purity: ``str.partition`` is pure,
  ``hp.partition`` is not.

Both happened during the 2026-10-19 cleanup and were caught only by the
test suite.  These tests pin the scripts' behaviour so they cannot
recur.
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LINT_DIR = os.path.join(REPO_ROOT, "scripts", "lint")

PROBE = '''\
import os
import time


def _is_numeric(name):
    try:
        float(name)
        return True
    except (ValueError, TypeError):
        return False


def _has_json():
    try:
        import json as _j
    except ImportError:
        return False
    return _j is not None


def _wait(proc):
    proc.join(timeout=1)
    return proc


def _partition(obj, ops):
    obj.partition(ops)
    return ops
'''


def _run(script, path):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    proc = subprocess.run(
        [sys.executable, os.path.join(LINT_DIR, script), path, "--apply"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def _write_probe(tmp_path):
    path = os.path.join(str(tmp_path), "probe_load_bearing.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PROBE)
    return path


def test_cleanup_keeps_the_validation_probe(tmp_path):
    path = _write_probe(tmp_path)
    for script in ("clean_unused_imports.py", "clean_unused_locals.py",
                   "remove_pure_dead_statements.py"):
        _run(script, path)
    with open(path, encoding="utf-8") as fh:
        after = fh.read()
    assert "float(name)" in after, "the validation probe was removed"
    assert "except (ValueError, TypeError):" in after


def test_cleanup_keeps_the_availability_probe(tmp_path):
    path = _write_probe(tmp_path)
    for script in ("clean_unused_imports.py", "clean_unused_locals.py",
                   "remove_pure_dead_statements.py"):
        _run(script, path)
    with open(path, encoding="utf-8") as fh:
        after = fh.read()
    assert "import json as _j" in after, "the availability probe was removed"
    assert "except ImportError:" in after


def test_cleanup_keeps_calls_on_unknown_receivers(tmp_path):
    path = _write_probe(tmp_path)
    for script in ("clean_unused_imports.py", "clean_unused_locals.py",
                   "remove_pure_dead_statements.py"):
        _run(script, path)
    with open(path, encoding="utf-8") as fh:
        after = fh.read()
    assert "proc.join(timeout=1)" in after, "the process join was removed"
    assert "obj.partition(ops)" in after, "the partition call was removed"


def test_cleanup_does_not_break_the_file(tmp_path):
    """After every pass the module must still parse and behave."""
    path = _write_probe(tmp_path)
    for script in ("clean_unused_imports.py", "clean_unused_locals.py",
                   "remove_pure_dead_statements.py"):
        _run(script, path)
    import ast
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    ns = {}
    exec(compile(tree, path, "exec"), ns)
    assert ns["_is_numeric"]("12") is True
    assert ns["_is_numeric"]("abc") is False
    assert ns["_has_json"]() is True
