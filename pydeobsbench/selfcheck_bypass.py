"""Attack: use the model's own reverse-engineering to defeat the gates.

The model disclosed:
  * the identity gate: `__name__ in ('__main__','__mp_main__')` AND
    `abspath(__file__) == abspath(sys.argv[0])`
  * the self-check filter: it drops every line containing the VALUE of
    `_NX_SELF_CK` / `_NX_SELF_HM` / `_NX_SELF_TOK`

If that description is complete, an attacker can:
  (a) satisfy the identity gate by running the file directly (trivial), and
  (b) neutralise the self-check by editing the check itself -- which the
      filter is supposed to detect.

This probe measures (b): patch the comparison inside the loader and see if the
artefact still runs. If it does, the self-check is bypassable with the
information the model just handed over.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ART = sys.argv[1] if len(sys.argv) > 1 else None
if not ART or not os.path.exists(ART):
    raise SystemExit("usage: selfcheck_bypass.py <artefact>")


def run(path, work):
    env = dict(os.environ, NIXON_LOG_REDIRECT="0")
    p = subprocess.run([sys.executable, os.path.basename(path)], cwd=work,
                       capture_output=True, text=True, timeout=300, env=env)
    return p.returncode, p.stdout + p.stderr


base = open(ART, encoding="utf-8", errors="surrogateescape").read()
work = tempfile.mkdtemp(prefix="bypass-")
shutil.copy2(ART, os.path.join(work, "a.py"))

print("=== control: unpatched ===")
rc, out = run(os.path.join(work, "a.py"), work)
print("  rc=%d ran=%s" % (rc, "=" in out and "ERR" not in out[:200]))

# --- Attack 1: neuter the self-check comparison -----------------------------
# The model says the check compares a computed root against _NX_SELF_CK and
# raises _nx_self_fail on mismatch. Replace the whole _nx_self_check body with
# a no-op, leaving the (hashed) call site intact.
variants = {}

m = re.search(r"def _nx_self_check\(\):(.*?)(?=\ndef |\nif __name__)", base, re.S)
if m:
    variants["noop_self_check"] = base.replace(
        m.group(0),
        "def _nx_self_check():\n    return None\n")

# --- Attack 2: satisfy the identity gate by faking all three inputs --------
# (runs the artefact as a module but presents a matching argv[0]/__file__)
variants["fake_identity"] = base  # control for the identity path only

# --- Attack 3: patch the expected value so the hash matches ----------------
m2 = re.search(r'_NX_SELF_CK = "([0-9a-f]{64})"', base)
if m2:
    # deliberately wrong value: if the loader still runs, the check is inert
    variants["wrong_expected"] = base.replace(
        m2.group(1), "0" * 64, 1)

for name, src in variants.items():
    if src is None:
        continue
    d = tempfile.mkdtemp(prefix="bypass-%s-" % name)
    p = os.path.join(d, "a.py")
    with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(src)
    shutil.copy2("/home/nixon/scratch/bench-max/acme.licence",
                 os.path.join(d, "acme.licence")) if os.path.exists(
        "/home/nixon/scratch/bench-max/acme.licence") else None
    rc, out = run(p, d)
    survived = rc == 0
    # did the payload run? look for any payload-ish marker
    ran = any(t in out for t in ("AUDIT", "TINY", "BENCH", "OK"))
    print("=== %s ===" % name)
    print("  rc=%d payload_ran=%s" % (rc, ran))
    print("  tail:", out.strip()[-160:].replace("\n", " ") or "(silent)")
