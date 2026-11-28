"""Regression tests for the seventh adversarial audit shard."""

import base64
import builtins
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_authenticode_signs_pe_whose_length_needs_alignment(tmp_path):
    pytest.importorskip("cryptography")
    from obfuscator import authenticode as ac
    if ac._openssl_path() is None:
        pytest.skip("OpenSSL CMS backend unavailable")

    import datetime
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "nx-a7")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256()))
    cert_path = tmp_path / "c.pem"
    key_path = tmp_path / "k.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))

    e_lfanew = 0x80
    head = bytearray(e_lfanew)
    head[:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, e_lfanew)
    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x8664)
    struct.pack_into("<H", coff, 2, 1)
    struct.pack_into("<H", coff, 16, 0xF0)
    opt = bytearray(0xF0)
    struct.pack_into("<H", opt, 0, 0x20B)
    struct.pack_into("<I", opt, 108, 16)
    unsigned = bytes(head) + b"PE\0\0" + bytes(coff) + bytes(opt) + b"\x00" * 512
    unsigned += b"X"  # 905 bytes: WIN_CERTIFICATE needs seven padding bytes.

    signed = ac.sign_pe(unsigned, str(cert_path), str(key_path))
    opt_abs = e_lfanew + 4 + 20
    cert_offset, cert_size = struct.unpack_from("<II", signed, opt_abs + 112 + 4 * 8)
    assert cert_offset % 8 == 0
    assert cert_offset > len(unsigned)
    assert struct.unpack_from("<HH", signed, cert_offset + 4) == (
        ac.WIN_CERT_REVISION_2_0, ac.WIN_CERT_TYPE_PKCS_SIGNED_DATA)
    assert cert_size > 8
    assert ac.pe_digest(unsigned) == ac.pe_digest(signed)


def test_loader_secure_write_unlinks_partial_secret_on_write_error(tmp_path, monkeypatch):
    import tempfile
    from obfuscator.secure_temp import emit_loader_snippet

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    ns = {}
    exec(compile(emit_loader_snippet(), "<st>", "exec"), ns)

    real_write = os.write
    calls = {"n": 0}

    def failing_write(fd, data):
        calls["n"] += 1
        if calls["n"] == 1:
            return real_write(fd, bytes(data)[:3])
        raise OSError("injected disk failure")

    monkeypatch.setattr(os, "write", failing_write)
    with pytest.raises(OSError, match="injected disk failure"):
        ns["_nx_secure_write"](b"secret-key-material", ".bin")
    assert list(tmp_path.iterdir()) == []


def test_secure_unlink_cannot_be_raced_into_wiping_symlink_target(tmp_path, monkeypatch):
    from obfuscator.secure_temp import secure_unlink

    victim = tmp_path / "victim.bin"
    victim.write_bytes(b"must-survive")
    candidate = tmp_path / "candidate.bin"
    candidate.write_bytes(b"wipe-me")
    real_open = builtins.open

    def racing_open(path, *args, **kwargs):
        if os.fspath(path) == os.fspath(candidate):
            candidate.unlink()
            os.symlink(victim, candidate)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", racing_open)
    secure_unlink(str(candidate), passes=1)
    assert victim.read_bytes() == b"must-survive"


def test_kill_ladder_direct_bytearray_holder_is_wiped():
    from obfuscator.kill_ladder import nx_kill

    buf = bytearray(b"key-material")
    actions = nx_kill("vm-detect", key_holders=buf, dry_run=True)
    assert buf == bytearray(len(buf))
    assert any(action.startswith("wipe:bytearray:") for action in actions)


def test_key_loader_rejects_mismatched_share_lengths():
    from obfuscator.key_emit import emit_key_loader

    with pytest.raises(ValueError, match="share length mismatch"):
        emit_key_loader(base64.b64encode(b"a").decode(),
                        base64.b64encode(b"bb").decode(), "build-id")


def test_get_hwid_rewrites_calls_but_not_string_or_comment_text():
    from obfuscator.macros import apply_macros

    src = (
        "text = 'literal GET_HWID() text'\n"
        "# comment GET_HWID() stays text\n"
        "value = GET_HWID()\n"
    )
    out = apply_macros(src, hwid="HW-1")
    assert "'literal GET_HWID() text'" in out
    assert "# comment GET_HWID() stays text" in out
    assert "value ='HW-1'" in out or "value = 'HW-1'" in out
    ns = {}
    exec(compile(out, "<macros>", "exec"), ns)
    assert ns["text"] == "literal GET_HWID() text"
    assert ns["value"] == "HW-1"


def test_lowering_does_not_rewrite_shadowed_builtin_calls():
    from obfuscator.lowering import lower_source

    module_shadow = "len = lambda x: 100\nout = len('abc')\n"
    lowered, count = lower_source(module_shadow, "container")
    assert "_nxk_len" not in lowered
    ns = {}
    exec(compile(lowered, "<low-shadow>", "exec"), ns)
    assert ns["out"] == 100

    param_shadow = "def f(len):\n    return len('abc')\n"
    lowered, _ = lower_source(param_shadow, "container")
    assert "_nxk_len" not in lowered

    plain, count = lower_source("out = len('abc')\n", "container")
    assert count == 1 and "_nxk_len" in plain


def test_adaptive_homoglyph_rename_does_not_collapse_existing_unicode_identifier(tmp_path):
    from obfuscator.adaptive_rewriter import AdaptiveRewriter

    class Profile:
        recommended_actions = ["strengthen_symbol_renaming"]

        def to_dict(self):
            return {}

    cyrillic_a = "\u0430"
    src = (
        f"{cyrillic_a} = 10\n"
        "def f(a):\n"
        f"    return a + {cyrillic_a}\n"
        "out = f(1)\n"
    )
    rewriter = AdaptiveRewriter(history_path=str(tmp_path / "history.json"), nonce=b"n")
    out = rewriter.rewrite(Profile(), src)
    compile(out, "<adaptive>", "exec")
    ns = {}
    exec(compile(out, "<adaptive>", "exec"), ns)
    assert ns["out"] == 11


def test_cross_module_collects_absolute_package_imports(tmp_path):
    from obfuscator.cross_module import sibling_imports

    (tmp_path / "_mod.py").write_text("def cmp_using():\n    return 1\n")
    (tmp_path / "__init__.py").write_text("from pkg._mod import cmp_using\n")
    assert "cmp_using" in sibling_imports(str(tmp_path / "_mod.py"))


def test_c_core_missing_symbol_table_fails_closed(monkeypatch):
    import subprocess
    from obfuscator.core.c_core_build import LOADER_SYMBOLS, missing_loader_symbols

    def no_nm(*args, **kwargs):
        raise FileNotFoundError("nm unavailable")

    monkeypatch.setattr(subprocess, "run", no_nm)
    assert missing_loader_symbols("anything.so") == list(LOADER_SYMBOLS)


def test_dep_guard_record_missing_file_fails_closed(tmp_path, monkeypatch):
    import base64
    import hashlib
    import importlib.metadata as md
    from obfuscator.dep_guard import verify_record

    present = tmp_path / "present.py"
    present.write_bytes(b"ok")
    digest = base64.urlsafe_b64encode(hashlib.sha256(b"ok").digest()).decode().rstrip("=")
    record = "present.py,sha256=%s,2\nmissing.py,sha256=%s,2\n" % (digest, digest)

    class FakeDist:
        def read_text(self, name):
            assert name == "RECORD"
            return record

        def locate_file(self, part):
            return str(tmp_path)

    monkeypatch.setattr(md, "distribution", lambda name: FakeDist())
    result = verify_record("fake")
    assert result["failed"] == 1
    assert "missing.py" in result["bad"]


def test_llm_resilient_does_not_rewrite_match_case_literals():
    import ast
    from obfuscator.llm_resilient import ContextCollapseObfuscator

    src = "def f(x):\n    match x:\n        case 'abcdef':\n            return 1\n        case _:\n            return 0\n"
    tree = ContextCollapseObfuscator(depth=1, dead_vars=1, seed=1).obfuscate(ast.parse(src))
    out = ast.unparse(tree)
    compile(out, "<llm-match>", "exec")
    ns = {}
    exec(compile(out, "<llm-match>", "exec"), ns)
    assert ns["f"]("abcdef") == 1
    assert ns["f"]("other") == 0


def test_function_intent_preserves_definition_order_for_defaults():
    import ast
    from obfuscator.function_intent import FunctionIntentObfuscator

    src = "x = 3\ndef compute(a=x):\n    return a\nout = compute()\n"
    tree = FunctionIntentObfuscator(seed=3).obfuscate_intent(ast.parse(src))
    out = ast.unparse(tree)
    ns = {}
    exec(compile(out, "<fi-order>", "exec"), ns)
    assert ns["out"] == 3


def test_rep_diversify_preserves_operand_values_of_and_or():
    from obfuscator.rep_diversify import diversify_source

    src = "def f(a, b):\n    return (a and b, a or b)\n"
    for seed in range(12):
        out, _ = diversify_source(src, seed=seed)
        ns = {}
        exec(compile(out, "<rep>", "exec"), ns)
        assert ns["f"](0, 2) == (0, 2)
        assert ns["f"](1, 2) == (2, 1)
