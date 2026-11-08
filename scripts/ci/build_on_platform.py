"""Build the portable artefact ON this platform, then run it and compare to source.

The previous workflow ran a pre-built artefact everywhere, which proves the artefact is
portable but not that the *builder* is. This script does the build here, so a Windows or
macOS runner produces a Windows- or macOS-built artefact and then has to run it.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.normpath(os.environ.get(
    "NX_PAYLOAD",
    os.path.join(ROOT, "tests", "fixtures", "portable", "secure_demo_source.py")))
# Extra build flags, space separated, so one matrix can isolate individual
# transforms instead of only ever testing the bundle.
EXTRA_FLAGS = [f for f in os.environ.get("NX_EXTRA_FLAGS", "").split() if f]


def normalise(text):
    return text.replace("\r\n", "\n")


HANG_WRAPPER = (
    "import faulthandler, runpy, sys; "
    "faulthandler.dump_traceback_later(%d, exit=True); "
    "sys.argv = [%r]; "
    "runpy.run_path(%r, run_name='__main__')"
)


def run_python(path, cwd, timeout=300):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    argv = [sys.executable, path]
    if os.environ.get("NX_HANG_TRACE") == "1":
        # A hang is Python-level, so faulthandler can name the frame. dump
        # _traceback_later fires even when the main thread never returns, which
        # is exactly the macOS + 3.14 case: the build succeeds and the artefact
        # then runs past the timeout with no output.
        argv = [sys.executable, "-c",
                HANG_WRAPPER % (max(30, timeout // 3), path, path)]
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True,
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        # Report a hang as a named failure instead of letting the traceback
        # escape. macOS + CPython 3.14 hit exactly this: the build succeeded and
        # the artefact then ran for the full 900s and was killed, which the
        # script surfaced as an unrelated-looking stack trace.
        return -1, "", "TIMED OUT after %ds" % timeout
    return p.returncode, normalise(p.stdout.decode("utf-8", "replace")), p.stderr.decode("utf-8", "replace")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("platform:", sys.platform, "| python:", sys.version.split()[0])

    work = tempfile.mkdtemp(prefix="nxbuild_")
    payload = os.path.join(work, "demo.py")
    shutil.copy(SOURCE, payload)

    # Configurable so one matrix can cover several build shapes. Defaults are
    # the strongest portable build.
    sections = os.environ.get("NX_SECTIONS", "6")
    zips = os.environ.get("NX_ZIPS", "2")
    level = os.environ.get("NX_OPT_LEVEL", "5")
    watermark = os.environ.get("NX_WATERMARK", "built-on-ci")
    print("config: sections=%s zips=%s opt-level=%s watermark=%s extra=%s"
          % (sections, zips, level, watermark, EXTRA_FLAGS))
    print("payload:", os.path.basename(SOURCE))
    # PIN THE SEED. Several transforms choose which functions to touch with
    # random.random(), so an unseeded build is a different artefact every run.
    # That made a CI failure impossible to reproduce: a job went red once with a
    # payload-exec error, 461 local iterations could not recreate it, and the
    # re-run of the same commit passed. The variation was not the bug -- losing
    # the ability to reproduce the bug was.
    #
    # NX_BUILD_SEED still overrides this, so a variation sweep is a decision
    # rather than an accident.
    os.environ.setdefault("NX_BUILD_SEED", "20261106")
    project_argv = ["ai-obf", "build", payload,
                    "--portable", "--section-split", "--section-count", sections,
                    "--zips", zips, "--opt-level", level, "--skip-cloud",
                    "--watermark", watermark] + EXTRA_FLAGS

    # Run the builder as a subprocess. Importing pipeline.main and calling it
    # terminates the whole process when the build finishes, so the comparison
    # below never ran and the script exited 0 having proved nothing.
    launcher = (
        "import sys; sys.path.insert(0, %r); "
        "sys.argv = %r; "
        "from obfuscator.core.pipeline import main; main()"
        % (ROOT, project_argv)
    )
    env = dict(os.environ, PYTHONIOENCODING="utf-8", NIXON_LOG_REDIRECT="0")
    proc = subprocess.run([sys.executable, "-c", launcher], cwd=ROOT,
                          capture_output=True, timeout=1800, env=env)
    # The builder's output is captured, so a warning it prints -- the
    # --fast reduced-profile notice is one -- would never reach the CI log.
    _seen_warn = set()
    for _line in (proc.stdout or b'').decode('utf-8', 'replace').splitlines() \
            + (proc.stderr or b'').decode('utf-8', 'replace').splitlines():
        if 'WARN' in _line and _line.strip() not in _seen_warn:
            # The same notice reaches both streams (the builder writes it to stderr
            # and to the saved console handle), so print it once.
            _seen_warn.add(_line.strip())
            print(_line.strip())
    if proc.returncode != 0:
        print("FAIL: builder exited %d" % proc.returncode)
        print(proc.stdout.decode("utf-8", "replace")[-3000:])
        print(proc.stderr.decode("utf-8", "replace")[-3000:])
        return 1

    built = os.path.join(work, "dist", "demo_protected.py")
    if not os.path.exists(built):
        candidates = []
        dist = os.path.join(work, "dist")
        if os.path.isdir(dist):
            candidates = [f for f in os.listdir(dist) if f.endswith(".py") and "protected" in f]
        print("FAIL: expected", built, "| dist has:", candidates)
        return 1

    size = os.path.getsize(built)
    print("built here:", built, size, "bytes")
    text = open(built, encoding="utf-8", errors="replace").read()
    if "nixon_core" in text:
        print("FAIL: the artefact built on this platform still references nixon_core")
        return 1

    # A portable build must ship no native binary. The reference check above is a
    # string grep, which this project has already seen produce a false negative
    # (the loader builds the filename by indirection), so check the directory
    # too: a Linux ELF beside an "OS-independent" artefact is a trap.
    # No unsubstituted template placeholder may survive into an artefact. A
    # single-pass .format() does not re-scan substituted values, so a
    # {NAME} inside one of the injected sources reaches the shipped file
    # literally -- and `if not {VAR_STRICT_DETECTIONS}:` is then a SET LITERAL
    # naming an undefined variable, not a flag. That made restored protections
    # inert and killed the noise threads on NameError while every test passed.
    # Only REAL template placeholders count. A bare {NAME} can be a legitimate
    # set literal in generated code -- `{LKME}` is a set containing the name LKME,
    # and flagging it was a false positive in this guard.
    import re as _re
    _known = set()
    for _src in ("obfuscator/core/sources.py", "obfuscator/core/pipeline.py"):
        try:
            _known.update(_re.findall(r"\{([A-Z][A-Z0-9_]{2,})\}",
                                      open(_src, encoding="utf-8").read()))
        except OSError:
            pass
    leftovers = sorted(set(_re.findall(r"\{([A-Z][A-Z0-9_]{2,})\}", text)) & _known)
    if leftovers:
        print("FAIL: unsubstituted placeholders in the artefact:", leftovers[:6])
        return 1

    dist_dir_check = os.path.dirname(built)
    native = [f for f in os.listdir(dist_dir_check)
              if f.endswith((".so", ".pyd", ".dll", ".dylib"))]
    if native:
        print("FAIL: portable build shipped native binaries:", native)
        return 1

    rc_a, out_a, err_a = run_python(built, os.path.dirname(built))

    # Surface the interpreter-integrity verdict. It only ever wrote to a global
    # nobody read, so a false positive was invisible; now it prints, and under
    # --strict-detections it exits, so CI has to say when it fires.
    if "interpreter-integrity" in err_a:
        # A FALSE POSITIVE, not a note. These runners are known-good interpreters,
        # so anything the guard reports here is the guard being wrong -- and a
        # guard that is wrong on an ordinary host is worse than no guard, because
        # the pressure to silence it is what made it decorative before.
        #
        # Failing the job turns the next occurrence into a red run carrying its
        # own reason code (win-exe-*, win-probe-*, builtins-*, probe-exception-*)
        # instead of a warning nobody reads.
        detail = [ln.strip() for ln in err_a.splitlines() if "integrity" in ln][:2]
        print("FAIL: interpreter-integrity guard fired on a known-good runner:", detail)
        return 1
    rc_s, out_s, _ = run_python(SOURCE, ROOT)

    failures = []
    if rc_s != 0:
        failures.append("source exited %d" % rc_s)
    if rc_a != 0:
        failures.append("artefact exited %d%s" % (rc_a, " (timeout)" if rc_a == -1 else ""))
        print("--- stderr ---")
        print("\n".join(err_a.strip().splitlines()[:20]))
    if out_a != out_s:
        failures.append("output differs from source")
        print("--- artefact output ---")
        print(out_a)
        print("--- source output ---")
        print(out_s)

    if failures:
        for f in failures:
            print("FAIL:", f)
        # Keep the failing artefact where CI can upload it. Without the bytes a
        # one-in-twenty failure is undiagnosable: the whole point is to compare
        # a bad build against a good one.
        try:
            keep = os.path.join(ROOT, "ci-artifacts")
            os.makedirs(keep, exist_ok=True)
            shutil.copy2(built, os.path.join(keep, "failing_artefact.py"))
            shutil.copy2(SOURCE, os.path.join(keep, "source.py"))
            with open(os.path.join(keep, "report.txt"), "w", encoding="utf-8") as fh:
                fh.write("platform: %s\npython: %s\n" % (sys.platform, sys.version))
                fh.write("\n".join(failures))
                # The artefact's own output is the evidence. The first capture
                # was useless without it: the file was there but the reason it
                # exited was not, so the failure could not be attributed.
                fh.write("\n\n--- artefact stdout ---\n" + out_a)
                fh.write("\n--- artefact stderr ---\n" + err_a)
                fh.write("\n--- source stdout ---\n" + out_s)
                # The artefact wrote nothing at all. Find out where its output
                # went: this project has redirected stdout to build.log before,
                # and the artefact runs with cwd=dist, so anything it created
                # lands there.
                import glob as _glob
                fh.write("\n--- dist directory ---\n")
                for name in sorted(os.listdir(os.path.dirname(built))):
                    fh.write("  " + name + "\n")
                for log in _glob.glob(os.path.join(os.path.dirname(built), "*.log")):
                    fh.write("\n--- %s ---\n" % os.path.basename(log))
                    try:
                        fh.write(open(log, encoding="utf-8", errors="replace").read()[-4000:])
                    except Exception as exc:
                        fh.write("<unreadable: %s>" % exc)
            print("kept the failing artefact in", keep)
        except Exception as exc:  # noqa: BLE001
            print("could not keep the artefact:", exc)
        return 1
    print("PASS: built on", sys.platform, "and ran correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
