"""Run the committed portable artefact and compare its output to the source's.

Exists so the CI matrix can test the SAME bytes on Linux, Windows and macOS. The claim is that
one file with no native library runs everywhere; that is only testable by running it everywhere.

Deliberately standalone: no imports from the project, no build step, no network.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE = os.path.join(HERE, "tests", "fixtures", "portable")
ARTEFACT = os.path.join(FIXTURE, "secure_demo_protected.py")
SOURCE = os.path.join(FIXTURE, "secure_demo_source.py")


def run(path):
    kwargs = {}
    if os.name == "nt":
        # Keep the console code page out of the comparison.
        kwargs["env"] = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, path],
        cwd=os.path.dirname(path),
        capture_output=True,
        timeout=900,
        **kwargs
    )
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def main():
    # The artefact's identifiers are unicode. Piping its stderr to a Windows
    # console raised UnicodeEncodeError on cp1252 and failed the job *after* the
    # artefact had printed the correct output -- a CI bug, not a portability one.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("platform:", sys.platform, "| python:", sys.version.split()[0])
    print("artefact:", os.path.basename(ARTEFACT), os.path.getsize(ARTEFACT), "bytes")

    a_rc, a_out, a_err = run(ARTEFACT)
    s_rc, s_out, _ = run(SOURCE)

    print("--- artefact stdout ---")
    print(a_out, end="")
    if a_err.strip():
        print("--- artefact stderr (first 15 lines) ---")
        print("\n".join(a_err.strip().splitlines()[:15]))

    failures = []
    if a_rc != 0:
        failures.append("artefact exited %d" % a_rc)
    if s_rc != 0:
        failures.append("source exited %d" % s_rc)
    if a_out != s_out:
        failures.append("output differs from source")
    # No native library may be referenced or required.
    text = open(ARTEFACT, encoding="utf-8", errors="replace").read()
    if "nixon_core" in text:
        failures.append("artefact still references nixon_core")

    if failures:
        for f in failures:
            print("FAIL:", f)
        print("--- expected ---")
        print(s_out, end="")
        return 1
    print("PASS: identical output on", sys.platform)
    return 0


if __name__ == "__main__":
    sys.exit(main())
