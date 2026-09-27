import ctypes
import hashlib
import multiprocessing
import os
from typing import Any, Dict, List, Optional, Tuple

from scripts.gpu.gpu_execution import GPUExecutor, is_gpu_available

DEFAULT_ENCRYPT_KEY = [0xA1B2C3D4E5F60708, 0x123456789ABCDEF0,
                       0xFEDCBA9876543210, 0x0F1E2D3C4B5A6978]

CPU_OPERATIONS = {"control_flow", "branch", "jmp", "cmp", "loop", "data", "memory", "store", "load"}
GPU_OPERATIONS = {"crypto", "encrypt", "decrypt", "key_derive", "hash", "sensitive", "parallel"}


def cpu_obfuscation_pass(data: bytes, seed: int) -> bytes:
    MASK = 0xFFFFFFFFFFFFFFFF
    state = seed
    result = bytearray(len(data))
    for i in range(len(data)):
        state = (state * 0x9E3779B97F4A7C15 + 1) & MASK
        result[i] = data[i] ^ (state & 0xFF)
    return bytes(result)


def gpu_parallel_transform(data: List[int], seed: int) -> List[int]:
    MASK = 0xFFFFFFFFFFFFFFFF
    return [
        ((v * 0xC6A4A7935BD1E995 + seed + tid) ^ (tid * 0x9E3779B97F4A7C15)) & MASK
        for tid, v in enumerate(data)
    ]


class HybridProtector:
    def __init__(self, seed: int = 0xDEADBEEF):
        self.seed = seed
        self.gpu_executor = GPUExecutor(use_gpu=None)
        self.cpu_control_flow: List[str] = []
        self.gpu_crypto_ops: List[Dict[str, Any]] = []
        self.gpu_code_store: Dict[int, bytes] = {}
        self.gpu_key_store: Dict[str, bytes] = {}
        self.gpu_memory_isolation = True
        self._cpu_trace: List[str] = []
        self._gpu_trace: List[str] = []

    def partition(self, operations: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        cpu_ops: List[Dict[str, Any]] = []
        gpu_ops: List[Dict[str, Any]] = []

        for op in operations:
            op_type = op.get("type", "")
            if op_type in GPU_OPERATIONS:
                gpu_ops.append(op)
            else:
                cpu_ops.append(op)

        self.cpu_control_flow = [o.get("name", str(o)) for o in cpu_ops]
        self.gpu_crypto_ops = gpu_ops
        return cpu_ops, gpu_ops

    def encrypt_gpu_code(self, code: bytes, key: bytes) -> bytes:
        encrypted = bytearray(len(code))
        for i in range(len(code)):
            k = key[i % len(key)]
            encrypted[i] = code[i] ^ k ^ 0xA5
        return bytes(encrypted)

    def decrypt_gpu_code(self, encrypted: bytes, key: bytes) -> bytes:
        decrypted = bytearray(len(encrypted))
        for i in range(len(encrypted)):
            k = key[i % len(key)]
            decrypted[i] = encrypted[i] ^ k ^ 0xA5
        return bytes(decrypted)

    def store_gpu_code(self, fragment_id: int, code: bytes) -> Tuple[int, bytes]:
        key = hashlib.sha256(f"{self.seed}:{fragment_id}".encode()).digest()[:16]
        encrypted = self.encrypt_gpu_code(code, key)
        self.gpu_code_store[fragment_id] = encrypted
        self.gpu_key_store[f"frag_{fragment_id}"] = key
        return fragment_id, encrypted

    def load_gpu_code(self, fragment_id: int) -> bytes:
        # Fail-closed: a missing fragment used to return b"" silently,
        # which callers could mistake for empty (but valid) GPU code.
        # Raise so a bad fragment id surfaces immediately; the
        # store→load round-trip path is unaffected.
        if fragment_id not in self.gpu_code_store:
            raise KeyError("unknown gpu fragment id: %r" % (fragment_id,))
        encrypted = self.gpu_code_store[fragment_id]
        key = self.gpu_key_store.get("frag_%s" % fragment_id)
        if not key:
            raise KeyError("missing gpu key for fragment id: %r" % (fragment_id,))
        return self.decrypt_gpu_code(encrypted, key)

    def execute_gpu_crypto(self, data: bytes, kernel_type: str = "encrypt") -> bytes:
        self._gpu_trace.append(f"gpu_exec::{kernel_type}(len={len(data)})")
        kernel = self.gpu_executor.generate_kernel(kernel_type)
        kernel["args"] = [len(data)]
        self.gpu_executor.transfer_to_gpu(data)
        self.gpu_executor.execute_kernel(kernel)
        return self.gpu_executor.transfer_to_cpu(len(data))

    def execute_cpu_control(self, control_data: Dict[str, Any]) -> int:
        MASK = 0xFFFFFFFFFFFFFFFF
        state = self.seed
        for op_name in self.cpu_control_flow:
            self._cpu_trace.append(f"cpu_exec::{op_name}")
            if "branch" in op_name or "jmp" in op_name:
                state = (state * 0x9E3779B97F4A7C15 + 1) & MASK
            elif "loop" in op_name:
                for _ in range(4):
                    state ^= state >> 17
                    state = (state * 0xC6A4A7935BD1E995) & MASK
            elif "cmp" in op_name:
                state ^= 0xDEADBEEF
        return state

    def hybrid_execute(self, control_input: Dict[str, Any], crypto_data: bytes) -> bytes:
        cpu_result = self.execute_cpu_control(control_input)
        crypto_key = hashlib.sha256(f"{cpu_result}:{self.seed}".encode()).digest()
        _ = self.encrypt_gpu_code(crypto_key[:16], crypto_key[16:32])
        for op in self.gpu_crypto_ops:
            op_type = op.get("type", "")
            if op_type in ("encrypt", "crypto"):
                crypto_data = self.execute_gpu_crypto(crypto_data, "encrypt")
            elif op_type == "decrypt":
                crypto_data = self.execute_gpu_crypto(crypto_data, "decrypt")
            elif op_type == "key_derive":
                crypto_data = self.execute_gpu_crypto(crypto_data, "mix")
        return crypto_data

    def execute_cpu_path(self, data: bytes) -> bytes:
        return cpu_obfuscation_pass(data, self.seed)

    def execute_gpu_path(self, data: bytes) -> bytes:
        original_use_gpu = self.gpu_executor.use_gpu
        self.gpu_executor.use_gpu = False
        ints = [int(b) for b in data]
        result = gpu_parallel_transform(ints, self.seed)
        self.gpu_executor.use_gpu = original_use_gpu
        return bytes(b & 0xFF for b in result)

    def verify_gpu_memory_isolation(self) -> bool:
        gpu_mem_before = bytes(self.gpu_executor.global_mem[:64])
        self.gpu_executor.global_mem[:64] = b"\x00" * 64
        gpu_mem_after = bytes(self.gpu_executor.global_mem[:64])
        return gpu_mem_before != gpu_mem_after

    def _mprotect_segment(self, addr: int, size: int, prot: int) -> bool:
        try:
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            page_size = 4096
            aligned_addr = addr & ~(page_size - 1)
            result = libc.mprotect(
                ctypes.c_void_p(aligned_addr), size, prot
            )
            return result == 0
        except Exception:
            return False

    def _cpu_worker(self, control_input: Dict[str, Any], seed: int, result_queue: multiprocessing.Queue) -> None:
        MASK = 0xFFFFFFFFFFFFFFFF
        state = seed
        for op_name in self.cpu_control_flow:
            if "branch" in op_name or "jmp" in op_name:
                state = (state * 0x9E3779B97F4A7C15 + 1) & MASK
            elif "loop" in op_name:
                for _ in range(4):
                    state ^= state >> 17
                    state = (state * 0xC6A4A7935BD1E995) & MASK
            elif "cmp" in op_name:
                state ^= 0xDEADBEEF
        result_queue.put(("cpu", state))

    def _gpu_worker(self, crypto_data: bytes, kernel_type: str, seed: int, result_queue: multiprocessing.Queue) -> None:
        try:
            executor = GPUExecutor(use_gpu=self.gpu_executor.use_gpu)
            kernel = executor.generate_kernel(kernel_type)
            kernel["args"] = [len(crypto_data)]
            executor.transfer_to_gpu(crypto_data)
            executor.execute_kernel(kernel)
            result = executor.transfer_to_cpu(len(crypto_data))
            result_queue.put(("gpu", result))
        except Exception as e:
            result_queue.put(("gpu_error", str(e)))

    def hybrid_execute_multiprocess(self, control_input: Dict[str, Any], crypto_data: bytes) -> Tuple[int, bytes]:
        result_queue = multiprocessing.Queue()
        cpu_proc = multiprocessing.Process(
            target=self._cpu_worker, args=(control_input, self.seed, result_queue)
        )
        gpu_proc = multiprocessing.Process(
            target=self._gpu_worker, args=(crypto_data, "encrypt", self.seed, result_queue)
        )
        cpu_proc.start()
        gpu_proc.start()
        cpu_proc.join(timeout=30)
        gpu_proc.join(timeout=30)

        cpu_result = self.seed
        gpu_result = crypto_data
        while not result_queue.empty():
            tag, val = result_queue.get()
            if tag == "cpu":
                cpu_result = val
            elif tag == "gpu":
                gpu_result = val
        return cpu_result, gpu_result

    def get_cpu_trace(self) -> List[str]:
        return list(self._cpu_trace)

    def get_gpu_trace(self) -> List[str]:
        return list(self._gpu_trace)

    def generate_protection_plan(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "gpu_crypto_ops": len(self.gpu_crypto_ops),
            "cpu_control_ops": len(self.cpu_control_flow),
            "gpu_code_fragments": len(self.gpu_code_store),
            "gpu_memory_isolation": self.gpu_memory_isolation,
            "gpu_available": is_gpu_available(),
            "encrypted_gpu_code": all(
                k in self.gpu_key_store for k in [f"frag_{f}" for f in self.gpu_code_store]
            ),
            "cpu_path_trace": self._cpu_trace,
            "gpu_path_trace": self._gpu_trace,
        }
