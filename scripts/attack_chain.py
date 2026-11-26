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
import subprocess
import sys
import tempfile

# The re-sign route needs the package (attestation + licensing); this script
# is run as a bare file, so put the repository root on the path here rather
# than relying on the caller's environment.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


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


HK = re.compile(r"^(?P<lead>[ \t]*)_NX_SELF_HK\s*=\s*(?P<q>['\"])(?P<val>[^'\"]*)(?P=q)", re.M)

# Provenance slots (provenance signing, 2026-11-20). Group 1/2 are the
# assignment prefix and the closing quote, so a caller can substitute a new
# value without disturbing the rest of the line.
PK = re.compile(r'(?m)^(_NX_PROV_PK\s*=\s*")([^"]*)(")')
SIG = re.compile(r'(?m)^(_NX_PROV_SIG\s*=\s*")([^"]*)(")')


def restamp_all(src):
    """Recompute BOTH integrity layers: ``_NX_SELF_CK`` and ``_NX_SELF_HM``.

    This is the "double-stamp" attacker, and it is the honest boundary of §1's
    anti-patching claim. The loader verifies:

      * a Merkle root over the file's own lines (`_NX_SELF_CK`), and
      * an HMAC-SHA256 over the same content keyed with `_NX_SELF_HK`.

    Both are derivable from the artefact: the Merkle construction is unkeyed,
    and the HMAC key is a plaintext literal in the same file. §5m measured that
    re-stamping only the Merkle root is insufficient — the HMAC catches it —
    which raised the obvious question this function exists to answer: what
    happens when the attacker recomputes both?

    Returns ``(new_src, ok)``. ``ok`` is False when an anchor is missing, so a
    caller never mistakes "this artefact has no self-check" for "the attack was
    defended against".
    """
    import hashlib
    import hmac

    ck = CK.search(src)
    hm = HM.search(src)
    hk = HK.search(src)
    if not (ck and hm and hk):
        return src, False
    ck_v, hm_v, hk_v = ck.group("val"), hm.group("val"), hk.group("val")
    tok = TOK.search(src)
    tok_v = tok.group("val") if tok else ""

    def _content(text, ck_value, hm_value):
        """The exact byte stream the loader hashes.

        The exclusion set must match the loader's, or a "restamped" artefact
        is rejected by the MERKLE layer before the layer under test is
        reached -- which would make every later row look defended for the
        wrong reason. The loader excludes its own anchor values, the CFI
        sequence slot, the licence token, and (provenance signing, 2026-11-20)
        both provenance slots.
        """
        lines = text.encode("utf-8", "surrogateescape").splitlines(keepends=True)
        return b"".join(
            ln for ln in lines
            if ck_value.encode() not in ln
            and hm_value.encode() not in ln
            and b"_NX_CFI_SEQ = " not in ln
            and b"_NX_PROV_SIG" not in ln
            and b"_NX_PROV_PK" not in ln
            and (not tok_v or tok_v.encode() not in ln))

    def _merkle(content):
        chunks = [content[i:i + 1024] for i in range(0, len(content), 1024)]
        hashes = [hashlib.sha256(b).hexdigest() for b in chunks]
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            hashes = [hashlib.sha256(
                (hashes[i] + hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(hashes), 2)]
        return hashes[0] if hashes else ""

    # First pass: recompute the Merkle root (the HM anchor is still the old
    # value, which is what the loader excludes — so the content is stable).
    root = _merkle(_content(src, ck_v, hm_v))
    if not root:
        return src, False
    out = src[:ck.start("val")] + root + src[ck.end("val"):]

    # Second pass: HMAC over the content with the NEW merkle root in place.
    # The CK line is excluded by value, and that value just changed, so the
    # filter must use the new root — otherwise the HMAC covers a stream the
    # loader will never compute.
    hm_now = HM.search(out)
    content = _content(out, root, hm_now.group("val"))
    try:
        sig = hmac.new(bytes.fromhex(hk_v), content,
                       hashlib.sha256).hexdigest()
    except ValueError:
        return src, False
    out = out[:hm_now.start("val")] + sig + out[hm_now.end("val"):]
    return out, True



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
        print("tamper + restamp (CK)  : rc=%-4s payload_ran=%-5s %s"
              % (rs_rc, rs_ok, rs2_tail[:60]))
    else:
        rs_ok = None
        print("restamp                : no _NX_SELF_CK anchor in this artefact")

    # ── DOUBLE-STAMP: recompute the Merkle root AND the HMAC ─────────────
    #
    # §5m measured that restamping only CK is caught by the HMAC layer. That
    # left the question this row answers: what if the attacker recomputes BOTH?
    # The HMAC key `_NX_SELF_HK` is a plaintext literal in the same file, so
    # nothing prevents it. If this row runs, the integrity control establishes
    # internal consistency, not provenance — and that is the honest scope of
    # the claim rather than a defect to be papered over.
    ds_tampered, did_ds = _flip_pack_byte(base)
    if did_ds:
        ds_src, ds_ok_flag = restamp_all(ds_tampered)
        if ds_ok_flag:
            ds_rc, ds_ok, ds_tail = run(ds_src, "tamper_double_stamp.py")
            print("tamper + BOTH stamps   : rc=%-4s payload_ran=%-5s %s"
                  % (ds_rc, ds_ok, ds_tail[:60]))
        else:
            ds_ok = None
            print("tamper + BOTH stamps   : no anchors (CK/HM/HK) to recompute")
    else:
        ds_ok = None
        print("tamper + BOTH stamps   : no section pack in this artefact")

    # ── INFORMED ATTACKER: re-sign with the attacker's own key ───────────
    #
    # An attacker who reads the loader knows the self-check is internal and
    # that a provenance signature exists. The cheapest route is to sign the
    # tampered file with a key they control and rewrite the embedded public
    # key. Both are in the file. What catches this is the KEY FINGERPRINT:
    # the build writes `<sha256(raw key)[:16]>: <b64>` and the loader
    # recomputes it, so a substituted key no longer matches its own prefix.
    # This row measures that, and it is the strongest evidence for the
    # layered design: it turns a two-line edit into several coordinated ones.
    resign_ok = None
    sig = SIG.search(base)
    pk = PK.search(base)
    if sig and pk:
        try:
            from obfuscator.attestation import signed_content
            from obfuscator.licensing import public_key_hex
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PrivateKey)
            import base64 as _b64

            attacker = Ed25519PrivateKey.generate()
            # 1. tamper, 2. re-stamp CK+HMAC so those layers agree
            stage, _ = _flip_pack_byte(base)
            stage, _ = restamp_all(stage)
            # 3. sign the would-be-shipped bytes with the attacker's key.
            # PK/SIG have three groups: 1 = prefix, 2 = OLD value,
            # 3 = closing quote. Using group(2) here once concatenated the
            # replacement with the previous value and produced a line that
            # merely failed to parse -- which would have made this row look
            # "blocked" when nothing had actually been checked.
            signature = attacker.sign(signed_content(stage.encode("utf-8")))
            forged = PK.sub(
                lambda m: m.group(1) + public_key_hex(attacker) + m.group(3),
                stage, count=1)
            forged = SIG.sub(
                lambda m: m.group(1) + _b64.b64encode(signature).decode()
                + m.group(3),
                forged, count=1)
            r_rc, r_ok, r_tail = run(forged, "resign_attacker_key.py")
            print("re-sign, attacker key  : rc=%-4s payload_ran=%-5s %s"
                  % (r_rc, r_ok, r_tail[:60]))
            resign_ok = r_ok
        except Exception as exc:
            print("re-sign, attacker key  : skipped (%s)" % (type(exc).__name__,))
    else:
        print("re-sign, attacker key  : no provenance slots in this artefact")

    # ── INFORMED ATTACKER: forge the CFI checkpoint chain ────────────────
    #
    # The CFI chain folds tags into a digest seeded from _NX_SELF_HK. An
    # attacker holding the whole file can recompute the expected value, which
    # is why the chain is a tamper-detector rather than a trust anchor --
    # §5r records that limit. This row makes the limit measured instead of
    # asserted: remove a checkpoint and recompute the chain.
    cfi_ok = None
    SEQ = re.compile(r'(?m)^(_NX_CFI_SEQ\s*=\s*")([0-9a-f]*)"')
    if SEQ.search(base) and "_nx_cfi_mark(" in base:
        try:
            stripped = re.sub(r"(?m)^\s*_nx_cfi_mark\([^)]*\)\n", "", base,
                              count=1)
            got = SEQ.search(stripped)
            if got and got.group(2) and set(got.group(2)) != {"0"}:
                # recompute the chain over the remaining checkpoints
                seed_m = HK.search(stripped)
                tags = re.findall(r"_nx_cfi_mark\(\s*['\"]([^'\"]+)['\"]",
                                  stripped)
                import hashlib as _h
                state = _h.sha256(
                    ("nx-cfi/v1:" + (seed_m.group("val") if seed_m else "")
                     ).encode()).digest()
                for tag in tags:
                    state = _h.sha256(state + str(tag).encode()).digest()
                forged_chain = SEQ.sub(
                    lambda m: m.group(1) + state.hex() + '"', stripped, count=1)
                c_rc, c_ok, c_tail = run(forged_chain, "cfi_forged.py")
                print("CFI removed + rechain  : rc=%-4s payload_ran=%-5s %s"
                      % (c_rc, c_ok, c_tail[:60]))
                cfi_ok = c_ok
        except Exception as exc:
            print("CFI removed + rechain  : skipped (%s)" % (type(exc).__name__,))
    else:
        print("CFI removed + rechain  : no CFI chain in this artefact")

    print()
    if ds_ok:
        print("INTEGRITY IS INTERNAL-ONLY: a tampered payload ran once _NX_SELF_CK "
              "AND _NX_SELF_HM were recomputed. Both layers are derivable from "
              "the artefact, so the check proves the file is self-consistent, "
              "not that it came from the publisher. The fix is load-time "
              "signature verification (obfuscator/attestation.py); see "
              "docs/security/THREAT_BOUNDARY_LOADER.md.")
        return 1
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
    # The two informed-attacker rows (2026-11-20). They are the ones that
    # distinguish "one layer held" from "the layers are independent".
    if resign_ok:
        print("SIGNATURE NOT BINDING: a tampered payload ran after it was "
              "re-signed with an attacker-controlled key. The key fingerprint "
              "prefix or the out-of-band pin is missing from this build; see "
              "docs/security/THREAT_BOUNDARY_LOADER.md "
              "(double-stamp mitigation).")
        return 1
    if cfi_ok:
        print("CFI IS A TAMPER DETECTOR, NOT A TRUST ANCHOR: the checkpoint "
              "chain was recomputed from the file's own seed and the payload "
              "ran. Recorded as a known limit (§5r); the protection is that "
              "removing a checkpoint is DETECTED, not that it is impossible.")
        return 1
    print("No chain: the tampered payload did not run after the bypass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
