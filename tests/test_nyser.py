"""Tests for obfuscator/nyser.py — NYSER1 code-object serializer."""
import dis
import io
import marshal
import re
import sys
import types

import pytest

from obfuscator.nyser import FORMAT_VERSION, MAGIC, dumps, loads, roundtrip_supported


def _dis_text(co):
    buf = io.StringIO()
    dis.dis(co, file=buf, show_caches=True)
    # strip addresses: "<code object fib at 0x..., ...>" -> "<code object fib>"
    import re
    return re.sub(r"(<code object [^ ]+) at 0x[0-9a-f]+", r"\1", buf.getvalue())


CASES = [
    "x = 1\ny = 2\nprint(x + y)\n",
    "def fib(n):\n    a, b = 0, 1\n    out = []\n    for _ in range(n):\n        out.append(a)\n        a, b = b, a + b\n    return out\n",
    "import os\ndef f(a, b=2, *args, c, d=4, **kw):\n    return [a, b, c]\nasync def g():\n    return 1\n",
    "x = 'hello world'\ny = 3.14 + 2j\nz = (1, 'a', None, True, ...)\n",
    "class C:\n    x = 1\n    def m(self):\n        return self.x\n",
    "try:\n    1/0\nexcept ZeroDivisionError as e:\n    y = str(e)\n",
]


@pytest.mark.skipif(not roundtrip_supported(), reason="NYSER1 unsupported on this Python")
def test_header_format():
    co = compile("x = 1\n", "<t>", "exec")
    blob = dumps(co)
    assert blob[:4] == MAGIC
    assert blob[4] == FORMAT_VERSION
    assert (blob[5], blob[6]) == (sys.version_info[0], sys.version_info[1])


@pytest.mark.skipif(not roundtrip_supported(), reason="NYSER1 unsupported on this Python")
@pytest.mark.parametrize("src", CASES)
def test_roundtrip_semantics(src):
    co = compile(src, "<test>", "exec")
    co2 = loads(dumps(co))
    assert _dis_text(co) == _dis_text(co2)
    ns1, ns2 = {}, {}
    exec(co, ns1)
    exec(co2, ns2)
    # compare user-visible bindings (drop dunders/modules; compare
    # classes/functions by disassembly, values otherwise)
    def _norm(v):
        if isinstance(v, type):
            out = {}
            for k, m in sorted(vars(v).items()):
                if isinstance(m, (types.FunctionType,)):
                    out[k] = _dis_text(m.__code__)
                else:
                    out[k] = repr(m)
            return out
        if isinstance(v, types.FunctionType):
            return _dis_text(v.__code__)
        return v
    filt = lambda ns: {k: _norm(v) for k, v in ns.items()
                       if not k.startswith("__") and not isinstance(v, types.ModuleType)}
    assert filt(ns1) == filt(ns2)


@pytest.mark.skipif(not roundtrip_supported(), reason="NYSER1 unsupported on this Python")
def test_no_marshal_on_load_path():
    """Hooking marshal.loads must not affect loads()."""
    orig = marshal.loads
    marshal.loads = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("hooked"))
    try:
        co2 = loads(dumps(compile("y = 41 + 1\n", "<h>", "exec")))
    finally:
        marshal.loads = orig
    ns = {}
    exec(co2, ns)
    assert ns["y"] == 42


@pytest.mark.skipif(not roundtrip_supported(), reason="NYSER1 unsupported on this Python")
def test_tamper_rejected():
    co = compile("x = 1\n", "<t>", "exec")
    blob = bytearray(dumps(co))
    blob[-5] ^= 0xFF
    with pytest.raises(ValueError):
        loads(bytes(blob))


@pytest.mark.skipif(not roundtrip_supported(), reason="NYSER1 unsupported on this Python")
def test_truncated_rejected():
    co = compile("x = 1\n", "<t>", "exec")
    blob = dumps(co)
    with pytest.raises(ValueError):
        loads(blob[:10])
    with pytest.raises(ValueError):
        loads(blob + b"\x00")


def test_bad_magic_rejected():
    with pytest.raises(ValueError):
        loads(b"XXXX\x01\x03\x0d\x00")


def test_version_mismatch_rejected():
    co = compile("x = 1\n", "<t>", "exec")
    blob = bytearray(dumps(co))
    blob[6] ^= 0x01  # flip minor version -> mismatch or unsupported
    with pytest.raises(ValueError):
        loads(bytes(blob))


def test_dumps_rejects_non_code():
    with pytest.raises(TypeError):
        dumps("not code")  # type: ignore[arg-type]


@pytest.mark.skipif(
    sys.version_info[:2] < (3, 14),
    reason="3.14 goldens need a 3.14 interpreter",
)
def test_314_goldens():
    """3.14 field audit: deferred annotations (PEP 649/749) and template
    strings (PEP 750) change consts but not the Code.replace field set
    NYSER1 serializes — round-trip must hold on 3.14 itself."""
    import dis
    cases = [
        "def f(x: int = 1) -> int:\n    return x\n",
        "t = 'hello'\ns = f'val={t}'\n",
        "def g(*args: int, **kw: str):\n    return args, kw\n",
    ]
    for src in cases:
        co = compile(src, "<t314>", "exec")
        blob = dumps(co)
        assert blob[5:7] == bytes((3, 14))
        co2 = loads(blob)
        b1, b2 = io.StringIO(), io.StringIO()
        dis.dis(co, file=b1, show_caches=True)
        dis.dis(co2, file=b2, show_caches=True)
        norm = lambda t: re.sub(r"(<code object [^ ]+) at 0x[0-9a-f]+", r"\1", t)
        assert norm(b1.getvalue()) == norm(b2.getvalue())
        ns1, ns2 = {}, {}
        exec(co, ns1)
        exec(co2, ns2)
        assert set(ns1) - set(ns2) == set()
        assert set(ns2) - set(ns1) == set()
