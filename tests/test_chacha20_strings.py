"""AUDIT GAP #55: ChaCha20 string encryption with allowlist.

Covers: RFC 8439 vector, AEAD round-trips (empty/unicode/long/binary-safe),
tamper rejection, allowlist (exact + regex), stub/module equivalence,
sources-level end-to-end, per-build uniqueness, legacy default preserved.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from obfuscator.chacha20 import (
    aead_decrypt,
    aead_encrypt,
    build_stub_decoder,
    chacha20_block,
    chacha20_xor,
)
from obfuscator.string_crypto import (
    decrypt_string,
    emit_decoder_source,
    encrypt_string,
    is_allowlisted,
    make_session,
    normalize_mode,
)

RFC_KEY = bytes(range(32))
# RFC 8439 Section 2.4.2: key 00..1f, nonce 00000009:0000004a:00000000.
RFC_NONCE = bytes.fromhex("000000090000004a00000000")
RFC_KEYSTREAM = "10f1e7e4d13b5915500fdd1fa32071c4"


def test_rfc8439_section_242_vector():
    ks = chacha20_block(RFC_KEY, 1, RFC_NONCE)
    assert len(ks) == 64
    assert ks.hex().startswith(RFC_KEYSTREAM)


def test_rfc8439_encryption_vector():
    # RFC 8439 Section 2.4.2: encrypting 114 zero bytes ("Ladies and ...").
    ct = chacha20_xor(RFC_KEY, RFC_NONCE, bytes(114), counter=1)
    assert ct.hex().startswith(RFC_KEYSTREAM)
    assert ct != bytes(114)


def test_chacha20_xor_is_inverse():
    pt = b"the quick brown fox"
    ct = chacha20_xor(RFC_KEY, RFC_NONCE, pt)
    assert chacha20_xor(RFC_KEY, RFC_NONCE, ct) == pt


@pytest.mark.parametrize("pt", [
    b"",
    b"a",
    b"hello world",
    "héllo wörld 🔒 residues ✓".encode("utf-8"),
    b"x" * 200,
    b"\x00\x01\x02 binary \xff safe \x00",
])
def test_aead_roundtrip(pt):
    blob = aead_encrypt(RFC_KEY, pt)
    # wire format: nonce(12) || ct || tag(16)
    assert len(blob) == 12 + len(pt) + 16
    assert aead_decrypt(RFC_KEY, blob) == pt


@pytest.mark.parametrize("tamper", ["nonce", "ciphertext", "tag", "truncate"])
def test_aead_tamper_rejected(tamper):
    blob = bytearray(aead_encrypt(RFC_KEY, b"secret payload here!!"))
    if tamper == "nonce":
        blob[0] ^= 1
    elif tamper == "ciphertext":
        blob[14] ^= 1
    elif tamper == "tag":
        blob[-1] ^= 1
    else:
        del blob[-5:]
    with pytest.raises(ValueError):
        aead_decrypt(RFC_KEY, bytes(blob))


def test_aead_wrong_key_rejected():
    blob = aead_encrypt(RFC_KEY, b"data")
    with pytest.raises(ValueError):
        aead_decrypt(bytes([7]) * 32, blob)


def test_aead_key_nonce_validation():
    with pytest.raises(ValueError):
        aead_encrypt(b"short", b"data")
    with pytest.raises(ValueError):
        aead_encrypt(RFC_KEY, b"data", nonce=b"short")
    with pytest.raises(ValueError):
        aead_decrypt(RFC_KEY, b"too short")


def test_aead_random_nonce_unique():
    b1 = aead_encrypt(RFC_KEY, b"same plaintext")
    b2 = aead_encrypt(RFC_KEY, b"same plaintext")
    assert b1 != b2  # fresh 96-bit nonce per seal


def test_aead_explicit_nonce_deterministic():
    b1 = aead_encrypt(RFC_KEY, b"pt", nonce=RFC_NONCE)
    b2 = aead_encrypt(RFC_KEY, b"pt", nonce=RFC_NONCE)
    assert b1 == b2


def test_allowlist_exact_and_regex():
    allow = ["keepme", "re:^sk-"]
    assert is_allowlisted("keepme", allow)
    assert is_allowlisted("sk-live-123", allow)
    assert not is_allowlisted("keepme2", allow)
    assert not is_allowlisted("hello world", allow)
    assert is_allowlisted("keepme", "keepme")  # bare str also accepted
    assert not is_allowlisted("hello", None)


def test_allowlist_sentinels_always_plaintext():
    assert is_allowlisted("_NX_PART_0", ["re:.*"])
    assert is_allowlisted("xxPLACEHOLDERxx", None)
    assert is_allowlisted("__NX_STR_KEY_A__", None)


def test_encrypt_string_allowlist_returns_none():
    key = bytes(range(32))
    assert encrypt_string("keepme", key, ["keepme"]) is None
    seal = encrypt_string("secret", key, ["keepme"])
    assert isinstance(seal, str)
    assert decrypt_string(seal, key) == "secret"


def test_encrypt_string_rejects_non_str():
    with pytest.raises(TypeError):
        encrypt_string(123, bytes(range(32)))


def test_normalize_mode():
    assert normalize_mode(None) == "chacha20"
    assert normalize_mode("chacha20") == "chacha20"
    assert normalize_mode("xor") == "xor"
    assert normalize_mode("legacy") == "xor"
    assert normalize_mode("bogus-future-mode") == "chacha20"


def test_make_session_roundtrip():
    session = make_session()
    assert len(session["key"]) == 32
    seal = session["encrypt"]("hello")
    assert session["decrypt"](seal) == "hello"
    pinned = make_session(bytes([9]) * 32)
    assert pinned["key"] == bytes([9]) * 32


def test_stub_matches_module_implementation():
    key = bytes(range(32))
    ns = {}
    exec(compile(build_stub_decoder("nxdec", key.hex()), "<stub>", "exec"), ns)
    for pt in ["", "hello world", "héllo wörld 🔒", "x" * 200, "a\x00b Humphrey"]:
        blob = aead_encrypt(key, pt.encode("utf-8")).hex()
        assert ns["nxdec"](blob) == pt
    # stub enforces the tag too
    blob = bytearray(aead_encrypt(key, b"tamper me please"))
    blob[-1] ^= 1
    with pytest.raises(ValueError):
        ns["nxdec"](bytes(blob).hex())


def test_stub_rejects_bad_name():
    with pytest.raises(ValueError):
        build_stub_decoder("not a name!", "00" * 32)


def test_transformer_chacha_end_to_end():
    from obfuscator.core.transforms import StringLiteralObfuscator
    slo = StringLiteralObfuscator(mode="chacha20", allowlist=["keepme"])
    tree = ast.parse('a = "hello world"\nb = "keepme"\n')
    tree = slo.visit(tree)
    code = slo.get_preamble() + "\n" + ast.unparse(tree)
    assert "hello world" not in code
    assert "'keepme'" in code  # allowlisted: stays plaintext
    ns = {}
    exec(compile(code, "<t>", "exec"), ns)
    assert ns["a"] == "hello world"
    assert ns["b"] == "keepme"


def test_transformer_chacha_regex_allowlist():
    from obfuscator.core.transforms import StringLiteralObfuscator
    slo = StringLiteralObfuscator(mode="chacha20", allowlist=["re:^sk-"])
    tree = ast.parse('a = "sk-live-1"\nb = "hidden gem"\n')
    tree = slo.visit(tree)
    code = slo.get_preamble() + "\n" + ast.unparse(tree)
    assert "sk-live-1" in code
    assert "hidden gem" not in code
    ns = {}
    exec(compile(code, "<t>", "exec"), ns)
    assert ns["a"] == "sk-live-1"
    assert ns["b"] == "hidden gem"


def test_transformer_chacha_unicode_and_emptyish():
    from obfuscator.core.transforms import StringLiteralObfuscator
    slo = StringLiteralObfuscator(mode="chacha20")
    tree = ast.parse('a = "héllo wörld 🔒"\nb = "xy"\n')
    tree = slo.visit(tree)
    code = slo.get_preamble() + "\n" + ast.unparse(tree)
    ns = {}
    exec(compile(code, "<t>", "exec"), ns)
    assert ns["a"] == "héllo wörld 🔒"
    assert ns["b"] == "xy"


def test_sources_level_chacha_end_to_end():
    from obfuscator.core.sources import apply_ast_mutation
    src = 'MSG = "hello world"\nVAL = MSG.upper() + "!"\n'
    out, _ = apply_ast_mutation(
        src, {"fragment_strings": True, "string_crypto": "chacha20",
              "string_allowlist": ["keep"]})
    assert "hello world" not in out
    ns = {}
    exec(compile(out, "<t>", "exec"), ns)
    assert ns["VAL"] == "HELLO WORLD!"


def test_sources_level_allowlist_stays_plaintext():
    from obfuscator.core.sources import apply_ast_mutation
    src = 'A = "keepme secret"\nB = "hide this string!!"\n'
    out, _ = apply_ast_mutation(
        src, {"fragment_strings": True, "string_crypto": "chacha20",
              "string_allowlist": ["keepme secret"]})
    assert "keepme secret" in out
    assert "hide this string!!" not in out
    ns = {}
    exec(compile(out, "<t>", "exec"), ns)
    assert ns["A"] == "keepme secret"
    assert ns["B"] == "hide this string!!"


def test_sources_level_xor_default_unchanged():
    from obfuscator.core.sources import apply_ast_mutation
    src = 'MSG = "hello world"\nVAL = MSG.upper()\n'
    out_legacy, _ = apply_ast_mutation(src, {"fragment_strings": True})
    ns = {}
    exec(compile(out_legacy, "<t>", "exec"), ns)
    assert ns["VAL"] == "HELLO WORLD"
    # legacy path emits the XOR stub, never the ChaCha20 stub
    assert "string seal" not in out_legacy


def test_per_build_uniqueness():
    from obfuscator.core.sources import apply_ast_mutation
    src = 'MSG = "identical input string here!!"\n'
    out1, _ = apply_ast_mutation(
        src, {"fragment_strings": True, "string_crypto": "chacha20"})
    out2, _ = apply_ast_mutation(
        src, {"fragment_strings": True, "string_crypto": "chacha20"})
    assert out1 != out2  # fresh key + nonces per build


def test_pinned_key_deterministic_with_seed():
    from obfuscator.core.pipeline import ObfuscationTransformer
    src = 'MSG = "identical input string here!!"\n'
    key = bytes([3]) * 32
    t1 = ObfuscationTransformer(seed=77)
    t2 = ObfuscationTransformer(seed=77)
    opts = {"fragment_strings": True, "string_crypto": "chacha20",
            "string_key": key}
    assert t1.transform(src, options=dict(opts)) == t2.transform(src, options=dict(opts))


def test_legacy_string_obfuscator_untouched():
    # Additive principle: default constructor path is byte-identical legacy.
    from obfuscator.core.transforms import StringLiteralObfuscator
    slo = StringLiteralObfuscator()
    assert slo.mode == "xor"
    tree = ast.parse('x = "secretsauce"')
    slo.visit(tree)
    assert isinstance(tree.body[0].value, ast.Call)


def test_emit_decoder_source_roundtrip():
    key = bytes(range(32))
    stub = emit_decoder_source("d", key)
    assert "string seal" in stub
    seal = encrypt_string("payload", key)
    assert seal is not None
    ns = {}
    exec(compile(stub + "\nR = d(%r)\n" % seal, "<t>", "exec"), ns)
    assert ns["R"] == "payload"
