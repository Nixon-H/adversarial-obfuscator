"""Full attack chain: bypass the self-check, then tamper the payload.

Two independently demonstrated facts:
  * replacing `_NX_SELF_OK = _nx_self_check()` with a constant let the payload
    run with integrity checking disabled (variant B of retest_bypass.py);
  * tampering the section pack alone is caught by the merkle self-check.

Put together, the attacker patches ONE line and then has a free hand with the
payload. This script proves the composition instead of arguing it: it patches
the call, corrupts the section pack, and reports whether the artefact still
runs.

Run: python3 -I attack_chain.py <artefact> [marker]
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


CALL = re.compile(r"^([ \t]*)_NX_SELF_OK = _nx_self_check\(\)[ \t]*$", re.M)
PACK = re.compile(r"_NX_SECTION_PACK\s*=\s*'([^']+)'")


def _flip_pack_byte(src):
    """Corrupt one interior byte of the base85 section pack."""
    m = PACK.search(src)
    if not m:
        return src, False
    blob = m.group(1)
    mid = len(blob) // 2
    pos = m.start(1) + mid
    repl = "0" if blob[mid] != "0" else "1"
    return src[:pos] + repl + src[pos + 1:], True


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    art = _validated(sys.argv[1])
    marker = sys.argv[2] if len(sys.argv) > 2 else None
    with open(art, encoding="utf-8", errors="surrogateescape") as fh:
        base = fh.read()

    workdir = tempfile.mkdtemp(prefix="chain-")

    def run(body, name):
        path = os.path.join(workdir, name)
        with open(path, "w", encoding="utf-8",
                  errors="surrogateescape") as fh:
            fh.write(body)
        p = subprocess.run([sys.executable, path], cwd=workdir,
                           capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, NIXON_LOG_REDIRECT="0"),
                           shell=False)
        out = (p.stdout or "") + (p.stderr or "")
        ok = p.returncode == 0 and (marker is None or marker in out)
        return p.returncode, ok, out.strip()[-140:].replace("\n", " ")

    c_rc, c_ok, _ = run(base, "control.py")
    print("control                : rc=%-4s payload_ran=%s" % (c_rc, c_ok))
    if not c_ok:
        raise SystemExit("control did not run; results meaningless")

    tampered, did = _flip_pack_byte(base)
    if did:
        t_rc, t_ok, t_tail = run(tampered, "tamper_only.py")
        print("tamper pack only       : rc=%-4s payload_ran=%-5s %s"
              % (t_rc, t_ok, t_tail[:60]))
    else:
        t_ok = None
        print("tamper pack only       : (no section pack in this artefact)")

    if not CALL.search(base):
        print("bypass+lookup          : call shape not present")
        return 0
    bypassed = CALL.sub(r"\1_NX_SELF_OK = '0' * 64", base, count=1)
    b_rc, b_ok, b_tail = run(bypassed, "bypass_only.py")
    print("bypass only            : rc=%-4s payload_ran=%-5s %s"
          % (b_rc, b_ok, b_tail[:60]))

    chain, had = _flip_pack_byte(bypassed)
    ch_rc, ch_ok, ch_tail = run(chain, "bypass_and_tamper.py")
    print("bypass + tamper        : rc=%-4s payload_ran=%-5s %s"
          % (ch_rc, ch_ok, ch_tail[:60]))

    print()
    if t_ok is False and ch_ok is True:
        print("ATTACK CHAIN CONFIRMED: the pack tamper alone is caught, but "
              "after bypassing the self-check the tampered payload RUNS.")
        return 1
    if ch_ok:
        print("Tampered payload ran with the self-check bypassed "
              "(but tamper-alone was not independently blocked here).")
        return 1
    print("No chain: the tampered payload did not run after the bypass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
