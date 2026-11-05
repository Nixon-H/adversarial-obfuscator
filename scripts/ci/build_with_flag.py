"""Build with scripts/build.py, then run the artefact and compare to its source.

build_on_platform.py drives `ai-obf build`, whose flag set is small. The 273
flags the protection ladder is made of belong to scripts/build.py, so isolating
an individual transform needs this path instead.

NX_EXTRA_FLAGS carries the flags to apply; NX_PAYLOAD the payload.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PAYLOAD = os.path.join(ROOT, "tests", "fixtures", "portable", "secure_demo_source.py")
SOURCE = os.path.normpath(os.environ.get("NX_PAYLOAD", DEFAULT_PAYLOAD))
EXTRA = [f for f in os.environ.get("NX_EXTRA_FLAGS", "").split() if f]
LEVEL = os.environ.get("NX_OPT_LEVEL", "5")


def run(cmd, **kw):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", NIXON_LOG_REDIRECT="0")
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=1800, env=env, **kw)


def norm(text):
    return text.replace("\r\n", "\n")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    stem = os.path.splitext(os.path.basename(SOURCE))[0]
    print("payload:", os.path.basename(SOURCE), "| flags:", EXTRA or ["(none)"])
    print("platform:", sys.platform, "python:", sys.version.split()[0])

    cmd = [sys.executable, "scripts/build.py", "--payload", SOURCE,
           "-o", os.path.join(ROOT, "build", stem + "_ci.py"), "--force-output",
           "--opt-level", LEVEL,
           "--skip-irgen", "--skip-llvmgen", "--skip-encrypt", "--skip-relay",
           "--skip-extras"] + EXTRA
    built = run(cmd)
    if built.returncode != 0:
        print("FAIL: builder exited %d" % built.returncode)
        print(built.stdout.decode("utf-8", "replace")[-2500:])
        print(built.stderr.decode("utf-8", "replace")[-2500:])
        return 1

    artefact = os.path.join(ROOT, "build", stem + "_obfuscated.py")
    if not os.path.exists(artefact):
        print("FAIL: expected", artefact, "| build/ has:",
              sorted(os.listdir(os.path.join(ROOT, "build")))[:12])
        return 1
    print("built:", os.path.getsize(artefact), "bytes")

    a = run([sys.executable, artefact])
    s = run([sys.executable, SOURCE])
    out_a = norm(a.stdout.decode("utf-8", "replace"))
    out_s = norm(s.stdout.decode("utf-8", "replace"))
    err_a = a.stderr.decode("utf-8", "replace")

    failures = []
    if a.returncode != 0:
        failures.append("artefact exited %d" % a.returncode)
    if out_a != out_s:
        failures.append("output differs from source")

    if failures:
        for f in failures:
            print("FAIL:", f)
        print("--- artefact stdout ---\n" + out_a)
        print("--- artefact stderr ---\n" + err_a[:3000])
        print("--- source stdout ---\n" + out_s)
        keep = os.path.join(ROOT, "ci-artifacts")
        os.makedirs(keep, exist_ok=True)
        with open(os.path.join(keep, "failing_artefact.py"), "w", encoding="utf-8") as fh:
            fh.write(open(artefact, encoding="utf-8", errors="replace").read())
        return 1
    print("PASS: built with", EXTRA or "no extra flags", "and ran correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
