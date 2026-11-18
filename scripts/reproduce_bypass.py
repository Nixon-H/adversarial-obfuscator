"""Independent reproduction of the self-check-call bypass.

Claim under test: patching the single line `_nx_self_check()` to `pass`
disables the whole integrity gate, and the payload still runs.

The probe reports this; this script reproduces it outside the probe so the
finding does not rest on the probe's own code.

Run: python3 -I reproduce_bypass.py <artefact> [output_marker]
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


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    try:
        art = _validated(sys.argv[1])
    except ValueError as exc:
        raise SystemExit(str(exc))
    marker = sys.argv[2] if len(sys.argv) > 2 else None

    with open(art, encoding="utf-8", errors="surrogateescape") as fh:
        src = fh.read()

    workdir = tempfile.mkdtemp(prefix="bypass-")
    control = os.path.join(workdir, "control.py")
    shutil.copyfile(art, control)

    pattern = re.compile(r"^([ \t]*)_nx_self_check\(\)[ \t]*$", re.M)
    hits = len(pattern.findall(src))
    patched = pattern.sub(r"\1pass  # self-check call removed", src, count=1)
    if patched == src:
        raise SystemExit("pattern did not match; nothing to test")
    victim = os.path.join(workdir, "patched.py")
    with open(victim, "w", encoding="utf-8",
              errors="surrogateescape") as fh:
        fh.write(patched)

    def run(path):
        p = subprocess.run([sys.executable, path], cwd=workdir,
                           capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, NIXON_LOG_REDIRECT="0"),
                           shell=False)
        out = (p.stdout or "") + (p.stderr or "")
        ok = p.returncode == 0
        if marker is not None:
            ok = ok and (marker in out)
        return p.returncode, ok, out.strip()[-160:].replace("\n", " ")

    c_rc, c_ok, c_tail = run(control)
    p_rc, p_ok, p_tail = run(victim)
    print("self-check call sites matched: %d" % hits)
    print("control: rc=%s payload_ran=%s  %s" % (c_rc, c_ok, c_tail))
    print("patched: rc=%s payload_ran=%s  %s" % (p_rc, p_ok, p_tail))
    if c_ok and p_ok:
        print("\nBYPASS CONFIRMED: disabling the self-check CALL alone did not "
              "stop the payload.")
        return 1
    print("\nNo bypass: the patched artefact did not run the payload.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
