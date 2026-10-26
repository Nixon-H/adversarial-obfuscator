"""Textual wiring tests for the archived native stubs.

ARCHIVED 2026-10-26 with their subjects.  These two tests used to live
in ``tests/test_crash_suppression.py`` and asserted three things: the
Linux stub includes ``crash_suppress.h`` and still builds through
``make stub-linux``; the Windows stub guards the same include and call
with ``_WIN32``; and both keep the silent-kill behaviour in the header.

``native/stub_linux.cpp`` and ``native/stub_win.cpp`` moved to
``archive/native/`` (see ../README.md -- reflective loading and AMSI/ETW
patching are out of scope), and the Makefile targets that built them
were removed.  The tests are kept next to the sources they describe and
are no longer collected: pytest runs ``tests/``, not ``archive/``.

The ``make stub-linux`` assertion is retained as the historical record
of the contract; it cannot pass against the shipped Makefile, which no
longer has the target.
"""
import os
import re
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_NATIVE = os.path.dirname(_HERE)
ROOT = os.path.abspath(os.path.join(ARCHIVE_NATIVE, "..", ".."))

HEADER = os.path.join(ARCHIVE_NATIVE, "crash_suppress.h")
LINUX_STUB = os.path.join(ARCHIVE_NATIVE, "stub_linux.cpp")
WIN_STUB = os.path.join(ARCHIVE_NATIVE, "stub_win.cpp")


def test_stub_linux_wires_header_and_builds():
    src = open(LINUX_STUB).read()
    assert '#include "crash_suppress.h"' in src
    assert "nixon_suppress_crash_dialogs();" in src
    assert "PR_SET_DUMPABLE" in src  # still present, not moved into header
    hdr = open(HEADER).read()
    assert "prctl(" not in hdr  # header must not duplicate the prctl call
    r = subprocess.run(
        ["make", "stub-linux"],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, r.stderr[-3000:]


def test_stub_win_wiring_textual():
    src = open(WIN_STUB).read()
    assert '#include "crash_suppress.h"' in src
    assert re.search(r"#ifdef _WIN32\s*\n\s*#include \"crash_suppress\.h\"", src), \
        "win include must be guarded by _WIN32"
    assert re.search(r"#ifdef _WIN32\s*\n.*nixon_suppress_crash_dialogs\(\);",
                     src, re.DOTALL), "win call must be guarded by _WIN32"
    hdr = open(HEADER).read()
    assert "SetErrorMode" in hdr
    assert "SEM_FAILCRITICALERRORS" in hdr
    assert "SEM_NOGPFAULTERRORBOX" in hdr
    assert "SEM_NOOPENFILEERRORBOX" in hdr
    assert "_set_abort_behavior" in hdr
    assert "_WRITE_ABORT_MSG" in hdr
    assert "SIGPIPE" in hdr
    assert "_exit(137)" in hdr
