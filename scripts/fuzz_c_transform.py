"""Fuzz the C transform layer: any seed must produce compilable C.

The 2026-11-18 audit found that a random seed produced invalid C
("expected identifier before '{' token", plus an undeclared Cython symbol).
The transform was only ever validated with the seed one build happened to
draw, so "it compiles" was a single sample.  This runs N seeds over the
payload's real Cython output and reports every distinct failure.

Usage: python3 -I scripts/fuzz_c_transform.py <payload.py> [n_seeds]
"""
import os
import re
import subprocess
import sys
import tempfile
import hashlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))


def cython_once(src_path, work):
    r = subprocess.run([sys.executable, "-m", "cython", "-3",
                        os.path.abspath(src_path)], cwd=work,
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise SystemExit("cython failed: %s" % r.stderr[-800:])
    stem = os.path.splitext(os.path.basename(src_path))[0]
    return os.path.join(work, stem + ".c")


def compile_errors(c_path, work):
    inc = subprocess.run([sys.executable, "-c",
                          "import sysconfig;print(sysconfig.get_paths()['include'])"],
                         capture_output=True, text=True).stdout.strip()
    r = subprocess.run(["gcc", "-fsyntax-only", "-std=c99", "-I", inc,
                        "-I", work, c_path],
                       capture_output=True, text=True, timeout=600)
    if r.returncode == 0:
        return []
    errs = [ln for ln in r.stderr.splitlines() if "error:" in ln]
    return errs or [r.stderr.splitlines()[-1]]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    payload = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    work = tempfile.mkdtemp(prefix="ctfuzz-")
    # Cython once; the transform is what is being fuzzed, not Cython.
    src = os.path.join(work, os.path.basename(payload))
    with open(payload, "r", encoding="utf-8") as fh:
        open(src, "w", encoding="utf-8").write(fh.read())
    base_c = cython_once(src, work)
    base = open(base_c, encoding="utf-8", errors="surrogateescape").read()
    print("baseline C: %d bytes, %d lines"
          % (len(base), base.count("\n")))

    import c_transform
    fails = {}
    ok = 0
    for i in range(n):
        seed = hashlib.sha256(b"fuzz-%d" % i).digest()
        out = os.path.join(work, "t%03d.c" % i)
        try:
            res = c_transform.transform_file(base_c, seed, out_path=out)
        except Exception as exc:
            fails.setdefault(("transform-raise", str(exc)[:120]), []).append(i)
            continue
        errs = compile_errors(out, work)
        if not errs:
            ok += 1
            continue
        # Group by the first distinct error signature (line numbers vary).
        sig = re.sub(r":\d+:\d+:", ":L:C:", errs[0])
        sig = re.sub(r"'__pyx_[A-Za-z0-9_]+'", "'__pyx_X'", sig)
        fails.setdefault(sig, []).append((i, res.transforms_applied))

    print("\n%d/%d seeds produced compilable C" % (ok, n))
    if not fails:
        return 0
    print("%d distinct failure signature(s):\n" % len(fails))
    for sig, hits in sorted(fails.items(), key=lambda kv: -len(kv[1])):
        print("  [%d seeds] %s" % (len(hits), sig if isinstance(sig, str) else sig[0]))
        print("      first: %r" % (hits[0],))
    return 1


if __name__ == "__main__":
    sys.exit(main())
