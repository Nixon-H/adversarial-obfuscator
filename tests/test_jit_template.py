"""JIT template encryption must reject short keys and hash the payload."""
import pytest

from irgen.jit_template import encrypt_template


def test_short_key_is_rejected():
    with pytest.raises(ValueError, match="32 bytes"):
        encrypt_template({"template_ir": "x"}, b"short")


def test_integrity_hash_covers_the_payload():
    base = {"template_ir": "aaa", "slot_map": {}, "specializer_ir": ""}
    other = {"template_ir": "bbb", "slot_map": {}, "specializer_ir": ""}
    key = b"k" * 32
    a = encrypt_template(base, key)
    b = encrypt_template(other, key)
    # Header: 20 bytes of lengths, then the 32-byte metadata hash.
    assert a[20:52] != b[20:52]
