"""
test_artifacts.py

Tests for Build Artifact Management.

Test coverage:
- Positive tests verify artifact collection, hashing, storage, retrieval
- Negative tests verify missing artifacts, corrupt data, edge cases
"""
import hashlib
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
    generate_executive_summary,
)
from scripts.artifacts.bundler import ReproducibilityBundle
from scripts.artifacts.builder import ArtifactBuilder


# =========================================================================
# Diagram Tests
# =========================================================================

def test_diagram_generation():
    modules = [
        {"name": "parse", "label": "AST Parse", "category": "analysis"},
        {"name": "obfuscate", "label": "Obfuscation", "category": "obfuscation"},
        {"name": "prove", "label": "Proof Check", "category": "proof"},
        {"name": "metric", "label": "Metrics", "category": "metric"},
        {"name": "attack", "label": "Attack Sim", "category": "attack"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".mmd", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_architecture_diagram(modules, out)
        assert "graph TD" in result
        assert "AST Parse" in result
        assert "Obfuscation" in result
        assert "Proof Check" in result
        assert "Metrics" in result
        assert "Attack Sim" in result
        assert "Protected Output" in result
        assert os.path.isfile(out)
        with open(out) as f:
            content = f.read()
        assert content == result
    finally:
        os.unlink(out)


def test_protection_flowchart():
    coverage_map = {
        "functions": {
            "func_a": {"protections": {"VM": True, "ROP": True, "FHE": True, "Watermark": False}, "uncovered_paths": []},
            "func_b": {"protections": {"VM": True, "ROP": False, "FHE": False, "Watermark": False}, "uncovered_paths": ["No ROP"]},
            "func_c": {"protections": {"VM": False, "ROP": False, "FHE": False, "Watermark": False}, "uncovered_paths": ["All missing"]},
        },
        "per_protection_stats": {
            "VM": {"functions_covered": 2, "total_functions": 3, "coverage_ratio": 0.667},
            "ROP": {"functions_covered": 1, "total_functions": 3, "coverage_ratio": 0.333},
            "FHE": {"functions_covered": 1, "total_functions": 3, "coverage_ratio": 0.333},
        },
    }
    with tempfile.NamedTemporaryFile(suffix=".mmd", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_protection_flowchart(coverage_map, out)
        assert "graph LR" in result
        assert "func_a" in result
        assert "func_b" in result
        assert "func_c" in result
        assert "Protection_Heatmap" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_attack_surface_diagram():
    knowledge_graph = {
        "attack_vectors": [
            {"name": "Symbolic Execution", "severity": "high"},
            {"name": "LLM Analysis", "severity": "medium"},
        ],
        "targets": [
            {"name": "Control Flow"},
            {"name": "Encryption Keys"},
        ],
        "mitigations": [
            {"name": "Opaque Predicates"},
            {"name": "VM Compilation"},
        ],
        "attack_target_map": {"0": [0, 1], "1": [0]},
        "mitigation_map": {"0": [0], "1": [1]},
    }
    with tempfile.NamedTemporaryFile(suffix=".mmd", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_attack_surface_diagram(knowledge_graph, out)
        assert "graph TB" in result
        assert "Symbolic Execution" in result
        assert "LLM Analysis" in result
        assert "Control Flow" in result
        assert "Encryption Keys" in result
        assert "Opaque Predicates" in result
        assert "VM Compilation" in result
        assert "attacks" in result
        assert "mitigates" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_comparison_chart():
    before = {"entropy": 0.2, "cyclomatic_complexity": 5, "instruction_count": 100}
    after = {"entropy": 0.8, "cyclomatic_complexity": 50, "instruction_count": 500}
    with tempfile.NamedTemporaryFile(suffix=".mmd", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_comparison_chart(before, after, out)
        assert "gantt" in result
        assert "Before/After Protection Comparison" in result
        assert "entropy" in result
        assert "cyclomatic_complexity" in result
        assert "instruction_count" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


# =========================================================================
# Table Tests
# =========================================================================

def test_benchmark_table():
    benchmark_data = {
        "ast_parse": {"mean": 0.0012, "min": 0.0010, "max": 0.0015, "std": 0.0001, "ops": 833.0},
        "ir_compile": {"mean": 0.0050, "min": 0.0045, "max": 0.0060, "std": 0.0003, "ops": 200.0},
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_benchmark_table(benchmark_data, out)
        assert "Benchmark" in result
        assert "Mean" in result
        assert "OPS" in result
        assert "ast_parse" in result
        assert "ir_compile" in result
        assert "833" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_comparison_table():
    baseline = {"entropy": 0.2, "execution_time": 100.0, "binary_size": 1024}
    current = {"entropy": 0.8, "execution_time": 90.0, "binary_size": 2048}
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_comparison_table(baseline, current, out)
        assert "Metric" in result
        assert "Baseline" in result
        assert "Current" in result
        assert "Delta" in result
        assert "Pass?" in result
        assert "entropy" in result
        assert "execution_time" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_coverage_table():
    coverage_map = {
        "functions": {
            "func_a": {"protections": {"VM": True, "ROP": False, "FHE": True}},
            "func_b": {"protections": {"VM": False, "ROP": True, "FHE": False}},
        },
        "per_protection_stats": {
            "VM": {"functions_covered": 1, "total_functions": 2, "coverage_ratio": 0.5},
            "ROP": {"functions_covered": 1, "total_functions": 2, "coverage_ratio": 0.5},
            "FHE": {"functions_covered": 1, "total_functions": 2, "coverage_ratio": 0.5},
        },
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_coverage_table(coverage_map, out)
        assert "Function" in result
        assert "Covered" in result
        assert "func_a" in result
        assert "✓" in result
        assert "—" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_threat_model_table():
    threats = [
        {"name": "Reverse Engineering", "severity": "high", "mitigation": "CFG Flattening", "status": "mitigated"},
        {"name": "Static Analysis", "severity": "medium", "mitigation": "Opaque Predicates", "status": "mitigated"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_threat_model_table(threats, out)
        assert "Threat" in result
        assert "Severity" in result
        assert "Mitigation" in result
        assert "Status" in result
        assert "Reverse Engineering" in result
        assert "Static Analysis" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


# =========================================================================
# Report Tests
# =========================================================================

def test_verification_report():
    vdata = {
        "test_results": {"total": 10, "passed": 9, "failed": 1, "skipped": 0, "failed_tests": [{"name": "test_fail", "error": "assert failed"}]},
        "benchmark_results": {"bench1": {"mean": 0.5, "min": 0.3, "max": 0.7}},
        "metrics": {"entropy": 0.85, "resilience": 0.92},
        "passed": False,
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_verification_report(vdata, out)
        assert "Verification Report" in result
        assert "Passed: 9" in result or "SOME FAILED" in result
        assert "test_fail" in result
        assert "entropy" in result
        assert "<!DOCTYPE html>" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_regression_report():
    baseline = {"entropy": 0.8, "execution_time": 100.0, "resilience": 0.9}
    current = {"entropy": 0.6, "execution_time": 95.0, "resilience": 0.85}
    gate_results = {"passed": 2, "total": 3, "failed": 1, "gates": [{"name": "quality_gate", "passed": False, "message": "Below threshold"}]}
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_regression_report(baseline, current, gate_results, out)
        assert "Regression Report" in result
        assert "REGRESSED" in result or "Regressions" in result
        assert "Quality Gates" in result
        assert "<!DOCTYPE html>" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_security_summary():
    metrics = {
        "entropy": {"value": 0.85, "status": "good"},
        "resilience": {"value": 0.45, "status": "warning"},
        "coverage": {"value": 0.2, "status": "bad"},
        "plain_metric": 0.9,
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_security_summary(metrics, out)
        assert "Security Metrics Summary" in result
        assert "Good" in result or "good" in result
        assert "Warning" in result or "warning" in result
        assert "Bad" in result or "bad" in result
        assert "<!DOCTYPE html>" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


def test_executive_summary():
    reports = {
        "overview": {"Project": "Nixon Shadow Compiler", "Status": "Complete"},
        "key_metrics": {"entropy": "0.85", "resilience": "0.92"},
        "protection_summary": {"layers_applied": 12, "coverage_percent": "85%", "resilience_score": "0.92"},
        "recommendations": ["Increase VM coverage", "Add more ROP chains"],
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        out = f.name
    try:
        result = generate_executive_summary(reports, out)
        assert "Executive Summary" in result
        assert "Key Metrics" in result
        assert "Protection Summary" in result
        assert "Recommendations" in result
        assert "Increase VM coverage" in result
        assert "<!DOCTYPE html>" in result
        assert os.path.isfile(out)
    finally:
        os.unlink(out)


# =========================================================================
# Bundle Tests
# =========================================================================

def test_reproducibility_bundle():
    tmpdir = tempfile.mkdtemp()
    try:
        bundle = ReproducibilityBundle(os.path.join(tmpdir, "bundle_data"))
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello world")

        bundle.add_file(test_file, "subdir/test.txt")
        bundle.add_metrics({"entropy": 0.85})
        bundle.add_report({"passed": True, "tests": 10}, "verification")

        manifest = bundle.generate_manifest()
        assert manifest["file_count"] == 1
        assert "entropy" in manifest["metrics"]
        assert "verification" in manifest["reports"]
        assert "manifest_sha256" in manifest

        bundle_path = bundle.bundle(os.path.join(tmpdir, "test_bundle.tar.gz"))
        assert os.path.isfile(bundle_path)
    finally:
        shutil.rmtree(tmpdir)


def test_bundle_verification():
    tmpdir = tempfile.mkdtemp()
    try:
        bundle = ReproducibilityBundle(os.path.join(tmpdir, "bundle_data"))
        test_file = os.path.join(tmpdir, "verify_test.txt")
        with open(test_file, "w") as f:
            f.write("verify data")

        bundle.add_file(test_file, "data/verify_test.txt")
        bundle.add_metrics({"score": 0.95})

        bundle_path = bundle.bundle(os.path.join(tmpdir, "verify_bundle.tar.gz"))

        result = ReproducibilityBundle.verify_bundle(bundle_path)
        assert result["valid"] is True
        assert result["file_count"] == 1
    finally:
        shutil.rmtree(tmpdir)


# =========================================================================
# Builder Tests
# =========================================================================

def test_artifact_builder():
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "build")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(build_dir)
        obf_path = os.path.join(build_dir, "test_obfuscated.py")
        with open(obf_path, "w") as f:
            f.write("x = 1\n")
        metrics_path = os.path.join(build_dir, "metrics_report.json")
        with open(metrics_path, "w") as f:
            json.dump({"entropy": 0.85}, f)

        builder = ArtifactBuilder(build_dir, output_dir)
        collected = builder.collect_artifacts()
        assert collected["file_count"] >= 2
        assert collected["has_payload"] is True

        modules_list = [{"name": "test", "label": "Test Stage", "category": "obfuscation"}]
        coverage_map = {"functions": {"f1": {"protections": {"VM": True}}}, "per_protection_stats": {"VM": {"coverage_ratio": 1.0}}, "summary": {"total_functions": 1}}
        benchmark_data = {"bench1": {"mean": 0.5, "min": 0.3, "max": 0.7, "std": 0.1, "ops": 2.0}}
        metrics = {"entropy": 0.85, "resilience": 0.9}
        kg = {
            "attack_vectors": [{"name": "Test Attack", "severity": "high"}],
            "targets": [{"name": "Test Target"}],
            "mitigations": [{"name": "Test Mitigation"}],
            "attack_target_map": {"0": [0]},
            "mitigation_map": {"0": [0]},
            "before_metrics": {"entropy": 0.2},
            "after_metrics": {"entropy": 0.85},
            "threats": [{"name": "Test Threat", "severity": "medium", "mitigation": "Opaque Predicates", "status": "mitigated"}],
        }
        result = builder.generate_all(modules_list, coverage_map, benchmark_data, metrics, kg)
        assert "diagrams" in result
        assert "tables" in result
        assert "reports" in result
        assert "bundle" in result
        assert os.path.isdir(os.path.join(output_dir, "diagrams"))
        assert os.path.isdir(os.path.join(output_dir, "tables"))
        assert os.path.isdir(os.path.join(output_dir, "reports"))
    finally:
        shutil.rmtree(tmpdir)


def test_artifact_builder_generate():
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "build")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(build_dir)

        builder = ArtifactBuilder(build_dir, output_dir)
        collected = builder.collect_artifacts()
        assert "build_dir" in collected
        assert "output_dir" in collected

        summary_path = builder.build_complete(output_dir)
        assert os.path.isdir(output_dir)
    finally:
        shutil.rmtree(tmpdir)


# =========================================================================
# Negative Tests
# =========================================================================

def test_empty_artifacts():
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "empty_build")
        output_dir = os.path.join(tmpdir, "empty_output")
        os.makedirs(build_dir)

        builder = ArtifactBuilder(build_dir, output_dir)
        collected = builder.collect_artifacts()
        assert collected["file_count"] == 0
        assert collected["has_payload"] is False

        result = builder.generate_all([], {}, {}, {}, {"attack_vectors": [], "targets": [], "mitigations": [], "attack_target_map": {}, "mitigation_map": {}, "before_metrics": {}, "after_metrics": {}, "threats": []})
        assert "diagrams" in result
        assert "tables" in result
        assert "reports" in result
        assert "bundle" in result
    finally:
        shutil.rmtree(tmpdir)


def test_missing_build_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "nonexistent")
        output_dir = os.path.join(tmpdir, "output")

        builder = ArtifactBuilder(build_dir, output_dir)
        collected = builder.collect_artifacts()
        assert collected["file_count"] == 0
        assert collected["has_payload"] is False
    finally:
        shutil.rmtree(tmpdir)


def test_bundle_integrity_fail():
    tmpdir = tempfile.mkdtemp()
    try:
        bundle = ReproducibilityBundle(os.path.join(tmpdir, "bundle_data"))
        test_file = os.path.join(tmpdir, "orig.txt")
        with open(test_file, "w") as f:
            f.write("original content")

        bundle.add_file(test_file, "data/orig.txt")
        bundle_path = bundle.bundle(os.path.join(tmpdir, "integrity_test.tar.gz"))

        extracted_dir = os.path.join(tmpdir, ".bundle_verify")
        os.makedirs(extracted_dir, exist_ok=True)
        import tarfile
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(extracted_dir)

        contents = os.listdir(extracted_dir)
        if contents:
            bundle_content_dir = os.path.join(extracted_dir, contents[0])
            manifest_path = os.path.join(bundle_content_dir, "manifest.json")
            if os.path.isfile(manifest_path):
                with open(manifest_path) as f:
                    manifest = json.load(f)
                manifest["manifest_sha256"] = "0" * 64
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f)

            import subprocess
            old_dir = os.getcwd()
            os.chdir(extracted_dir)
            try:
                if os.path.isdir(bundle_content_dir):
                    shutil.make_archive(os.path.join(tmpdir, "tampered_bundle"), "gztar", bundle_content_dir)
                else:
                    for d in os.listdir(extracted_dir):
                        dp = os.path.join(extracted_dir, d)
                        if os.path.isdir(dp):
                            shutil.make_archive(os.path.join(tmpdir, "tampered_bundle"), "gztar", dp)
                            break
                tampered_path = os.path.join(tmpdir, "tampered_bundle.tar.gz")
                result = ReproducibilityBundle.verify_bundle(tampered_path)
                assert result["valid"] is False
                assert "integrity" in result.get("error", "").lower() or "mismatch" in result.get("error", "").lower() or "sha256" in result.get("error", "").lower()
            finally:
                os.chdir(old_dir)
    finally:
        shutil.rmtree(tmpdir)
