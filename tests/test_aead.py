"""§2 authenticated encryption: AES-256-GCM, and every way it must refuse.

The review asks for "authenticated encryption using AES-256-GCM or
ChaCha20-Poly1305". The existing helper was AES-**CTR**, which is confidential
but unauthenticated: a modified ciphertext decrypts to garbage and only a later
hash check would notice. That is not the property the requirement asks for.

The tests below are about refusals, because a tampered ciphertext that still
opens is the entire failure mode GCM exists to prevent. Two details are
deliberate and worth stating:

  * the nonce lives INSIDE the envelope. GCM nonce reuse is catastrophic (it
    leaks the authentication key), so the public API has no caller-supplied
    nonce to reuse. ``nonce=`` exists only for the seeded-reproducibility path.
  * the AEAD key is derived with its own label, so it is a different value from
    the CTR/XOR stream key even given the same build secret.
"""
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import (  # noqa: E402
    AEAD_MAGIC, AEAD_NONCE_BYTES, _aead_available, derive_aead_key, open_aead,
    seal_aead)

pytestmark = pytest.mark.skipif(
    not _aead_available(), reason="no AES-GCM backend installed")

KEY = b"k" * 32
PLAINTEXT = b"top secret payload\n" * 20


def _roundtrip(aad=None):
    envelope = seal_aead(PLAINTEXT, KEY, aad=aad)
    return envelope, open_aead(envelope, KEY, aad=aad)


# ── the genuine path ─────────────────────────────────────────────────────

def test_a_sealed_payload_opens_to_the_same_bytes():
    envelope, opened = _roundtrip()
    assert opened == PLAINTEXT


def test_the_envelope_carries_its_magic_and_nonce():
    envelope = seal_aead(PLAINTEXT, KEY)
    assert envelope.startswith(AEAD_MAGIC)
    nonce = envelope[len(AEAD_MAGIC):len(AEAD_MAGIC) + AEAD_NONCE_BYTES]
    assert len(nonce) == AEAD_NONCE_BYTES


def test_the_ciphertext_does_not_contain_the_plaintext():
    envelope = seal_aead(PLAINTEXT, KEY)
    assert b"top secret" not in envelope


def test_each_seal_uses_a_fresh_nonce():
    """The API gives no way to reuse a nonce: that is the point."""
    nonces = set()
    for _ in range(50):
        envelope = seal_aead(PLAINTEXT, KEY)
        nonces.add(envelope[len(AEAD_MAGIC):len(AEAD_MAGIC) + AEAD_NONCE_BYTES])
    assert len(nonces) == 50, "nonce repeated across seals"


def test_two_seals_of_the_same_plaintext_differ():
    """Deterministic ciphertext would leak equality of plaintexts."""
    assert seal_aead(PLAINTEXT, KEY) != seal_aead(PLAINTEXT, KEY)


def test_a_seeded_nonce_is_available_for_reproducible_builds():
    """The ONE reason a nonce may be supplied: identical bytes on rebuild."""
    nonce = b"\x01" * AEAD_NONCE_BYTES
    first = seal_aead(PLAINTEXT, KEY, nonce=nonce)
    second = seal_aead(PLAINTEXT, KEY, nonce=nonce)
    assert first == second
    assert open_aead(first, KEY) == PLAINTEXT


# ── refusals: the reason to use GCM at all ───────────────────────────────

def test_a_flipped_ciphertext_bit_is_rejected():
    envelope = bytearray(seal_aead(PLAINTEXT, KEY))
    envelope[-1] ^= 0x01
    with pytest.raises(ValueError):
        open_aead(bytes(envelope), KEY)


def test_a_flipped_nonce_bit_is_rejected():
    envelope = bytearray(seal_aead(PLAINTEXT, KEY))
    envelope[len(AEAD_MAGIC)] ^= 0x01
    with pytest.raises(ValueError):
        open_aead(bytes(envelope), KEY)


def test_a_truncated_envelope_is_rejected():
    envelope = seal_aead(PLAINTEXT, KEY)
    with pytest.raises(ValueError):
        open_aead(envelope[:len(AEAD_MAGIC) + AEAD_NONCE_BYTES + 4], KEY)


def test_a_stripped_tag_is_rejected():
    envelope = seal_aead(PLAINTEXT, KEY)
    with pytest.raises(ValueError):
        open_aead(envelope[:-8], KEY)


def test_a_wrong_key_is_rejected():
    envelope = seal_aead(PLAINTEXT, KEY)
    with pytest.raises(ValueError):
        open_aead(envelope, b"z" * 32)


def test_a_wrong_aad_is_rejected():
    """AAD binds context: a ciphertext cannot move to a different slot."""
    envelope = seal_aead(PLAINTEXT, KEY, aad=b"section-3")
    with pytest.raises(ValueError):
        open_aead(envelope, KEY, aad=b"section-4")
    # ...and the correct AAD still opens it.
    assert open_aead(envelope, KEY, aad=b"section-3") == PLAINTEXT


def test_a_missing_aad_is_rejected_when_one_was_supplied():
    envelope = seal_aead(PLAINTEXT, KEY, aad=b"section-3")
    with pytest.raises(ValueError):
        open_aead(envelope, KEY)


def test_an_extra_aad_is_rejected_when_none_was_supplied():
    envelope = seal_aead(PLAINTEXT, KEY)
    with pytest.raises(ValueError):
        open_aead(envelope, KEY, aad=b"unexpected")


def test_a_non_envelope_is_rejected():
    with pytest.raises(ValueError):
        open_aead(b"NXAEAD\x02" + b"\x00" * 40, KEY)
    with pytest.raises(ValueError):
        open_aead(b"random bytes that are not an envelope", KEY)


def test_an_invalid_nonce_length_is_refused_at_seal_time():
    with pytest.raises(ValueError):
        seal_aead(PLAINTEXT, KEY, nonce=b"short")


# ── key separation ──────────────────────────────────────────────────────

def test_the_aead_key_is_not_the_raw_build_key():
    """Reusing one value across two constructions spreads a break in one."""
    assert derive_aead_key(KEY) != hashlib.sha256(KEY).digest()
    assert len(derive_aead_key(KEY)) == 32


def test_the_aead_key_is_labelled_and_salted():
    assert derive_aead_key(KEY) != derive_aead_key(KEY, salt=b"other")
    assert derive_aead_key(KEY) != derive_aead_key(b"k" * 31 + b"j")


def test_two_different_build_secrets_give_unrelated_keys():
    left = derive_aead_key(b"a" * 32)
    right = derive_aead_key(b"b" * 32)
    assert left != right
    # Not a byte-wise near-miss.
    assert sum(x != y for x, y in zip(left, right)) > 24


# ── the CTR path is still available and still distinct ───────────────────

def test_aes_ctr_remains_selectable_for_loader_compatibility():
    """The artefact loader is stdlib-only, so CTR must not be removed."""
    from obfuscator.core.pipeline import encrypt_payload, _check_aes_ctr
    if not _check_aes_ctr():
        pytest.skip("no AES-CTR backend")
    sealed = encrypt_payload(PLAINTEXT, KEY, b"n" * 16, use_aes_ctr=True)
    assert sealed != PLAINTEXT
    assert not sealed.startswith(AEAD_MAGIC), (
        "CTR output must not masquerade as an AEAD envelope")


def test_the_xor_stream_is_still_reachable_when_asked_for_deliberately():
    from obfuscator.core.pipeline import encrypt_payload
    sealed = encrypt_payload(PLAINTEXT, KEY, b"n" * 16, use_aes_ctr=False)
    assert sealed != PLAINTEXT
    assert not sealed.startswith(AEAD_MAGIC)
