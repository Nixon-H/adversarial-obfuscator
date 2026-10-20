"""
test_manipulation_detector.py

Tests for Metric Manipulation Detector (Feature 183).

Test coverage:
- Positive tests verify detection of hardcoded scores, inflated coverage, fake survivability
- Negative tests verify computed metrics, non-metric variables, low values are ignored
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.manipulation_detector.detector import (
    MetricManipulationDetector,
    ManipulationFinding,
    AdversarialMutation,
    detect_metric_manipulation,
)


def _make_py(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


# =========================================================================
# Domain Model Tests
# =========================================================================

class TestManipulationFinding:
    """
    TestManipulationFinding
    
    Positive test cases for manipulationfinding.
    """
    def test_dataclass_defaults(self):
        f = ManipulationFinding(
            file="a.py", line=1, metric_type="hardcoded_score",
            pattern="test", snippet="x = 100", score_contribution=0.5,
        )
        assert f.file == "a.py"
        assert f.line == 1

    def test_dataclass_all_fields(self):
        f = ManipulationFinding(
            file="/x.py", line=42, metric_type="fake_survivability",
            pattern="survivability", snippet="return 100",
            score_contribution=0.8,
        )
        assert f.score_contribution == 0.8


class TestAdversarialMutation:
    """
    TestAdversarialMutation
    
    Positive test cases for adversarialmutation.
    """
    def test_dataclass(self):
        m = AdversarialMutation(
            original_file="a.py", original_line=10,
            original_code="return 100", mutated_code="return random.randint(0,100)",
            metric_type="coverage",
        )
        assert m.metric_type == "coverage"
        assert m.mutated_code != m.original_code


# =========================================================================
# Hardcoded Score Detection Tests
# =========================================================================

class TestDetectorHardcodedScore:
    """
    TestDetectorHardcodedScore
    
    Positive test cases for detectorhardcodedscore.
    """
    def test_detect_hardcoded_score(self, tmpdir):
        code = "proof_coverage = 100\n"
        _make_py(tmpdir, "metrics.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert result["total_findings"] >= 1
        assert any("proof_coverage" in str(f) for f in result["findings_per_file"].get("metrics.py", []))

    def test_detect_survivability_hardcode(self, tmpdir):
        code = "survivability = 95\n"
        _make_py(tmpdir, "eval.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert result["total_findings"] >= 1

    def test_ignore_low_values(self, tmpdir):
        code = "score = 50\n"
        _make_py(tmpdir, "ok.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        relevant = [f for f in result["findings_per_file"].get("ok.py", []) if "hardcoded_score" in f["metric_type"]]
        assert len(relevant) == 0

    def test_ignore_non_metric_vars(self, tmpdir):
        code = "x = 100\ny = 95\n"
        _make_py(tmpdir, "normal.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert result["total_findings"] == 0


# =========================================================================
# Inflated Coverage Detection Tests
# =========================================================================

class TestDetectorInflatedCoverage:
    """
    TestDetectorInflatedCoverage
    
    Positive test cases for detectorinflatedcoverage.
    """
    def test_detect_inflated_coverage(self, tmpdir):
        code = "def compute_coverage():\n    return 100\n"
        _make_py(tmpdir, "coverage.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert any(
            f["metric_type"] == "inflated_coverage"
            for finds in result["findings_per_file"].values()
            for f in finds
        )

    def test_coverage_with_calculation_not_flagged(self, tmpdir):
        code = (
            "def compute_coverage(covered, total):\n"
            "    return (covered / total) * 100\n"
        )
        _make_py(tmpdir, "real_coverage.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        inflated = [
            f for finds in result["findings_per_file"].values()
            for f in finds if f["metric_type"] == "inflated_coverage"
        ]
        assert len(inflated) == 0


class TestDetectorFakeSurvivability:
    """
    TestDetectorFakeSurvivability
    
    Positive test cases for detectorfakesurvivability.
    """
    def test_detect_fake_survivability(self, tmpdir):
        code = "def get_survivability():\n    return 99.9\n"
        _make_py(tmpdir, "surv.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert any(
            f["metric_type"] == "fake_survivability"
            for finds in result["findings_per_file"].values()
            for f in finds
        )


class TestDetectorFakeResistance:
    """
    TestDetectorFakeResistance
    
    Positive test cases for detectorfakeresistance.
    """
    def test_detect_fake_resistance(self, tmpdir):
        code = "def compute_resistance():\n    return 95\n"
        _make_py(tmpdir, "resist.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert any(
            f["metric_type"] == "fake_resistance"
            for finds in result["findings_per_file"].values()
            for f in finds
        )


class TestDetectorFakeProofCoverage:
    """
    TestDetectorFakeProofCoverage
    
    Positive test cases for detectorfakeproofcoverage.
    """
    def test_detect_fake_proof_coverage(self, tmpdir):
        code = "def proof_coverage():\n    return 1.0\n"
        _make_py(tmpdir, "proof_cover.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert any(
            f["metric_type"] == "fake_proof_coverage"
            for finds in result["findings_per_file"].values()
            for f in finds
        )


class TestAdversarialMutationGeneration:
    """
    TestAdversarialMutationGeneration
    
    Positive test cases for adversarialmutationgeneration.
    """
    def test_mutation_generated(self, tmpdir):
        code = "def compute_coverage():\n    return 100\n"
        _make_py(tmpdir, "cov.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        mutations = result.get("adversarial_mutations", [])
        assert len(mutations) >= 1
        assert "random.randint" in mutations[0]["mutated_code"]


# =========================================================================
# Manipulation Score Tests
# =========================================================================

class TestManipulationScore:
    """
    TestManipulationScore
    
    Positive test cases for manipulationscore.
    """
    def test_score_zero_when_clean(self, tmpdir):
        code = "x = 1\ny = 2\n"
        _make_py(tmpdir, "clean.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert result["manipulation_score"] == 0.0

    def test_score_positive_when_findings(self, tmpdir):
        code = "proof_coverage = 100\n"
        _make_py(tmpdir, "bad.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert result["manipulation_score"] > 0.0


# =========================================================================
# Top-Level Function Tests
# =========================================================================

class TestTopLevelFunction:
    """
    TestTopLevelFunction
    
    Positive test cases for toplevelfunction.
    """
    def test_detect_metric_manipulation_returns_dict(self):
        result = detect_metric_manipulation()
        assert isinstance(result, dict)
        assert "findings_per_file" in result
        assert "manipulation_score" in result
        assert "adversarial_mutations" in result

    def test_empty_scripts_dir(self, tmpdir):
        result = detect_metric_manipulation(scripts_dir=tmpdir)
        assert result["total_findings"] == 0
        assert result["manipulation_score"] == 0.0


# =========================================================================
# Negative Tests
# =========================================================================

class TestNegativeCases:
    """
    TestNegativeCases
    
    Negative test cases — exercises error handling and edge cases for negativecases.
    """
    def test_no_false_positive_on_computed_metrics(self, tmpdir):
        code = (
            "class Metrics:\n"
            "    def get_score(self):\n"
            "        return self._compute()\n"
            "    def _compute(self):\n"
            "        return sum(self.values) / len(self.values)\n"
        )
        _make_py(tmpdir, "real_metrics.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert result["total_findings"] == 0

    def test_variable_named_cover_not_flagged(self, tmpdir):
        code = "cover = {'a': 1, 'b': 2}\n"
        _make_py(tmpdir, "cover_dict.py", code)
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        result = detector.scan_all()
        assert result["total_findings"] == 0
