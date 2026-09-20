import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestROP:

    def test_rop_rust_compiles(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "rop::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"ROP tests failed:\n{result.stderr}"

    def test_rop_gadget_scan_finds_gadgets(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "rop::tests::test_scan_gadgets_finds_ret", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Gadget scan test failed:\n{result.stderr}"

    def test_rop_chain_encrypt_decrypt_roundtrip(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "rop::tests::test_encrypt_decrypt_roundtrip", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Encrypt/decrypt test failed:\n{result.stderr}"

    def test_rop_python_compiler_compile_simple_add(self):
        from irgen.rop_compiler import RopFunctionCompiler
        gadgets = {
            "0x401000": {"address": 0x401000, "signature": "pop rax; ret"},
            "0x401002": {"address": 0x401002, "signature": "pop rdi; ret"},
            "0x401004": {"address": 0x401004, "signature": "add rax, rdi; ret"},
        }
        compiler = RopFunctionCompiler(gadgets)
        ir_func = {
            "name": "@test_add",
            "return_type": "i32",
            "params": [],
            "blocks": [
                {
                    "label": "entry",
                    "instructions": [
                        {"result": "%0", "opcode": "add", "type": "i32",
                         "operands": ["3", "4"]},
                        {"result": "", "opcode": "ret", "void": False,
                         "type": "i32", "value": "%0"},
                    ],
                    "terminator": None,
                }
            ],
        }
        chain = compiler.compile_ir_function(ir_func)
        assert isinstance(chain, list)
        assert len(chain) > 0

    def test_rop_stack_pivot_stub_generation(self):
        from irgen.rop_compiler import RopFunctionCompiler
        compiler = RopFunctionCompiler({})
        chain = [0x401000, 0x42, 0x401002]
        stub = compiler.emit_stack_pivot(chain, 0x7ffff000)
        assert isinstance(stub, bytes)
        assert len(stub) > 0
        assert stub[:2] == bytes([0x48, 0xBC])

    def test_rop_python_encrypt_decrypt_roundtrip(self):
        from irgen.rop_compiler import RopFunctionCompiler
        compiler = RopFunctionCompiler({})
        chain = [0x401000, 0x42, 0x401002]
        key = [0xAB, 0xCD, 0xEF, 0x01, 0x23, 0x45, 0x67, 0x89,
               0xAB, 0xCD, 0xEF, 0x01, 0x23, 0x45, 0x67, 0x89,
               0xAB, 0xCD, 0xEF, 0x01, 0x23, 0x45, 0x67, 0x89,
               0xAB, 0xCD, 0xEF, 0x01, 0x23, 0x45, 0x67, 0x89]
        encrypted = compiler.generate_encrypted_rop_blob(chain, key)
        assert len(encrypted) == len(chain) * 8
        raw = b"".join(v.to_bytes(8, 'little') for v in chain)
        expected = bytes(raw[i] ^ key[i % 32] for i in range(len(raw)))
        assert encrypted == expected

    def test_rop_chain_builder_simple_chain(self):
        from irgen.rop_compiler import RopFunctionCompiler
        gadgets = {
            "0x401000": {"address": 0x401000, "signature": "xor rax, rax; ret"},
            "0x401002": {"address": 0x401002, "signature": "pop rax; ret"},
        }
        compiler = RopFunctionCompiler(gadgets)
        ir_func = {
            "name": "@test_xor",
            "return_type": "i32",
            "params": [],
            "blocks": [
                {
                    "label": "entry",
                    "instructions": [
                        {"result": "%0", "opcode": "xor", "type": "i32",
                         "operands": ["42", "42"]},
                        {"result": "", "opcode": "ret", "void": False,
                         "type": "i32", "value": "%0"},
                    ],
                    "terminator": None,
                }
            ],
        }
        chain = compiler.compile_ir_function(ir_func)
        assert isinstance(chain, list)
        assert len(chain) > 0

    def test_rop_generate_gadget_database_from_binary(self):
        from irgen.rop_compiler import generate_gadget_database
        import os
        test_binary = "/bin/ls"
        if os.path.exists(test_binary):
            db = generate_gadget_database(test_binary)
            assert isinstance(db, dict)

    def test_rop_all_rust_tests_pass(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "rop::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some rop tests failed:\n{result.stderr}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if "test rop::tests::" in line and "FAILED" in line:
                fail_count += 1
            elif "test rop::tests::" in line and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} rop tests FAILED"
        assert pass_count >= 5, f"Expected at least 5 passing tests, got {pass_count}"
