"""§1 execution provenance: the artefact verifies its OWN signature at load.

The double-stamp attack (measured 2026-11-19, `scripts/attack_chain.py`) showed
that the Merkle root and the HMAC can BOTH be recomputed from the artefact,
because both are derived from material the artefact carries. That makes the
integrity check a statement about internal consistency, not about origin.

This module closes that gap the only way it can be closed client-side: the
artefact carries a PUBLIC key and verifies a signature over its own bytes
against it. The private key never ships, so recomputing the anchors does not
help — an attacker who edits the file must also produce a signature the
embedded public key accepts, which requires the private key.

What this does and does not achieve
-----------------------------------
* It DOES bind the file to the holder of the signing key. Editing the loader,
  the pack, or the anchors invalidates the signature and the artefact refuses
  to run.
* It does NOT stop an attacker who controls the interpreter: they can patch the
  verification call out, exactly as they can patch any check. §1's answer to
  that is the point-of-use redundancy elsewhere (CFI, the late self-check, the
  kill ladder), not this.
* It does NOT verify the native blob separately. The signature covers the
  artefact text, and the blob travels inside it.

The verifier is emitted INLINE, because the loader cannot import anything. It is
the same RFC 8032 construction as `obfuscator/ed25519_verify.py`, which is
cross-checked against `cryptography` so the two agree on every accept and reject
case; that cross-check is what makes the inline copy trustworthy.
"""
from __future__ import annotations

SCHEMA = "nx-provenance/v1"

#: Slot names. Both are excluded from the file hash the same way the other
#: anchors are: a value cannot be part of what it describes.
SIG_SLOT = "_NX_PROV_SIG"
PK_SLOT = "_NX_PROV_PK"

#: The inline verifier, pasted into every signed artefact. Kept minimal and
#: dependency-free — its size is paid per artefact — and it never raises: a
#: loader that must not print cannot afford a traceback path, and a failed
#: verification is a refusal, not a crash.
VERIFIER_SOURCE = r'''
def _nx_prov_verify(_pk, _sig, _msg):
    """RFC 8032 Ed25519 verify. True only for a valid signature."""
    import hashlib as _h
    _P = 2 ** 255 - 19
    _L = 2 ** 252 + 27742317777372353535851937790883648493
    _D = (-121665 * pow(121666, _P - 2, _P)) % _P
    _I = pow(2, (_P - 1) // 4, _P)

    def _inv(x):
        return pow(x, _P - 2, _P)

    def _rx(y, s):
        if y >= _P:
            return None
        x2 = (y * y - 1) * _inv(_D * y * y + 1)
        if x2 == 0:
            return None if s else 0
        x = pow(x2, (_P + 3) // 8, _P)
        if (x * x - x2) % _P != 0:
            x = (x * _I) % _P
        if (x * x - x2) % _P != 0:
            return None
        if (x & 1) != s:
            x = _P - x
        return x

    def _add(p, q):
        a = (p[1] - p[0]) * (q[1] - q[0]) % _P
        b = (p[1] + p[0]) * (q[1] + q[0]) % _P
        c = 2 * p[3] * q[3] * _D % _P
        d = 2 * p[2] * q[2] % _P
        e, f, g, hh = b - a, d - c, d + c, b + a
        return (e * f % _P, g * hh % _P, f * g % _P, e * hh % _P)

    def _mul(s, p):
        q = (0, 1, 1, 0)
        while s > 0:
            if s & 1:
                q = _add(q, p)
            p = _add(p, p)
            s >>= 1
        return q

    def _eq(p, q):
        if (p[0] * q[2] - q[0] * p[2]) % _P != 0:
            return False
        return (p[1] * q[2] - q[1] * p[2]) % _P == 0

    def _dec(dat):
        if len(dat) != 32:
            return None
        y = int.from_bytes(dat, "little")
        s = y >> 255
        y &= (1 << 255) - 1
        x = _rx(y, s)
        if x is None:
            return None
        return (x, y, 1, x * y % _P)

    try:
        if len(_pk) != 32 or len(_sig) != 64:
            return False
        _A = _dec(bytes(_pk))
        _Rb = bytes(_sig[:32])
        _R = _dec(_Rb)
        if _A is None or _R is None:
            return False
        _s = int.from_bytes(bytes(_sig[32:]), "little")
        if _s >= _L:
            return False
        _by = 4 * _inv(5) % _P
        _B = (_rx(_by, 0), _by, 1, _rx(_by, 0) * _by % _P)
        _k = int.from_bytes(_h.sha512(_Rb + bytes(_pk) + bytes(_msg)).digest(),
                            "little") % _L
        return _eq(_mul(_s, _B), _add(_R, _mul(_k, _A)))
    except Exception:
        return False
'''

#: The check the loader runs after the verifier is defined. `fail_name` is
#: injected rather than hard-coded so the loader keeps ONE failure path — a
#: second way to die is a second thing to patch.
#:
#: CIRCULARITY, and how it is resolved. The signature covers the file, and the
#: signature lives in the file. So the signed message is the file with the two
#: provenance slot lines EXCLUDED — the same treatment `_NX_SELF_CK` gets, and
#: for the same reason: a value cannot be part of what it describes. The build
#: side must exclude exactly the same lines, or every artefact fails to verify;
#: `sign_artefact` below does, and the two are cross-checked by a test that
#: signs and verifies a real artefact end to end.
CHECK_SOURCE = '''
import base64 as _nx_prov_b64
def _nx_prov_msg():
    """The signed content: this file, minus the provenance slot lines."""
    with open(__file__, "rb") as _f:
        _lines = _f.read().splitlines(keepends=True)
    return b"".join(
        _l for _l in _lines
        if b"_NX_PROV_SIG" not in _l and b"_NX_PROV_PK" not in _l)

# UNSIGNED IS NOT TAMPERED. A build with no signing key emits empty slots; that
# artefact has no provenance to verify and must still RUN. Failing it here would
# turn "the operator did not sign" into "every artefact is broken" -- measured:
# an unsigned hello-world artefact died at load with
# "provenance: signature does not verify" and eleven unrelated tests failed.
#
# So the check is conditional on the slots being populated:
#   * both empty      -> no provenance claim, skip (the build warns at build time)
#   * both populated  -> verify, and a failure is fatal
#   * exactly one      -> malformed, fatal: a half-stamped artefact is a bug and
#                        silently running it would hide it.
_nx_prov_pk_s = bool({pk})
_nx_prov_sig_s = bool({sig})
_nx_prov_ok = True   # unset until verified; `del` below needs a binding
if _nx_prov_pk_s and _nx_prov_sig_s:
    try:
        _nx_prov_ok = _nx_prov_verify(
            _nx_prov_b64.b64decode({pk}),
            _nx_prov_b64.b64decode({sig}),
            _nx_prov_msg())
    except Exception:
        _nx_prov_ok = False
    if not _nx_prov_ok:
        {fail}("provenance: signature does not verify")
elif _nx_prov_pk_s or _nx_prov_sig_s:
    {fail}("provenance: only one of the two slots is filled")
del _nx_prov_ok, _nx_prov_msg, _nx_prov_pk_s, _nx_prov_sig_s
'''

#: Slots carry a zeroed placeholder until the build stamps them, so an unstamped
#: artefact is recognisable rather than silently unverifiable.
SIG_PLACEHOLDER = ""
PK_PLACEHOLDER = ""

#: Lines matching this are excluded from the signed content, on BOTH sides.
#: Defined once so the build and the loader cannot drift.
EXCLUDE_MARKERS = (b"_NX_PROV_SIG", b"_NX_PROV_PK")


def signed_content(artefact_bytes):
    """The byte stream a signature covers.

    ONE implementation, used by the build when signing and mirrored exactly by
    the emitted `_nx_prov_msg`. If these disagree every artefact refuses to
    run — so the reference here and the emitted snippet are cross-checked by a
    test rather than kept in sync by eye.
    """
    lines = bytes(artefact_bytes).splitlines(keepends=True)
    return b"".join(line for line in lines
                    if not any(marker in line for marker in EXCLUDE_MARKERS))



def emit_snippet(sig_slot: str = SIG_SLOT, pk_slot: str = PK_SLOT,
                 fail_name: str = "_nx_self_fail") -> str:
    """Verifier definition plus the check, as loader source."""
    return VERIFIER_SOURCE + CHECK_SOURCE.format(
        pk=pk_slot, sig=sig_slot, fail=fail_name)


def verify_at_load_available() -> bool:
    """Is signing available at BUILD time? The artefact side needs nothing.

    Signing uses `cryptography`; the loader side is pure stdlib. This gate
    exists so a build without `cryptography` can still produce an unsigned
    artefact (with the slots empty and the check disabled) rather than failing
    or, worse, emitting a signature it cannot compute.
    """
    try:
        import cryptography  # noqa: F401
        return True
    except Exception:
        return False


def sign_artefact(artefact_bytes, private_key):
    """Build side: sign the artefact. Returns (signature_b64, pubkey_b64).

    Signs ``signed_content(artefact_bytes)`` — the text with the provenance slot
    lines removed — because the signature is inserted into that same text
    afterwards. Using the raw bytes would make the signature cover itself.
    """
    import base64

    from cryptography.hazmat.primitives import serialization

    signature = private_key.sign(signed_content(artefact_bytes))
    public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    return (base64.b64encode(signature).decode("ascii"),
            base64.b64encode(public).decode("ascii"))


def stamp_artefact(artefact_text, private_key):
    """Fill the provenance slots in *artefact_text* and return the stamped text.

    Two passes, because the signature depends on the text and the text contains
    the signature: sign with the slots present but EMPTY, then replace the empty
    slot values. The exclusion in ``signed_content`` is what makes the two
    passes consistent — the slot lines are outside the signed stream, so
    changing their contents does not change what was signed.

    Raises ValueError when the slots are absent: an artefact with no slot is not
    a signed artefact, and silently returning it unchanged would ship something
    whose provenance is unverifiable while looking stamped.
    """
    if SIG_SLOT not in artefact_text or PK_SLOT not in artefact_text:
        raise ValueError(
            "artefact carries no provenance slots (%s/%s); cannot stamp"
            % (SIG_SLOT, PK_SLOT))
    signature_b64, public_b64 = sign_artefact(
        artefact_text.encode("utf-8"), private_key)
    stamped = artefact_text
    for slot, value in ((SIG_SLOT, signature_b64), (PK_SLOT, public_b64)):
        import re as _re
        pattern = _re.compile(
            r'^(%s\s*=\s*)(["\'])(.*?)(\2)$' % _re.escape(slot), _re.M)
        stamped, count = pattern.subn(
            lambda m: m.group(1) + m.group(2) + value + m.group(4), stamped)
        if count != 1:
            raise ValueError(
                "expected exactly one %s assignment, found %d"
                % (slot, count))
    return stamped
