"""
test_benchmark_integrity.py

Tests for Benchmark Integrity Verification (Feature 184).

Test coverage:
- Positive tests verify hashing, tamper detection, replay detection, modification detection
- Negative tests verify no false positives on intact files, unique hashes, stable env
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.benchmark_integrity.integrity import (
    BenchmarkIntegrityVerifier,
    verify_benchmark_integrity,
)


def _make_bench(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestHashFile:
    """
    TestHashFile
    
    Positive test cases for hashfile.
    """
    def test_hash_is_sha256(self, tmpdir):
        fpath = _make_bench(tmpdir, "bench_test.py", "def test():\n    assert 1\n")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        h = verifier.hash_file(fpath)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_changes_on_content_change(self, tmpdir):
        fpath = _make_bench(tmpdir, "bench_a.py", "x = 1")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        h1 = verifier.hash_file(fpath)
        with open(fpath, "w") as f:
            f.write("x = 2")
        h2 = verifier.hash_file(fpath)
        assert h1 != h2

    def test_hash_deterministic(self, tmpdir):
        fpath = _make_bench(tmpdir, "bench_a.py", "same content")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        h1 = verifier.hash_file(fpath)
        h2 = verifier.hash_file(fpath)
        assert h1 == h2


class TestEnvironmentFingerprint:
    """
    TestEnvironmentFingerprint
    
    Positive test cases for environmentfingerprint.
    """
    def test_fingerprint_contains_python_version(self):
        verifier = BenchmarkIntegrityVerifier()
        fp = verifier.finger_print_environment()
        assert "python_version" in fp
        assert "platform" in fp
        assert "architecture" in fp

    def test_fingerprint_deterministic(self):
        verifier = BenchmarkIntegrityVerifier()
        fp1 = verifier.finger_print_environment()
        fp2 = verifier.finger_print_environment()
        assert fp1["python_version"] == fp2["python_version"]
        assert fp1["platform"] == fp2["platform"]


class TestHashBenchmarkFiles:
    """
    TestHashBenchmarkFiles
    
    Positive test cases for hashbenchmarkfiles.
    """
    def test_hashes_bench_files(self, tmpdir):
        _make_bench(tmpdir, "bench_a.py", "def bench_a(benchmark):\n    pass\n")
        _make_bench(tmpdir, "bench_b.py", "def bench_b(benchmark):\n    pass\n")
        _make_bench(tmpdir, "not_bench.py", "x = 1\n")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        hashes = verifier.hash_benchmark_files()
        assert "bench_a.py" in hashes
        assert "bench_b.py" in hashes
        assert "not_bench.py" not in hashes

    def test_returns_empty_dict_if_no_dir(self, tmpdir):
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        hashes = verifier.hash_benchmark_files()
        assert hashes == {}


class TestTamperDetection:
    """
    TestTamperDetection
    
    Positive test cases for tamperdetection.
    """
    def test_baseline_sets_status(self):
        verifier = BenchmarkIntegrityVerifier()
        tamper = verifier.detect_tampering(previous_hashes=None)
        assert all(t["status"] == "baseline_set" for t in tamper)

    def test_detect_tampered_file(self, tmpdir):
        fpath = _make_bench(tmpdir, "bench_x.py", "original")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        previous = {"bench_x.py": verifier.hash_file(fpath)}
        with open(fpath, "w") as f:
            f.write("modified")
        tamper = verifier.detect_tampering(previous)
        x_entries = [t for t in tamper if t["file"] == "bench_x.py"]
        assert len(x_entries) >= 1
        assert x_entries[0]["status"] == "tampered"

    def test_detect_added_file(self, tmpdir):
        previous = {"bench_existing.py": "abc" * 20}
        _make_bench(tmpdir, "bench_new.py", "new file")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        tamper = verifier.detect_tampering(previous)
        new_entries = [t for t in tamper if t["file"] == "bench_new.py"]
        assert len(new_entries) >= 1
        assert new_entries[0]["status"] == "added"

    def test_detect_removed_file(self, tmpdir):
        _make_bench(tmpdir, "bench_existing.py", "exists")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        previous = {"bench_existing.py": verifier.hash_file(os.path.join(tmpdir, "bench_existing.py")), "bench_gone.py": "hash"}
        os.remove(os.path.join(tmpdir, "bench_existing.py"))
        tamper = verifier.detect_tampering(previous)
        gone = [t for t in tamper if t["file"] == "bench_gone.py"]
        assert len(gone) >= 1
        assert gone[0]["status"] == "removed"


class TestReplayDetection:
    """
    TestReplayDetection
    
    Positive test cases for replaydetection.
    """
    def test_detect_identical_hashes(self, tmpdir):
        content = "def bench_x():\n    assert 1\n"
        _make_bench(tmpdir, "bench_a.py", content)
        _make_bench(tmpdir, "bench_b.py", content)
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        verifier.hash_benchmark_files()
        replay = verifier.detect_replay()
        assert len(replay) >= 1
        assert replay[0]["status"] == "potential_replay"

    def test_no_replay_with_unique_hashes(self, tmpdir):
        _make_bench(tmpdir, "bench_a.py", "content a")
        _make_bench(tmpdir, "bench_b.py", "content b")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        verifier.hash_benchmark_files()
        replay = verifier.detect_replay()
        assert len(replay) == 0


class TestModificationDetection:
    """
    TestModificationDetection
    
    Positive test cases for modificationdetection.
    """
    def test_baseline_on_first_call(self):
        verifier = BenchmarkIntegrityVerifier()
        modify = verifier.detect_modification()
        assert any(m["status"] == "baseline_set" for m in modify)

    def test_detect_env_change(self):
        verifier = BenchmarkIntegrityVerifier()
        previous_fp = {
            "python_version": "3.8.0 (fake)",
            "platform": "fake-platform",
            "architecture": "x86_64",
        }
        modify = verifier.detect_modification(previous_fingerprint=previous_fp)
        assert any(m["status"] == "modified" for m in modify)
        for m in modify:
            if m["status"] == "modified":
                assert len(m["changes"]) >= 1


class TestIntegrityScore:
    """
    TestIntegrityScore
    
    Positive test cases for integrityscore.
    """
    def test_score_is_100_with_no_issues(self, tmpdir):
        _make_bench(tmpdir, "bench_a.py", "def bench_a():\n    assert 1\n")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        verifier.hash_benchmark_files()
        verifier.detect_tampering()
        verifier.detect_replay()
        verifier.detect_modification()
        score = verifier.compute_integrity_score()
        assert score == 100.0

    def test_score_reduced_by_tampering(self, tmpdir):
        _make_bench(tmpdir, "bench_x.py", "original")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        previous = {"bench_x.py": "different_hash_here_12345678901234567890123456789012"}
        verifier.detect_tampering(previous)
        verifier.hash_benchmark_files()
        verifier.detect_replay()
        verifier.detect_modification()
        score = verifier.compute_integrity_score()
        assert score < 100.0


class TestTopLevelFunction:
    """
    TestTopLevelFunction
    
    Positive test cases for toplevelfunction.
    """
    def test_verify_benchmark_integrity_returns_dict(self):
        result = verify_benchmark_integrity()
        assert isinstance(result, dict)
        for key in ("file_hashes", "env_fingerprint", "tamper_detection", "replay_detection", "modification_detection", "integrity_score"):
            assert key in result

    def test_integrity_with_empty_dir(self, tmpdir):
        result = verify_benchmark_integrity(benchmark_dir=tmpdir)
        assert result["file_hashes"] == {}
        assert result["integrity_score"] >= 0


class TestNegativeCases:
    """
    TestNegativeCases
    
    Negative test cases — exercises error handling and edge cases for negativecases.
    """
    def test_tamper_detection_no_false_positive(self, tmpdir):
        content = "def bench_a():\n    assert 1\n"
        _make_bench(tmpdir, "bench_a.py", content)
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        previous = {"bench_a.py": verifier.hash_file(os.path.join(tmpdir, "bench_a.py"))}
        tamper = verifier.detect_tampering(previous)
        a_entry = [t for t in tamper if t["file"] == "bench_a.py"]
        assert a_entry[0]["status"] == "intact"

    def test_replay_no_false_positive_with_different_names(self, tmpdir):
        _make_bench(tmpdir, "bench_a.py", "unique content a")
        _make_bench(tmpdir, "bench_b.py", "unique content b")
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        verifier.hash_benchmark_files()
        replay = verifier.detect_replay()
        assert len(replay) == 0

    def test_modification_no_false_positive(self):
        verifier = BenchmarkIntegrityVerifier()
        fp = verifier.finger_print_environment()
        modify = verifier.detect_modification(previous_fingerprint=fp)
        assert any(m["status"] == "intact" for m in modify)
