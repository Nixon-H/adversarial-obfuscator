import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from irgen.tee_partition import (generate_enclave_entry_stubs,
                                 generate_tee_config,
                                 identify_critical_functions,
                                 partition_program)

class TestTEE:

    def test_tee_partition_creates_correctly(self):
        from irgen.tee_partition import identify_critical_functions, partition_program
        from irgen.compile import IrModule, IrFunction, IrType

        mod = IrModule("test_tee")
        func1 = IrFunction("derive_key_material", IrType.i32())
        func1.new_block("entry")
        func2 = IrFunction("print_output", IrType.void())
        func2.new_block("entry")
        mod.functions.extend([func1, func2])

        critical = identify_critical_functions(mod, {"crown_jewel_patterns": ["key"]})
        assert "derive_key_material" in critical
        assert "print_output" not in critical

        host_mod, enclave_mod = partition_program(mod, critical)
        assert len(enclave_mod.functions) == 1
        assert enclave_mod.functions[0].name == "derive_key_material"
        assert len(host_mod.functions) == 1
        assert host_mod.functions[0].name == "print_output"

    def test_software_fallback_initializes(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "tee::tests::test_init_software_fallback", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"TEE init test failed:\n{result.stderr}"

    def test_seal_unseal_roundtrip(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "tee::tests::test_seal_unseal_roundtrip", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Seal/unseal test failed:\n{result.stderr}"

    def test_enclave_function_identification(self):
        from irgen.compile import IrModule, IrFunction, IrType

        mod = IrModule("test")
        funcs_def = [
            ("validate_license", IrType.i32()),
            ("compute_hash", IrType.i32()),
            ("log_message", IrType.void()),
        ]
        for name, rtype in funcs_def:
            f = IrFunction(name, rtype)
            f.new_block("entry")
            mod.functions.append(f)

        critical = identify_critical_functions(mod, {"crown_jewel_patterns": ["license"]})
        assert "validate_license" in critical
        assert "compute_hash" not in critical
        assert "log_message" not in critical

    def test_program_partitioning_splits_correctly(self):
        from irgen.compile import IrModule, IrFunction, IrType

        mod = IrModule("split_test")
        names = ["secure_boot", "read_config", "write_log", "derive_key", "attest"]
        for n in names:
            f = IrFunction(n, IrType.i32())
            f.new_block("entry")
            mod.functions.append(f)

        critical = identify_critical_functions(mod, {"crown_jewel_patterns": ["key", "boot", "attest"]})
        host_mod, enclave_mod = partition_program(mod, critical)

        for c in critical:
            assert any(f.name == c for f in enclave_mod.functions)
        for n in set(names) - set(critical):
            assert any(f.name == n for f in host_mod.functions)

    def test_entry_stub_generation(self):
        stubs = generate_enclave_entry_stubs(["derive_key", "attest"])
        assert "tee_enclave_derive_key" in stubs
        assert "tee_enclave_attest" in stubs
        assert "tee_enclave_call" in stubs
        assert "malloc" in stubs

    def test_config_generation(self):
        config = generate_tee_config(["derive_key", "attest"], tee_type="sgx")
        assert config["enabled"] is True
        assert config["tee_type"] == "sgx"
        assert config["target_functions"] == ["derive_key", "attest"]
        assert config["enclave"]["heap_size"] == 64 * 1024
        assert config["attestation"]["type"] == "epid"
        assert config["entry_stubs"]["derive_key"] == "tee_enclave_derive_key"

    def test_config_generation_disabled(self):
        config = generate_tee_config([], tee_type="sev")
        assert config["enabled"] is False
        assert config["tee_type"] == "sev"
        assert config["target_functions"] == []

    def test_rust_tee_all_tests_pass(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "tee::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some TEE tests failed:\n{result.stderr}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if "test tee::tests::" in line and "FAILED" in line:
                fail_count += 1
            elif "test tee::tests::" in line and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} TEE tests FAILED"
        assert pass_count >= 10, f"Expected at least 10 passing TEE tests, got {pass_count}"
