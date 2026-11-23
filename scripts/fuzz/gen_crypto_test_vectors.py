"""Generate worked test vectors for the cryptographic review bundle.

A reviewer should be able to verify the construction WITHOUT running this
project: recompute each intermediate by hand from K, the nonces and the
plaintext, and check it against what the builder emitted. This script produces
those vectors and prints them in a form that pastes into the bundle.

It is a generator, not a test. The test that pins the published vectors lives in
tests/test_crypto_test_vectors.py, so a wire-format change fails CI rather than
silently making the bundle wrong.
"""
import hashlib
import hmac
import os
import sys

# scripts/fuzz/x.py -> fuzz -> scripts -> repo root. Computed rather than
# required from PYTHONPATH: this is the same trap that broke three other
# reproduction commands in this project, and a generator that only runs when
# the caller happens to have exported a variable is a generator that fails for
# the next person.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from obfuscator.section_split import (  # noqa: E402
    _keystream, _mac_context_v2, _pack_id, _section_keys_v2, split_sealed,
)

KEY = bytes(range(32))
PAYLOAD = b"ABCDEFGH"
NONCE_SEED = b"vector"


def _hex(b):
    return b.hex()


def build():
    pack = split_sealed(PAYLOAD, sections=2, key=KEY, nonce_seed=NONCE_SEED)
    lines = []
    add = lines.append

    add("K            = " + _hex(KEY))
    add("plaintext    = " + _hex(PAYLOAD) + "  (%r)" % (PAYLOAD,))
    add("nonce_seed   = " + _hex(NONCE_SEED))
    add("")
    add("pack_nonce   = " + pack["pack_nonce"])
    pack_nonce = bytes.fromhex(pack["pack_nonce"])
    add("pack_id      = " + _hex(_pack_id(KEY, pack_nonce)) +
        "   (16 bytes)")
    add("key_hint     = " + pack["key_hint"])
    add("state        = " + pack["state"])
    add("v            = %d" % (pack["v"],))
    add("count        = %d" % (pack["count"],))
    add("total        = %d" % (pack["total"],))

    pid = _pack_id(KEY, pack_nonce)
    for sec in pack["sections"]:
        i = sec["i"]
        nonce = bytes.fromhex(sec["nonce"])
        enc_key, mac_key = _section_keys_v2(KEY, i, nonce)
        ctx = _mac_context_v2(i, len(PAYLOAD), nonce, pid,
                              version=pack["v"])
        ciphertext = bytes.fromhex(sec["data"])
        body = bytes(a ^ b for a, b in
                     zip(ciphertext, _keystream(enc_key, nonce, len(ciphertext))))
        tag, part = body[:32], body[32:]
        expected_tag = hmac.new(mac_key, ctx + part,
                                hashlib.sha256).digest()
        add("")
        add("--- section %d ---" % (i,))
        add("nonce        = " + _hex(nonce))
        add("enc_key      = " + _hex(enc_key))
        add("mac_key      = " + _hex(mac_key))
        add("ctx          = " + _hex(ctx) + "   (%d bytes)" % (len(ctx),))
        add("salt         = " + sec["salt"] +
            "   (= sha256(enc_key || nonce)[:16])")
        add("plaintext_i  = " + _hex(part))
        add("tag          = " + _hex(tag))
        add("tag_matches  = %s" % (tag == expected_tag,))
        add("ciphertext   = " + sec["data"][:64] +
            ("..." if len(sec["data"]) > 64 else ""))
        assert tag == expected_tag, "self-check failed for section %d" % (i,)
        assert sec["salt"] == hashlib.sha256(
            enc_key + nonce).hexdigest()[:16], "salt self-check failed"

    add("")
    add("SELF-CHECK: every tag above was recomputed from the stated "
        "intermediates and matched.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(build())
