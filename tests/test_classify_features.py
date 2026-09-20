"""Tests for feature classification (Phase 5)."""
import json
import os
import sys
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestClassifyFeatures:
    """
    TestClassifyFeatures
    
    Positive test cases for classifyfeatures.
    """
    def test_classify_script_runs(self):
        result = subprocess.run(
            [sys.executable, "scripts/classify_features.py", "--report"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0

    def test_classify_script_outputs_json(self):
        out_path = os.path.join(tempfile.gettempdir(), "test_feature_classification.json")
        try:
            result = subprocess.run(
                [sys.executable, "scripts/classify_features.py", "--output", out_path],
                capture_output=True, text=True, timeout=30,
            )
            assert result.returncode == 0
            assert os.path.exists(out_path)
            with open(out_path) as f:
                report = json.load(f)
            assert "summary" in report
            assert "features" in report
            assert report["summary"]["total"] == 129
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_all_features_classified(self):
        result = subprocess.run(
            [sys.executable, "scripts/classify_features.py", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert len(report["features"]) == 129
        for f in report["features"]:
            assert f["classification"] in (
                "IMPLEMENTED", "PARTIAL", "EXPERIMENTAL", "SIMULATION", "DEAD CODE"
            ), f"Item {f['id']} has invalid classification: {f['classification']}"

    def test_no_unclassified_features(self):
        result = subprocess.run(
            [sys.executable, "scripts/classify_features.py", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        unclassified = [f for f in report["features"] if f["classification"] not in (
            "IMPLEMENTED", "PARTIAL", "EXPERIMENTAL", "SIMULATION", "DEAD CODE"
        )]
        assert len(unclassified) == 0, f"Unclassified: {[f['id'] for f in unclassified]}"

    def test_partial_features_correct(self):
        result = subprocess.run(
            [sys.executable, "scripts/classify_features.py", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        partial_ids = [f["id"] for f in report["features"] if f["classification"] == "PARTIAL"]
        assert 103 in partial_ids, "Difficulty Curves should be PARTIAL"
        assert 104 in partial_ids, "Economic Model should be PARTIAL"
        assert 105 in partial_ids, "Calibration Data should be PARTIAL"

    def test_implemented_count(self):
        result = subprocess.run(
            [sys.executable, "scripts/classify_features.py", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["summary"]["implemented"] == 126
        assert report["summary"]["partial"] == 3
        assert report["summary"]["experimental"] == 0
        assert report["summary"]["simulation"] == 0
        assert report["summary"]["dead_code"] == 0

    def test_summary_totals(self):
        result = subprocess.run(
            [sys.executable, "scripts/classify_features.py", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        s = report["summary"]
        total = s["implemented"] + s["partial"] + s["experimental"] + s["simulation"] + s["dead_code"]
        assert total == 129, f"Sum of categories ({total}) != 129"
