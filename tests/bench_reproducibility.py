"""
bench_reproducibility.py

Benchmarks for Reproducibility Scoring (Feature 178).

Measures environment snapshotting, scoring, and checker performance.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.reproducibility.scorer import compute_reproducibility
from scripts.reproducibility.environment import (
    snapshot_environment,
    compare_environments,
    environment_fingerprint,
)
from scripts.reproducibility.checker import (
    check_result_reproducibility,
    check_attack_reproducibility,
)


def _build_artifact_dir(path: str, num_files: int = 100) -> None:
    os.makedirs(path, exist_ok=True)
    for i in range(num_files):
        if i % 5 == 0:
            fpath = os.path.join(path, f"benchmark_{i}.json")
            with open(fpath, "w") as f:
                json.dump({"mean": i, "std": i * 0.1}, f)
        elif i % 5 == 1:
            fpath = os.path.join(path, f"attack_{i}.py")
            with open(fpath, "w") as f:
                f.write(f"import random; x = random.randint(0, {i})")
        elif i % 5 == 2:
            fpath = os.path.join(path, f"proof_{i}.json")
            with open(fpath, "w") as f:
                json.dump({"theorem": "equiv", "seed": i}, f)
        elif i % 5 == 3:
            fpath = os.path.join(path, f"test_{i}.txt")
            with open(fpath, "w") as f:
                f.write(f"PASS: {i} tests passed\nFAIL: 0 tests failed\n")
        else:
            fpath = os.path.join(path, f"source_{i}.py")
            with open(fpath, "w") as f:
                f.write(f"x = {i}\n")


def _build_large_source(path: str, num_lines: int = 10000) -> str:
    fpath = os.path.join(path, "large_source.py")
    with open(fpath, "w") as f:
        for i in range(num_lines):
            f.write(f"x_{i} = {i} * 2\n")
    return fpath


def test_bench_full_reproducibility_analysis(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        _build_artifact_dir(tmpdir, 50)
        result = benchmark(compute_reproducibility, tmpdir)
        assert result.overall_score >= 0.0
        assert len(result.results) == 50
    finally:
        shutil.rmtree(tmpdir)


def test_bench_environment_snapshot(benchmark):
    benchmark(snapshot_environment)


def test_bench_environment_fingerprint(benchmark):
    env = snapshot_environment()
    benchmark(environment_fingerprint, env)


def test_bench_compare_environments(benchmark):
    env_a = snapshot_environment()
    env_b = dict(env_a)
    env_b["hostname"] = "other-host"
    benchmark(compare_environments, env_a, env_b)


def test_bench_check_result_reproducibility(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        fpath = _build_large_source(tmpdir, 5000)
        result = benchmark(check_result_reproducibility, fpath)
        assert result.reproducibility_score >= 0.0
    finally:
        shutil.rmtree(tmpdir)


def test_bench_check_attack_reproducibility(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        fpath = os.path.join(tmpdir, "attack_report.json")
        data = {
            "attack_type": "angr",
            "seed": 42,
            "timestamp": "2026-06-14",
            "results": {"found": True, "confidence": 0.95},
            "parameters": {"timeout": 300, "depth": 100},
        }
        with open(fpath, "w") as f:
            json.dump(data, f)
        result = benchmark(check_attack_reproducibility, fpath)
        assert result.artifact_type == "attack"
    finally:
        shutil.rmtree(tmpdir)


def test_bench_large_artifact_dir(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        _build_artifact_dir(tmpdir, 200)
        result = benchmark(compute_reproducibility, tmpdir)
        assert len(result.results) == 200
    finally:
        shutil.rmtree(tmpdir)
