"""
bench_feature_effectiveness.py

Benchmarks for Feature Effectiveness Scoring (Feature 194).

Measures feature discovery, impact metrics, and docstring extraction performance.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.feature_effectiveness.scorer import FeatureEffectivenessScorer


def bench_full_feature_effectiveness() -> dict:
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    tests_dir = os.path.join(os.path.dirname(__file__))
    scorer = FeatureEffectivenessScorer(scripts_dir=scripts_dir, tests_dir=tests_dir)

    timings = []
    for _ in range(3):
        start = time.perf_counter()
        result = scorer.compute_feature_effectiveness()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    avg_time = round(sum(timings) / len(timings), 4)
    return {
        "avg_time_seconds": avg_time,
        "min_time_seconds": round(min(timings), 4),
        "max_time_seconds": round(max(timings), 4),
        "num_runs": len(timings),
        "total_features": result["total_features"],
        "overall_score": result["overall_score"],
        "low_impact_count": len(result["low_impact_features"]),
    }


def bench_empty_directory() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        scorer = FeatureEffectivenessScorer(scripts_dir=str(tmpdir))
        start = time.perf_counter()
        result = scorer.compute_feature_effectiveness()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "total_features": result["total_features"],
            "overall_score": result["overall_score"],
        }


def bench_large_feature_set() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            pkg_dir = os.path.join(tmpdir, f"feature_pkg_{i}")
            os.makedirs(pkg_dir, exist_ok=True)
            fpath = os.path.join(pkg_dir, f"feature_{i}.py")
            impact = i % 3 == 0
            before_after = i % 4 == 0
            resistance = i % 5 == 0
            with open(fpath, "w") as f:
                f.write(
                    f'"""Feature {i}: Detect security threats."""\n'
                    f"def run():\n"
                    f"    score = {i * 10}\n"
                    f"    assert score > 0\n"
                    f"    return score\n"
                )
            if impact:
                with open(fpath, "a") as f:
                    f.write(
                        "\n# Measure improvement\n"
                        "original = 30\n"
                        "obfuscated = 85\n"
                        "improvement = obfuscated - original\n"
                    )
            if before_after:
                with open(fpath, "a") as f:
                    f.write(
                        "\n# Before/after comparison\n"
                        "baseline_score = 20\n"
                        "protected_score = 90\n"
                    )
            if resistance:
                with open(fpath, "a") as f:
                    f.write(
                        "\n# resistance benchmark\n"
                        "bench_attack()\n"
                    )

        # Also create some test files
        tests_dir = os.path.join(tmpdir, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        for i in range(50):
            with open(os.path.join(tests_dir, f"test_feature_{i}.py"), "w") as f:
                f.write(
                    "import pytest\n"
                    "def test_basic():\n"
                    "    assert True\n"
                )
            with open(os.path.join(tests_dir, f"bench_feature_{i}.py"), "w") as f:
                f.write(
                    "def bench_run():\n"
                    "    return {'score': 85}\n"
                )

        scorer = FeatureEffectivenessScorer(
            scripts_dir=str(tmpdir), tests_dir=str(tests_dir),
        )
        start = time.perf_counter()
        result = scorer.compute_feature_effectiveness()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "total_features": result["total_features"],
            "overall_score": result["overall_score"],
            "low_impact_count": len(result["low_impact_features"]),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  FEATURE EFFECTIVENESS SCORER — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full effectiveness analysis:")
    ft = bench_full_feature_effectiveness()
    print(f"    avg: {ft['avg_time_seconds']:.4f}s, "
          f"features: {ft['total_features']}, "
          f"overall score: {ft['overall_score']}, "
          f"low-impact: {ft['low_impact_count']}")

    print("\n  [2] Empty directory:")
    em = bench_empty_directory()
    print(f"    scan: {em['scan_time_seconds']:.4f}s")

    print("\n  [3] Large feature set (100 features):")
    lg = bench_large_feature_set()
    print(f"    scan: {lg['scan_time_seconds']:.4f}s, "
          f"{lg['total_features']} features, "
          f"score: {lg['overall_score']}, "
          f"low-impact: {lg['low_impact_count']}")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
