"""
bench_claim_auditor.py

Benchmarks for Claim Auditor (Feature 172).

Measures source scan time for claim pattern detection.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.claim_auditor.detector import ClaimDetector
from scripts.claim_auditor.auditor import audit_source


def _generate_large_source(num_lines: int) -> str:
    lines: list[str] = []
    claim_phrases = [
        "secure", "unbreakable", "tamper-proof", "AI resistant",
        "military grade", "unhackable", "bulletproof", "provably secure",
        "undetectable", "guaranteed protection", "invulnerable",
        "patented security", "certified secure", "absolute protection",
        "fully protected", "immune to analysis",
    ]
    for i in range(num_lines):
        if i % 30 == 0:
            phrase = claim_phrases[i % len(claim_phrases)]
            lines.append(f"# This code is {phrase} against all threats\n")
        elif i % 50 == 0:
            lines.append("# TODO: verify this works\n")
        else:
            lines.append(f"x_{i} = {i * 2}\n")
    return "".join(lines)


def bench_full_source_scan() -> dict:
    results: dict = {}

    for size, label in [(1000, "1k"), (5000, "5k"), (10000, "10k")]:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = _generate_large_source(size)
            fpath = os.path.join(tmpdir, "bench_source.py")
            with open(fpath, "w") as f:
                f.write(src)

            detector = ClaimDetector(str(tmpdir))
            start = time.perf_counter()
            result = detector.scan_all()
            elapsed = time.perf_counter() - start

            report = detector.generate_report()

            results[f"{label}_lines"] = {
                "num_lines": size,
                "scan_time_seconds": round(elapsed, 4),
                "claims_found": result.total_claims,
                "critical": result.critical_count,
                "high": result.high_count,
                "medium": result.medium_count,
                "low": result.low_count,
                "lines_per_second": round(size / elapsed, 2) if elapsed > 0 else 0,
                "report_length_chars": len(report),
            }

    return results


def bench_multi_file_scan() -> dict:
    results: dict = {}

    for num_files in [10, 50, 100]:
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(num_files):
                fpath = os.path.join(tmpdir, f"module_{i}.py")
                lines: list[str] = []
                for j in range(200):
                    if j % 25 == 0:
                        lines.append("# This is bulletproof secure code\n")
                    else:
                        lines.append(f"var_{i}_{j} = {j + i}\n")
                with open(fpath, "w") as f:
                    f.writelines(lines)

            start = time.perf_counter()
            result = audit_source(str(tmpdir))
            elapsed = time.perf_counter() - start

            results[f"{num_files}_files"] = {
                "num_files": num_files,
                "scan_time_seconds": round(elapsed, 4),
                "claims_found": result.total_claims,
                "supported": result.supported_count,
                "score": round(result.score, 1),
                "files_per_second": round(num_files / elapsed, 2) if elapsed > 0 else 0,
            }

    return results


def bench_evidence_checking() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(50):
            fpath = os.path.join(tmpdir, f"module_{i}.py")
            with open(fpath, "w") as f:
                f.write(f"# This is secure module {i}\nvar = {i}\n")
            tpath = os.path.join(tmpdir, f"test_module_{i}.py")
            with open(tpath, "w") as f:
                f.write(f"def test_module_{i}():\n    assert True\n")

        start = time.perf_counter()
        result = audit_source(str(tmpdir))
        elapsed = time.perf_counter() - start

        return {
            "50_files_with_evidence": {
                "scan_time_seconds": round(elapsed, 4),
                "claims_found": result.total_claims,
                "supported": result.supported_count,
                "score": round(result.score, 1),
            }
        }


def bench_all() -> dict:
    results: dict = {}
    results.update(bench_full_source_scan())
    results.update(bench_multi_file_scan())
    results.update(bench_evidence_checking())
    return results


if __name__ == "__main__":
    import json
    results = bench_all()
    print(json.dumps(results, indent=2))
