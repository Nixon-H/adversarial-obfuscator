"""
test_reproducibility.py

Tests for Reproducibility Scoring (Feature 178).

Test coverage:
- Positive tests verify environment snapshots, scoring by artifact type
- Negative tests verify nonexistent files, empty directories, random content
"""
import json
import os
import platform
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.reproducibility.environment import (
    snapshot_environment,
    compare_environments,
    environment_fingerprint,
)
from scripts.reproducibility.scorer import compute_reproducibility, ReproducibilityReport
from scripts.reproducibility.checker import (
    check_result_reproducibility,
    check_benchmark_reproducibility,
    check_attack_reproducibility,
    check_proof_reproducibility,
    check_test_reproducibility,
)


# =========================================================================
# Environment Tests
# =========================================================================

def test_snapshot_environment_returns_all_keys():
    env = snapshot_environment()
    required_keys = {
        "python_version", "os", "cpu", "hostname", "timestamp",
        "git_commit", "git_dirty", "packages",
    }
    assert required_keys.issubset(env.keys()), f"Missing keys: {required_keys - env.keys()}"


def test_snapshot_environment_python_version():
    env = snapshot_environment()
    major, minor, micro = sys.version_info[0], sys.version_info[1], sys.version_info[2]
    expected = f"{major}.{minor}.{micro}"
    assert env["python_version"] == expected


def test_snapshot_environment_os_matches():
    env = snapshot_environment()
    assert platform.platform() in env["os"] or env["os"] == platform.platform()


def test_snapshot_environment_does_not_shell_out_for_the_cpu(monkeypatch):
    """The snapshot must not shell out for the CPU name.

    ``platform.processor()`` and ``platform.machine()`` each run an
    untimed ``uname`` subprocess.  Under load one of them blocked the
    build for five minutes.  The snapshot wants the architecture, not a
    subprocess, so it reads ``os.uname()``.
    """
    def _boom(*args, **kwargs):
        raise AssertionError("snapshot_environment shelled out for the CPU")

    monkeypatch.setattr(platform, "processor", _boom)
    monkeypatch.setattr(platform, "machine", _boom)

    env = snapshot_environment()
    assert env["cpu"]
    assert env["hostname"]


def test_environment_fingerprint_is_deterministic():
    env1 = {"a": "1", "b": "2", "timestamp": "t1"}
    env2 = {"a": "1", "b": "2", "timestamp": "t2"}
    fp1 = environment_fingerprint(env1)
    fp2 = environment_fingerprint(env2)
    assert fp1 == fp2


def test_environment_fingerprint_changes_on_diff():
    env1 = {"a": "1", "b": "2"}
    env2 = {"a": "1", "b": "3"}
    assert environment_fingerprint(env1) != environment_fingerprint(env2)


def test_compare_environments_identical():
    env = {"a": "1", "b": "2"}
    identical, diffs = compare_environments(env, env)
    assert identical is True
    assert len(diffs) == 0


def test_compare_environments_different():
    env_a = {"a": "1", "b": "2"}
    env_b = {"a": "1", "b": "3", "c": "4"}
    identical, diffs = compare_environments(env_a, env_b)
    assert identical is False
    assert "b" in diffs
    assert "c" in diffs


# =========================================================================
# Scorer Tests
# =========================================================================

def test_compute_reproducibility_empty_dir():
    with tempfile.TemporaryDirectory() as td:
        report = compute_reproducibility(td)
        assert report.overall_score == 100.0
        assert len(report.results) == 0
        assert "ReproducibilityReport" in type(report).__name__


def test_compute_reproducibility_nonexistent_dir():
    report = compute_reproducibility("/tmp/nonexistent_repro_dir_178")
    assert report.overall_score == 0.0
    assert len(report.non_reproducible_artifacts) > 0


def test_compute_reproducibility_static_file():
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "benchmark_result.json")
        with open(fpath, "w") as f:
            json.dump({"metric": 42}, f)
        report = compute_reproducibility(td)
        assert len(report.results) == 1
        assert report.results[0].reproducibility_score == 100.0
        assert report.overall_score == 100.0


def test_compute_reproducibility_time_based_file():
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "result.py")
        with open(fpath, "w") as f:
            f.write("import time; x = time.time()")
        report = compute_reproducibility(td)
        assert len(report.results) == 1
        assert report.results[0].reproducibility_score == 50.0


def test_compute_reproducibility_random_file():
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "attack_result.py")
        with open(fpath, "w") as f:
            f.write("import random; x = random.randint(0, 10)")
        report = compute_reproducibility(td)
        assert len(report.results) == 1
        assert report.results[0].reproducibility_score == 0.0


def test_compute_reproducibility_empty_file():
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "empty.benchmark")
        open(fpath, "w").close()
        report = compute_reproducibility(td)
        assert any("Empty" in note for result in report.results for note in result.notes)


def test_compute_reproducibility_mixed_artifacts():
    with tempfile.TemporaryDirectory() as td:
        static = os.path.join(td, "benchmark.json")
        with open(static, "w") as f:
            json.dump({"x": 1}, f)
        random_f = os.path.join(td, "attack_output.py")
        with open(random_f, "w") as f:
            f.write("import secrets; x = secrets.token_hex()")
        report = compute_reproducibility(td)
        assert len(report.results) == 2
        scores = [r.reproducibility_score for r in report.results]
        assert 100.0 in scores
        assert 0.0 in scores


def test_compute_reproducibility_binary_file():
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "program.o")
        with open(fpath, "wb") as f:
            f.write(b"\x7fELF" + os.urandom(100))
        report = compute_reproducibility(td)
        assert any(r.reproducibility_score == 60.0 for r in report.results)


def test_compute_reproducibility_artifact_types():
    with tempfile.TemporaryDirectory() as td:
        files = {
            "benchmark_result.json": "benchmark",
            "attack_report.json": "attack",
            "proof_certificate.json": "proof",
            "test_output.txt": "test",
            "program.ir": "proof",
        }
        for fname, expected_type in files.items():
            fpath = os.path.join(td, fname)
            with open(fpath, "w") as f:
                f.write("42")
            report = compute_reproducibility(td)
            found = [r for r in report.results if fname in r.artifact_path]
            assert len(found) > 0, f"Artifact {fname} not found in results"
            assert found[0].artifact_type == expected_type, f"{fname}: expected {expected_type}, got {found[0].artifact_type}"


def test_reproducibility_report_to_dict():
    report = ReproducibilityReport(
        overall_score=85.0,
        results=[],
        environment={},
        non_reproducible_artifacts=[],
        recommendations=["All good"],
        timestamp="2026-01-01T00:00:00Z",
    )
    d = report.to_dict()
    assert d["overall_score"] == 85.0
    assert d["recommendations"] == ["All good"]


def test_reproducibility_report_to_json():
    report = ReproducibilityReport(
        overall_score=75.0,
        results=[],
        environment={"python": "3.11"},
        non_reproducible_artifacts=[],
        recommendations=["Fix it"],
        timestamp="2026-06-14T00:00:00Z",
    )
    js = report.to_json()
    parsed = json.loads(js)
    assert parsed["overall_score"] == 75.0
    assert parsed["environment"]["python"] == "3.11"


# =========================================================================
# Checker Tests
# =========================================================================

def test_check_result_reproducibility_nonexistent():
    result = check_result_reproducibility("/tmp/nonexistent_file_178")
    assert result.reproducibility_score == 0.0
    assert "not found" in result.notes[0]


def test_check_result_reproducibility_static():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"value": 42}, f)
        fpath = f.name
    try:
        result = check_result_reproducibility(fpath)
        assert result.reproducibility_score >= 60.0
        assert len(result.content_hash) == 64
        assert len(result.metadata_hash) == 64
    finally:
        os.unlink(fpath)


def test_check_result_reproducibility_with_env():
    env = {"python_version": "3.11", "os": "Linux", "cpu": "x86_64", "hostname": "test"}
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write("static content")
        fpath = f.name
    try:
        result = check_result_reproducibility(fpath, original_env=env)
        assert result is not None
    finally:
        os.unlink(fpath)


def test_check_benchmark_reproducibility():
    with tempfile.NamedTemporaryFile(suffix=".benchmark.json", mode="w", delete=False) as f:
        json.dump({"mean": 0.5, "std": 0.1}, f)
        fpath = f.name
    try:
        result = check_benchmark_reproducibility(fpath)
        assert result.artifact_type == "benchmark"
    finally:
        os.unlink(fpath)


def test_check_attack_reproducibility():
    with tempfile.NamedTemporaryFile(suffix=".attack.json", mode="w", delete=False) as f:
        json.dump({"attack_type": "angr", "seed": 42, "timestamp": "now"}, f)
        fpath = f.name
    try:
        result = check_attack_reproducibility(fpath)
        assert result.artifact_type == "attack"
    finally:
        os.unlink(fpath)


def test_check_attack_reproducibility_nonexistent():
    result = check_attack_reproducibility("/tmp/no_attack_178")
    assert result.reproducibility_score == 0.0
    assert result.artifact_type == "attack"


def test_check_proof_reproducibility():
    with tempfile.NamedTemporaryFile(suffix=".proof.json", mode="w", delete=False) as f:
        json.dump({"theorem": "equivalence"}, f)
        fpath = f.name
    try:
        result = check_proof_reproducibility(fpath)
        assert result.artifact_type == "proof"
    finally:
        os.unlink(fpath)


def test_check_test_reproducibility():
    with tempfile.NamedTemporaryFile(suffix=".test.txt", mode="w", delete=False) as f:
        f.write("PASS: 10 tests passed\nFAIL: 2 tests failed\n")
        fpath = f.name
    try:
        result = check_test_reproducibility(fpath)
        assert result.artifact_type == "test"
    finally:
        os.unlink(fpath)


def test_check_test_reproducibility_empty():
    with tempfile.NamedTemporaryFile(suffix=".test.txt", mode="w", delete=False) as f:
        fpath = f.name
    try:
        result = check_test_reproducibility(fpath)
        assert result.reproducibility_score == 0.0
    finally:
        os.unlink(fpath)


def test_check_test_reproducibility_nonexistent():
    result = check_test_reproducibility("/tmp/no_test_178")
    assert result.reproducibility_score == 0.0


# =========================================================================
# Integration Tests
# =========================================================================

def test_compute_reproducibility_produces_report_json():
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "bench.json")
        with open(fpath, "w") as f:
            f.write("data")
        report = compute_reproducibility(td)
        js = report.to_json()
        parsed = json.loads(js)
        assert "overall_score" in parsed
        assert "results" in parsed
        assert "environment" in parsed
        assert "non_reproducible_artifacts" in parsed
        assert "recommendations" in parsed
        assert "timestamp" in parsed


def test_compute_reproducibility_nonreproducible_list():
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "bad.py")
        with open(fpath, "w") as f:
            f.write("import random")
        report = compute_reproducibility(td)
        if report.overall_score < 50.0:
            assert len(report.non_reproducible_artifacts) > 0
        else:
            assert len(report.non_reproducible_artifacts) == 0
