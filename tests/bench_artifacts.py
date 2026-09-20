"""
bench_artifacts.py

Benchmarks for Build Artifact Management.

Measures diagram, table, report generation, and bundling performance.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.artifacts.diagram_generator import (
    generate_architecture_diagram,
    generate_protection_flowchart,
    generate_attack_surface_diagram,
    generate_comparison_chart,
)
from scripts.artifacts.table_generator import (
    generate_benchmark_table,
    generate_comparison_table,
    generate_threat_model_table,
    generate_coverage_table,
)
from scripts.artifacts.report_generator import (
    generate_verification_report,
    generate_regression_report,
    generate_security_summary,
)
from scripts.artifacts.bundler import ReproducibilityBundle
from scripts.artifacts.builder import ArtifactBuilder


def _large_modules(n: int = 50) -> list[dict]:
    categories = ["obfuscation", "proof", "metric", "attack", "analysis", "hardware", "runtime"]
    return [
        {"name": f"stage_{i}", "label": f"Stage {i}", "category": categories[i % len(categories)]}
        for i in range(n)
    ]


def _large_coverage_map(n: int = 100) -> dict:
    protections = [f"prot_{i}" for i in range(20)]
    functions = {}
    for i in range(n):
        functions[f"func_{i}"] = {
            "protections": {p: i % (j + 1) == 0 for j, p in enumerate(protections)},
            "uncovered_paths": [] if i % 5 else ["Missing protection"],
        }
    per_prot = {p: {"functions_covered": n // 2, "total_functions": n, "coverage_ratio": 0.5} for p in protections}
    return {
        "functions": functions,
        "per_protection_stats": per_prot,
        "summary": {"total_functions": n},
    }


def _large_benchmark_data(n: int = 50) -> dict:
    return {
        f"bench_{i}": {"mean": 0.001 * i, "min": 0.0005 * i, "max": 0.002 * i, "std": 0.0001 * i, "ops": 1000 / max(i, 1)}
        for i in range(n)
    }


def _large_metrics(n: int = 30) -> dict:
    result = {}
    for i in range(n):
        result[f"metric_{i}"] = {"value": i / n, "status": "good" if i < n // 3 else ("warning" if i < 2 * n // 3 else "bad")}
    return result


def _knowledge_graph() -> dict:
    attacks = [{"name": f"Attack_{i}", "severity": "high" if i % 2 == 0 else "medium"} for i in range(10)]
    targets = [{"name": f"Target_{i}"} for i in range(10)]
    mitigations = [{"name": f"Mitigation_{i}"} for i in range(10)]
    atm = {str(i): [i % len(targets)] for i in range(len(attacks))}
    mm = {str(i): [i % len(mitigations)] for i in range(len(attacks))}
    threats = [
        {"name": f"Threat_{i}", "severity": "high", "mitigation": "CFG Flattening", "status": "mitigated"}
        for i in range(10)
    ]
    return {
        "attack_vectors": attacks,
        "targets": targets,
        "mitigations": mitigations,
        "attack_target_map": atm,
        "mitigation_map": mm,
        "before_metrics": {"entropy": 0.2, "complexity": 5},
        "after_metrics": {"entropy": 0.8, "complexity": 50},
        "threats": threats,
    }


def test_bench_full_artifact_generation(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "build")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(build_dir)

        obf_path = os.path.join(build_dir, "test_obfuscated.py")
        with open(obf_path, "w") as f:
            f.write("x = 1\n")

        builder = ArtifactBuilder(build_dir, output_dir)
        modules_list = _large_modules(20)
        coverage_map = _large_coverage_map(50)
        benchmark_data = _large_benchmark_data(20)
        metrics = _large_metrics(15)
        kg = _knowledge_graph()

        def run():
            builder.generate_all(modules_list, coverage_map, benchmark_data, metrics, kg)

        benchmark(run)
    finally:
        shutil.rmtree(tmpdir)


def test_bench_diagram_generation(benchmark):
    modules = _large_modules(50)
    tmpdir = tempfile.mkdtemp()
    try:
        out_path = os.path.join(tmpdir, "diagram.mmd")

        def run():
            generate_architecture_diagram(modules, out_path)

        benchmark(run)
    finally:
        shutil.rmtree(tmpdir)


def test_bench_table_generation(benchmark):
    data = _large_benchmark_data(100)
    tmpdir = tempfile.mkdtemp()
    try:
        out_path = os.path.join(tmpdir, "table.md")

        def run():
            generate_benchmark_table(data, out_path)

        benchmark(run)
    finally:
        shutil.rmtree(tmpdir)


def test_bench_bundle_creation(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        bundle_dir = os.path.join(tmpdir, "bundle_data")
        bundle = ReproducibilityBundle(bundle_dir)

        for i in range(50):
            fp = os.path.join(tmpdir, f"file_{i}.bin")
            with open(fp, "wb") as f:
                f.write(os.urandom(1024))
            bundle.add_file(fp, f"data/file_{i}.bin")

        bundle.add_metrics({"bench": 1.0})
        out_path = os.path.join(tmpdir, "test_bundle.tar.gz")

        def run():
            bundle.bundle(out_path)

        benchmark(run)
    finally:
        shutil.rmtree(tmpdir)


def test_bench_bundle_verification(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        bundle_dir = os.path.join(tmpdir, "bundle_data")
        bundle = ReproducibilityBundle(bundle_dir)

        for i in range(20):
            fp = os.path.join(tmpdir, f"vfile_{i}.bin")
            with open(fp, "wb") as f:
                f.write(os.urandom(512))
            bundle.add_file(fp, f"data/vfile_{i}.bin")

        bundle_path = bundle.bundle(os.path.join(tmpdir, "verify_bundle.tar.gz"))

        def run():
            ReproducibilityBundle.verify_bundle(bundle_path)

        benchmark(run)
    finally:
        shutil.rmtree(tmpdir)
