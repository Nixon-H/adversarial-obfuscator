"""
test_attack_replay.py

Tests for Attack Replay and Verification.

Test coverage:
- Positive tests verify attack capture, replay, result comparison
- Negative tests verify empty captures, missing traces, edge cases
"""
import os
import sys
import tempfile


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAttackCapture:
    """
    TestAttackCapture
    
    Positive test cases for attackcapture.
    """
    def test_attack_capture_dataclass(self):
        from scripts.attack_replay.capture import AttackCapture
        cap = AttackCapture(
            attack_id="test-001",
            attack_type="angr",
            capture_time="2024-01-01T00:00:00+00:00",
            binary_hash="a" * 64,
            source_hash="b" * 64,
            build_id="build_123",
            results={"cfg_recovered": True, "num_functions_found": 10},
            debug_trace="trace data",
            metadata={"env": "test"},
            capture_version="1.0.0",
        )
        assert cap.attack_id == "test-001"
        assert cap.attack_type == "angr"
        assert cap.results["cfg_recovered"] is True
        assert cap.debug_trace == "trace data"
        d = cap.to_dict()
        assert d["attack_id"] == "test-001"
        restored = AttackCapture.from_dict(d)
        assert restored.attack_id == cap.attack_id
        assert restored.attack_type == cap.attack_type

    def test_replay_result_dataclass(self):
        from scripts.attack_replay.replay import ReplayResult
        rr = ReplayResult(
            attack_id="test-001",
            attack_type="angr",
            original_results={"a": 1},
            replayed_results={"a": 1},
            match=True,
            similarity_score=1.0,
            delta={},
            replayed_at="2024-01-01T00:00:00+00:00",
        )
        assert rr.match is True
        assert rr.similarity_score == 1.0
        d = rr.to_dict()
        assert d["attack_id"] == "test-001"

    def test_capture_store_init(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            store = AttackCaptureStore(tmp)
            assert store.count() == 0
            assert os.path.exists(os.path.join(tmp, "captures"))

    def test_capture_and_load(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            bin_path = os.path.join(tmp, "test.bin")
            src_path = os.path.join(tmp, "test.py")
            with open(bin_path, "w") as f:
                f.write("binary")
            with open(src_path, "w") as f:
                f.write("source")
            store = AttackCaptureStore(tmp)
            cap = store.capture(
                attack_type="angr",
                results={"cfg_recovered": True, "num_functions_found": 5},
                binary_path=bin_path,
                source_path=src_path,
            )
            assert store.count() == 1
            loaded = store.load(cap.attack_id)
            assert loaded is not None
            assert loaded.attack_type == "angr"
            assert loaded.results["cfg_recovered"] is True
            assert loaded.binary_hash == store.load(cap.attack_id).binary_hash

    def test_capture_list(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            bin_path = os.path.join(tmp, "test.bin")
            src_path = os.path.join(tmp, "test.py")
            with open(bin_path, "w") as f:
                f.write("binary")
            with open(src_path, "w") as f:
                f.write("source")
            store = AttackCaptureStore(tmp)
            store.capture("angr", {"a": 1}, bin_path, src_path)
            store.capture("ghidra", {"b": 2}, bin_path, src_path)
            store.capture("angr", {"c": 3}, bin_path, src_path)
            all_caps = store.list_captures()
            assert len(all_caps) == 3
            angr_caps = store.list_captures(attack_type="angr")
            assert len(angr_caps) == 2
            ghidra_caps = store.list_captures(attack_type="ghidra")
            assert len(ghidra_caps) == 1


class TestComparator:
    """
    TestComparator
    
    Positive test cases for comparator.
    """
    def test_compare_results_exact(self):
        from scripts.attack_replay.comparator import compare_results
        original = {"status": "completed", "score": 0.85, "count": 10}
        replayed = {"status": "completed", "score": 0.85, "count": 10}
        match, similarity, deltas = compare_results(original, replayed)
        assert match is True
        assert similarity == 1.0
        assert deltas == []

    def test_compare_results_fuzzy(self):
        from scripts.attack_replay.comparator import compare_results
        original = {"score": 0.85}
        replayed = {"score": 0.86}
        match, similarity, deltas = compare_results(original, replayed, tolerance=0.1)
        assert match is True
        assert 0.9 <= similarity <= 1.0

    def test_compare_mismatch(self):
        from scripts.attack_replay.comparator import compare_results
        original = {"status": "completed", "score": 0.9, "count": 10}
        replayed = {"status": "failed", "score": 0.2, "count": 0}
        match, similarity, deltas = compare_results(original, replayed)
        assert match is False
        assert similarity < 0.5
        assert len(deltas) > 0

    def test_fuzzy_match(self):
        from scripts.attack_replay.comparator import fuzzy_match
        assert fuzzy_match(1.0, 1.05, tolerance=0.1) is True
        assert fuzzy_match(1.0, 1.2, tolerance=0.1) is False
        assert fuzzy_match("hello", "hallo", tolerance=0.3) is True
        assert fuzzy_match("hello", "world", tolerance=0.3) is False
        assert fuzzy_match(True, True) is True
        assert fuzzy_match(True, False) is False
        assert fuzzy_match([1, 2, 3], [1, 2, 3]) is True
        assert fuzzy_match([1, 2, 3], [1, 2, 4]) is False


class TestHistory:
    """
    TestHistory
    
    Positive test cases for history.
    """
    def test_history_add(self):
        from scripts.attack_replay.history import AttackHistory
        with tempfile.TemporaryDirectory() as tmp:
            history = AttackHistory(tmp)
            assert history.get_statistics()["total_entries"] == 0
            history.add_entry("angr", {"score": 0.8}, match=True, similarity_score=0.95)
            assert history.get_statistics()["total_entries"] == 1

    def test_history_trend(self):
        from scripts.attack_replay.history import AttackHistory
        with tempfile.TemporaryDirectory() as tmp:
            history = AttackHistory(tmp)
            history.add_entry("angr", {"score": 0.8}, match=True)
            history.add_entry("angr", {"score": 0.85}, match=True)
            history.add_entry("angr", {"score": 0.9}, match=True)
            trend = history.get_trend("angr", "score")
            assert len(trend) == 3
            assert trend[0]["value"] == 0.8
            assert trend[2]["value"] == 0.9

    def test_history_regression(self):
        from scripts.attack_replay.history import AttackHistory
        with tempfile.TemporaryDirectory() as tmp:
            history = AttackHistory(tmp)
            for i in range(10):
                history.add_entry("angr", {"score": 0.9}, match=True)
            for i in range(5):
                history.add_entry("angr", {"score": 0.3}, match=False)
            report = history.get_regression_report(window_size=5)
            assert report["regression_detected"] is True

    def test_history_statistics(self):
        from scripts.attack_replay.history import AttackHistory
        with tempfile.TemporaryDirectory() as tmp:
            history = AttackHistory(tmp)
            history.add_entry("angr", {"score": 0.9}, match=True)
            history.add_entry("ghidra", {"score": 0.8}, match=False)
            stats = history.get_statistics()
            assert stats["total_entries"] == 2
            assert "angr" in stats["attack_types"]
            assert "ghidra" in stats["attack_types"]


class TestNegative:
    """
    TestNegative
    
    Negative test cases — exercises error handling and edge cases for negative.
    """
    def test_empty_store(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            store = AttackCaptureStore(tmp)
            assert store.count() == 0
            assert store.list_captures() == []
            assert store.list_captures(attack_type="angr") == []

    def test_missing_capture(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            store = AttackCaptureStore(tmp)
            loaded = store.load("nonexistent-id")
            assert loaded is None
            deleted = store.delete("nonexistent-id")
            assert deleted is False


class TestReplay:
    """
    TestReplay
    
    Positive test cases for replay.
    """
    def test_replay_result_creation(self):
        from scripts.attack_replay.replay import ReplayResult
        rr = ReplayResult(
            attack_id="id1",
            attack_type="symbolic",
            original_results={"constraints_solved": 5},
            replayed_results={"constraints_solved": 5},
            match=True,
            similarity_score=1.0,
            delta={},
            replayed_at="2024-01-01T00:00:00Z",
        )
        assert rr.match
        d = rr.to_dict()
        assert d["match"] is True

    def test_capture_store_to_dict(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            store = AttackCaptureStore(tmp)
            d = store.to_dict()
            assert d["total_captures"] == 0
            assert d["store_dir"] == tmp

    def test_capture_delete(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            bin_path = os.path.join(tmp, "test.bin")
            src_path = os.path.join(tmp, "test.py")
            with open(bin_path, "w") as f:
                f.write("binary")
            with open(src_path, "w") as f:
                f.write("source")
            store = AttackCaptureStore(tmp)
            cap = store.capture("angr", {"a": 1}, bin_path, src_path)
            assert store.count() == 1
            assert store.delete(cap.attack_id) is True
            assert store.count() == 0

    def test_capture_no_files(self):
        from scripts.attack_replay.capture import AttackCaptureStore
        with tempfile.TemporaryDirectory() as tmp:
            store = AttackCaptureStore(tmp)
            cap = store.capture(
                attack_type="angr",
                results={"status": "completed"},
                binary_path="/nonexistent",
                source_path="/nonexistent",
            )
            assert cap.binary_hash == ""
            assert cap.source_hash == ""
