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
#: Both quote styles: the loader emits double quotes, older artefacts and tests
#: use single. Matching only one silently skipped the restamp scenario, which is
#: the most important row — so it accepts both.
CK = re.compile(r"^(?P<lead>[ \t]*)_NX_SELF_CK\s*=\s*(?P<q>['\"])(?P<val>[^'\"]*)(?P=q)", re.M)
HM = re.compile(r"^(?P<lead>[ \t]*)_NX_SELF_HM\s*=\s*(?P<q>['\"])(?P<val>[^'\"]*)(?P=q)", re.M)
TOK = re.compile(r"^(?P<lead>[ \t]*)_NX_SELF_TOK\s*=\s*(?P<q>['\"])(?P<val>[^'\"]*)(?P=q)", re.M)


def recompute_self_ck(src):
    """Recompute ``_NX_SELF_CK`` from the artefact's own text.

    The self-check is a Merkle root over the file's own lines, excluding the
    anchor lines — and the exclusion set is DERIVED FROM THE FILE. Nothing in
    that construction is a secret, so an attacker who edits the payload can
    recompute the stamp. This function exists to MEASURE that, not to enable
    it: if it produces a stamp the loader accepts, the integrity check is bound
    to the file's text rather than to the publisher.

    Returns ``(new_src, ok)``.
    """
    import hashlib

    ck = CK.search(src)
    hm = HM.search(src)
    tok = TOK.search(src)
    if not ck:
        return src, False
    ck_v = ck.group("val")
    hm_v = hm.group("val") if hm else ""
    tok_v = tok.group("val") if tok else ""
    lines = src.encode("utf-8", "surrogateescape").splitlines(keepends=True)
    filtered = [ln for ln in lines
                if ck_v.encode() not in ln
                and (not hm_v or hm_v.encode() not in ln)
                and b"_NX_CFI_SEQ = " not in ln
                and (not tok_v or tok_v.encode() not in ln)]
    content = b"".join(filtered)
    chunks = [content[i:i + 1024] for i in range(0, len(content), 1024)]
    hashes = [hashlib.sha256(b).hexdigest() for b in chunks]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [hashlib.sha256((hashes[i] + hashes[i + 1]).encode()).hexdigest()
                  for i in range(0, len(hashes), 2)]
    root = hashes[0] if hashes else ""
    if not root:
        return src, False
    return src[:ck.start("val")] + root + src[ck.end("val"):], True


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

    # ── re-stamp: tamper WITHOUT touching the self-check ─────────────────
    #
    # This is the scenario that matters most, because it does not require the
    # attacker to disable anything. The self-check is a Merkle root over the
    # file's own lines, and the exclusion set is derived from the file, so a
    # tampered artefact can carry a consistent stamp. If this row shows the
    # payload running, the integrity check is bound to the artefact's TEXT, not
    # to the publisher — and §1's "anti-patching redundancy" reduces to
    # "recompute one hash".
    restamped_src, could = recompute_self_ck(base)
    if could:
        restamped_only_rc, restamped_only_ok, rs_tail = run(
            restamped_src, "restamp_only.py")
        print("restamp (no edit)      : rc=%-4s payload_ran=%-5s %s"
              % (restamped_only_rc, restamped_only_ok, rs_tail[:60]))
        tampered_then, _ = _flip_pack_byte(base)
        restamped, _ = recompute_self_ck(tampered_then)
        rs_rc, rs_ok, rs2_tail = run(restamped, "tamper_then_restamp.py")
        print("tamper + restamp       : rc=%-4s payload_ran=%-5s %s"
              % (rs_rc, rs_ok, rs2_tail[:60]))
    else:
        rs_ok = None
        print("restamp                : no _NX_SELF_CK anchor in this artefact")

    print()
    if rs_ok:
        print("SELF-CHECK IS NOT BINDING: a tampered payload ran after the "
              "stamp was recomputed from the artefact's own text. The check "
              "detects accidental corruption, not a deliberate edit.")
        return 1
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
