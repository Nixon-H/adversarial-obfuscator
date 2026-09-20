"""
bench_attack_replay.py

Benchmarks for Attack Replay and Verification.

Measures capture, comparison, and replay history performance.
"""
import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAttackReplayBenchmarks:
    @pytest.fixture
    def store_with_captures(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        tmpdir = tempfile.mkdtemp()
        bin_path = os.path.join(tmpdir, "test.bin")
        src_path = os.path.join(tmpdir, "test.py")
        with open(bin_path, "w") as f:
            f.write("x" * 1024)
        with open(src_path, "w") as f:
            f.write("def foo():\n    return 42\n")
        store = AttackCaptureStore(tmpdir)
        for i in range(10):
            store.capture(
                attack_type=["angr", "ghidra", "bninja", "llm", "symbolic"][i % 5],
                results={
                    "status": "completed",
                    "score": 0.85 + i * 0.01,
                    "count": i * 10,
                    "flags": {"a": True, "b": False} if i % 2 == 0 else {"c": 42},
                },
                binary_path=bin_path,
                source_path=src_path,
                metadata={"iteration": i},
            )
        yield tmpdir, store
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bench_capture_time(self, benchmark):
        from scripts.attack_replay.capture import AttackCaptureStore
        tmpdir = tempfile.mkdtemp()
        bin_path = os.path.join(tmpdir, "test.bin")
        src_path = os.path.join(tmpdir, "test.py")
        with open(bin_path, "w") as f:
            f.write("binary data")
        with open(src_path, "w") as f:
            f.write("source data")

        store = AttackCaptureStore(tmpdir)

        def run_capture():
            return store.capture(
                attack_type="angr",
                results={"a": 1, "b": 2, "c": [1, 2, 3]},
                binary_path=bin_path,
                source_path=src_path,
            )

        result = benchmark(run_capture)
        assert result is not None
        assert result.attack_id is not None
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bench_load_time(self, store_with_captures, benchmark):
        from scripts.attack_replay.capture import AttackCaptureStore
        tmpdir, store = store_with_captures
        captures = store.list_captures()
        assert len(captures) == 10
        target_id = captures[0]["attack_id"]

        store2 = AttackCaptureStore(tmpdir)

        def run_load():
            return store2.load(target_id)

        result = benchmark(run_load)
        assert result is not None
        assert result.attack_id == target_id

    def test_bench_comparison_exact(self, benchmark):
        from scripts.attack_replay.comparator import compare_results
        original = {
            "status": "completed",
            "score": 0.85,
            "count": 42,
            "details": {
                "a": 1.0,
                "b": "hello",
                "c": [1, 2, 3, 4, 5],
                "d": True,
            },
            "flags": {"x": 10, "y": 20},
        }
        replayed = {
            "status": "completed",
            "score": 0.85,
            "count": 42,
            "details": {
                "a": 1.0,
                "b": "hello",
                "c": [1, 2, 3, 4, 5],
                "d": True,
            },
            "flags": {"x": 10, "y": 20},
        }

        def run():
            return compare_results(original, replayed)

        result = benchmark(run)
        assert result[0] is True  # match

    def test_bench_comparison_fuzzy(self, benchmark):
        from scripts.attack_replay.comparator import compare_results
        original = {
            "status": "completed",
            "score": 0.85,
            "count": 42,
            "details": {
                "a": 1.0,
                "b": "hello world",
                "c": [1, 2, 3, 4, 5],
            },
        }
        replayed = {
            "status": "completed",
            "score": 0.87,
            "count": 43,
            "details": {
                "a": 1.02,
                "b": "hello world!",
                "c": [1, 2, 3, 4, 6],
            },
        }

        def run():
            return compare_results(original, replayed, tolerance=0.15)

        result = benchmark(run)
        assert isinstance(result[0], bool)

    def test_bench_full_replay_simulation(self, store_with_captures, benchmark):
        from scripts.attack_replay.replay import AttackReplay, ReplayResult
        tmpdir, store = store_with_captures

        class MockConfig:
            binary_path = None
            source_path = None

        replay = AttackReplay(tmpdir, MockConfig())

        def run():
            results = replay.replay_all()
            return results

        results = benchmark(run)
        assert isinstance(results, list)
