"""
test_verification_bundle.py

Tests for Verification Bundle (Feature 177).

Test coverage:
- Positive tests verify hashing, manifest building, artifact collection, bundling
- Negative tests verify corrupt bundles, missing files, hash mismatches
"""
import json
import os
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.verification_bundle.hasher import (
    file_sha256,
    data_sha256,
    sha256_manifest,
    build_manifest_entry,
    verify_manifest_entry,
)
from scripts.verification_bundle.manifest import ManifestBuilder
from scripts.verification_bundle.collector import ArtifactCollector
from scripts.verification_bundle.bundler import VerificationBundler


# =========================================================================
# Hasher Tests
# =========================================================================

def test_file_sha256_consistent():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("hello world")
        path = f.name
    try:
        h1 = file_sha256(path)
        h2 = file_sha256(path)
        assert h1 == h2
        assert len(h1) == 64
    finally:
        os.unlink(path)


def test_file_sha256_different():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("content a")
        path_a = f.name
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("content b")
        path_b = f.name
    try:
        assert file_sha256(path_a) != file_sha256(path_b)
    finally:
        os.unlink(path_a)
        os.unlink(path_b)


def test_file_sha256_nonexistent():
    try:
        file_sha256("/tmp/nonexistent_file_xyz_177")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_data_sha256_consistent():
    h1 = data_sha256(b"test data")
    h2 = data_sha256(b"test data")
    assert h1 == h2
    assert len(h1) == 64


def test_data_sha256_empty():
    h = data_sha256(b"")
    assert len(h) == 64


def test_sha256_manifest_deterministic():
    entries = {"a.txt": "abc", "b.txt": "def"}
    m1 = sha256_manifest(entries)
    m2 = sha256_manifest(entries)
    assert m1 == m2


def test_sha256_manifest_order():
    entries1 = {"a.txt": "abc", "b.txt": "def"}
    entries2 = {"b.txt": "def", "a.txt": "abc"}
    assert sha256_manifest(entries1) == sha256_manifest(entries2)


def test_sha256_manifest_changes():
    entries1 = {"a.txt": "abc"}
    entries2 = {"a.txt": "xyz"}
    assert sha256_manifest(entries1) != sha256_manifest(entries2)


def test_build_manifest_entry():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("entry data")
        path = f.name
    try:
        entry = build_manifest_entry(path, "subdir/file.txt")
        assert entry["local_path"] == path
        assert entry["archive_rel"] == "subdir/file.txt"
        assert len(entry["sha256"]) == 64
        assert entry["size_bytes"] == 10
    finally:
        os.unlink(path)


def test_verify_manifest_entry_match():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("verify me")
        path = f.name
    try:
        digest = file_sha256(path)
        assert verify_manifest_entry(path, digest) is True
    finally:
        os.unlink(path)


def test_verify_manifest_entry_mismatch():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("verify me")
        path = f.name
    try:
        bad_digest = "0" * 64
        assert verify_manifest_entry(path, bad_digest) is False
    finally:
        os.unlink(path)


def test_verify_manifest_entry_nonexistent():
    assert verify_manifest_entry("/tmp/no_file_177", "0" * 64) is False


# =========================================================================
# ManifestBuilder Tests
# =========================================================================

def test_manifest_builder_build():
    mb = ManifestBuilder()
    mb.add_entry("a.txt", "abc123", 10, category="source")
    mb.add_entry("b.json", "def456", 20, category="benchmark")
    manifest = mb.build()
    assert manifest["manifest_version"] == "1.0"
    assert manifest["file_count"] == 2
    assert manifest["algorithm"] == "SHA-256"
    assert len(manifest["files"]) == 2
    assert manifest["files"][0]["path"] == "a.txt"
    assert manifest["files"][1]["path"] == "b.json"


def test_manifest_builder_add_entries():
    mb = ManifestBuilder()
    entries = [
        {"path": "x.txt", "sha256": "111", "size_bytes": 5, "category": "source"},
        {"path": "y.txt", "sha256": "222", "size_bytes": 7, "category": "proof"},
    ]
    mb.add_entries(entries)
    manifest = mb.build()
    assert manifest["file_count"] == 2


def test_manifest_builder_empty():
    mb = ManifestBuilder()
    manifest = mb.build()
    assert manifest["file_count"] == 0
    assert manifest["files"] == []


def test_manifest_builder_json_output():
    mb = ManifestBuilder()
    mb.add_entry("f.txt", "abc", 3, "trace")
    js = mb.build_json()
    parsed = json.loads(js)
    assert parsed["file_count"] == 1


def test_manifest_builder_manifest_hash_changes():
    mb1 = ManifestBuilder()
    mb1.add_entry("a.txt", "abc", 3)
    m1 = mb1.build()
    mb2 = ManifestBuilder()
    mb2.add_entry("a.txt", "xyz", 3)
    m2 = mb2.build()
    assert m1["manifest_sha256"] != m2["manifest_sha256"]


def test_manifest_verify_pass():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, "w") as f:
            f.write("data")
        digest = file_sha256(fpath)
        mb = ManifestBuilder()
        mb.add_entry("test.txt", digest, 4, "source")
        manifest = mb.build()
        ok, errors = ManifestBuilder.verify(tmpdir, manifest)
        assert ok is True
        assert len(errors) == 0


def test_manifest_verify_missing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        mb = ManifestBuilder()
        mb.add_entry("missing.txt", "0" * 64, 10, "source")
        manifest = mb.build()
        ok, errors = ManifestBuilder.verify(tmpdir, manifest)
        assert ok is False
        assert any("MISSING" in e for e in errors)


def test_manifest_verify_hash_mismatch():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "bad.txt")
        with open(fpath, "w") as f:
            f.write("original")
        mb = ManifestBuilder()
        mb.add_entry("bad.txt", "f" * 64, 8, "source")
        manifest = mb.build()
        ok, errors = ManifestBuilder.verify(tmpdir, manifest)
        assert ok is False
        assert any("HASH_MISMATCH" in e for e in errors)


# =========================================================================
# ArtifactCollector Tests
# =========================================================================

def test_collector_empty_build_dir():
    with tempfile.TemporaryDirectory() as td:
        collector = ArtifactCollector(td)
        summary = collector.collect_all()
        assert summary["total_entries"] >= 0
        assert "entries" in summary


def test_collector_with_source_files():
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "source.py")
        with open(src, "w") as f:
            f.write("x = 1")
        collector = ArtifactCollector(td)
        summary = collector.collect_all()
        assert summary["total_entries"] >= 0


def test_collector_with_benchmark():
    with tempfile.TemporaryDirectory() as td:
        bench = os.path.join(td, "benchmark_report.json")
        with open(bench, "w") as f:
            json.dump({"mean": 0.5}, f)
        collector = ArtifactCollector(td)
        summary = collector.collect_all()
        bench_entries = summary["benchmarks_list"]
        assert any("benchmark_report" in e.get("archive_rel", e.get("path", "")) for e in bench_entries)


def test_collector_with_proof_artifact():
    with tempfile.TemporaryDirectory() as td:
        proofs_dir = os.path.join(td, "proofs")
        os.makedirs(proofs_dir)
        proof = os.path.join(proofs_dir, "vm_proof.json")
        with open(proof, "w") as f:
            json.dump({"theorem": "equiv"}, f)
        collector = ArtifactCollector(td)
        summary = collector.collect_all()
        assert any("proof" in e["archive_rel"] for e in summary["proofs_list"])


def test_collector_with_trace():
    with tempfile.TemporaryDirectory() as td:
        trace = os.path.join(td, "pipeline.prof")
        with open(trace, "w") as f:
            f.write("trace data")
        collector = ArtifactCollector(td)
        summary = collector.collect_all()
        trace_entries = summary["traces_list"]
        assert any("pipeline.prof" in e["archive_rel"] for e in trace_entries)


def test_collector_with_attack_artifact():
    with tempfile.TemporaryDirectory() as td:
        attacks_dir = os.path.join(td, "redteam")
        os.makedirs(attacks_dir)
        attack = os.path.join(attacks_dir, "attack_result.json")
        with open(attack, "w") as f:
            json.dump({"found": True}, f)
        collector = ArtifactCollector(td)
        summary = collector.collect_all()
        assert any("attack_result" in e["archive_rel"] for e in summary["attacks_list"])


def test_collector_summary_keys():
    with tempfile.TemporaryDirectory() as td:
        collector = ArtifactCollector(td)
        summary = collector.collect_all()
        required = {"total_entries", "source_references", "benchmarks", "traces", "proof_artifacts", "attack_artifacts"}
        assert required.issubset(summary.keys())


# =========================================================================
# VerificationBundler Tests
# =========================================================================

def test_bundler_builds_tar_gz():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir)
        src = os.path.join(build_dir, "benchmark_report.json")
        with open(src, "w") as f:
            json.dump({"score": 95}, f)
        output_dir = os.path.join(td, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        manifest = bundler.build_bundle()
        assert manifest["file_count"] >= 1
        assert manifest["bundle_path"] is not None
        assert os.path.isfile(manifest["bundle_path"])
        assert manifest["bundle_path"].endswith(".tar.gz")


def test_bundler_bundle_contains_manifest():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir)
        src = os.path.join(build_dir, "test.py")
        with open(src, "w") as f:
            f.write("print('hi')")
        output_dir = os.path.join(td, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        manifest = bundler.build_bundle()
        bundle_path = manifest["bundle_path"]
        with tarfile.open(bundle_path, "r:gz") as tar:
            names = tar.getnames()
        assert "manifest.json" in names


def test_bundler_verify_self():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir)
        src = os.path.join(build_dir, "data.json")
        with open(src, "w") as f:
            json.dump({"key": "value"}, f)
        output_dir = os.path.join(td, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        bundler.build_bundle()
        ok, errors = bundler.verify_bundle()
        assert ok is True
        assert len(errors) == 0


def test_bundler_verify_corrupt_bundle():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir)
        src = os.path.join(build_dir, "file.py")
        with open(src, "w") as f:
            f.write("code")
        output_dir = os.path.join(td, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        bundler.build_bundle()
        bundle_path = bundler.bundle_path
        with open(bundle_path, "wb") as f:
            f.write(b"NOT A VALID TAR.GZ FILE")
        ok, errors = bundler.verify_bundle()
        assert ok is False
        assert len(errors) > 0


def test_bundler_no_build_artifacts():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "empty_build")
        os.makedirs(build_dir)
        output_dir = os.path.join(td, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        manifest = bundler.build_bundle()
        assert manifest["file_count"] >= 0
        assert os.path.isfile(manifest["bundle_path"])
        ok, errors = bundler.verify_bundle()
        assert ok is True


def test_bundler_verify_no_bundle():
    bundler = VerificationBundler("/tmp", "/tmp")
    ok, errors = bundler.verify_bundle()
    assert ok is False
    assert len(errors) > 0


def test_bundler_bundle_sha256_changes():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir)
        output_dir1 = os.path.join(td, "output1")
        bundler = VerificationBundler(build_dir, output_dir1)
        m1 = bundler.build_bundle()
        sha1 = m1["bundle_sha256"]
        src = os.path.join(build_dir, "benchmark_results.json")
        with open(src, "w") as f:
            json.dump({"mean": 42}, f)
        output_dir2 = os.path.join(td, "output2")
        bundler2 = VerificationBundler(build_dir, output_dir2)
        m2 = bundler2.build_bundle()
        sha2 = m2["bundle_sha256"]
        assert sha1 != sha2


def test_bundler_summary_json_written():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir)
        output_dir = os.path.join(td, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        bundler.build_bundle()
        summary_path = os.path.join(output_dir, "bundle_summary.json")
        assert os.path.isfile(summary_path)
        with open(summary_path) as f:
            data = json.load(f)
        assert "bundle_sha256" in data
        assert "file_count" in data


def test_bundler_multiple_categories():
    with tempfile.TemporaryDirectory() as td:
        build_dir = os.path.join(td, "build")
        os.makedirs(build_dir)
        bench = os.path.join(build_dir, "benchmark_report.json")
        with open(bench, "w") as f:
            json.dump({"m": 1}, f)
        trace = os.path.join(build_dir, "pipeline.prof")
        with open(trace, "w") as f:
            f.write("trace")
        proofs = os.path.join(build_dir, "proofs")
        os.makedirs(proofs)
        proof = os.path.join(proofs, "cert.json")
        with open(proof, "w") as f:
            json.dump({"p": True}, f)
        output_dir = os.path.join(td, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        manifest = bundler.build_bundle()
        assert manifest["file_count"] >= 3
        with tarfile.open(manifest["bundle_path"], "r:gz") as tar:
            names = tar.getnames()
        assert any("benchmarks" in n for n in names)
        assert any("traces" in n for n in names)
        assert any("proofs" in n for n in names)
