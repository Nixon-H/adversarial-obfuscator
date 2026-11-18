"""Self-check bypass, done properly.

The model's disclosure: the check computes a Merkle root over every line
except those containing _NX_SELF_CK / _NX_SELF_HM / _NX_SELF_TOK, then
compares it to _NX_SELF_CK with constant_time_compare.

Three surgical attacks:

  A. Replace ONLY the comparison call with a no-op that returns True, so the
     function still exists and the rest of the loader keeps working.
  B. Patch the payload region (_NX_SECTION_PACK) AND re-stamp _NX_SELF_CK with
     the hash of the patched file -- the attack the HMAC is supposed to stop.
  C. Patch the payload and leave the stamps alone (should die).

Attack B is the one that matters: if an attacker can recompute the anchor,
the self-check is only a speed bump.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

ART = sys.argv[1]
base = open(ART, encoding="utf-8", errors="surrogateescape").read()


def run(src_text, label, licence=None):
    d = tempfile.mkdtemp(prefix="sc-%s-" % label)
    p = os.path.join(d, "a.py")
    with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(src_text)
    env = dict(os.environ, NIXON_LOG_REDIRECT="0")
    if licence and os.path.exists(licence):
        shutil.copy2(licence, os.path.join(d, "acme.licence"))
    proc = subprocess.run([sys.executable, "a.py"], cwd=d,
                          capture_output=True, text=True, timeout=300, env=env)
    out = proc.stdout + proc.stderr
    return proc.returncode, out


LIC = "/home/nixon/scratch/bench-max/acme.licence"

print("=== C: control (unpatched) ===")
rc, out = run(base, "ctl", LIC)
print("  rc=%d  payload=%s" % (rc, "AUDIT" in out))

# ---- A: neuter only the comparison --------------------------------------
# find the constant_time_compare call inside the self-check and force True
m = re.search(r"if not constant_time_compare\(([^)]*)\):", base)
if m:
    patched = base.replace(
        m.group(0),
        "if False:  # neutered comparison", 1)
    rc, out = run(patched, "A", LIC)
    print("=== A: comparison neutered ===")
    print("  rc=%d  payload=%s" % (rc, "AUDIT" in out))
    print("  tail:", out.strip()[-120:].replace("\n", " ") or "(silent)")
else:
    print("=== A: comparison pattern not found ===")

# ---- C2: patch the section pack, leave stamps ---------------------------
mpack = re.search(r"_NX_SECTION_PACK\s*=\s*'([^']+)'", base)
if mpack:
    blob = mpack.group(1)
    pos = mpack.start(1) + len(blob) // 2
    flip = "0" if blob[len(blob) // 2] != "0" else "1"
    tampered = base[:pos] + flip + base[pos + 1:]
    rc, out = run(tampered, "C", LIC)
    print("=== C: pack tampered, stamps untouched ===")
    print("  rc=%d  payload=%s" % (rc, "AUDIT" in out))
    print("  tail:", out.strip()[-140:].replace("\n", " ") or "(silent)")

# ---- B: patch the pack AND re-stamp the Merkle anchor ------------------
# The model disclosed the filter: skip lines containing the three VALUES.
if mpack:
    tampered = base[:pos] + flip + base[pos + 1:]

    def merkle(content):
        chunks = [content[i:i + 1024] for i in range(0, len(content), 1024)]
        hs = [hashlib.sha256(c).hexdigest() for c in chunks]
        while len(hs) > 1:
            if len(hs) % 2 == 1:
                hs.append(hs[-1])
            hs = [hashlib.sha256((hs[i] + hs[i + 1]).encode()).hexdigest()
                  for i in range(0, len(hs), 2)]
        return hs[0] if hs else ""

    ck = re.search(r'_NX_SELF_CK = "([0-9a-f]{64})"', tampered)
    hm = re.search(r'_NX_SELF_HM = "([0-9a-f]{64})"', tampered)
    tok = re.search(r'_NX_SELF_TOK = "([^"]*)"', tampered)
    if ck and hm:
        body = tampered.replace(ck.group(0), "", 1)
        body = body.replace(hm.group(0), "", 1)
        if tok:
            body = body.replace(tok.group(0), "", 1)
        root = merkle(body.encode("utf-8"))
        # re-stamp the Merkle anchor with the recomputed root
        b2 = tampered.replace(ck.group(1), root, 1)
        rc, out = run(b2, "B", LIC)
        print("=== B: pack patched + Merkle anchor recomputed ===")
        print("  rc=%d  payload=%s" % (rc, "AUDIT" in out))
        print("  tail:", out.strip()[-200:].replace("\n", " ") or "(silent)")
