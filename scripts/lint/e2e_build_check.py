#!/usr/bin/env python3
"""End-to-end build check: N default builds must produce a RUNNING artifact.

Each iteration builds a fresh payload through the real pipeline CLI in a
scratch directory, then executes the artifact and requires its marker on
stdout.  A build that produces a file which dies at import is a failure,
not a warning: that is exactly the failure mode the seal-corruption bug
had (roughly 80% of default builds produced a dead artifact).

Usage::

    python3 scripts/lint/e2e_build_check.py [iterations] [--section-split]
"""
import os
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

PAYLOAD = '''\
def main():
    print("E2E-OK")


if __name__ == "__main__":
    main()
'''


def _build_and_run(index, extra=()):
    work = tempfile.mkdtemp(prefix="nixon-e2e-")
    try:
        src_dir = os.path.join(work, "src")
        run_dir = os.path.join(work, "run")
        os.makedirs(src_dir)
        os.makedirs(run_dir)
        source = os.path.join(src_dir, "payload.py")
        with open(source, "w", encoding="utf-8") as fh:
            fh.write(PAYLOAD)

        env = dict(os.environ)
        env["NIXON_LOG_REDIRECT"] = "0"
        env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        build = subprocess.run(
            [sys.executable, "-m", "obfuscator.core.pipeline", "build", source]
            + list(extra),
            cwd=run_dir, env=env, capture_output=True, text=True, timeout=1800)
        if build.returncode != 0:
            return False, "build failed: %s" % (build.stderr[-500:])

        packed = [n for n in sorted(os.listdir(src_dir))
                  if n.endswith(".py") and "_Nixon-Enc" in n and "Packed" in n]
        if not packed:
            return False, "no artifact produced"
        artifact = os.path.join(src_dir, packed[0])
        run = subprocess.run([sys.executable, artifact], capture_output=True,
                             text=True, timeout=300, env=env)
        if run.returncode != 0:
            return False, "artifact died: %s" % (run.stderr[-500:])
        if "E2E-OK" not in run.stdout:
            return False, "artifact produced no marker: %r" % (run.stdout[-300:])
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "timed out"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    iterations = int(args[0]) if args else 5
    extra = ["--section-split"] if "--section-split" in sys.argv else []
    failures = []
    for i in range(iterations):
        ok, why = _build_and_run(i, extra)
        status = "ok" if ok else "FAIL"
        print("build %2d/%d: %s%s" % (i + 1, iterations, status,
                                     "" if ok else " -- " + why))
        if not ok:
            failures.append((i, why))
    print("%d/%d builds produced a running artifact"
          % (iterations - len(failures), iterations))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
