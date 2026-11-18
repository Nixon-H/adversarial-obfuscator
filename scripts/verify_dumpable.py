"""Verify PR_SET_DUMPABLE=0 actually blocks a parent reading /proc/<pid>/mem.

This is the empirical question behind the "process inspection" row of the
runtime-memory work: if the prctl does not stop the read, adding it to the
loader would be decoration and must not be claimed as a control.

Run as: python3 -I verify_dumpable.py
"""
import os
import subprocess
import sys
import tempfile
import time

PR_SET_DUMPABLE = 4


def _child_source():
    """Child program text. Built here so no path is interpolated into code."""
    lines = [
        "import ctypes, time",
        "libc = ctypes.CDLL('libc.so.6', use_errno=True)",
        # argv[1] is the interval to stay alive, passed as a plain integer
        "stay = int(__import__('sys').argv[1])",
        "rc = libc.prctl(%d, 0, 0, 0, 0)" % PR_SET_DUMPABLE,
        "SECRET = b'DUMPABLE_TEST_SECRET_9f3a2b'",
        "__import__('sys').stdout.write(str(rc) + '\\n')",
        "__import__('sys').stdout.flush()",
        "time.sleep(stay)",
    ]
    return "\n".join(lines) + "\n"


def _write_child(directory):
    """Create the child script inside ``directory`` and return its path."""
    name = "child.py"
    if os.path.basename(name) != name:
        raise ValueError("bare filename required")
    target = os.path.join(directory, name)
    if os.path.dirname(os.path.realpath(target)) != os.path.realpath(directory):
        raise ValueError("path escaped its directory")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(_child_source())
    return target


def main():
    workdir = tempfile.mkdtemp(prefix="dumpable-")
    script = _write_child(workdir)
    # List argv, no shell: a path with spaces or metacharacters stays a path.
    proc = subprocess.Popen([sys.executable, script, "3"],
                            stdout=subprocess.PIPE, text=True)
    time.sleep(1.0)
    prctl_rc = proc.stdout.readline().strip() if proc.stdout else "?"
    print("child prctl() returned: %s (0 = success)" % prctl_rc)
    try:
        fd = os.open("/proc/%d/mem" % proc.pid, os.O_RDONLY)
    except PermissionError as exc:
        print("RESULT: BLOCKED (%s)" % (exc,))
    except OSError as exc:
        print("RESULT: error %s" % (exc,))
    else:
        os.close(fd)
        print("RESULT: NOT BLOCKED - the parent could still open the mem fd")
    proc.kill()
    proc.wait()


if __name__ == "__main__":
    main()
