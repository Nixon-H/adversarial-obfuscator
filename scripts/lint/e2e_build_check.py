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
            cwd=run_dir, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        if build.returncode != 0:
            return False, "build failed: %s" % (build.stderr[-500:])

        # Artefact naming moved on: the build writes
        # `<stem>_protected_Packed.py` (and a `_dbg` twin) beside the source,
        # and a sectioned build writes the hybrid loader into dist/ as
        # `<stem>_protected.py`.  The old filter required "_Nixon-Enc" in the
        # name, which no longer appears -- so this check reported 0/5 on
        # builds that were in fact fine (verified: every candidate ran and
        # printed the marker).  Accept the real names, preferring the silent
        # variant over the _dbg twin.
        def _candidates():
            names = sorted(os.listdir(src_dir))
            silent = [n for n in names if n.endswith("_protected_Packed.py")
                      and "_dbg" not in n]
            if silent:
                return [os.path.join(src_dir, n) for n in silent]
            any_packed = [n for n in names if n.endswith("_Packed.py")]
            if any_packed:
                return [os.path.join(src_dir, n) for n in any_packed]
            for sub in ("dist", "dist-staging"):
                d = os.path.join(src_dir, sub)
                if os.path.isdir(d):
                    for root, _dirs, files in os.walk(d):
                        hit = [os.path.join(root, f) for f in files
                               if f.endswith("_protected.py")]
                        if hit:
                            return sorted(hit)
            return []

        packed = _candidates()
        if not packed:
            return False, "no artifact produced"
        artifact = packed[0]
        # Same diagnostic as the pipeline's verification step: a run that
        # hangs must name the frame it is stuck in.  On the 3.14 runner
        # this run times out at 300 s while finishing in ~4 s here.
        env["PYTHONFAULTHANDLER"] = "1"
        proc = subprocess.Popen([sys.executable, artifact],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=env)
        try:
            out, err = proc.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            try:
                import signal as _signal
                proc.send_signal(_signal.SIGABRT)
            except Exception:
                pass
            try:
                out, err = proc.communicate(timeout=30)
            except Exception:
                out, err = "", ""
            print("artifact run timed out; child stack:")
            print((err or "")[-4000:])
            raise
        run = subprocess.CompletedProcess([sys.executable, artifact],
                                          proc.returncode, out, err)
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
    # --no-section-split is passed through to the pipeline; --section-split
    # names the DEFAULT (the pass is on unless --no-section-split), so it
    # needs no extra flag -- but it is a KNOWN flag now, and unknown --flags
    # are an error instead of being silently dropped.
    known = {"--no-section-split", "--section-split"}
    unknown = [a for a in sys.argv[1:] if a.startswith("--") and a not in known]
    if unknown:
        print("unknown flags: %s" % unknown, file=sys.stderr)
        return 2
    extra = ["--no-section-split"] if "--no-section-split" in sys.argv else []
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
