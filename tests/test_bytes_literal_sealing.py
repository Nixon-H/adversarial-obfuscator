"""Bytes literals must be sealed, not shipped in plaintext.

Benchmark 2026-11-17 (DeepSeek V4.1 Flash layer ablation): the string
obfuscator's ``visit_Constant`` matched only ``str``, so every ``bytes``
literal passed through untouched.  ``SIGNING_SALT = b"wh-salt-2026-11"``
survived the *full* stack — salts, HMAC keys and byte secrets are exactly
the constants worth hiding, and the DeepSeek run recovered the salt from
the fully-obfuscated arm because of it.

The fix seals bytes the same way as strings: hex-encode, seal, rebuild with
``bytes.fromhex(<decoder>(seal))`` at run time.
"""
import ast

from obfuscator.core.pipeline import ObfuscationTransformer

SECRET = b"wh-salt-2026-11"
SOURCE = (
    'import hashlib\n'
    'SALT = b"wh-salt-2026-11"\n'
    'API = "wt_live_8f3a91c2d7e04b56"\n'
    '\n'
    'def audit(p):\n'
    '    return hashlib.sha256(SALT + str(p).encode()).hexdigest()[:8]\n'
    '\n'
    'def main():\n'
    '    print("AUDIT", audit(1))\n'
    '\n'
    'if __name__ == "__main__":\n'
    '    main()\n'
)

_OFF = {k: False for k in (
    "cfg_flatten", "opaque_predicates", "bogus_exceptions", "mba_subs",
    "fragment_strings", "unicode_ids", "symbol_rename", "strip_meta",
    "split_vars", "unfold_constants", "enhanced_junk", "break_decompiler",
    "code_checksums", "obf_calls", "exception_flow", "residue_random",
    "decoy_apis", "attention_poison")}


def _transform(**on):
    opts = dict(_OFF)
    opts.update(on)
    out = ObfuscationTransformer(seed=4242).transform(SOURCE, options=opts)
    if isinstance(out, tuple):
        out = out[0]
    return out


def test_bytes_literal_is_not_plaintext_under_string_encryption():
    out = _transform(fragment_strings=True)
    assert SECRET.decode() not in out, (
        "the bytes salt shipped in plaintext despite string encryption")
    assert SECRET.hex() not in out, "the hex form leaked instead"


def test_bytes_literal_survives_the_full_stack_sealed():
    out = _transform(
        cfg_flatten=True, opaque_predicates=True, bogus_exceptions=True,
        mba_subs=True, fragment_strings=True, unicode_ids=True,
        symbol_rename=True, strip_meta=True, split_vars=True,
        unfold_constants=True, enhanced_junk=True, break_decompiler=True,
        code_checksums=True, obf_calls=True, exception_flow=True,
        residue_random=True)
    assert SECRET.decode() not in out, (
        "the bytes salt survived the full stack (the 2026-11-17 finding)")
    compile(out, "<full>", "exec")


def test_sealed_bytes_still_evaluate_to_the_original_value():
    """The transform must preserve the value, not merely hide it."""
    out = _transform(fragment_strings=True)
    ns = {"__name__": "sealed"}
    exec(compile(out, "<sealed>", "exec"), ns)
    assert ns["SALT"] == SECRET
    assert isinstance(ns["SALT"], bytes)


def test_sealed_bytes_module_runs():
    out = _transform(fragment_strings=True)
    assert "__main__" in out, "the main guard must survive"
    ns = {"__name__": "__main__"}
    exec(compile(out, "<run>", "exec"), ns)  # prints AUDIT <hash>


def test_bytes_are_sealed_by_the_real_decoder_shape():
    """The emitted call must rebuild bytes, not a str."""
    out = _transform(fragment_strings=True)
    tree = ast.parse(out)
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "fromhex"]
    assert calls, "no bytes.fromhex(...) rebuild found in the output"
