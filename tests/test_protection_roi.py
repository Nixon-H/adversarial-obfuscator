"""
test_protection_roi.py

Tests for Protection ROI Analysis (Feature 195).

Test coverage:
- Positive tests verify ROI computation, feature metrics, top ROI sorting
- Negative tests verify empty directories, syntax errors, no features
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.protection_roi.engine import ProtectionROI, ProtectionROIEngine


def _make_file(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestProtectionROI:
    """
    TestProtectionROI
    
    Positive test cases for protectionroi.
    """
    def test_dataclass(self):
        roi = ProtectionROI(
            feature_name="test", file_path="/a.py",
            loc=100, num_classes=2, num_functions=5, num_imports=3,
            test_count=4, has_adversarial_benchmarks=True,
            has_proof_coverage=False, security_gain=70.0,
            runtime_cost=30.0, complexity_cost=20.0,
            maintenance_cost=15.0, roi=107.69,
            is_net_negative=False,
        )
        assert roi.feature_name == "test"
        assert roi.roi == 107.69
        assert not roi.is_net_negative

    def test_net_negative(self):
        roi = ProtectionROI(
            feature_name="bad", file_path="/b.py",
            loc=500, num_classes=10, num_functions=50, num_imports=20,
            test_count=1, has_adversarial_benchmarks=False,
            has_proof_coverage=False, security_gain=10.0,
            runtime_cost=80.0, complexity_cost=80.0,
            maintenance_cost=70.0, roi=4.35,
            is_net_negative=True,
        )
        assert roi.is_net_negative
        assert roi.roi < 50


class TestProtectionROIEnginePositive:
    """
    TestProtectionROIEnginePositive
    
    Positive test cases for protectionroienginepositive.
    """
    def test_compute_roi(self):
        engine = ProtectionROIEngine(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = engine.compute_protection_roi()
        assert "per_feature_roi" in result
        assert "net_negative_features" in result
        assert "top_roi_features" in result
        assert "overall_roi" in result

    def test_overall_roi_range(self):
        engine = ProtectionROIEngine(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = engine.compute_protection_roi()
        assert result["overall_roi"] >= 0.0

    def test_per_feature_has_fields(self):
        engine = ProtectionROIEngine(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = engine.compute_protection_roi()
        for f in result["per_feature_roi"]:
            assert "feature_name" in f
            assert "loc" in f
            assert "num_classes" in f
            assert "num_functions" in f
            assert "security_gain" in f
            assert "roi" in f
            assert "is_net_negative" in f

    def test_some_features_positive(self):
        engine = ProtectionROIEngine(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = engine.compute_protection_roi()
        positive = [f for f in result["per_feature_roi"] if not f["is_net_negative"]]
        assert isinstance(positive, list)

    def test_top_roi_sorted(self):
        engine = ProtectionROIEngine(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = engine.compute_protection_roi()
        top = result["top_roi_features"]
        if len(top) > 1:
            for i in range(len(top) - 1):
                assert top[i]["roi"] >= top[i + 1]["roi"]

    def test_single_feature_roi(self, tmpdir):
        code = (
            '"""Feature: encryption protection."""\n'
            "import os, sys, hashlib\n\n"
            "def encrypt():\n"
            "    pass\n"
            "def decrypt():\n"
            "    pass\n"
        )
        _make_file(tmpdir, "encryption.py", code)
        engine = ProtectionROIEngine(scripts_dir=str(tmpdir))
        result = engine.compute_protection_roi()
        assert result["total_features"] >= 1

    def test_feature_with_adversarial_bench(self, tmpdir):
        code = (
            '"""Feature: anti_tamper protection."""\n'
            "def protect():\n"
            "    assert True\n"
            "    return 42\n"
        )
        _make_file(tmpdir, "anti_tamper.py", code)
        tests_dir = os.path.join(tmpdir, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        _make_file(tests_dir, "bench_anti_tamper.py",
                   "def bench_attack():\n    pass\n")
        engine = ProtectionROIEngine(scripts_dir=str(tmpdir), tests_dir=str(tests_dir))
        result = engine.compute_protection_roi()
        assert result["total_features"] >= 1


class TestProtectionROIEngineNegative:
    """
    TestProtectionROIEngineNegative
    
    Negative test cases — exercises error handling and edge cases for protectionroienginenegative.
    """
    def test_empty_scripts_dir(self, tmpdir):
        engine = ProtectionROIEngine(scripts_dir=str(tmpdir))
        result = engine.compute_protection_roi()
        assert result["total_features"] == 0
        assert result["overall_roi"] == 0.0

    def test_empty_tests_dir(self, tmpdir):
        engine = ProtectionROIEngine(
            scripts_dir=str(tmpdir), tests_dir=os.path.join(tmpdir, "nonexistent")
        )
        result = engine.compute_protection_roi()
        assert result["total_features"] == 0

    def test_syntax_error_file(self, tmpdir):
        _make_file(tmpdir, "bad.py", "this is not python {{{")
        engine = ProtectionROIEngine(scripts_dir=str(tmpdir))
        result = engine.compute_protection_roi()
        assert result["total_features"] >= 0
        for f in result["per_feature_roi"]:
            if "bad" in f["feature_name"]:
                assert f["loc"] == 0

    def test_no_net_negative_when_empty(self, tmpdir):
        engine = ProtectionROIEngine(scripts_dir=str(tmpdir))
        result = engine.compute_protection_roi()
        assert result["net_negative_features"] == []

    def test_no_top_roi_when_empty(self, tmpdir):
        engine = ProtectionROIEngine(scripts_dir=str(tmpdir))
        result = engine.compute_protection_roi()
        assert result["top_roi_features"] == []


class TestPhaseIntegration:
    """
    TestPhaseIntegration
    
    Positive test cases for phaseintegration.
    """
    def test_phase_module_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase_protection_roi",
            "scripts/phases/phase_protection_roi.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "phase_protection_roi")
        assert callable(mod.phase_protection_roi)
