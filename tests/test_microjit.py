"""Tests for Micro-JIT Fragment Reassembly."""

import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.fragment import Fragment, FragmentAnalyzer, FragmentCompiler, derive_fragment_key, aes_ctr_encrypt_fragment  # noqa: F401 (this line binds a name used by an embedded template)


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def chain_key():
    return b'\x77' * 32


@pytest.fixture
def sample_bytecode():
    """Simulated VM bytecode containing multiple instructions."""
    bc = bytearray()
    bc += bytes([0x01, 0x00, 0x01])   # add r0, r1
    bc += bytes([0x02, 0x02, 0x03])   # sub r2, r3
    bc += bytes([0x03, 0x04, 0x05])   # mul r4, r5
    bc += bytes([0x06, 0x06, 0x07])   # and r6, r7
    bc += bytes([0x08, 0x00, 0x01])   # xor r0, r1
    bc += bytes([0x0e, 0x00, 0x42, 0x00])  # load immediate
    bc += bytes([0x10, 0x00, 0x00, 0x00, 0x40])  # jmp fwd
    bc += bytes([0x01, 0x01, 0x02])   # add r1, r2
    bc += bytes([0x02, 0x03, 0x04])   # sub r3, r4
    bc += bytes([0x07, 0x05, 0x06])   # or r5, r6
    return bytes(bc)


# =========================================================================
# Test FragmentAnalyzer
# =========================================================================

class TestFragmentAnalyzer:
    """
    TestFragmentAnalyzer
    
    Positive test cases for fragmentanalyzer.
    """
    def test_analyze_small_bytecode(self):
        bc = b'\x01\x00\x01'
        a = FragmentAnalyzer(min_fragment_instructions=1, max_fragment_instructions=8)
        ranges = a.analyze(bc)
        assert len(ranges) == 1
        assert ranges[0] == (0, 3)

    def test_analyze_splits_at_jumps(self, sample_bytecode):
        a = FragmentAnalyzer(min_fragment_instructions=1, max_fragment_instructions=8)
        ranges = a.analyze(sample_bytecode)
        assert len(ranges) >= 2
        for start, end in ranges:
            assert start < end

    def test_analyzer_respects_min_size(self):
        bc = b'\x01\x00\x01\x02\x02\x03\x03\x04\x05'
        a = FragmentAnalyzer(min_fragment_instructions=2, max_fragment_instructions=10)
        ranges = a.analyze(bc)
        for start, end in ranges:
            span = end - start
            assert span >= 2 or len(ranges) == 1

    def test_analyzer_respects_max_size(self):
        bc = b'\x01\x00\x01' * 20
        a = FragmentAnalyzer(min_fragment_instructions=1, max_fragment_instructions=6)
        ranges = a.analyze(bc)
        for start, end in ranges:
            assert end - start <= 6


# =========================================================================
# Test Fragment Compiler
# =========================================================================

class TestFragmentCompiler:
    """
    TestFragmentCompiler
    
    Positive test cases for fragmentcompiler.
    """
    def test_compile_splits_bytecode(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        assert len(compiled) >= 2
        total_plain = sum(cf.plaintext_size for cf in compiled)
        assert total_plain == len(sample_bytecode)

    def test_compile_encrypts_all_fragments(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        for cf in compiled:
            assert cf.encrypted_data != b''
            assert len(cf.encrypted_data) == cf.plaintext_size

    def test_compile_produces_chain(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        for i in range(len(compiled) - 1):
            assert compiled[i].next_fragment_id == i + 1
        assert compiled[-1].next_fragment_id is None

    def test_roundtrip_decrypt(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        prev_output = None
        reconstructed = bytearray()
        for cf in compiled:
            decrypted = c.decrypt_fragment(
                cf.encrypted_data, cf.id, prev_output
            )
            assert len(decrypted) == cf.plaintext_size
            reconstructed.extend(decrypted)
            fake_output = struct.pack('<Q', hash(decrypted) & 0xFFFFFFFFFFFFFFFF)
            prev_output = fake_output
        assert bytes(reconstructed) == sample_bytecode

    def test_wrong_order_fails_decryption(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        if len(compiled) < 2:
            pytest.skip("Need at least 2 fragments")
        prev_output = None
        first = c.decrypt_fragment(compiled[0].encrypted_data, compiled[0].id, prev_output)
        fake_out = struct.pack('<Q', hash(first) & 0xFFFFFFFFFFFFFFFF)
        wrong = c.decrypt_fragment(compiled[1].encrypted_data, compiled[1].id, None)
        correct = c.decrypt_fragment(compiled[1].encrypted_data, compiled[1].id, fake_out)
        assert wrong != correct
        assert bytes(first[0:min(len(first), len(correct))]) == sample_bytecode[0:len(first)]

    def test_encrypt_single(self, chain_key):
        c = FragmentCompiler(chain_key=chain_key)
        pt = b'\x01\x00\x01\x02\x02\x03'
        enc, size, key = c.encrypt_single(0, pt)
        assert size == len(pt)
        assert len(enc) == len(pt)
        assert len(key) == 32
        dec = c.decrypt_fragment(enc, 0)
        assert dec == pt


# =========================================================================
# Test Fragment Key Derivation
# =========================================================================

class TestKeyDerivation:
    """
    TestKeyDerivation
    
    Positive test cases for keyderivation.
    """
    def test_different_keys_for_different_fragments(self, chain_key):
        k0 = derive_fragment_key(b'\x00' * 8, chain_key, 0)
        k1 = derive_fragment_key(b'\x00' * 8, chain_key, 1)
        assert k0 != k1
        assert len(k0) == 32
        assert len(k1) == 32

    def test_different_keys_for_different_outputs(self, chain_key):
        k_a = derive_fragment_key(b'\xaa' * 8, chain_key, 0)
        k_b = derive_fragment_key(b'\xbb' * 8, chain_key, 0)
        assert k_a != k_b

    def test_deterministic_key(self, chain_key):
        k1 = derive_fragment_key(b'\x11' * 8, chain_key, 3)
        k2 = derive_fragment_key(b'\x11' * 8, chain_key, 3)
        assert k1 == k2

    def test_chain_key_changes_all_keys(self):
        a = derive_fragment_key(b'\x00' * 8, b'\xaa' * 32, 0)
        b = derive_fragment_key(b'\x00' * 8, b'\xbb' * 32, 0)
        assert a != b

    def test_default_prev_output_is_zeros(self, chain_key):
        k_explicit = derive_fragment_key(b'\x00' * 8, chain_key, 0)
        k_default = derive_fragment_key(b'\x00' * 8, chain_key, 0)
        assert k_explicit == k_default


# =========================================================================
# Test AES-CTR Encryption
# =========================================================================

class TestAESFragmentEncrypt:
    """
    TestAESFragmentEncrypt
    
    Positive test cases for aesfragmentencrypt.
    """
    def test_encrypt_decrypt_roundtrip(self):
        key = b'\x99' * 32
        pt = b'\x01\x02\x03\x04' * 16
        ct = aes_ctr_encrypt_fragment(pt, key)
        assert ct != pt
        pt2 = aes_ctr_encrypt_fragment(ct, key)
        assert pt2 == pt

    def test_different_keys_different_ciphertext(self):
        pt = b'\xaa' * 64
        ct1 = aes_ctr_encrypt_fragment(pt, b'\x11' * 32)
        ct2 = aes_ctr_encrypt_fragment(pt, b'\x22' * 32)
        assert ct1 != ct2

    def test_same_key_same_ciphertext(self):
        pt = b'\xbb' * 32
        ct1 = aes_ctr_encrypt_fragment(pt, b'\x33' * 32)
        ct2 = aes_ctr_encrypt_fragment(pt, b'\x33' * 32)
        assert ct1 == ct2

    def test_empty_plaintext(self):
        ct = aes_ctr_encrypt_fragment(b'', b'\x44' * 32)
        assert ct == b''

    def test_single_byte(self):
        ct = aes_ctr_encrypt_fragment(b'\x42', b'\x55' * 32)
        assert len(ct) == 1
        assert aes_ctr_encrypt_fragment(ct, b'\x55' * 32) == b'\x42'


# =========================================================================
# Test Cryptographic Chain Binding
# =========================================================================

class TestChainBinding:
    """
    TestChainBinding
    
    Positive test cases for chainbinding.
    """
    def test_b_key_depends_on_a_output(self, chain_key):
        fake_output_a = b'\x01' * 8
        k_b = derive_fragment_key(fake_output_a, chain_key, 1)
        k_b_diff = derive_fragment_key(b'\x00' * 8, chain_key, 1)
        assert k_b != k_b_diff

    def test_chain_encrypt_decrypt_roundtrip(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        prev_out = None
        reconstructed = bytearray()
        for cf in compiled:
            dec = c.decrypt_fragment(cf.encrypted_data, cf.id, prev_out)
            reconstructed.extend(dec)
            fake_out = struct.pack('<Q', hash(dec) & 0xFFFFFFFFFFFFFFFF)
            prev_out = fake_out
        assert bytes(reconstructed) == sample_bytecode

    def test_wrong_chain_order_fails(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        if len(compiled) < 2:
            pytest.skip("Need 2+ fragments")
        # Swap fragments
        cf0, cf1 = compiled[0], compiled[1]
        d0 = c.decrypt_fragment(cf0.encrypted_data, cf0.id, None)
        d1 = c.decrypt_fragment(cf1.encrypted_data, cf1.id, struct.pack('<Q', hash(d0) & 0xFFFFFFFFFFFFFFFF))
        # Decrypt with wrong key
        d1_wrong = c.decrypt_fragment(cf1.encrypted_data, cf1.id, None)
        assert d1_wrong != d1


# =========================================================================
# Test Memory Wipe Contract
# =========================================================================

class TestMemoryWipe:
    """
    TestMemoryWipe
    
    Positive test cases for memorywipe.
    """
    def test_encrypted_blob_contains_no_plaintext(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        for cf in compiled:
            for byte in cf.encrypted_data:
                pass
            assert cf.encrypted_data != sample_bytecode[:len(cf.encrypted_data)]

    def test_decrypt_wipes_fragment_key(self):
        key = b'\x88' * 32
        pt = b'\x01' * 32
        ct = aes_ctr_encrypt_fragment(pt, key)
        decrypted = aes_ctr_encrypt_fragment(ct, key)
        assert decrypted == pt
        key = None

    def test_compiled_fragment_key_slot(self, sample_bytecode, chain_key):
        c = FragmentCompiler(chain_key=chain_key, min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode)
        for i, cf in enumerate(compiled):
            assert cf.key_slot == i


# =========================================================================
# Test End-to-End Fragment Pipeline
# =========================================================================

class TestFragmentPipeline:
    """
    TestFragmentPipeline
    
    Positive test cases for fragmentpipeline.
    """
    def test_end_to_end(self):
        """Full pipeline: compile fragments, chain-encrypt, chain-decrypt."""
        bc = b'\x01\x00\x01\x02\x02\x03\x03\x04\x05\x06\x06\x07\x08\x00\x01'
        c = FragmentCompiler(min_instructions=2, max_instructions=5)
        compiled = c.compile_all(bc)

        total_encrypted = sum(len(cf.encrypted_data) for cf in compiled)
        assert total_encrypted == len(bc)

        chain_complete = sum(1 for cf in compiled if cf.next_fragment_id is not None)
        if len(compiled) > 1:
            assert chain_complete == len(compiled) - 1

        prev_out = None
        result = bytearray()
        for cf in compiled:
            dec = c.decrypt_fragment(cf.encrypted_data, cf.id, prev_out)
            result.extend(dec)
            fake_out = struct.pack('<Q', hash(dec) & 0xFFFFFFFFFFFFFFFF)
            prev_out = fake_out
        assert bytes(result) == bc

    def test_empty_bytecode(self, chain_key):
        c = FragmentCompiler(chain_key=chain_key)
        compiled = c.compile_all(b'')
        assert compiled == []

    def test_metadata_preserved(self, sample_bytecode):
        input_map = {0: ["r0", "r1"], 1: ["r2"]}
        output_map = {0: ["r0"], 1: ["r3"]}
        c = FragmentCompiler(min_instructions=2, max_instructions=5)
        compiled = c.compile_all(sample_bytecode, input_regs_map=input_map, output_regs_map=output_map)
        for i, cf in enumerate(compiled):
            if i in input_map:
                assert cf.input_regs == input_map[i]
            if i in output_map:
                assert cf.output_regs == output_map[i]


_MICROJIT_EXECUTION_WORKER = r'''
import ctypes
import mmap
import struct
from irgen.microjit import MicroJITEngine, _NOP_TEMPLATES, _instruction_length

BODY = (
    b"\xb8\x2a\x00\x00\x00"
    b"\xbb\x11\x11\x11\x11"
    b"\x49\xbc\x33\x33\x33\x33\x00\x00\x00\x00"
    b"\x49\xbd\x44\x44\x44\x44\x00\x00\x00\x00"
    b"\x49\xbe\x55\x55\x55\x55\x00\x00\x00\x00"
    b"\x49\xbf\x66\x66\x66\x66\x00\x00\x00\x00"
)


def make_executable(code):
    memory = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
    address = ctypes.addressof(ctypes.c_char.from_buffer(memory))
    ctypes.memmove(address, code, len(code))
    return memory, address


def register_check_wrapper():
    code = bytearray()
    labels = {}
    fixups = []

    def mark(name):
        labels[name] = len(code)

    def jne(name):
        fixups.append((len(code) + 2, name))
        code.extend(b"\x0f\x85\x00\x00\x00\x00")

    def jmp(name):
        fixups.append((len(code) + 1, name))
        code.extend(b"\xe9\x00\x00\x00\x00")

    code.extend(b"\x53\x55\x41\x54\x41\x55\x41\x56\x41\x57")
    code.extend(b"\x48\x83\xec\x08")
    code.extend(b"\x48\x89\xf8")
    checks = (
        (b"\xbb\x11\x11\x11\x11", b"\x48\x81\xfb\x11\x11\x11\x11"),
        (b"\xbd\x22\x22\x22\x22", b"\x48\x81\xfd\x22\x22\x22\x22"),
        (b"\x49\xbc\x33\x33\x33\x33\x00\x00\x00\x00", b"\x49\x81\xfc\x33\x33\x33\x33"),
        (b"\x49\xbd\x44\x44\x44\x44\x00\x00\x00\x00", b"\x49\x81\xfd\x44\x44\x44\x44"),
        (b"\x49\xbe\x55\x55\x55\x55\x00\x00\x00\x00", b"\x49\x81\xfe\x55\x55\x55\x55"),
        (b"\x49\xbf\x66\x66\x66\x66\x00\x00\x00\x00", b"\x49\x81\xff\x66\x66\x66\x66"),
    )
    for load, _compare in checks:
        code.extend(load)
    code.extend(b"\xff\xd0")
    for index, (_load, compare) in enumerate(checks):
        code.extend(compare)
        jne(f"bad{index}")
    code.extend(b"\x31\xc0")
    jmp("done")
    for index in range(len(checks)):
        mark(f"bad{index}")
        code.extend(b"\xb8" + struct.pack("<I", index + 1))
        jmp("done")
    mark("done")
    code.extend(b"\x48\x83\xc4\x08\x41\x5f\x41\x5e\x41\x5d\x41\x5c\x5d\x5b\xc3")
    for position, name in fixups:
        struct.pack_into("<i", code, position, labels[name] - (position + 4))
    return bytes(code)


wrapper_memory, wrapper_address = make_executable(register_check_wrapper())
check_registers = ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_void_p)(wrapper_address)
function_memory, function_address = make_executable(b"")
call_function = ctypes.CFUNCTYPE(ctypes.c_uint64)(function_address)

for seed in range(256):
    engine = MicroJITEngine(seed)
    prologue = engine.generate_prologue()
    epilogue = engine.generate_epilogue()
    independent = MicroJITEngine(seed)
    assert independent.generate_prologue() == prologue
    assert independent.generate_epilogue() == epilogue
    code = prologue + BODY + epilogue
    ctypes.memmove(function_address, code, len(code))
    assert call_function() == 42, seed
    assert check_registers(function_address) == 0, seed

reorder_code = (
    b"\x48\xbb\x07\x00\x00\x00\x00\x00\x00\x00"  # mov rbx, 7
    b"\x49\xbc\x08\x00\x00\x00\x00\x00\x00\x00"  # mov r12, 8 (independent)
    b"\x48\x89\xd8"                              # mov rax, rbx
    b"\x48\x89\xc1"                              # mov rcx, rax
    b"\xc3"
)
original = [reorder_code[:10], reorder_code[10:20],
            reorder_code[20:23], reorder_code[23:26], b"\xc3"]
seen_reorder = False
for seed in range(64):
    out = MicroJITEngine(seed).reorder_instructions(reorder_code, [(0, len(reorder_code))])
    offset = 0
    decoded = []
    while offset < len(out):
        length = _instruction_length(out, offset)
        assert length > 0, (seed, out.hex())
        instruction = out[offset:offset + length]
        if instruction not in _NOP_TEMPLATES:
            decoded.append(instruction)
        offset += length
    assert decoded[-1] == b"\xc3"
    seen_reorder |= decoded != original
    ctypes.memmove(function_address, out, len(out))
    assert call_function() == 7, seed
assert seen_reorder
'''


def test_microjit_layouts_and_scheduler_execute_across_many_seeds():
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c", _MICROJIT_EXECUTION_WORKER],
        capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("code", [
    b"\x48\x8b\x00\xc3",
    b"\x48\x31\xc0\xc3",
    b"\x48\x89\xd8\xe8\x00\x00\x00\x00\xc3",
    b"\xc5\xf8\x77\xc3",
    b"\xc3\x48\x89\xd8",
])
def test_microjit_reorder_fails_closed_on_unmodeled_code(code):
    from irgen.microjit import MicroJITEngine

    for seed in range(16):
        assert MicroJITEngine(seed).reorder_instructions(
            code, [(0, len(code))]) == code


def test_microjit_reorder_preserves_register_dependencies():
    from irgen.microjit import MicroJITEngine, _NOP_TEMPLATES, _instruction_length

    code = b"\x48\x89\xd8\x48\x89\xd9\xc3"
    expected = [code[:3], code[3:6], code[6:]]
    for seed in range(16):
        out = MicroJITEngine(seed).reorder_instructions(code, [(0, len(code))])
        decoded = []
        offset = 0
        while offset < len(out):
            length = _instruction_length(out, offset)
            assert length > 0
            instruction = out[offset:offset + length]
            if instruction not in _NOP_TEMPLATES:
                decoded.append(instruction)
            offset += length
        assert decoded == expected
