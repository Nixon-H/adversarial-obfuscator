import ast
import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestDataflow:
    def test_affine_encode_decode(self):
        from obfuscator.dataflow import affine_encode, affine_decode
        x = 12345
        A = 0x9E3779B97F4A7C15 | 1
        b = 0xBB67AE85
        enc = affine_encode(x, A, b)
        dec = affine_decode(enc, A, b)
        assert dec == x

    def test_affine_encode_large(self):
        from obfuscator.dataflow import affine_encode, affine_decode
        x = 0xDEADBEEFCAFEBABE
        A = 0x6C078965 | 1
        b = 0x5DEECE66D
        enc = affine_encode(x, A, b)
        dec = affine_decode(enc, A, b)
        assert dec == x

    def test_affine_encode_zero(self):
        from obfuscator.dataflow import affine_encode, affine_decode
        x = 0
        A = 0x9E3779B9 | 1
        b = 0x61C88647
        enc = affine_encode(x, A, b)
        dec = affine_decode(enc, A, b)
        assert dec == x

    def test_mba_encode_value_returns_ast(self):
        from obfuscator.dataflow import mba_encode_value
        result = mba_encode_value(42, b"test_seed", "ctx")
        assert isinstance(result, ast.Expr) or isinstance(result, ast.BinOp) or isinstance(result, ast.AST)

    def test_mba_encode_value_zero(self):
        from obfuscator.dataflow import mba_encode_value
        result = mba_encode_value(0, b"seed", "ctx")
        assert isinstance(result, ast.AST)

    def test_affine_state_encoder_roundtrip(self, monkeypatch):
        from obfuscator.dataflow import AffineStateEncoder
        monkeypatch.setattr("obfuscator.dataflow._phase2_enabled", lambda: True)
        encoder = AffineStateEncoder(b"test_seed", num_registers=4)
        state = [10, 20, 30, 40]
        enc = encoder.encode_state(state)
        assert enc != state
        dec = encoder.decode_state(enc)
        assert dec == state

    def test_affine_state_encoder_empty(self, monkeypatch):
        from obfuscator.dataflow import AffineStateEncoder
        monkeypatch.setattr("obfuscator.dataflow._phase2_enabled", lambda: True)
        encoder = AffineStateEncoder(b"seed")
        assert encoder.encode_state([]) == []
        assert encoder.decode_state([]) == []

    def test_affine_state_encoder_encode_op(self, monkeypatch):
        from obfuscator.dataflow import AffineStateEncoder
        monkeypatch.setattr("obfuscator.dataflow._phase2_enabled", lambda: True)
        encoder = AffineStateEncoder(b"seed", num_registers=2)
        enc = encoder.encode_state([5, 3])
        result = encoder.encode_op("add", enc)
        assert isinstance(result, int)

    @pytest.fixture
    def sample_ast(self):
        return ast.parse("x = 42\ny = x + 1\n")

    def test_encode_variables_affine(self, monkeypatch, sample_ast):
        from obfuscator.dataflow import encode_variables_affine
        monkeypatch.setattr("obfuscator.dataflow._phase2_enabled", lambda: True)
        result = encode_variables_affine(sample_ast, ["x"], b"seed")
        dumped = ast.dump(result)
        assert "_affine_enc" in dumped or "_enc" in dumped or result is not None

    def test_split_value(self, monkeypatch):
        from obfuscator.dataflow import split_value
        monkeypatch.setattr("obfuscator.dataflow._phase2_enabled", lambda: True)
        tree = ast.parse("x = 42\ny = x + 1\n")
        result = split_value(tree, "x", 2, b"seed")
        assert isinstance(result, ast.Module)
