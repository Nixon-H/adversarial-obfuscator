"""Write requirements.lock minus one package, for platforms it cannot install on.

numpy publishes no cp314 wheel for Windows, so `pip install -r requirements.lock`
there tries to compile it from source and fails. Nothing else in the lock depends
on numpy, and the project now degrades gracefully without it
(obfuscator/core/np_safe.py), so the honest fix is to install the rest of the stack
rather than skip the whole platform.

requirements.lock is pip-compile output: a name==version line followed by
hash continuation lines. Blocks are dropped whole.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOCK = os.path.join(ROOT, "requirements.lock")


def main():
    drop = sys.argv[1].lower() if len(sys.argv) > 1 else "numpy"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("/tmp", "requirements-no-%s.txt" % drop)
    with open(LOCK, encoding="utf-8") as fh:
        lines = fh.read().splitlines(keepends=True)

    kept, skipping = [], False
    for line in lines:
        stripped = line.strip()
        starts_pkg = (
            line[:1].isalpha() and "==" in line and not stripped.startswith("#")
        )
        if starts_pkg:
            skipping = stripped.split("==", 1)[0].strip().lower() == drop
        if not skipping:
            kept.append(line)

    with open(out, "w", encoding="utf-8") as fh:
        fh.writelines(kept)
    dropped = len(lines) - len(kept)
    print("wrote %s (%d lines kept, %d dropped for %s)" % (out, len(kept), dropped, drop))
    return 0


if __name__ == "__main__":
    sys.exit(main())
