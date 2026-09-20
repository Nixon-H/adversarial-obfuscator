import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestJitTemplate:
    def test_xor_encrypt_roundtrip(self):
        from irgen.jit_template import _xor_encrypt
        data = b"Hello Nixon JIT!"
        key = b"key123"
        enc = _xor_encrypt(data, key)
        dec = _xor_encrypt(enc, key)
        assert dec == data

    def test_xor_encrypt_empty(self):
        from irgen.jit_template import _xor_encrypt
        assert _xor_encrypt(b"", b"key") == b""

    def test_xor_encrypt_different_key(self):
        from irgen.jit_template import _xor_encrypt
        data = b"test"
        c1 = _xor_encrypt(data, b"k1")
        c2 = _xor_encrypt(data, b"k2")
        assert c1 != c2

    def test_generate_template_disabled(self, monkeypatch, ir_func):
        from irgen.jit_template import generate_template
        monkeypatch.setattr("irgen.jit_template._phase2_enabled", lambda: False)
        with pytest.raises(RuntimeError, match="Advanced Protection must be enabled"):
            generate_template(ir_func, [], b"seed")

    def test_generate_template_enabled(self, monkeypatch, ir_func):
        from irgen.jit_template import generate_template
        monkeypatch.setattr("irgen.jit_template._phase2_enabled", lambda: True)
        entry = ir_func.blocks[0]
        from irgen.compile import IrValue, IrType
        entry.instructions.append(type('Inst', (), {'result': IrValue(IrType.i32()), 'operands': [], 'opcode': 'add'})())
        result = generate_template(ir_func, [], b"seed")
        assert "template_ir" in result
        assert "slot_map" in result

    def test_encrypt_template_empty(self):
        from irgen.jit_template import encrypt_template
        assert encrypt_template({}, b"key") == b""

    def test_encrypt_template_returns_bytes(self, monkeypatch, ir_func):
        from irgen.jit_template import generate_template, encrypt_template
        monkeypatch.setattr("irgen.jit_template._phase2_enabled", lambda: True)
        template = generate_template(ir_func, [], b"seed")
        blob = encrypt_template(template, b"a" * 32)
        if template:
            assert isinstance(blob, bytes)
            assert len(blob) > 0
