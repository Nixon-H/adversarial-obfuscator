"""Exec tests for provenance string-encode / library-wrap fixes (items 4-5)."""
import ast

from obfuscator.provenance import encode_sensitive_strings, wrap_library_calls


def _exec(tree):
    ns = {}
    exec(compile(tree, "<test>", "exec"), ns)
    return ns


def test_encode_sensitive_strings_roundtrip():
    src = 'HDR = "Content-Type: application/json"\nresult = HDR + "!"\n'
    tree = ast.parse(src, feature_version=(3, 10))
    out = encode_sensitive_strings(tree, b"seed-123")
    ns = _exec(ast.fix_missing_locations(out))
    assert ns["result"] == "Content-Type: application/json!"


def test_encode_multibyte_split_roundtrip():
    src = 'S = "Bearer caf\xe9 \u4e2d\u6587 base64"\nresult = S\n'
    tree = ast.parse(src, feature_version=(3, 10))
    out = encode_sensitive_strings(tree, b"seed-456")
    ns = _exec(ast.fix_missing_locations(out))
    assert ns["result"] == "Bearer café 中文 base64"


def test_wrap_library_calls_arity_and_names():
    src = (
        "def chacha20_poly1305_encrypt(key, nonce, data, tag=None):\n"
        "    return (key, nonce, data, tag)\n"
        "r1 = chacha20_poly1305_encrypt(b'k', b'n', b'd')\n"
        "r2 = chacha20_poly1305_encrypt(b'k', b'n', b'd', tag=b't')\n"
    )
    tree = ast.parse(src, feature_version=(3, 10))
    out = wrap_library_calls(tree, {"enc": "chacha20_poly1305_encrypt"})
    ns = _exec(ast.fix_missing_locations(out))
    assert ns["r1"] == (b"k", b"n", b"d", None)
    assert ns["r2"] == (b"k", b"n", b"d", b"t")
    # All call targets must resolve: no undefined adapter names remain.
    for node in ast.walk(out):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id in ns, node.func.id
