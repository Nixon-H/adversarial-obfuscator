"""
bench_silent_fallback.py

Benchmarks for Silent Fallback Detection (Feature 192).

Measures source scan performance for fallback pattern detection.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.silent_fallback.detector import SilentFallbackDetector


def _generate_large_source(num_lines: int) -> str:
    lines: list[str] = []
    for i in range(num_lines):
        if i % 20 == 0:
            lines.append(
                "def foo():\n"
                "    try:\n"
                "        secure_path()\n"
                "    except:\n"
                "        insecure_path()\n"
            )
        elif i % 30 == 0:
            lines.append(
                "def bar():\n"
                "    try:\n"
                "        safe_call()\n"
                "    except Exception:\n"
                "        log('logged')\n"
                "        fallback()\n"
            )
        else:
            lines.append(f"x_{i} = {i}\n")
    return "".join(lines)


def bench_full_source_scan() -> dict:
    results: dict = {}
    for size, label in [(1000, "1k"), (5000, "5k"), (10000, "10k")]:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = _generate_large_source(size)
            fpath = os.path.join(tmpdir, "bench_source.py")
            with open(fpath, "w") as f:
                f.write(src)
            detector = SilentFallbackDetector(str(tmpdir))
            start = time.perf_counter()
            result = detector.detect_silent_fallbacks()
            elapsed = time.perf_counter() - start
            results[f"{label}_lines"] = {
                "num_lines": size,
                "scan_time_seconds": round(elapsed, 4),
                "total_findings": result["total_findings"],
                "total_silent": result["total_silent"],
                "silent_fallback_score": result["silent_fallback_score"],
                "lines_per_second": round(size / elapsed, 2) if elapsed > 0 else 0,
            }
    return results


def bench_multi_file_scan() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            code = (
                f"def func_{i}():\n"
                f"    try:\n"
                f"        safe_{i}()\n"
                f"    except:\n"
                f"        unsafe_{i}()\n"
            )
            fpath = os.path.join(tmpdir, f"file_{i}.py")
            with open(fpath, "w") as f:
                f.write(code)
        detector = SilentFallbackDetector(str(tmpdir))
        start = time.perf_counter()
        result = detector.detect_silent_fallbacks()
        elapsed = time.perf_counter() - start
        return {
            "num_files": 100,
            "scan_time_seconds": round(elapsed, 4),
            "total_findings": result["total_findings"],
            "total_silent": result["total_silent"],
            "files_per_second": round(100 / elapsed, 2) if elapsed > 0 else 0,
        }


def bench_empty_directory() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        detector = SilentFallbackDetector(str(tmpdir))
        start = time.perf_counter()
        result = detector.detect_silent_fallbacks()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "total_findings": result["total_findings"],
        }


def bench_mixed_classifications() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(50):
            if i % 3 == 0:
                code = (
                    f"def silent_{i}():\n"
                    f"    try:\n        pass\n    except:\n        pass\n"
                )
            elif i % 3 == 1:
                code = (
                    f"def logged_{i}():\n"
                    f"    try:\n        pass\n"
                    f"    except:\n        print('log')\n        pass\n"
                )
            else:
                code = (
                    f"def reported_{i}():\n"
                    f"    try:\n        pass\n"
                    f"    except:\n        raise\n"
                )
            with open(os.path.join(tmpdir, f"mix_{i}.py"), "w") as f:
                f.write(code)
        detector = SilentFallbackDetector(str(tmpdir))
        start = time.perf_counter()
        result = detector.detect_silent_fallbacks()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "total_findings": result["total_findings"],
            "total_silent": result["total_silent"],
            "classification_stats": result["classification_stats"],
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  SILENT FALLBACK DETECTOR — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full source scan:")
    results = bench_full_source_scan()
    for label, data in results.items():
        print(f"    {label:>10s}: {data['scan_time_seconds']:.4f}s, "
              f"{data['total_findings']} findings, "
              f"{data['lines_per_second']:.0f} lines/s")

    print("\n  [2] Multi-file scan (100 files):")
    mf = bench_multi_file_scan()
    print(f"    scan: {mf['scan_time_seconds']:.4f}s, "
          f"{mf['total_findings']} findings, "
          f"{mf['files_per_second']:.0f} files/s")

    print("\n  [3] Empty directory scan:")
    em = bench_empty_directory()
    print(f"    scan: {em['scan_time_seconds']:.4f}s, "
          f"{em['total_findings']} findings")

    print("\n  [4] Mixed classifications:")
    mx = bench_mixed_classifications()
    print(f"    scan: {mx['scan_time_seconds']:.4f}s, "
          f"{mx['total_findings']} findings, "
          f"{mx['total_silent']} silent, "
          f"stats: {mx['classification_stats']}")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
