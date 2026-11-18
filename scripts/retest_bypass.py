"""Re-test the bypass against the patched call shape.

The first bypass replaced `_nx_self_check()` (bare statement) with `pass` and
the payload ran. The loader now binds the result (`_NX_SELF_OK = _nx_self_check()`)
and folds it into the payload key. An attacker would adapt, so this script
tries the equivalent edits against the NEW shape and reports which, if any,
still let the payload run:

  A. delete the call assignment, leaving `_NX_SELF_OK` unbound
  B. replace the call with a constant (fabricate a "successful" digest)
  C. neuter the comparison inside the function
  D. neuter the failure handler

Run: python3 -I retest_bypass.py <artefact> [marker]
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile


def _validated(path):
    if not path:
        raise ValueError("artefact path required")
    full = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(full):
        raise ValueError("not a regular file: %r" % (path,))
    return full


VARIANTS = (
    ("A-unbound",
     re.compile(r"^([ \t]*)_NX_SELF_OK = _nx_self_check\(\)[ \t]*$", re.M),
     r"\1pass  # call removed"),
    ("B-fabricated",
     re.compile(r"^([ \t]*)_NX_SELF_OK = _nx_self_check\(\)[ \t]*$", re.M),
     r"\1_NX_SELF_OK = '0' * 64"),
    ("C-compare-neutered",
     re.compile(r"if\s+not\s+constant_time_compare\(.*?\)\s*:", re.S),
     "if False:"),
    ("D-failhandler-neutered",
     re.compile(r"^([ \t]*)_nx_self_fail\(", re.M),
     r"\1(lambda *a, **k: None)("),
)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    art = _validated(sys.argv[1])
    marker = sys.argv[2] if len(sys.argv) > 2 else None
    with open(art, encoding="utf-8", errors="surrogateescape") as fh:
        base = fh.read()

    workdir = tempfile.mkdtemp(prefix="retest-")
    control = os.path.join(workdir, "control.py")
    shutil.copyfile(art, control)

    def run(path):
        p = subprocess.run([sys.executable, path], cwd=workdir,
                           capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, NIXON_LOG_REDIRECT="0"),
                           shell=False)
        out = (p.stdout or "") + (p.stderr or "")
        ok = p.returncode == 0 and (marker is None or marker in out)
        return p.returncode, ok, out.strip()[-120:].replace("\n", " ")

    c_rc, c_ok, _ = run(control)
    print("control: rc=%s payload_ran=%s" % (c_rc, c_ok))
    if not c_ok:
        raise SystemExit("control did not run; results would be meaningless")

    bypasses = []
    for name, pattern, repl in VARIANTS:
        if not pattern.search(base):
            print("%-24s pattern absent (shape changed)" % (name,))
            continue
        patched = pattern.sub(repl, base, count=1)
        if patched == base:
            print("%-24s no change" % (name,))
            continue
        path = os.path.join(workdir, name + ".py")
        with open(path, "w", encoding="utf-8",
                  errors="surrogateescape") as fh:
            fh.write(patched)
        rc, ok, tail = run(path)
        verdict = "BYPASS" if ok else "blocked"
        if ok:
            bypasses.append(name)
        print("%-24s rc=%-4s payload_ran=%-5s %-8s %s"
              % (name, rc, ok, verdict, tail[:60]))
    print()
    if bypasses:
        print("STILL BYPASSABLE by: %s" % (", ".join(bypasses),))
        return 1
    print("No single-edit bypass found against the hardened call shape.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
