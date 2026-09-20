import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestBytecodeCompiler:
    def test_compile_to_bytecode_raises_on_invalid_input(self):
        from vm.bytecode_compiler import compile_to_bytecode
        with pytest.raises((AttributeError, TypeError)):
            compile_to_bytecode(None)

    def test_compile_to_bytecode_returns_bytes(self, monkeypatch):
        from vm.bytecode_compiler import compile_to_bytecode
        from irgen.compile import IrFunction, IrType, IrValue, IrInstruction
        monkeypatch.setattr("vm.bytecode_compiler._phase2_enabled", lambda: True)
        IrValue.reset_counter()
        func = IrFunction("main", IrType.i32())
        entry = func.new_block("entry")
        a = IrValue(IrType.i32())
        b = IrValue(IrType.i32())
        entry.instructions.append(IrInstruction("add", IrType.i32(), [a, b]))
        entry.set_terminator("ret", operands=[IrType.i32(), IrValue.const_int(0)])
        bc = compile_to_bytecode(func)
        assert isinstance(bc, bytearray)
        assert len(bc) > 0

    def test_compile_to_bytecode_encrypt_decrypt(self):
        from vm.bytecode_compiler import encrypt_bytecode, decrypt_bytecode
        bc = bytearray([1, 2, 3, 4, 5])
        key = b"K" * 32
        encrypted = encrypt_bytecode(bc, key, block_size=16)
        assert encrypted != bytes(bc)
        decrypted = decrypt_bytecode(encrypted, key, block_size=16)
        assert bytes(decrypted) == bytes(bc)

    def test_encrypt_bytecode_empty(self):
        from vm.bytecode_compiler import encrypt_bytecode
        assert encrypt_bytecode(bytearray(), b"K" * 32) == b""

    def test_encrypt_bytecode_different_key(self):
        from vm.bytecode_compiler import encrypt_bytecode
        bc = bytearray([1, 2, 3])
        e1 = encrypt_bytecode(bc, b"A" * 32)
        e2 = encrypt_bytecode(bc, b"B" * 32)
        assert e1 != e2

    def test_rng_deterministic(self):
        from vm.bytecode_compiler import _Rng
        r1 = _Rng(b"seed")
        r2 = _Rng(b"seed")
        assert r1.next() == r2.next()

    def test_rng_different_seed(self):
        from vm.bytecode_compiler import _Rng
        r1 = _Rng(b"seed_a")
        r2 = _Rng(b"seed_b")
        assert r1.next() != r2.next()
