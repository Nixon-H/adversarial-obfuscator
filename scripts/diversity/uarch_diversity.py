import ast
import hashlib
import math
import platform
from typing import Any, Dict, List, Optional


_EMULATOR_DETECTED = False
_CPU_VENDOR = "unknown"
_CPU_MODEL = "unknown"
_CPU_FLAGS: List[str] = []
_ARCH = platform.machine().lower()

try:
    with open("/proc/cpuinfo") as f:
        cpuinfo = f.read()
    if "GenuineIntel" in cpuinfo:
        _CPU_VENDOR = "intel"
    elif "AuthenticAMD" in cpuinfo:
        _CPU_VENDOR = "amd"
    if "hypervisor" in cpuinfo:
        _EMULATOR_DETECTED = True
    for line in cpuinfo.splitlines():
        if line.startswith("model name"):
            _CPU_MODEL = line.split(":", 1)[1].strip()
        if line.startswith("flags"):
            _CPU_FLAGS = line.split(":", 1)[1].strip().split()
except (FileNotFoundError, PermissionError):
    _CPU_VENDOR = platform.processor() or "unknown"


def _has_cpu_flag(flag: str) -> bool:
    return flag in _CPU_FLAGS


def detect_microarchitecture() -> Dict[str, Any]:
    return {
        "arch": _ARCH,
        "vendor": _CPU_VENDOR,
        "model": _CPU_MODEL,
        "emulator": _EMULATOR_DETECTED,
        "cache_line": 64,
        "has_rdtsc": _ARCH in ("x86_64", "amd64", "i386", "i686"),
        "flags": list(_CPU_FLAGS),
        "has_avx2": _has_cpu_flag("avx2"),
        "has_avx512": _has_cpu_flag("avx512f"),
        "has_sse4_1": _has_cpu_flag("sse4_1"),
        "has_aes": _has_cpu_flag("aes"),
        "has_sha": _has_cpu_flag("sha_ni"),
        "has_bmi2": _has_cpu_flag("bmi2"),
    }


def select_variant_for_uarch(
    variants: Dict[str, str], uarch_info: Optional[Dict[str, Any]] = None,
) -> str:
    if uarch_info is None:
        uarch_info = detect_microarchitecture()
    vendor = uarch_info.get("vendor", "unknown")
    if vendor == "intel":
        for key in ("intel", "x86", "cache", "default"):
            if key in variants:
                return variants[key]
    elif vendor == "amd":
        for key in ("amd", "x86", "cache", "default"):
            if key in variants:
                return variants[key]
    return variants.get("default", next(iter(variants.values()), ""))


class MicroarchitecturalDiversityGenerator:
    def __init__(self, seed: int = 0xCAFEBABE):
        self.seed = seed
        self.variant_counter = 0
        self.uarch_info = detect_microarchitecture()

    def _derive_variant_seed(self, variant_id: int) -> int:
        h = hashlib.sha256(f"{self.seed}:uarch:{variant_id}:{_CPU_VENDOR}".encode()).digest()
        return int.from_bytes(h[:8], "little")

    def generate_cache_pattern_variant(self, source: str) -> str:
        vid = self.variant_counter
        self.variant_counter += 1
        vseed = self._derive_variant_seed(vid)

        stride = (vseed % 7) + 1
        line_count = 64 + (vseed % 64)
        access_pattern = self._generate_cache_access(stride, line_count, vseed)

        wrapper_source = (
            f"def _uarch_cache_pattern_{vid}():\n"
            f"    _buf = bytearray({line_count * 64})\n"
            f"{access_pattern}\n"
            f"_uarch_cache_pattern_{vid}()\n"
        )

        tree = ast.parse(source)
        wrapper = ast.parse(wrapper_source, mode="exec")
        if isinstance(tree, ast.Module):
            tree.body.extend(wrapper.body)
        return ast.unparse(tree)

    def _generate_cache_access(self, stride: int, line_count: int, seed: int) -> str:
        lines: List[str] = []
        MASK = 0xFFFFFFFFFFFFFFFF
        rng_state = seed
        for i in range(line_count):
            idx = (i * stride) % line_count
            offset = idx * 64 + (rng_state % 60)
            lines.append(f"    _buf[{offset}] ^= {rng_state & 0xFF}")
            rng_state = (rng_state * 0x6C078965 + 1) & MASK
        return "\n".join(lines)

    def generate_branch_pattern_variant(self, source: str) -> str:
        vid = self.variant_counter
        self.variant_counter += 1
        vseed = self._derive_variant_seed(vid)
        pattern_len = 32 + (vseed % 64)

        branch_body: List[str] = []
        rng = vseed
        for i in range(pattern_len):
            taken = (rng >> 31) & 1
            var = f"_bp_{vid}_{i}"
            if taken:
                branch_body.append(f"{var} = ({rng} ^ {i}) & 1")
            else:
                branch_body.append(f"{var} = (({rng} * {i}) & 0xFF) >> 7")
            branch_body.append(
                f"if {var}:\n"
                f"    _bp_acc_{vid} = (_bp_acc_{vid} * 0x9E3779B9 + {i}) & 0xFFFFFFFFFFFFFFFF"
            )
            rng = (rng * 0x6C078965 + 1) & 0xFFFFFFFFFFFFFFFF

        wrapper_source = f"_bp_acc_{vid} = {vseed}\n" + "\n".join(branch_body)
        tree = ast.parse(source)
        wrapper = ast.parse(wrapper_source, mode="exec")
        if isinstance(tree, ast.Module):
            tree.body.extend(wrapper.body)
        return ast.unparse(tree)

    def generate_tlb_pressure_variant(self, source: str) -> str:
        vid = self.variant_counter
        self.variant_counter += 1
        vseed = self._derive_variant_seed(vid)
        num_pages = 4 + (vseed % 12)
        page_size = 4096

        lines: List[str] = [f"_tlb_buf_{vid} = bytearray({num_pages * page_size})"]
        for i in range(num_pages):
            access_count = 1 + (vseed >> (i % 8)) % 4
            for j in range(access_count):
                offset = i * page_size + (vseed + j * 64) % page_size
                lines.append(f"_tlb_buf_{vid}[{offset}] ^= {(vseed + i + j) & 0xFF}")

        wrapper_source = "\n".join(lines)
        tree = ast.parse(source)
        wrapper = ast.parse(wrapper_source, mode="exec")
        if isinstance(tree, ast.Module):
            tree.body.extend(wrapper.body)
        return ast.unparse(tree)

    def generate_simd_usage_variant(self, source: str) -> str:
        vid = self.variant_counter
        self.variant_counter += 1
        vseed = self._derive_variant_seed(vid)
        simd_width = 2 ** (1 + (vseed % 4))
        vec_len = simd_width * 4

        wrapper_source = (
            f"_simd_buf_{vid} = [0] * {vec_len}\n"
            f"for _si_{vid} in range({simd_width * 2}):\n"
            f"    for _sj_{vid} in range({simd_width}):\n"
            f"        idx = _si_{vid} % {vec_len}\n"
            f"        _simd_buf_{vid}[idx] ^= (_si_{vid} * {vseed}) & 0xFF\n"
        )

        tree = ast.parse(source)
        wrapper = ast.parse(wrapper_source, mode="exec")
        if isinstance(tree, ast.Module):
            tree.body.extend(wrapper.body)
        return ast.unparse(tree)

    def generate_variant(self, source: str, variant_type: str = "cache") -> str:
        generators = {
            "cache": self.generate_cache_pattern_variant,
            "branch": self.generate_branch_pattern_variant,
            "tlb": self.generate_tlb_pressure_variant,
            "simd": self.generate_simd_usage_variant,
        }
        gen = generators.get(variant_type)
        if gen is None:
            raise ValueError(f"Unknown variant type: {variant_type}")
        return gen(source)

    def generate_all_variant_types(self, source: str) -> Dict[str, str]:
        return {
            "cache": self.generate_cache_pattern_variant(source),
            "branch": self.generate_branch_pattern_variant(source),
            "tlb": self.generate_tlb_pressure_variant(source),
            "simd": self.generate_simd_usage_variant(source),
        }

    def _select_variant_strategy_for_cpu(self) -> str:
        vendor = self.uarch_info.get("vendor", "unknown")
        flags = self.uarch_info.get("flags", [])
        if vendor == "intel" and "avx512f" in flags:
            return "simd"
        elif vendor == "intel" and ("avx2" in flags or "sse4_1" in flags):
            return "cache"
        elif vendor == "amd" and "bmi2" in flags:
            return "branch"
        elif vendor == "amd":
            return "tlb"
        elif "aes" in flags:
            return "simd"
        return "cache"

    def generate_uarch_aware_variants(self, source: str) -> Dict[str, Any]:
        variants = self.generate_all_variant_types(source)
        selected_variant_type = self._select_variant_strategy_for_cpu()
        selected = variants.get(selected_variant_type, variants.get("cache", ""))
        return {"all": variants, "selected": selected,
                "selected_type": selected_variant_type,
                "uarch": self.uarch_info,
                "variant_counter": self.variant_counter}

    def uarch_fingerprint(self, source: str) -> Dict[str, float]:
        tree = ast.parse(source)
        stats = self._compute_ast_stats(tree)
        fingerprint: Dict[str, float] = {
            "cache_access_density": self._estimate_cache_density(source),
            "branch_density": stats["branch_density"],
            "tlb_pressure": self._estimate_tlb_pressure(source),
            "simd_usage": self._estimate_simd_usage(source),
            "loop_nesting": stats["max_nesting"],
            "instruction_count": stats["total_nodes"],
        }
        return fingerprint

    def _compute_ast_stats(self, tree: ast.AST) -> Dict[str, float]:
        counters: Dict[str, float] = {
            "branch_count": 0,
            "loop_count": 0,
            "total_nodes": 0,
            "max_nesting": 0,
            "branch_density": 0.0,
        }
        for node in ast.walk(tree):
            counters["total_nodes"] += 1
            if isinstance(node, (ast.If, ast.IfExp)):
                counters["branch_count"] += 1
            if isinstance(node, (ast.For, ast.While)):
                counters["loop_count"] += 1
        if counters["total_nodes"] > 0:
            counters["branch_density"] = counters["branch_count"] / counters["total_nodes"]
        return counters

    def _estimate_cache_density(self, source: str) -> float:
        count = source.count("[")
        assign = source.count("=")
        if assign == 0:
            return 0.0
        return min(1.0, count / assign)

    def _estimate_tlb_pressure(self, source: str) -> float:
        bytearray_count = source.count("bytearray")
        page_refs = source.count("page_size") + source.count("4096")
        return min(1.0, (bytearray_count + page_refs) / 10.0)

    def _estimate_simd_usage(self, source: str) -> float:
        simd_keywords = ["for", "range", "//", ">>", "<<"]
        count = sum(source.count(kw) for kw in simd_keywords)
        return min(1.0, count / 100.0)

    def uarch_aware_distance(self, variant_a: str, variant_b: str) -> float:
        fp_a = self.uarch_fingerprint(variant_a)
        fp_b = self.uarch_fingerprint(variant_b)
        common_keys = set(fp_a.keys()) & set(fp_b.keys())
        if not common_keys:
            return 0.0
        squared_diff = sum((fp_a[k] - fp_b[k]) ** 2 for k in common_keys)
        return min(1.0, math.sqrt(squared_diff / len(common_keys)))

    def source_similarity(self, source_a: str, source_b: str) -> float:
        tokens_a = set(source_a.split())
        tokens_b = set(source_b.split())
        if not tokens_a and not tokens_b:
            return 1.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union) if union else 0.0
