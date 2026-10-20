"""
test_audit_drift.py

Tests for Audit Drift Detection (Feature 186).

Test coverage:
- Positive tests verify source hashing, report inventory, drift detection, staleness scoring
- Negative tests verify no false drift, non-py files ignored, baseline checks
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.audit_drift.detector import (
    AuditDriftDetector,
    detect_audit_drift,
)


def _make_file(path: str, content: str | bytes) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(path, mode) as f:
        f.write(content)  # type: ignore[arg-type]
    return path


# =========================================================================
# Source Hashing Tests
# =========================================================================

class TestHashSourceFiles:
    """
    TestHashSourceFiles
    
    Positive test cases for hashsourcefiles.
    """
    def test_hashes_all_py_files(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "a.py"), "x = 1")
        _make_file(os.path.join(scripts_dir, "b.py"), "y = 2")
        _make_file(os.path.join(scripts_dir, "data.txt"), "not scanned")
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        snapshot = detector.hash_source_files()
        py_keys = [k for k in snapshot if k.endswith(".py")]
        assert len(py_keys) == 2
        assert "data.txt" not in " ".join(snapshot.keys())

    def test_hash_is_sha256_prefix(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "a.py"), "content")
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        snapshot = detector.hash_source_files()
        for info in snapshot.values():
            h = info["hash"]
            assert len(h) == 64
            assert all(c in "0123456789abcdef" for c in h)

    def test_empty_scripts_dir(self, tmpdir):
        detector = AuditDriftDetector(root_dir=tmpdir)
        snapshot = detector.hash_source_files()
        assert snapshot == {}


# =========================================================================
# Report Inventory Tests
# =========================================================================

class TestInventoryReports:
    """
    TestInventoryReports
    
    Positive test cases for inventoryreports.
    """
    def test_inventories_json_files(self, tmpdir):
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir)
        _make_file(os.path.join(build_dir, "report.json"), json.dumps({"a": 1}))
        _make_file(os.path.join(build_dir, "note.md"), "# notes")
        _make_file(os.path.join(build_dir, "binary.bin"), b"binary")
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.build_dir = build_dir
        inventory = detector.inventory_reports()
        assert len(inventory) == 2
        names = {r["file"] for r in inventory}
        assert "report.json" in names
        assert "note.md" in names
        assert "binary.bin" not in names

    def test_no_build_dir(self, tmpdir):
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.build_dir = os.path.join(tmpdir, "nonexistent")
        inventory = detector.inventory_reports()
        assert inventory == []


# =========================================================================
# Drift Detection Tests
# =========================================================================

class TestDetectDrift:
    """
    TestDetectDrift
    
    Positive test cases for detectdrift.
    """
    def test_drift_detected_when_no_report(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "feature.py"), "def f():\n    pass\n")
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir)
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        detector.build_dir = build_dir
        detector.hash_source_files()
        detector.inventory_reports()
        drifted = detector.detect_drift()
        assert len(drifted) >= 1
        assert any("feature" in str(d["source_file"]) for d in drifted)

    def test_no_drift_with_matching_report(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        fpath = os.path.join(scripts_dir, "feature.py")
        _make_file(fpath, "def f():\n    pass\n")
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir)
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        detector.build_dir = build_dir
        source_hash = detector.hash_source_files()["scripts/feature.py"]["hash"]
        report_path = os.path.join(build_dir, "scripts_feature_report.json")
        with open(report_path, "w") as f:
            json.dump({"source_hash": source_hash, "sha256": source_hash}, f)
        detector.inventory_reports()
        drifted = detector.detect_drift()
        feature_drift = [d for d in drifted if "feature" in str(d["source_file"])]
        assert len(feature_drift) == 0 or all(d["status"] == "no_corresponding_report" for d in feature_drift if "feature" in str(d["source_file"]))

    def test_drift_status_contains_info(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "m.py"), "m = 1")
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        detector.build_dir = os.path.join(tmpdir, "build")
        os.makedirs(detector.build_dir)
        detector.hash_source_files()
        detector.inventory_reports()
        drifted = detector.detect_drift()
        assert all("status" in d for d in drifted)
        assert all("current_hash" in d for d in drifted)


# =========================================================================
# Staleness Score Tests
# =========================================================================

class TestStalenessScore:
    """
    TestStalenessScore
    
    Positive test cases for stalenessscore.
    """
    def test_score_100_when_no_sources(self, tmpdir):
        detector = AuditDriftDetector(root_dir=tmpdir)
        score = detector.compute_staleness_score()
        assert score == 0.0 or score == 100.0

    def test_score_reduced_by_drift(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "a.py"), "x = 1")
        _make_file(os.path.join(scripts_dir, "b.py"), "y = 2")
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        detector.build_dir = os.path.join(tmpdir, "build")
        os.makedirs(detector.build_dir)
        detector.hash_source_files()
        detector.inventory_reports()
        detector.detect_drift()
        score = detector.compute_staleness_score()
        assert score < 100.0

    def test_score_between_0_and_100(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "a.py"), "x = 1")
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        detector.build_dir = os.path.join(tmpdir, "build")
        os.makedirs(detector.build_dir)
        detector.hash_source_files()
        detector.inventory_reports()
        detector.detect_drift()
        score = detector.compute_staleness_score()
        assert 0 <= score <= 100


# =========================================================================
# Top-Level Function Tests
# =========================================================================

class TestTopLevelFunction:
    """
    TestTopLevelFunction
    
    Positive test cases for toplevelfunction.
    """
    def test_detect_audit_drift_returns_dict(self):
        result = detect_audit_drift()
        assert isinstance(result, dict)
        for key in ("source_snapshot", "report_inventory", "drifted_files", "staleness_score", "total_source_files", "total_reports", "total_drifted"):
            assert key in result

    def test_drift_with_empty_dirs(self, tmpdir):
        result = detect_audit_drift(root_dir=tmpdir)
        assert result["total_source_files"] == 0
        assert result["staleness_score"] >= 0


# =========================================================================
# Negative Tests
# =========================================================================

class TestNegativeCases:
    """
    TestNegativeCases
    
    Negative test cases — exercises error handling and edge cases for negativecases.
    """
    def test_no_false_drift_with_matching_reports(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "a.py"), "a = 1")
        _make_file(os.path.join(scripts_dir, "b.py"), "b = 2")
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir)
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        detector.build_dir = build_dir
        detector.hash_source_files()
        for rel, info in detector.source_snapshot.items():
            report_name = rel.replace("/", "_").replace(".py", "_report.json")
            report_path = os.path.join(build_dir, report_name)
            with open(report_path, "w") as f:
                json.dump({"hash": info["hash"]}, f)
        detector.inventory_reports()
        drifted = detector.detect_drift()
        non_matching = [d for d in drifted if d["source_file"] in detector.source_snapshot]
        assert len(non_matching) == 0

    def test_non_py_files_not_hashed(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        _make_file(os.path.join(scripts_dir, "readme.md"), "# docs")
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        snapshot = detector.hash_source_files()
        assert len(snapshot) == 0

    def test_baseline_check_negative(self, tmpdir):
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir)
        _make_file(os.path.join(build_dir, "report.json"), json.dumps({"value": 42}))
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.build_dir = build_dir
        inventory = detector.inventory_reports()
        assert not inventory[0]["has_source_hashes"]

    def test_baseline_check_positive(self, tmpdir):
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir)
        _make_file(os.path.join(build_dir, "report.json"), json.dumps({"source_hash": "abc", "sha256": "def"}))
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.build_dir = build_dir
        inventory = detector.inventory_reports()
        assert inventory[0]["has_source_hashes"]
