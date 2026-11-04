"""Build with ONE ladder flag at a time, run the artefact, compare to its source.

Every flag in the catalogue is exercised on its own, so a broken transform is
named by the flag that enables it rather than hiding inside a bundle. Sharded so
the whole catalogue fits in CI: --start/--count select a contiguous slice.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flag_catalogue import catalogue  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PAYLOAD = os.path.join(ROOT, "tests", "fixtures", "portable", "constructs_source.py")
SOURCE = os.environ.get("NX_PAYLOAD", DEFAULT_PAYLOAD)
LEVEL = os.environ.get("NX_OPT_LEVEL", "3")
BUILD_TIMEOUT = int(os.environ.get("NX_BUILD_TIMEOUT", "600"))
RUN_TIMEOUT = int(os.environ.get("NX_RUN_TIMEOUT", "300"))


def run(cmd, cwd, timeout):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None


def norm(text):
    return text.replace("\r\n", "\n")


def try_flag(entry, src_out):
    flag = entry["flag"]
    stem = os.path.splitext(os.path.basename(SOURCE))[0]
    out = os.path.join(ROOT, "build", "%s_iso.py" % stem)
    cmd = [sys.executable, "scripts/build.py", "--payload", SOURCE,
           "-o", out, "--force-output", "--opt-level", LEVEL,
           "--skip-irgen", "--skip-llvmgen", "--skip-encrypt", "--skip-relay",
           "--skip-extras"] + entry["argv"]
    built = run(cmd, ROOT, BUILD_TIMEOUT)
    if built is None:
        return "FAIL", "builder timed out"
    if built.returncode != 0:
        tail = (built.stderr or built.stdout).decode("utf-8", "replace").strip().splitlines()
        return "FAIL", "builder exited %d: %s" % (built.returncode, tail[-1][:120] if tail else "")

    artefact = os.path.join(ROOT, "build", "%s_obfuscated.py" % stem)
    if not os.path.exists(artefact):
        return "FAIL", "no artefact produced"

    res = run([sys.executable, artefact], os.path.dirname(artefact), RUN_TIMEOUT)
    if res is None:
        return "FAIL", "artefact timed out"
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", "replace").strip().splitlines()
        return "FAIL", "artefact exited %d: %s" % (res.returncode, err[-1][:120] if err else "")
    if norm(res.stdout.decode("utf-8", "replace")) != src_out:
        return "FAIL", "output differs from source"
    return "PASS", ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    start, count = 0, 10 ** 6
    for i, a in enumerate(sys.argv):
        if a == "--start":
            start = int(sys.argv[i + 1])
        elif a == "--count":
            count = int(sys.argv[i + 1])

    entries = catalogue()
    shard = entries[start:start + count]
    print("catalogue=%d shard=%d..%d (%d flags) payload=%s level=%s"
          % (len(entries), start, start + len(shard) - 1, len(shard),
             os.path.basename(SOURCE), LEVEL))

    src = run([sys.executable, SOURCE], ROOT, RUN_TIMEOUT)
    if src is None or src.returncode != 0:
        print("FATAL: the source payload does not run; nothing to compare against")
        return 2
    src_out = norm(src.stdout.decode("utf-8", "replace"))

    failures = []
    for entry in shard:
        if entry["kind"] == "excluded":
            print("SKIP %-40s %s" % (entry["flag"], entry["why"]))
            continue
        verdict, detail = try_flag(entry, src_out)
        print("%-4s %-40s %s" % (verdict, entry["flag"], detail))
        if verdict == "FAIL":
            failures.append(entry["flag"])

    print("\nshard result: %d flags, %d failed" % (len(shard), len(failures)))
    if failures:
        print("FAILED FLAGS:", " ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
