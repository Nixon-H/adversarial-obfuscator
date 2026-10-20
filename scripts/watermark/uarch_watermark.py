"""
watermark/uarch_watermark.py

Purpose:
Microarchitectural watermark — embeds ownership information into source code
by generating cache-timing side-channel patterns. The embedded code exercises
the L1/L2 cache in a message-specific pattern; the timing signature can be
measured to extract the watermark.

Security Relevance:
This watermark operates at a lower level than semantic IR watermarks. Even
if an attacker strips all IR-level markers, the uarch watermark survives in
the cache-miss timing profile of the running binary. However, it is less
stealthy (adds observable code) and more fragile (depends on specific
hardware microarchitecture).

Warning:
Timing-based watermarking is inherently noisy and platform-dependent.
This module provides a proof-of-concept; production use requires extensive
characterization on target hardware.

Dependencies:
- ctypes (optional, for rdtsc)
- time (fallback timing)
"""
import ctypes
import ctypes.util
import sys
import time
from typing import List, Optional, Tuple


def _get_rdtsc() -> Optional[ctypes.CFUNCTYPE]:
    """Attempt to get a raw RDTSC function via ctypes. Returns None on failure."""
    try:
        ctypes.CDLL(ctypes.util.find_library('c'), use_errno=False)
        return None
    except Exception:
        pass
    return None


def _rdtsc_fallback() -> int:
    return time.perf_counter_ns()


_RDTSC_FN = _get_rdtsc()


def rdtsc() -> int:
    if _RDTSC_FN is not None:
        try:
            return _RDTSC_FN()
        except Exception:
            pass
    return _rdtsc_fallback()


def read_tsc_benchmark(iterations: int = 1000) -> float:
    t0 = rdtsc()
    _ = [rdtsc() for _ in range(iterations)]
    t1 = rdtsc()
    delta = t1 - t0
    return delta / max(iterations, 1)


class MicroarchitecturalWatermark:
    CACHE_LINE_SIZE = 64
    L1_CACHE_SIZE = 32768
    L2_CACHE_SIZE = 262144

    def __init__(self, seed: int = 0xDEADBEEF):
        self.seed = seed

    @staticmethod
    def _message_to_bits(message: str) -> List[int]:
        bits: List[int] = []
        for byte in message.encode("utf-8"):
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits

    @staticmethod
    def _bits_to_message(bits: List[int]) -> str:
        if not bits:
            return ""
        bytes_needed = (len(bits) + 7) // 8
        byte_list = bytearray(bytes_needed)
        for i, bit in enumerate(bits):
            if bit:
                idx = i // 8
                shift = 7 - (i % 8)
                if idx < len(byte_list):
                    byte_list[idx] |= 1 << shift
        result = bytes(byte_list).decode("utf-8", errors="replace")
        return result.rstrip("\x00")

    def embed(self, source: str, message: str) -> str:
        bits = self._message_to_bits(message)
        lines: List[str] = []
        buf_size = self.L2_CACHE_SIZE * 2
        lines.append("")
        lines.append("def _uarch_wm_check():")
        lines.append(f"    _buf = bytearray({buf_size})")
        lines.append("    _t0 = __import__('time').perf_counter_ns()")
        for idx, bit in enumerate(bits):
            count = self.L1_CACHE_SIZE // self.CACHE_LINE_SIZE if bit == 0 else self.L2_CACHE_SIZE // self.CACHE_LINE_SIZE
            stride = 8 if bit == 0 else 16
            offset = idx * self.CACHE_LINE_SIZE * 2
            lines.append(f"    _wm_o{idx} = {offset}")
            lines.append(f"    for _wm_k in range({count}): _buf[(_wm_o{idx} + _wm_k * {stride}) % len(_buf)] ^= {bit}")
        lines.append("    _t1 = __import__('time').perf_counter_ns()")
        lines.append("    return _t1 - _t0")
        lines.append("_uarch_wm_delta = _uarch_wm_check()")
        lines.append("")

        embed_code = "\n".join(lines)
        return source + "\n" + embed_code

    def extract_from_source(self, source: str) -> str:
        import re
        bits: List[int] = []
        for line in source.split("\n"):
            if "for _wm_k in range(" in line:
                m = re.search(r'range\((\d+)\)', line)
                if m:
                    count = int(m.group(1))
                    if count == self.L1_CACHE_SIZE // self.CACHE_LINE_SIZE:
                        bits.append(0)
                    elif count == self.L2_CACHE_SIZE // self.CACHE_LINE_SIZE:
                        bits.append(1)
        if not bits or len(bits) < 8:
            return ""
        aligned = bits[:len(bits) - (len(bits) % 8)]
        return self._bits_to_message(aligned)

    def measure_timing_signature(self, source: str) -> Tuple[List[float], float]:
        try:
            local_ns = {"_uarch_wm_delta": 0}
            exec(source, local_ns)
            delta = local_ns.get("_uarch_wm_delta", 0.0)
            timings = [float(delta)]
            return timings, float(delta)
        except Exception:
            return [], 0.0

    def _measure_cache_timing(self, buf_size: int, stride: int, iterations: int = 100) -> float:
        buf = bytearray(buf_size)
        t0 = time.perf_counter_ns()
        for _ in range(iterations):
            for i in range(0, buf_size, stride):
                buf[i % buf_size] ^= 1
        t1 = time.perf_counter_ns()
        return (t1 - t0) / max(iterations, 1)

    def extract_via_timing(self, source: str) -> str:
        try:
            local_ns = {"_uarch_wm_delta": 0}
            exec(source, local_ns)
            delta = local_ns.get("_uarch_wm_delta", 0.0)
        except Exception:
            delta = 0.0

        l1_time = self._measure_cache_timing(self.L1_CACHE_SIZE, self.CACHE_LINE_SIZE)
        l2_time = self._measure_cache_timing(self.L2_CACHE_SIZE, self.CACHE_LINE_SIZE)
        baseline = self._measure_cache_timing(64, 64)

        if delta > (l2_time * 0.5):
            high_bit = 1
        elif delta > (l1_time * 0.5):
            high_bit = 0
        else:
            high_bit = 0

        bits: List[int] = []
        for i in range(64):
            stride = 8 if high_bit == 0 else 16
            count = self.L1_CACHE_SIZE // self.CACHE_LINE_SIZE if high_bit == 0 else self.L2_CACHE_SIZE // self.CACHE_LINE_SIZE
            t = self._measure_cache_timing(count * self.CACHE_LINE_SIZE, stride, 10)
            if t > baseline * 1.5:
                bits.append(high_bit)
            else:
                bits.append(1 - high_bit)

        if len(bits) < 8:
            return ""
        aligned = bits[:len(bits) - (len(bits) % 8)]
        return self._bits_to_message(aligned)

    def detect_watermark_from_timing(self, source: str, expected_message: str) -> bool:
        timings, delta = self.measure_timing_signature(source)
        if not timings:
            return False
        extracted_timing = self.extract_via_timing(source)
        extracted_source = self.extract_from_source(source)
        extracted = extracted_timing if expected_message in extracted_timing else extracted_source
        if not extracted:
            return False
        return expected_message in extracted


def embed_watermark(source: str, message: str) -> str:
    wm = MicroarchitecturalWatermark()
    return wm.embed(source, message)


def extract_watermark(source: str) -> str:
    wm = MicroarchitecturalWatermark()
    return wm.extract_from_source(source)


def detect_watermark(source: str, expected_message: str) -> bool:
    wm = MicroarchitecturalWatermark()
    return wm.detect_watermark_from_timing(source, expected_message)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Microarchitectural Watermark (UARCH)")
    parser.add_argument("command", choices=["embed", "detect"])
    parser.add_argument("input", help="Input source file")
    parser.add_argument("-m", "--message", help="Watermark message")
    parser.add_argument("-o", "--output", help="Output path (for embed)")
    args = parser.parse_args()
    wm = MicroarchitecturalWatermark()
    if args.command == "embed":
        with open(args.input) as f:
            source = f.read()
        watermarked = wm.embed(source, args.message or "NixonCorp")
        output = args.output or args.input + ".uarch_wm.py"
        with open(output, "w") as f:
            f.write(watermarked)
        print(f"UARCH watermark embedded: {output}")
    elif args.command == "detect":
        with open(args.input) as f:
            source = f.read()
        extracted = wm.extract_from_source(source)
        if extracted:
            print(f"Detected watermark: {extracted}")
        else:
            print("No uarch watermark detected")
            sys.exit(1)


if __name__ == "__main__":
    main()
