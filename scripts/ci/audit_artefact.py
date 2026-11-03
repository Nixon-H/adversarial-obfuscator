"""Audit the portable artefact under varied environments.

Cheap, repeatable checks that a single happy-path run cannot find: path assumptions,
hash-seed dependence, repeated runs, odd locations, missing trailing newline, symlinks.

Each check reports PASS/FAIL; the script exits non-zero if any fails, so it composes
with CI and with a loop.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTEFACT = os.environ.get(
    "AUDIT_ARTEFACT",
    os.path.join(HERE, "tests", "fixtures", "portable", "secure_demo_protected.py"))
SOURCE = os.path.join(HERE, "tests", "fixtures", "portable", "secure_demo_source.py")

EXPECTED = None
# macOS runners run the pure-Python FHE/ORAM bootstrap far slower than Linux:
# ~40-60s per invocation was measured, so a 120s budget made the three-run check
# fail as a timeout rather than as a difference.
CHECK_TIMEOUT = 300


def normalise(text):
    return text.replace("\r\n", "\n")


def run(path, cwd=None, env=None):
    e = dict(os.environ)
    e.setdefault("PYTHONIOENCODING", "utf-8")
    if env:
        e.update(env)
    try:
        p = subprocess.run([sys.executable, path], cwd=cwd or os.path.dirname(path),
                           capture_output=True, timeout=CHECK_TIMEOUT, env=e)
    except subprocess.TimeoutExpired:
        # A hang must be reported as a named failure with the environment that
        # caused it, not left to stall the job. This is how the Windows/macOS
        # audit legs stalled for 15 minutes without saying where.
        raise AssertionError("timed out after %ds (cwd=%s env=%s)"
                             % (CHECK_TIMEOUT, cwd, env))
    return p.returncode, normalise(p.stdout.decode("utf-8", "replace"))


def expect():
    global EXPECTED
    if EXPECTED is None:
        _, EXPECTED = run(SOURCE)
    return EXPECTED


RESULTS = []


def check(name, fn):
    # Printed BEFORE the work: if a check hangs, the last line in the log names
    # it, which is the whole point of a diagnostic.
    print("%-46s ..." % name, flush=True)
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001 - the message is the finding
        ok, detail = False, "%s: %s" % (type(exc).__name__, exc)
    RESULTS.append((name, ok, detail))
    print("%-46s %s%s" % (name, "PASS" if ok else "FAIL", "" if ok else "  <- " + detail),
          flush=True)


def c_direct():
    rc, out = run(ARTEFACT)
    return (rc == 0 and out == expect()), "rc=%d" % rc


def c_repeat():
    outs = {run(ARTEFACT)[1] for _ in range(2)}
    return len(outs) == 1 and outs.pop() == expect(), "distinct outputs across 2 runs"


def c_hashseed():
    for seed in ("0", "1", "4294967295"):
        rc, out = run(ARTEFACT, env={"PYTHONHASHSEED": seed})
        if rc != 0 or out != expect():
            return False, "PYTHONHASHSEED=%s rc=%d" % (seed, rc)
    return True, "3 seeds"


def c_cwd_elsewhere():
    with tempfile.TemporaryDirectory() as td:
        rc, out = run(ARTEFACT, cwd=td)
        return (rc == 0 and out == expect()), "rc=%d from %s" % (rc, td)


def c_path_with_spaces():
    with tempfile.TemporaryDirectory() as td:
        spaced = os.path.join(td, "dir with spaces")
        os.makedirs(spaced)
        dst = os.path.join(spaced, "artefact file.py")
        shutil.copy2(ARTEFACT, dst)
        rc, out = run(dst)
        return (rc == 0 and out == expect()), "rc=%d" % rc


def c_renamed():
    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, "renamed.py")
        shutil.copy2(ARTEFACT, dst)
        rc, out = run(dst)
        return (rc == 0 and out == expect()), "rc=%d" % rc


def c_deep_dir():
    with tempfile.TemporaryDirectory() as td:
        deep = os.path.join(td, *["d%d" % i for i in range(12)])
        os.makedirs(deep)
        dst = os.path.join(deep, "a.py")
        shutil.copy2(ARTEFACT, dst)
        rc, out = run(dst)
        return (rc == 0 and out == expect()), "rc=%d" % rc


def c_no_trailing_newline():
    with tempfile.TemporaryDirectory() as td:
        data = open(ARTEFACT, "rb").read()
        dst = os.path.join(td, "a.py")
        with open(dst, "wb") as f:
            f.write(data.rstrip(b"\n") + b"# trailing comment, no newline")
        rc, out = run(dst)
        # Any non-zero exit is the correct answer: edited bytes must be refused,
        # not run. The first version of this check asserted rc != 137, which is
        # backwards -- 137 is exactly what the self-integrity check raises.
        return rc != 0, "edited copy rejected with rc=%d" % rc


def c_tamper_detected():
    with tempfile.TemporaryDirectory() as td:
        data = bytearray(open(ARTEFACT, "rb").read())
        i = len(data) // 2
        data[i] = (data[i] + 1) % 256
        dst = os.path.join(td, "a.py")
        with open(dst, "wb") as f:
            f.write(data)
        rc, out = run(dst)
        return rc != 0, "tampered file rc=%d (0 would mean it ran)" % rc


def c_utf8_env():
    rc, out = run(ARTEFACT, env={"PYTHONUTF8": "1", "LC_ALL": "C"})
    return (rc == 0 and out == expect()), "rc=%d" % rc


def c_readonly_dir():
    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, "a.py")
        shutil.copy2(ARTEFACT, dst)
        os.chmod(td, 0o555)
        try:
            rc, out = run(dst)
        finally:
            os.chmod(td, 0o755)
        return (rc == 0 and out == expect()), "rc=%d in read-only dir" % rc


def c_no_home():
    rc, out = run(ARTEFACT, env={"HOME": "/nonexistent", "TMPDIR": "/tmp"})
    return (rc == 0 and out == expect()), "rc=%d" % rc


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("artefact:", ARTEFACT, os.path.getsize(ARTEFACT), "bytes")
    print("platform:", sys.platform, "python:", sys.version.split()[0])
    print()
    for name, fn in (
        ("direct run", c_direct),
        ("three runs agree", c_repeat),
        ("PYTHONHASHSEED varies", c_hashseed),
        ("cwd elsewhere", c_cwd_elsewhere),
        ("path with spaces", c_path_with_spaces),
        ("renamed file", c_renamed),
        ("deep directory", c_deep_dir),
        ("utf8 env", c_utf8_env),
        ("read-only directory", c_readonly_dir),
        ("HOME missing", c_no_home),
        ("tamper is detected", c_tamper_detected),
        ("edited bytes not accepted", c_no_trailing_newline),
    ):
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print()
    print("%d checks, %d failed" % (len(RESULTS), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
