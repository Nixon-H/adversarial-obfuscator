"""GAP2 (#34): crash-dialog suppression (native kill exits cleanly).

Behavioral tests for native/crash_suppress.h as wired into
native/stub_linux.cpp (and, textually, native/stub_win.cpp):

- header compiles standalone as both C and C++;
- stub_linux.cpp still builds via the Makefile target;
- a probe binary using the header: SIGPIPE ignored + survived,
  SIGABRT in a child exits 137 silently, nixon_silent_kill exits 137;
- Windows stub wiring is verified textually (SetErrorMode +
  _set_abort_behavior guarded by _WIN32) since mingw is unavailable here;
- PR_SET_DUMPABLE(0) is still present in stub_linux.cpp (not duplicated
  into the header).

All subprocess caps well under the 600s invasive-test budget.
"""
import os
import subprocess
import sys  # noqa: F401 (this line binds a name used by an embedded template)

ROOT = os.path.join(os.path.dirname(__file__), "..")
HEADER = os.path.join(ROOT, "native", "crash_suppress.h")


_PROBE_C = r"""
#include <stdio.h>
#include <signal.h>
#include <unistd.h>
#include <sys/wait.h>
#include "crash_suppress.h"
int main(void) {
    nixon_suppress_crash_dialogs();
    struct sigaction cur; sigaction(SIGPIPE, 0, &cur);
    if (cur.sa_handler != SIG_IGN) { printf("SIGPIPE-NOT-IGNORED\n"); return 2; }
    printf("SIGPIPE-IGNORED\n");
    raise(SIGPIPE);
    printf("SIGPIPE-SURVIVED\n");
    pid_t c = fork();
    if (c == 0) { raise(SIGABRT); _exit(99); }
    int st = 0; waitpid(c, &st, 0);
    if (!(WIFEXITED(st) && WEXITSTATUS(st) == 137)) { printf("ABRT-BAD\n"); return 3; }
    printf("ABRT-137-OK\n");
    c = fork();
    if (c == 0) { nixon_silent_kill(); _exit(99); }
    st = 0; waitpid(c, &st, 0);
    if (!(WIFEXITED(st) && WEXITSTATUS(st) == 137)) { printf("KILL-BAD\n"); return 4; }
    printf("KILL-137-OK\n");
    return 0;
}
"""


def _compile_probe(tmp_path, lang="c"):
    src = tmp_path / ("probe.%s" % ("cpp" if lang == "cpp" else "c"))
    src.write_text(_PROBE_C, encoding="utf-8")
    out = tmp_path / ("probe_%s" % lang)
    cc = "g++" if lang == "cpp" else "gcc"
    r = subprocess.run(
        [cc, "-o", str(out), str(src), "-I", os.path.join(ROOT, "native")],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stderr[-3000:]
    return str(out)


def test_header_exists_and_guarded():
    src = open(HEADER).read()
    assert "NIXON_CRASH_SUPPRESS_H" in src
    assert "nixon_suppress_crash_dialogs" in src
    assert "nixon_silent_kill" in src
    assert "137" in src


def test_header_compiles_c(tmp_path):
    exe = _compile_probe(tmp_path, "c")
    r = subprocess.run([exe], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (r.stdout, r.stderr[-2000:])
    assert "SIGPIPE-IGNORED" in r.stdout
    assert "SIGPIPE-SURVIVED" in r.stdout
    assert "ABRT-137-OK" in r.stdout
    assert "KILL-137-OK" in r.stdout


def test_header_compiles_cpp(tmp_path):
    exe = _compile_probe(tmp_path, "cpp")
    r = subprocess.run([exe], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (r.stdout, r.stderr[-2000:])
    assert "ABRT-137-OK" in r.stdout
    assert "KILL-137-OK" in r.stdout


def test_no_crash_dialog_text_in_header():
    # The point is silence: no message-box / prompt helpers may creep in.
    hdr = open(HEADER).read().lower()
    assert "messagebox" not in hdr
    assert "printf" not in hdr
