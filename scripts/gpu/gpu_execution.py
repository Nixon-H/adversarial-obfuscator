import hashlib
import struct
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

_HAVE_PYOPENCL = False
try:
    import pyopencl as cl
    _HAVE_PYOPENCL = True
except ImportError:
    pass

KERNEL_TEMPLATES = {
    "add": """
__kernel void add(__global ulong *data, ulong arg, int n) {
    int tid = get_global_id(0);
    if (tid < n) {
        data[tid] = data[tid] + arg;
    }
}
""",
    "xor": """
__kernel void xor_kernel(__global ulong *data, ulong arg, int n) {
    int tid = get_global_id(0);
    if (tid < n) {
        data[tid] = data[tid] ^ arg;
    }
}
""",
    "mix": """
__kernel void mix(__global ulong *data, ulong arg, int n) {
    int tid = get_global_id(0);
    if (tid < n) {
        ulong val = data[tid];
        val = val * 0x9E3779B97F4A7C15UL + arg + tid;
        data[tid] = val ^ (val >> 31);
    }
}
""",
    "encrypt": """
__kernel void encrypt(__global ulong *data, __global ulong *key, int n) {
    int tid = get_global_id(0);
    if (tid < n) {
        ulong k = key[tid % 4];
        data[tid] = data[tid] ^ k;
        data[tid] = data[tid] * 0xC6A4A7935BD1E995UL;
    }
}
""",
    "decrypt": """
__kernel void decrypt(__global ulong *data, __global ulong *key, int n) {
    int tid = get_global_id(0);
    if (tid < n) {
        ulong k = key[tid % 4];
        data[tid] = data[tid] * 0x9E3779B97F4A7C15UL;
        data[tid] = data[tid] ^ k;
    }
}
""",
}


def is_gpu_available() -> bool:
    if _HAVE_PYOPENCL:
        try:
            platforms = cl.get_platforms()
            for p in platforms:
                devices = p.get_devices()
                if devices:
                    return True
        except Exception:
            pass
    return False


def _simulate_kernel_add(data: List[int], arg: int) -> List[int]:
    return [(v + arg) & 0xFFFFFFFFFFFFFFFF for v in data]


def _simulate_kernel_xor(data: List[int], arg: int) -> List[int]:
    return [v ^ arg for v in data]


def _simulate_kernel_mix(data: List[int], arg: int) -> List[int]:
    result = []
    for tid, val in enumerate(data):
        val = (val * 0x9E3779B97F4A7C15 + arg + tid) & 0xFFFFFFFFFFFFFFFF
        val ^= val >> 31
        result.append(val)
    return result


def _simulate_kernel_encrypt(data: List[int], key: List[int]) -> List[int]:
    result = []
    for tid, val in enumerate(data):
        k = key[tid % 4]
        val ^= k
        val = (val * 0xC6A4A7935BD1E995) & 0xFFFFFFFFFFFFFFFF
        result.append(val)
    return result


def _simulate_kernel_decrypt(data: List[int], key: List[int]) -> List[int]:
    result = []
    for tid, val in enumerate(data):
        k = key[tid % 4]
        val = (val * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        val ^= k
        result.append(val)
    return result


SIMULATION_KERNELS = {
    "add": lambda data, args: _simulate_kernel_add(data, args[0]),
    "xor": lambda data, args: _simulate_kernel_xor(data, args[0]),
    "mix": lambda data, args: _simulate_kernel_mix(data, args[0]),
    "encrypt": lambda data, args: _simulate_kernel_encrypt(data, args),
    "decrypt": lambda data, args: _simulate_kernel_decrypt(data, args),
}


class GPUExecutor:
    MAX_THREADS = 64
    GLOBAL_MEM_SIZE = 65536
    LOCAL_MEM_SIZE = 16384

    def __init__(self, use_gpu: Optional[bool] = None):
        if use_gpu is None:
            self.use_gpu = is_gpu_available()
        else:
            self.use_gpu = use_gpu and is_gpu_available()
        self.global_mem = bytearray(self.GLOBAL_MEM_SIZE)
        self.local_mem = bytearray(self.LOCAL_MEM_SIZE)
        self.kernels: List[Dict[str, Any]] = []
        self.thread_results: List[int] = []

    def generate_kernel(self, kernel_type: str, num_threads: int = 4) -> Dict[str, Any]:
        source = KERNEL_TEMPLATES.get(kernel_type)
        if source is None:
            raise ValueError(f"Unknown kernel type: {kernel_type}")
        kernel = {
            "type": kernel_type,
            "source": source,
            "num_threads": num_threads,
            "args": [],
            "compiled": False,
        }
        self.kernels.append(kernel)
        return kernel

    def compile_fragment(self, fragment_data: bytes, kernel_type: str = "mix") -> Dict[str, Any]:
        kernel = self.generate_kernel(kernel_type)
        kernel["args"] = [len(fragment_data)]
        return kernel

    def transfer_to_gpu(self, data: bytes) -> int:
        size = min(len(data), self.GLOBAL_MEM_SIZE)
        self.global_mem[:size] = data[:size]
        return size

    def transfer_to_cpu(self, size: int) -> bytes:
        return bytes(self.global_mem[:size])

    def _execute_pyopencl(self, kernel: Dict[str, Any]) -> List[int]:
        if not _HAVE_PYOPENCL:
            raise RuntimeError("PyOpenCL not available")
        ktype = kernel["type"]
        source = KERNEL_TEMPLATES.get(ktype)
        if source is None:
            source = KERNEL_TEMPLATES["mix"]

        try:
            platform = cl.get_platforms()[0]
            device = platform.get_devices()[0]
            ctx = cl.Context([device])
            queue = cl.CommandQueue(ctx)
            mf = cl.mem_flags

            num_threads = min(kernel["num_threads"], self.MAX_THREADS)
            n = max(num_threads, 1)
            buf_size = n * 8

            h_data = (cl.cltypes.ulong * n)()
            for i in range(min(n, len(self.global_mem) // 8)):
                val = 0
                for j in range(8):
                    idx = i * 8 + j
                    if idx < len(self.global_mem):
                        val |= self.global_mem[idx] << (j * 8)
                h_data[i] = val

            d_data = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=h_data)
            prg = cl.Program(ctx, source).build()

            args_list = kernel["args"]
            if ktype in ("encrypt", "decrypt"):
                k = [0xA1B2C3D4E5F60708, 0x123456789ABCDEF0,
                     0xFEDCBA9876543210, 0x0F1E2D3C4B5A6978]
                h_key = (cl.cltypes.ulong * 4)(*k)
                d_key = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=h_key)
                kernel_exec = getattr(prg, ktype)
                kernel_exec(queue, (n,), None, d_data, d_key, n)
            elif ktype == "add":
                arg_val = args_list[0] if args_list else 0
                prg.add(queue, (n,), None, d_data, cl.cltypes.ulong(arg_val), n)
            elif ktype == "xor":
                arg_val = args_list[0] if args_list else 0
                prg.xor_kernel(queue, (n,), None, d_data, cl.cltypes.ulong(arg_val), n)
            else:
                arg_val = args_list[0] if args_list else 0
                getattr(prg, ktype)(queue, (n,), None, d_data, cl.cltypes.ulong(arg_val), n)

            cl.enqueue_copy(queue, h_data, d_data)

            results = [h_data[i] for i in range(n)]
            gm_view = memoryview(self.global_mem).cast("Q")
            for tid, val in enumerate(results):
                if tid < len(gm_view):
                    gm_view[tid] = val

            self.thread_results = results
            return results
        except Exception:
            return self._execute_software(kernel)

    def _execute_software(self, kernel: Dict[str, Any]) -> List[int]:
        num_threads = min(kernel["num_threads"], self.MAX_THREADS)
        args = kernel["args"]

        gm_view = memoryview(self.global_mem).cast("Q")
        data = [gm_view[i] for i in range(min(num_threads, len(gm_view)))]

        ktype = kernel["type"]
        if ktype == "encrypt" or ktype == "decrypt":
            k = [0xA1B2C3D4E5F60708, 0x123456789ABCDEF0,
                 0xFEDCBA9876543210, 0x0F1E2D3C4B5A6978]
            sim_args = k
        elif args:
            sim_args = args
        else:
            sim_args = [0]

        sim_fn = SIMULATION_KERNELS.get(ktype)
        if sim_fn is None:
            sim_fn = SIMULATION_KERNELS["mix"]

        results = sim_fn(data, sim_args)
        for tid, val in enumerate(results):
            if tid < len(gm_view):
                gm_view[tid] = val

        self.thread_results = results
        return results

    def execute_kernel(self, kernel: Dict[str, Any]) -> List[int]:
        if self.use_gpu and _HAVE_PYOPENCL:
            try:
                return self._execute_pyopencl(kernel)
            except Exception:
                pass
        return self._execute_software(kernel)

    def execute_parallel(self, kernel: Dict[str, Any]) -> List[int]:
        return self.execute_kernel(kernel)

    def execute_all(self) -> int:
        total = 0
        for kernel in self.kernels:
            results = self.execute_kernel(kernel)
            total += len(results)
        return total

    def get_thread_result(self, thread_id: int) -> int:
        if 0 <= thread_id < len(self.thread_results):
            return self.thread_results[thread_id]
        return 0

    def get_trace(self) -> List[Dict[str, Any]]:
        trace = []
        for kernel in self.kernels:
            trace.append({
                "type": kernel["type"],
                "num_threads": kernel["num_threads"],
                "results": self.thread_results[:kernel["num_threads"]] if self.thread_results else [],
            })
        return trace


def gpu_process_fragment(data: bytes, kernel_type: str = "mix") -> bytes:
    executor = GPUExecutor()
    kernel = executor.generate_kernel(kernel_type)
    kernel["args"] = [len(data)]
    executor.transfer_to_gpu(data)
    executor.execute_kernel(kernel)
    return executor.transfer_to_cpu(len(data))
