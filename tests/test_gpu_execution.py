import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGPUExecutor:
    """
    TestGPUExecutor
    
    Positive test cases for gpuexecutor.
    """
    def test_gpu_available_check(self):
        from scripts.gpu.gpu_execution import is_gpu_available
        result = is_gpu_available()
        assert isinstance(result, bool)

    def test_generate_kernel(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        kernel = ex.generate_kernel("add", num_threads=4)
        assert kernel["type"] == "add"
        assert kernel["num_threads"] == 4

    def test_transfer_to_gpu_and_back(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        data = b"\x01\x02\x03\x04"
        size = ex.transfer_to_gpu(data)
        assert size == len(data)
        result = ex.transfer_to_cpu(size)
        assert result[:size] == data

    def test_execute_add_kernel(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        ex.transfer_to_gpu(b"\x01\x00\x00\x00\x00\x00\x00\x00" * 4)
        kernel = ex.generate_kernel("add")
        kernel["args"] = [1]
        results = ex.execute_kernel(kernel)
        assert len(results) >= 1

    def test_execute_xor_kernel(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        ex.transfer_to_gpu(b"\xFF\x00\x00\x00\x00\x00\x00\x00" * 4)
        kernel = ex.generate_kernel("xor")
        kernel["args"] = [0xFF]
        results = ex.execute_kernel(kernel)
        assert len(results) >= 1

    def test_execute_mix_kernel(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        ex.transfer_to_gpu(b"\x01\x00\x00\x00\x00\x00\x00\x00" * 4)
        kernel = ex.generate_kernel("mix")
        kernel["args"] = [42]
        results = ex.execute_kernel(kernel)
        assert len(results) >= 1

    def test_execute_all(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        ex.transfer_to_gpu(b"\x01\x00\x00\x00\x00\x00\x00\x00" * 4)
        k1 = ex.generate_kernel("add")
        k1["args"] = [1]
        k2 = ex.generate_kernel("xor")
        k2["args"] = [0xFF]
        total = ex.execute_all()
        assert total >= 2

    def test_get_thread_result(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        ex.transfer_to_gpu(b"\x01\x00\x00\x00\x00\x00\x00\x00" * 4)
        kernel = ex.generate_kernel("add")
        kernel["args"] = [1]
        ex.execute_kernel(kernel)
        assert ex.get_thread_result(0) != 0
        assert ex.get_thread_result(999) == 0

    def test_gpu_process_fragment(self):
        from scripts.gpu.gpu_execution import gpu_process_fragment
        data = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        result = gpu_process_fragment(data, "mix")
        assert len(result) == len(data)
        assert result != data

    def test_get_trace(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        ex.transfer_to_gpu(b"\x01\x00\x00\x00\x00\x00\x00\x00")
        k = ex.generate_kernel("add")
        k["args"] = [1]
        ex.execute_kernel(k)
        trace = ex.get_trace()
        assert len(trace) >= 1
        assert trace[0]["type"] == "add"

    def test_unknown_kernel_type(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        with pytest.raises(ValueError):
            ex.generate_kernel("nonexistent")

    def test_compile_fragment(self):
        from scripts.gpu.gpu_execution import GPUExecutor
        ex = GPUExecutor(use_gpu=False)
        kernel = ex.compile_fragment(b"\x01\x02\x03\x04", "encrypt")
        assert kernel["type"] == "encrypt"
