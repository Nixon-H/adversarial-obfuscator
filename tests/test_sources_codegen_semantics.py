"""Focused regressions for the obfuscator/core/sources.py A2 audit."""
import ast
import base64
import hashlib
import hmac
import random

import pytest

from obfuscator.core import sources


def _transformed_function(src, seed=1):
    random.seed(seed)
    tree = ast.parse(src)
    xform = sources.ExceptionFlowTransformer()
    tree = xform.visit(tree)
    assert xform.transform_count == 1
    ast.fix_missing_locations(tree)
    ns = {}
    exec(compile(tree, "<x>", "exec"), ns)
    return ns


def test_exception_flow_preserves_normal_block_order():
    src = """def f():\n    out.append(1)\n    out.append(2)\n    out.append(3)\n    out.append(4)\n    out.append(5)\n    out.append(6)\n"""
    ns = _transformed_function(src)
    out = []
    ns["out"] = out
    ns["f"]()
    assert out == [1, 2, 3, 4, 5, 6]


def test_exception_flow_does_not_capture_payload_exception():
    # Seed 3 maps the synthetic edge and the payload's own ZeroDivisionError
    # onto the same handler.  Before the control-token fix this re-entered
    # state 1 forever instead of propagating the payload exception.
    src = """def f():\n    a=1\n    b=2\n    c=1/0\n    d=3\n    e=4\n    f=5\n"""
    ns = _transformed_function(src, seed=3)
    with pytest.raises(ZeroDivisionError):
        ns["f"]()


def test_unknown_string_crypto_mode_does_not_downgrade_to_xor():
    with pytest.warns(RuntimeWarning, match="unknown string_crypto"):
        out, _ = sources.apply_ast_mutation(
            "x = 'abcdef'\n",
            {"fragment_strings": True, "string_crypto": "bogus"},
            strict=False,
        )
    assert out == "x = 'abcdef'\n"


def test_key_shard_template_uses_defined_secrets_alias():
    import secrets as secrets_mod
    import json as json_mod
    import urllib as urllib_mod
    code = sources.KEY_SHARD_SOURCE
    for key, val in (
        ("KEY_SHARD_CLS", "KeyShardTest"),
        ("METHOD_SPLIT_KEY", "split_key"),
        ("METHOD_RECONSTRUCT", "reconstruct"),
        ("METHOD_FETCH_SHARDS", "fetch_shards"),
        ("METHOD_DISTRIBUTE_SHARDS", "distribute_shards"),
    ):
        code = code.replace("{%s}" % key, val)
    code = code.replace("{TOR_CLIENT_CLS}()", "()")
    ns = {
        "_nixon_シークレット시크릿": secrets_mod,
        "_nixon_ウラルユーアールエル유알엘": urllib_mod,
        "_nixon_ジェイソン제이슨": json_mod,
    }
    exec(code, ns)
    inst = ns["KeyShardTest"](threshold=3, total_shards=5)
    key = bytes(range(32))
    assert inst.reconstruct(inst.split_key(key)[:3]) == key


def _decode_function():
    text = sources.LOADER_HEAD
    start = text.index("def {FUNC_STR_DEC}(idx):")
    end = text.index("_打印輸出", start)
    code = text[start:end].replace("{FUNC_STR_DEC}", "str_dec").replace(
        "{FUNC_TBL_INIT}", "tbl_init")
    return code


def test_fragmented_string_table_entries_decode_independently():
    key_a = b"a" * 32
    key_b = b"b" * 32

    def seal(part, key, idx):
        idx_key = hashlib.sha256(key + str(idx).encode()).digest()
        enc = bytes(c ^ idx_key[i % 32] for i, c in enumerate(part.encode()))
        tag = hmac.new(key, enc, hashlib.sha256).digest()[:8]
        return base64.b64encode(enc + tag).decode()

    plain = ("a123456789" * 8) + ("b123456789" * 8)
    half = len(plain) // 2
    table = {
        "router": {0: ("FRAG", "A", 0, "B", 0)},
        "tables": {"A": [seal(plain[:half], key_a, 0)],
                    "B": [seal(plain[half:], key_b, 0)]},
        "keys": {"A": base64.b64encode(key_a).decode(),
                 "B": base64.b64encode(key_b).decode()},
    }
    import hmac as hmac_mod
    ns = {
        "_nixon_ベース베이스": base64,
        "_nixon_ハッシュ해시": hashlib,
        "_nixon_エイチマック에이치": hmac_mod,
        "_nx_salt_m": 0,
        "tbl_init": lambda: table,
    }
    exec(_decode_function(), ns)
    assert ns["str_dec"](0) == plain


def test_hardware_binding_template_uses_real_subprocess_and_sys_path():
    assert "import subprocess as _nixon_サブプロセス서브" in sources.LOADER_BODY
    assert "import _nixon_サブプロセス서브\n" not in sources.LOADER_BODY
    assert '"/sys/class/dmi/id/product_uuid"' in sources.LOADER_BODY
    assert "/_nixon_システム시스템/class/dmi" not in sources.LOADER_BODY


def test_oram_bootstrap_probe_stays_inside_allocated_store():
    assert "_oram_.access('write', 0x1337 % _BATCH_SIZE_" in sources.LOADER_HEAD
    assert "_oram_.access('write', 0x1337, " not in sources.LOADER_HEAD


def test_cython_vm_hashes_integer_operand_not_stale_val():
    assert "if isinstance(v, int): v = str(v).encode()" in sources.CYTHON_VM_SOURCE
    assert "if isinstance(v, int): val = str(val).encode()" not in sources.CYTHON_VM_SOURCE


def test_canary_content_type_is_ascii_json_mime():
    assert "application/json" in sources.CANARY_SOURCE
    assert "application/_nixon_" not in sources.CANARY_SOURCE
