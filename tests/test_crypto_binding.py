import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.binding.crypto_binding import CryptoFragmentBinder, Fragment, BoundFragment


def make_fragment(fid: str, size: int = 64) -> Fragment:
    return Fragment(fragment_id=fid, payload=os.urandom(size))


class TestKeyDerivation:
    def test_same_identity_same_binding(self):
        binder = CryptoFragmentBinder(master_key=b"test-secret-32-bytes-long!!!")
        frag = make_fragment("0", 32)
        b1 = binder.bind(frag, "identity-A")
        b2 = binder.bind(frag, "identity-A")
        # Same identity -> different ciphertexts (random IV)
        assert b1.payload_ciphertext != b2.payload_ciphertext
        assert b1.binding_identity == "identity-A"

    def test_different_identity_different_binding(self):
        binder = CryptoFragmentBinder(master_key=b"test-secret-32-bytes-long!!!")
        frag = make_fragment("0", 32)
        b1 = binder.bind(frag, "identity-A")
        b2 = binder.bind(frag, "identity-B")
        assert b1.binding_identity != b2.binding_identity

    def test_genesis_uses_master_key(self):
        frag = Fragment(fragment_id="0", payload=b"test-data")
        binder = CryptoFragmentBinder(master_key=b"test-secret-32-bytes-long!!!")
        bound = binder.bind(frag, "test-id")
        result = binder.unbind(bound, "test-id")
        assert result is not None
        assert result.payload == b"test-data"


class TestFragmentEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        binder = CryptoFragmentBinder()
        frag = Fragment(fragment_id="0", payload=b"Hello, this is a secret fragment!")
        bound = binder.bind(frag, "ctx-1")
        result = binder.unbind(bound, "ctx-1")
        assert result is not None
        assert result.payload == b"Hello, this is a secret fragment!"

    def test_wrong_identity_fails_decryption(self):
        binder = CryptoFragmentBinder()
        frag = Fragment(fragment_id="0", payload=b"Secret data")
        bound = binder.bind(frag, "ctx-A")
        result = binder.unbind(bound, "ctx-B")
        assert result is None

    def test_tampered_ciphertext_fails(self):
        binder = CryptoFragmentBinder()
        frag = Fragment(fragment_id="0", payload=b"Secret data")
        bound = binder.bind(frag, "ctx-A")
        tampered = BoundFragment(
            fragment_id=bound.fragment_id,
            payload_ciphertext=b"\x00" * len(bound.payload_ciphertext),
            binding_identity=bound.binding_identity,
        )
        result = binder.unbind(tampered, "ctx-A")
        assert result is None


class TestCryptoFragmentBinder:
    def test_basic_binding(self):
        binder = CryptoFragmentBinder(master_key=b"test-chain-secret-0123456789ab")
        frag = Fragment(fragment_id="0", payload=b"test")
        bound = binder.bind(frag, "test-ctx")
        assert bound.is_bound()
        assert bound.binding_identity == "test-ctx"

    def test_wrong_identity_fails(self):
        binder = CryptoFragmentBinder(master_key=b"test-chain-secret-0123456789ab")
        frag = Fragment(fragment_id="0", payload=b"test")
        bound = binder.bind(frag, "correct-ctx")
        result = binder.unbind(bound, "wrong-ctx")
        assert result is None

    def test_tampered_data_fails(self):
        binder = CryptoFragmentBinder(master_key=b"test-chain-secret-0123456789ab")
        frag = Fragment(fragment_id="0", payload=b"sensitive-data")
        bound = binder.bind(frag, "ctx-1")
        tampered = BoundFragment(
            fragment_id=bound.fragment_id,
            payload_ciphertext=b"\x01" + bound.payload_ciphertext[1:],
            binding_identity=bound.binding_identity,
        )
        result = binder.unbind(tampered, "ctx-1")
        assert result is None

    def test_wrong_master_key_fails(self):
        binder1 = CryptoFragmentBinder(master_key=b"secret-one-xxxxxxxxxxxxxxxxx")
        binder2 = CryptoFragmentBinder(master_key=b"secret-two-yyyyyyyyyyyyyyyyy")
        frag = Fragment(fragment_id="0", payload=b"test")
        bound = binder1.bind(frag, "same-ctx")
        result = binder2.unbind(bound, "same-ctx")
        assert result is None

    def test_multi_fragment_execution(self):
        binder = CryptoFragmentBinder(master_key=b"test-chain-secret-0123456789ab")
        frag0 = Fragment(fragment_id="0", payload=b"\x01\x02\x03\x04")
        frag1 = Fragment(fragment_id="1", payload=b"\x05\x06\x07\x08")
        b0 = binder.bind(frag0, "test-ctx")
        b1 = binder.bind(frag1, "test-ctx")
        r0 = binder.unbind(b0, "test-ctx")
        r1 = binder.unbind(b1, "test-ctx")
        assert r0 is not None
        assert r1 is not None
        assert r0.payload == b"\x01\x02\x03\x04"
        assert r1.payload == b"\x05\x06\x07\x08"

    def test_single_fragment_isolation(self):
        binder = CryptoFragmentBinder()
        frag = Fragment(fragment_id="0", payload=b"isolated")
        bound = binder.bind(frag, "test-ctx")
        decrypted = binder.unbind(bound, "test-ctx")
        assert decrypted is not None
        assert decrypted.payload == b"isolated"

    def test_is_bound_property(self):
        binder = CryptoFragmentBinder()
        frag = Fragment(fragment_id="0", payload=b"check-bound")
        bound = binder.bind(frag, "ctx")
        assert bound.is_bound()

    def test_unbound_fragment_not_bound(self):
        frag = Fragment(fragment_id="0", payload=b"")
        assert not hasattr(frag, 'is_bound') or not frag.is_bound()

    def test_metadata_preserved(self):
        frag = Fragment(fragment_id="0", payload=b"data", metadata={"key": "value"})
        binder = CryptoFragmentBinder()
        bound = binder.bind(frag, "ctx")
        assert bound.metadata.get("key") == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
