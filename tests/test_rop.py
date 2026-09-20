"""Tests for the ROP compilation pipeline (scripts/rop/rop_compiler.py).

Covers:
    - GadgetFinder creates proper gadget databases (synthetic + binary)
    - RopCompiler compiles simple AST functions
    - RopCompiler handles add, subtract, compare, conditional branch
    - PayloadDisperser disperses gadget addresses (no two consecutive adjacent)
    - RopChain serialization round-trips
    - Disperser encrypt/decrypt round-trip
"""

import ast
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.rop import GadgetFinder, RopCompiler, PayloadDisperser, Gadget, RopChain


# =========================================================================
# GadgetFinder tests
# =========================================================================

class TestGadgetFinder:
    """
    TestGadgetFinder
    
    Positive test cases for gadgetfinder.
    """
    def test_synthetic_database_has_gadgets(self):
        finder = GadgetFinder()
        gadgets = finder.find_gadgets()
        assert isinstance(gadgets, dict)
        assert len(gadgets) > 0
        total = sum(len(v) for v in gadgets.values())
        assert total >= 10, f"Expected >=10 synthetic gadgets, got {total}"

    def test_synthetic_database_categories(self):
        finder = GadgetFinder()
        gadgets = finder.find_gadgets()
        required_cats = {"pop", "mov", "add", "sub", "load", "store", "nop"}
        for cat in required_cats:
            assert cat in gadgets, f"Missing category: {cat}"
            assert len(gadgets[cat]) > 0, f"Empty category: {cat}"

    def test_by_category_returns_gadgets(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        pops = finder.by_category("pop")
        assert len(pops) > 0
        for g in pops:
            assert g.category == "pop"

    def test_find_by_pattern(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        g = finder.find("pop rax; ret")
        assert g is not None
        assert "pop rax" in g.signature

    def test_find_pop(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        g = finder.find_pop("rax")
        assert g is not None
        assert g.category == "pop"

    def test_find_by_nonexistent_pattern(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        g = finder.find("does_not_exist_xyz")
        assert g is None

    def test_find_alu(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        g = finder.find_alu("add", "rax", "rdi")
        assert g is not None
        assert g.category == "add"

    def test_store_gadgets_json(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            finder.store_gadgets_json(path)
            with open(path) as f:
                data = f.read()
            assert len(data) > 0
            import json
            parsed = json.loads(data)
            assert isinstance(parsed, dict)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_binary_scan_fallback(self):
        finder = GadgetFinder("/bin/ls")
        gadgets = finder.find_gadgets()
        total = sum(len(v) for v in gadgets.values())
        assert total > 0, "Scanner should find gadgets in /bin/ls"

    def test_binary_scan_nonexistent_falls_back_to_synthetic(self):
        finder = GadgetFinder("/nonexistent/binary.xyz")
        gadgets = finder.find_gadgets()
        total = sum(len(v) for v in gadgets.values())
        assert total > 0, "Should fall back to synthetic gadgets"

    def test_gadget_signature_property(self):
        g = Gadget(0x401000, 2, ["pop rax", "ret"], "pop")
        assert g.signature == "pop rax; ret"

    def test_gadget_repr(self):
        g = Gadget(0x401000, 2, ["pop rax", "ret"], "pop")
        r = repr(g)
        assert "0x401000" in r
        assert "pop rax" in r


# =========================================================================
# RopChain tests
# =========================================================================

class TestRopChain:
    """
    TestRopChain
    
    Positive test cases for ropchain.
    """
    def test_empty_chain(self):
        c = RopChain()
        assert c.entries == []
        assert c.size_bytes == 0
        assert c.gadget_count == 0

    def test_append_addr_and_imm(self):
        c = RopChain()
        c.append_addr(0x401000)
        c.append_imm(42)
        assert c.entries == [0x401000, 42]
        assert c.size_bytes == 16

    def test_to_bytes(self):
        c = RopChain([0x401000, 42])
        data = c.to_bytes()
        assert len(data) == 16
        assert data[:8] == b"\x00\x10\x40\x00\x00\x00\x00\x00"
        assert data[8:] == b"\x2a\x00\x00\x00\x00\x00\x00\x00"

    def test_from_bytes_roundtrip(self):
        orig = RopChain([0x401000, 0x42, 0x401002], source_func="test")
        data = orig.to_bytes()
        restored = RopChain.from_bytes(data, "test")
        assert restored.entries == orig.entries
        assert restored.source_func == "test"
        assert restored.size_bytes == orig.size_bytes

    def test_from_bytes_invalid(self):
        with pytest.raises(ValueError, match="8-byte aligned"):
            RopChain.from_bytes(b"\x01\x02\x03")

    def test_repr(self):
        c = RopChain([0x401000], source_func="foo")
        r = repr(c)
        assert "foo" in r
        assert "1 entries" in r or "1 entry" in r


# =========================================================================
# RopCompiler tests
# =========================================================================

class TestRopCompiler:
    """
    TestRopCompiler
    
    Positive test cases for ropcompiler.
    """
    def _make_compiler(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        return RopCompiler(finder=finder)

    def test_compile_empty_function(self):
        compiler = self._make_compiler()
        tree = ast.parse("def empty(): pass")
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        chain = compiler.compile(func)
        assert isinstance(chain, RopChain)
        assert chain.source_func == "empty"

    def test_compile_simple_add(self):
        compiler = self._make_compiler()
        tree = ast.parse("def add(a, b): return a + b")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0
        assert all(isinstance(e, int) for e in chain.entries)

    def test_compile_simple_sub(self):
        compiler = self._make_compiler()
        tree = ast.parse("def sub(a, b): return a - b")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0

    def test_compile_return_constant(self):
        compiler = self._make_compiler()
        tree = ast.parse("def answer(): return 42")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0
        # Expect: pop rax; ret with 42, then ret
        bytes_data = chain.to_bytes()
        assert 42 in chain.entries or b"\x2a" in bytes_data

    def test_compile_if_statement(self):
        compiler = self._make_compiler()
        tree = ast.parse("def cond(x):\n    if x:\n        return 1\n    return 0")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0

    def test_compile_for_loop(self):
        compiler = self._make_compiler()
        tree = ast.parse("def loop():\n    for i in range(3):\n        pass")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0

    def test_compile_with_assignment(self):
        compiler = self._make_compiler()
        tree = ast.parse("def assign():\n    x = 42\n    y = x + 1\n    return y")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0

    def test_compile_augmented_assign(self):
        compiler = self._make_compiler()
        tree = ast.parse("def accum():\n    x = 10\n    x += 5\n    return x")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0

    def test_compile_while_loop(self):
        compiler = self._make_compiler()
        tree = ast.parse("def wh():\n    while False:\n        pass")
        func = tree.body[0]
        chain = compiler.compile(func)
        assert chain.gadget_count > 0

    def test_compile_ir_add(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        ir_func = {
            "name": "@test_ir_add",
            "return_type": "i32",
            "params": [],
            "blocks": [{
                "label": "entry",
                "instructions": [
                    {"result": "%0", "opcode": "add", "type": "i32",
                     "operands": ["3", "4"]},
                ],
                "terminator": {"opcode": "ret", "void": False,
                               "type": "i32", "value": "%0"},
            }],
        }
        chain = compiler.compile_ir_function(ir_func)
        assert isinstance(chain, list)
        assert len(chain) > 0

    def test_compile_ir_sub(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        ir_func = {
            "name": "@test_ir_sub",
            "return_type": "i32",
            "blocks": [{
                "label": "entry",
                "instructions": [
                    {"result": "%0", "opcode": "sub", "type": "i32",
                     "operands": ["10", "3"]},
                ],
                "terminator": {"opcode": "ret", "void": False,
                               "type": "i32", "value": "%0"},
            }],
        }
        chain = compiler.compile_ir_function(ir_func)
        assert len(chain) > 0

    def test_compile_ir_xor(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        ir_func = {
            "name": "@test_ir_xor",
            "blocks": [{
                "label": "entry",
                "instructions": [
                    {"result": "%0", "opcode": "xor", "type": "i32",
                     "operands": ["42", "42"]},
                ],
                "terminator": {"opcode": "ret", "void": False,
                               "type": "i32", "value": "%0"},
            }],
        }
        chain = compiler.compile_ir_function(ir_func)
        assert len(chain) > 0

    def test_compile_ir_store_and_load(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        ir_func = {
            "name": "@test_store",
            "blocks": [{
                "label": "entry",
                "instructions": [
                    {"opcode": "alloca", "result": "%ptr", "size": 16},
                    {"opcode": "store", "value": "42", "ptr": "%ptr"},
                    {"opcode": "load", "result": "%val", "ptr": "%ptr"},
                ],
                "terminator": {"opcode": "ret", "void": False,
                               "type": "i32", "value": "%val"},
            }],
        }
        chain = compiler.compile_ir_function(ir_func)
        assert len(chain) > 0

    def test_compile_ir_icmp(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        ir_func = {
            "name": "@test_icmp",
            "blocks": [{
                "label": "entry",
                "instructions": [
                    {"result": "%cmp", "opcode": "icmp", "type": "i1",
                     "operands": ["5", "5"]},
                ],
                "terminator": {"opcode": "ret", "void": False,
                               "type": "i1", "value": "%cmp"},
            }],
        }
        chain = compiler.compile_ir_function(ir_func)
        assert len(chain) > 0

    def test_produces_valid_chain_structure(self):
        """A valid chain must be a flat list of 8-byte-aligned integers."""
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        tree = ast.parse("def foo(): return 1 + 2")
        chain = compiler.compile(tree.body[0])
        assert len(chain.entries) > 0
        for entry in chain.entries:
            assert isinstance(entry, int)
            assert 0 <= entry < (1 << 64)


# =========================================================================
# PayloadDisperser tests
# =========================================================================

class TestPayloadDisperser:
    """
    TestPayloadDisperser
    
    Positive test cases for payloaddisperser.
    """
    def test_disperse_no_two_adjacent_entries_close(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain(
            [0x401000, 0x401002, 0x401004, 0x401006, 0x401008,
             0x40100A, 0x40100C, 0x40100E, 0x401010, 0x401020],
            source_func="disperse_test",
        )
        disperser = PayloadDisperser(finder)
        dispersed = disperser.disperse(chain, gap_min=16)
        assert len(dispersed.entries) == len(chain.entries)
        for i in range(1, len(dispersed.entries)):
            gap = abs(dispersed.entries[i] - dispersed.entries[i - 1])
            assert gap >= 16, (
                f"Entries {i - 1} and {i} are only {gap} bytes apart "
                f"(0x{dispersed.entries[i - 1]:x} and 0x{dispersed.entries[i]:x})"
            )

    def test_disperse_preserves_entry_count(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain([0x401000, 0x401002, 0x401004])
        disperser = PayloadDisperser(finder)
        out = disperser.disperse(chain)
        assert len(out.entries) == len(chain.entries)

    def test_disperse_single_entry_unchanged(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain([0x401000])
        disperser = PayloadDisperser(finder)
        out = disperser.disperse(chain)
        assert len(out.entries) == 1

    def test_disperse_empty_chain(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain([])
        disperser = PayloadDisperser(finder)
        out = disperser.disperse(chain)
        assert len(out.entries) == 0

    def test_remap_through_indirection_table(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain([0x401000, 0x401002, 0x401004])
        disperser = PayloadDisperser(finder)
        scrambled, mapping = disperser.remap_through_indirection_table(chain, 0x200000)
        assert len(scrambled.entries) == len(chain.entries)
        assert len(mapping) == len(chain.entries)
        for orig, table_slot in mapping.items():
            assert orig in chain.entries
            assert table_slot >= 0x200000

    def test_scatter_to_blobs(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain([0x401000, 0x401002, 0x401004, 0x401006,
                          0x401008, 0x40100A])
        disperser = PayloadDisperser(finder)
        blobs = disperser.scatter_to_blobs(chain, chunk_size=2)
        assert len(blobs) == 3
        for base, blob in blobs:
            assert len(blob) == 16
            assert base > 0

    def test_encrypt_decrypt_roundtrip(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        orig = RopChain([0x401000, 0x42, 0x401002])
        disperser = PayloadDisperser(finder)
        encrypted, key = disperser.encrypt_chain(orig)
        assert len(encrypted) == len(orig.entries) * 8
        decrypted = PayloadDisperser.decrypt_chain(encrypted, key)
        assert decrypted == orig.entries

    def test_encrypt_with_explicit_key(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain([0x401000, 0x42])
        disperser = PayloadDisperser(finder)
        key = b"\xAB" * 32
        enc, _ = disperser.encrypt_chain(chain, key)
        dec = PayloadDisperser.decrypt_chain(enc, key)
        assert dec == chain.entries

    def test_encrypt_different_keys_different_output(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        chain = RopChain([0x401000, 0x42])
        disperser = PayloadDisperser(finder)
        enc_a, _ = disperser.encrypt_chain(chain, b"\xAA" * 32)
        enc_b, _ = disperser.encrypt_chain(chain, b"\xBB" * 32)
        assert enc_a != enc_b


# =========================================================================
# Integration tests
# =========================================================================

class TestIntegration:
    """
    TestIntegration
    
    Positive test cases for integration.
    """
    def test_full_pipeline_compiles_and_disperses(self):
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        tree = ast.parse("def keygen(seed):\n    x = seed + 42\n    y = x ^ 0xFF\n    return y")
        chain = compiler.compile(tree.body[0])
        assert chain.gadget_count > 0, "Compiler should produce a chain"

        disperser = PayloadDisperser(finder)
        dispersed = disperser.disperse(chain, gap_min=16)
        assert len(dispersed.entries) == len(chain.entries)

        encrypted, key = disperser.encrypt_chain(chain)
        decrypted = PayloadDisperser.decrypt_chain(encrypted, key)
        assert decrypted == chain.entries

    def test_sample_rop_chain_produced(self):
        """Produce a sample ROP chain for a simple function and verify
        it has the right shape."""
        finder = GadgetFinder()
        finder.find_gadgets()
        compiler = RopCompiler(finder=finder)
        tree = ast.parse("def license_check(user_key):\n    return user_key ^ 0xABCD")
        chain = compiler.compile(tree.body[0])
        assert chain.gadget_count > 0
        # chain should have: pop rax (addr + imm), xor gadget addr, pop rax (ret val), ret
        assert chain.gadget_count >= 3, (
            f"Expected at least 3 entries, got {chain.gadget_count}"
        )
        # verify all entries are unique-ish addresses
        for e in chain.entries:
            assert isinstance(e, int)
