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
SOURCE = os.path.join(ROOT, "tests", "fixtures", "portable", "secure_demo_source.py")


def normalise(text):
    return text.replace("\r\n", "\n")


def run_python(path, cwd):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, path], cwd=cwd, capture_output=True,
                       timeout=900, env=env)
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
    print("config: sections=%s zips=%s opt-level=%s watermark=%s"
          % (sections, zips, level, watermark))
    project_argv = ["ai-obf", "build", payload,
                    "--portable", "--section-split", "--section-count", sections,
                    "--zips", zips, "--opt-level", level, "--skip-cloud",
                    "--watermark", watermark]

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

    rc_a, out_a, err_a = run_python(built, os.path.dirname(built))
    rc_s, out_s, _ = run_python(SOURCE, ROOT)

    failures = []
    if rc_s != 0:
        failures.append("source exited %d" % rc_s)
    if rc_a != 0:
        failures.append("artefact exited %d" % rc_a)
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
            print("kept the failing artefact in", keep)
        except Exception as exc:  # noqa: BLE001
            print("could not keep the artefact:", exc)
        return 1
    print("PASS: built on", sys.platform, "and ran correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
