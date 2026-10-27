"""Run a generated artifact, and name the frame when it hangs.

Every 3.13/3.14 CI failure of this shape has been "the artifact run timed
out" with an empty message: a bare ``TimeoutExpired`` is the least useful
diagnostic there is, and the run finishes in seconds on a dev machine, so
the failing path only exists on the runner.

This starts the child under ``faulthandler`` and sends ``SIGABRT`` when
the timeout expires, so the child prints the Python stack it is stuck in
before the exception propagates.  That is how the uuid.getnode() stall
was found; the same instrumentation is what the remaining intermittent
hang needs.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys


def run_artifact(path, *, timeout=300, env=None, cwd=None):
    """Run ``path`` with the current interpreter; return CompletedProcess."""
    child_env = dict(env if env is not None else os.environ)
    child_env.setdefault("PYTHONFAULTHANDLER", "1")
    proc = subprocess.Popen(
        [sys.executable, path], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, env=child_env, cwd=cwd)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.send_signal(signal.SIGABRT)
        except Exception:
            pass
        try:
            out, err = proc.communicate(timeout=30)
        except Exception:
            out, err = "", ""
        print("[!] artifact run timed out after %ss; child stack:" % timeout)
        print((err or "")[-4000:])
        raise
    return subprocess.CompletedProcess(
        [sys.executable, path], proc.returncode, out, err)
