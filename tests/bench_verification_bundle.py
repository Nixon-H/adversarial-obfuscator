"""
bench_verification_bundle.py

Benchmarks for Verification Bundle (Feature 177).

Measures hashing, manifest building, artifact collection, and bundling.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.verification_bundle.hasher import (
    file_sha256,
    data_sha256,
    sha256_manifest,
)
from scripts.verification_bundle.bundler import VerificationBundler
from scripts.verification_bundle.collector import ArtifactCollector
from scripts.verification_bundle.manifest import ManifestBuilder


def _populate_build_dir(path: str, num_files: int = 100) -> None:
    os.makedirs(path, exist_ok=True)
    proofs_dir = os.path.join(path, "proofs")
    os.makedirs(proofs_dir, exist_ok=True)
    redteam_dir = os.path.join(path, "redteam")
    os.makedirs(redteam_dir, exist_ok=True)
    for i in range(num_files):
        if i % 4 == 0:
            fpath = os.path.join(path, f"benchmark_{i}.json")
            with open(fpath, "w") as f:
                json.dump({"mean": i, "std": i * 0.1}, f)
        elif i % 4 == 1:
            fpath = os.path.join(proofs_dir, f"proof_{i}.json")
            with open(fpath, "w") as f:
                json.dump({"theorem": "equiv", "seed": i}, f)
        elif i % 4 == 2:
            fpath = os.path.join(path, f"pipeline_{i}.prof")
            with open(fpath, "w") as f:
                f.write(f"# profile data {i}\n")
        else:
            fpath = os.path.join(redteam_dir, f"attack_{i}.json")
            with open(fpath, "w") as f:
                json.dump({"attack": "angr", "found": True}, f)


def _populate_large_build(path: str, num_files: int = 500) -> None:
    _populate_build_dir(path, num_files)


def test_bench_file_sha256(benchmark):
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(b"x" * 100000)
        path = f.name
    try:
        result = benchmark(file_sha256, path)
        assert len(result) == 64
    finally:
        os.unlink(path)


def test_bench_data_sha256(benchmark):
    data = b"benchmark data" * 10000
    result = benchmark(data_sha256, data)
    assert len(result) == 64


def test_bench_sha256_manifest(benchmark):
    entries = {f"file_{i}.txt": f"digest_{i}" for i in range(1000)}
    result = benchmark(sha256_manifest, entries)
    assert len(result) == 64


def test_bench_manifest_builder(benchmark):
    def _build():
        mb = ManifestBuilder()
        for i in range(500):
            mb.add_entry(f"file_{i}.bin", f"digest_{i:064x}", 100, "source")
        return mb.build()
    result = benchmark(_build)
    assert result["file_count"] == 500


def test_bench_collector_small(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        _populate_build_dir(tmpdir, 50)
        collector = ArtifactCollector(tmpdir)
        result = benchmark(collector.collect_all)
        assert result["total_entries"] >= 0
    finally:
        shutil.rmtree(tmpdir)


def test_bench_collector_large(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        _populate_build_dir(tmpdir, 500)
        collector = ArtifactCollector(tmpdir)
        result = benchmark(collector.collect_all)
        assert result["total_entries"] >= 0
    finally:
        shutil.rmtree(tmpdir)


def test_bench_bundler_small(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "build")
        _populate_build_dir(build_dir, 20)
        output_dir = os.path.join(tmpdir, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        result = benchmark(bundler.build_bundle)
        assert result["file_count"] >= 0
    finally:
        shutil.rmtree(tmpdir)


def test_bench_bundler_large(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "build")
        _populate_build_dir(build_dir, 500)
        output_dir = os.path.join(tmpdir, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        result = benchmark(bundler.build_bundle)
        assert result["file_count"] >= 0
    finally:
        shutil.rmtree(tmpdir)


def test_bench_bundler_verify(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "build")
        _populate_build_dir(build_dir, 100)
        output_dir = os.path.join(tmpdir, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        bundler.build_bundle()
        ok, errors = benchmark(bundler.verify_bundle)
        assert ok is True
    finally:
        shutil.rmtree(tmpdir)


def test_bench_bundler_empty(benchmark):
    tmpdir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir)
        output_dir = os.path.join(tmpdir, "output")
        bundler = VerificationBundler(build_dir, output_dir)
        result = benchmark(bundler.build_bundle)
        assert result["file_count"] >= 0
    finally:
        shutil.rmtree(tmpdir)
