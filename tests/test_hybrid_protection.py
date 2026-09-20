import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestHybridProtector:
    """
    TestHybridProtector
    
    Positive test cases for hybridprotector.
    """
    def test_partition_basic(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        ops = [
            {"type": "crypto", "name": "encrypt"},
            {"type": "control_flow", "name": "branch"},
            {"type": "hash", "name": "hash_data"},
        ]
        cpu_ops, gpu_ops = hp.partition(ops)
        assert len(cpu_ops) == 1
        assert len(gpu_ops) == 2

    def test_cpu_obfuscation_pass(self):
        from scripts.gpu.hybrid_protection import cpu_obfuscation_pass
        data = b"hello world"
        result = cpu_obfuscation_pass(data, 0xDEAD)
        assert len(result) == len(data)
        assert result != data

    def test_gpu_parallel_transform(self):
        from scripts.gpu.hybrid_protection import gpu_parallel_transform
        data = [1, 2, 3, 4, 5]
        result = gpu_parallel_transform(data, 0xCAFE)
        assert len(result) == len(data)
        assert result != data

    def test_cpu_path_distinct_from_gpu_path(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=0x1234)
        data = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        cpu_r = hp.execute_cpu_path(data)
        gpu_r = hp.execute_gpu_path(data)
        assert cpu_r != gpu_r, "CPU and GPU paths must produce different intermediate state"

    def test_encrypt_decrypt_gpu_code(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        code = b"test code here"
        key = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        encrypted = hp.encrypt_gpu_code(code, key)
        assert encrypted != code
        decrypted = hp.decrypt_gpu_code(encrypted, key)
        assert decrypted == code

    def test_store_and_load_gpu_code(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        fid, encrypted = hp.store_gpu_code(0, b"my gpu code")
        assert fid == 0
        loaded = hp.load_gpu_code(0)
        assert loaded == b"my gpu code"

    def test_verify_gpu_memory_isolation(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        hp.gpu_executor.global_mem[:64] = b"\x01" * 64
        assert hp.verify_gpu_memory_isolation() is True

    def test_protection_plan(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        ops = [{"type": "crypto", "name": "aes"}]
        hp.partition(ops)
        plan = hp.generate_protection_plan()
        assert "gpu_crypto_ops" in plan
        assert "cpu_control_ops" in plan
        assert "gpu_available" in plan

    def test_cpu_trace_produced(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        ops = [{"type": "control_flow", "name": "branch_main"}, {"type": "crypto", "name": "encrypt"}]
        hp.partition(ops)
        hp.execute_cpu_control({"test": 1})
        trace = hp.get_cpu_trace()
        assert len(trace) > 0
        assert any("branch_main" in t for t in trace)

    def test_gpu_trace_produced(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        ops = [{"type": "encrypt", "name": "aes256"}]
        hp.partition(ops)
        hp.execute_gpu_crypto(b"\x01\x02\x03\x04", "encrypt")
        trace = hp.get_gpu_trace()
        assert len(trace) > 0
        assert any("encrypt" in t for t in trace)

    def test_hybrid_execute(self):
        from scripts.gpu.hybrid_protection import HybridProtector
        hp = HybridProtector(seed=42)
        ops = [{"type": "encrypt", "name": "aes256"}]
        hp.partition(ops)
        result = hp.hybrid_execute({"test": 1}, b"\x01\x02\x03\x04")
        assert len(result) == 4
        assert result != b"\x01\x02\x03\x04"
