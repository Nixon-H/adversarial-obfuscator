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
        from vm.bytecode_compiler import encrypt_bytecode, decrypt_bytecode
        key = b"K" * 32
        encrypted = encrypt_bytecode(bytearray(), key)
        assert encrypted != b""  # even empty plaintext carries a version and MAC
        assert decrypt_bytecode(encrypted, key) == bytearray()

    def test_encrypt_bytecode_different_key(self):
        from vm.bytecode_compiler import encrypt_bytecode
        bc = bytearray([1, 2, 3])
        e1 = encrypt_bytecode(bc, b"A" * 32)
        e2 = encrypt_bytecode(bc, b"B" * 32)
        assert e1 != e2

    def test_encrypt_bytecode_known_answer(self, monkeypatch):
        from vm.bytecode_compiler import encrypt_bytecode
        monkeypatch.setattr("vm.bytecode_compiler.os.urandom", lambda size: bytes(range(size)))
        encrypted = encrypt_bytecode(bytearray(b"VM bytecode\x00\xff"), bytes(range(32)), block_size=8)
        assert encrypted.hex() == (
            "4e564d3101000000080001020304050607960924c7f7782b0ebf5f4e37f612a1d13b1e"
            "31fe312aa2362f7383f278b02001054ae77ebd7886c5b682fc6ca9"
        )

    def test_decrypt_rejects_wrong_key(self):
        from vm.bytecode_compiler import encrypt_bytecode, decrypt_bytecode, BytecodeAuthenticationError
        encrypted = encrypt_bytecode(bytearray(b"authenticated"), b"A" * 32)
        with pytest.raises(BytecodeAuthenticationError, match="wrong key or tampered"):
            decrypt_bytecode(encrypted, b"B" * 32)

    @pytest.mark.parametrize("offset", [0, 4, 5, 9, 17, -1])
    def test_decrypt_rejects_tampering(self, offset):
        from vm.bytecode_compiler import encrypt_bytecode, decrypt_bytecode, BytecodeAuthenticationError
        encrypted = bytearray(encrypt_bytecode(bytearray(b"authenticated"), b"A" * 32))
        encrypted[offset] ^= 1
        with pytest.raises(BytecodeAuthenticationError, match="wrong key or tampered"):
            decrypt_bytecode(bytes(encrypted), b"A" * 32)

    def test_decrypt_rejects_legacy_unauthenticated_container(self):
        from vm.bytecode_compiler import decrypt_bytecode, BytecodeAuthenticationError
        with pytest.raises(BytecodeAuthenticationError):
            decrypt_bytecode(b"legacy ciphertext", b"A" * 32)

    @pytest.mark.parametrize("opcode", ["call", "phi", "gep", "mystery"])
    def test_compile_rejects_unsupported_ops(self, monkeypatch, opcode):
        from irgen.compile import IrBlock, IrFunction, IrInstruction, IrType, IrValue
        from vm.bytecode_compiler import compile_to_bytecode
        monkeypatch.setattr("vm.bytecode_compiler._phase2_enabled", lambda: True)
        IrValue.reset_counter()
        func = IrFunction("unsupported", IrType.i32())
        block = IrBlock("entry")
        func.blocks.append(block)
        a = IrValue.const_int(1)
        b = IrValue.const_int(2)
        inst = IrInstruction(opcode, IrType.i32(), [a, b], func_name="callee" if opcode == "call" else None)
        block.instructions.append(inst)
        block.set_terminator("ret", operands=[IrType.i32(), inst.result])
        pattern = "calling convention" if opcode == "call" else opcode
        with pytest.raises(NotImplementedError, match=pattern):
            compile_to_bytecode(func, seed=b"test-seed")

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
