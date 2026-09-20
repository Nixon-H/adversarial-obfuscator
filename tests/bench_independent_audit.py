"""
bench_independent_audit.py

Benchmarks for Independent Audit (Feature 182).

Measures full audit time across reachability, proof, benchmark, and claim checks.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.independent_audit.auditor import IndependentAuditor, independent_audit


def bench_full_audit() -> dict:
    start = time.perf_counter()
    result = independent_audit()
    elapsed = time.perf_counter() - start
    total_checks = (
        len(result.get("reachability_audit", []))
        + len(result.get("proof_audit", []))
        + len(result.get("benchmark_audit", []))
        + len(result.get("evidence_audit", []))
        + len(result.get("claim_audit", []))
    )
    return {
        "time_seconds": round(elapsed, 4),
        "total_checks": total_checks,
        "checks_per_second": round(total_checks / elapsed, 2) if elapsed > 0 else 0,
    }


def bench_reachability_scan() -> dict:
    auditor = IndependentAuditor()
    start = time.perf_counter()
    findings = auditor.check_reachability()
    elapsed = time.perf_counter() - start
    return {
        "time_seconds": round(elapsed, 4),
        "phases_checked": len(findings),
        "phases_per_second": round(len(findings) / elapsed, 2) if elapsed > 0 else 0,
    }


def bench_claim_scan() -> dict:
    auditor = IndependentAuditor()
    start = time.perf_counter()
    findings = auditor.check_claims()
    elapsed = time.perf_counter() - start
    return {
        "time_seconds": round(elapsed, 4),
        "files_scanned": len(set(f.get("file", "") for f in findings)) if findings else 0,
        "claims_found": len(findings),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("  INDEPENDENT AUDITOR — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full audit:")
    fa = bench_full_audit()
    print(f"    {fa['time_seconds']:.4f}s, {fa['total_checks']} checks, {fa['checks_per_second']:.0f} checks/s")

    print("\n  [2] Reachability scan:")
    rs = bench_reachability_scan()
    print(f"    {rs['time_seconds']:.4f}s, {rs['phases_checked']} phases, {rs['phases_per_second']:.0f} phases/s")

    print("\n  [3] Claim scan:")
    cs = bench_claim_scan()
    print(f"    {cs['time_seconds']:.4f}s, {cs['files_scanned']} files, {cs['claims_found']} claims")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
