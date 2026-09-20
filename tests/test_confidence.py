"""
test_confidence.py

Tests for Security Confidence Interval Computation (Feature 179).

Test coverage:
- Positive tests verify normal, t-distribution, degenerate, and identical-sample CIs
- Negative tests verify negative values, large variance, zero values, mixed types
"""

import math
import json
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.confidence import (
    compute_confidence_interval,
    format_confidence_interval,
    SecurityConfidenceInterval,
)
from scripts.confidence.interval import _t_critical, _normal_critical


# ---------------------------------------------------------------------------
# Positive tests
# ---------------------------------------------------------------------------

def test_compute_confidence_interval_normal():
    samples = [85, 87, 86, 88, 84, 86, 87, 85, 89, 83,
               86, 84, 88, 87, 85, 86, 84, 87, 88, 86,
               85, 87, 86, 88, 84, 86, 87, 85, 89, 83]
    ci = compute_confidence_interval(samples, confidence_level=0.95)
    assert ci.sample_size == 30
    assert ci.distribution == "normal"
    assert 85.0 <= ci.mean <= 87.0
    assert ci.margin > 0.0
    assert ci.lower < ci.mean < ci.upper
    assert ci.lower < ci.upper


def test_compute_confidence_interval_t_distribution():
    samples = [85, 87, 86, 88, 84]
    ci = compute_confidence_interval(samples, confidence_level=0.95)
    assert ci.sample_size == 5
    assert ci.distribution == "t-distribution"
    assert 85.0 <= ci.mean <= 88.0
    assert ci.margin > 0.0
    assert ci.lower < ci.mean < ci.upper


def test_compute_confidence_interval_single_sample():
    samples = [87]
    ci = compute_confidence_interval(samples)
    assert ci.sample_size == 1
    assert ci.distribution == "degenerate"
    assert ci.mean == 87.0
    assert ci.margin == 0.0


def test_compute_confidence_interval_empty():
    ci = compute_confidence_interval([])
    assert ci.sample_size == 0
    assert ci.distribution == "none"
    assert ci.mean == 0.0


def test_compute_confidence_interval_identical_values():
    samples = [80, 80, 80, 80, 80]
    ci = compute_confidence_interval(samples)
    assert ci.mean == 80.0
    assert ci.margin == 0.0
    assert ci.lower == ci.upper == 80.0


def test_format_confidence_interval():
    samples = [85, 87, 86, 88, 84]
    result = format_confidence_interval("Security Score", samples)
    assert "Security Score" in result
    assert "±" in result
    assert "/100" in result
    assert "t-distribution" in result
    assert "Margin:" in result


def test_security_confidence_interval_to_tuple():
    ci = SecurityConfidenceInterval(
        mean=86, margin=3, lower=83, upper=89,
        confidence_level=0.95, sample_size=10, distribution="t-distribution",
    )
    t = ci.to_tuple()
    assert t == (83, 89)


def test_security_confidence_interval_to_dict():
    ci = SecurityConfidenceInterval(
        mean=86.0, margin=2.5, lower=83.5, upper=88.5,
        confidence_level=0.95, sample_size=10, distribution="normal",
    )
    d = ci.to_dict()
    assert d["mean"] == 86.0
    assert d["margin"] == 2.5
    assert d["lower"] == 83.5
    assert d["upper"] == 88.5
    assert d["distribution"] == "normal"
    assert d["sample_size"] == 10


def test_str_representation():
    ci = SecurityConfidenceInterval(
        mean=87.3, margin=7.8, lower=79.5, upper=95.1,
        confidence_level=0.95, sample_size=10, distribution="t-distribution",
    )
    s = str(ci)
    assert s == "87 ± 8"


def test_different_confidence_level():
    samples = [80, 90, 85, 88, 82]
    ci_90 = compute_confidence_interval(samples, confidence_level=0.90)
    ci_95 = compute_confidence_interval(samples, confidence_level=0.95)
    ci_99 = compute_confidence_interval(samples, confidence_level=0.99)
    assert ci_99.margin >= ci_95.margin >= ci_90.margin


# ---------------------------------------------------------------------------
# Negative / edge-case tests
# ---------------------------------------------------------------------------

def test_negative_values():
    samples = [-10, -20, -15]
    ci = compute_confidence_interval(samples)
    assert ci.mean == -15.0
    assert ci.margin > 0.0


def test_large_variance():
    samples = [10, 50, 90, 30, 70]
    ci = compute_confidence_interval(samples)
    assert ci.margin > 5.0


def test_zero_values():
    samples = [0, 0, 0]
    ci = compute_confidence_interval(samples)
    assert ci.mean == 0.0
    assert ci.margin == 0.0


def test_mixed_types():
    samples = [85.0, 87, 86.5, 88, 84.3]
    ci = compute_confidence_interval(samples)
    assert isinstance(ci.mean, float)
    assert ci.margin > 0.0


def test_exactly_thirty_samples():
    samples = [float(x) for x in range(30)]
    ci = compute_confidence_interval(samples, confidence_level=0.95)
    assert ci.sample_size == 30
    assert ci.distribution == "normal"


def test_twenty_nine_samples():
    samples = [float(x) for x in range(29)]
    ci = compute_confidence_interval(samples, confidence_level=0.95)
    assert ci.sample_size == 29
    assert ci.distribution == "t-distribution"


def test_t_critical_order():
    t5 = _t_critical(0.05, 5)
    t30 = _t_critical(0.05, 30)
    t100 = _t_critical(0.05, 100)
    assert t5 >= t30
    assert t30 >= t100
    assert t100 >= 1.9


def test_normal_critical_values():
    z01 = _normal_critical(0.01)
    z05 = _normal_critical(0.05)
    z10 = _normal_critical(0.10)
    assert abs(z01 - 2.576) < 0.01
    assert abs(z05 - 1.96) < 0.01
    assert abs(z10 - 1.645) < 0.01


# ---------------------------------------------------------------------------
# Integration-style tests
# ---------------------------------------------------------------------------

def test_phase_confidence_imports():
    from scripts.phases.phase_confidence import (
        collect_metric_samples,
        compute_all_intervals,
        format_intervals_report,
        phase_confidence,
    )
    assert callable(collect_metric_samples)
    assert callable(compute_all_intervals)
    assert callable(format_intervals_report)
    assert callable(phase_confidence)


def test_compute_all_intervals():
    from scripts.phases.phase_confidence import compute_all_intervals
    samples = {
        "security": [80, 85, 90],
        "resilience": [70, 75, 80],
    }
    intervals = compute_all_intervals(samples)
    assert "security" in intervals
    assert "resilience" in intervals
    for ci in intervals.values():
        assert isinstance(ci, SecurityConfidenceInterval)
        assert ci.lower < ci.upper


def test_format_intervals_report():
    from scripts.phases.phase_confidence import format_intervals_report
    ci = SecurityConfidenceInterval(
        mean=85, margin=5, lower=80, upper=90,
        confidence_level=0.95, sample_size=10, distribution="t-distribution",
    )
    intervals = {"test_score": ci}
    report = format_intervals_report(intervals)
    assert "Test Score" in report
    assert "85 ± 5" in report
    assert "n=10" in report
    assert "t-distribution" in report


def test_collect_metric_samples_no_files():
    from scripts.phases.phase_confidence import collect_metric_samples

    class FakeArgs:
        build_dir = "/tmp/nonexistent_opencode_test_dir"

    args = FakeArgs()
    samples = collect_metric_samples(args)
    assert isinstance(samples, dict)
    assert "default_security" in samples


def test_collect_metric_samples_with_files():
    from scripts.phases.phase_confidence import collect_metric_samples

    with tempfile.TemporaryDirectory() as tmpdir:
        surv_path = os.path.join(tmpdir, "survivability_report.json")
        with open(surv_path, "w") as f:
            json.dump({"combined_index": 0.85}, f)

        gate_path = os.path.join(tmpdir, "security_gate_report.json")
        with open(gate_path, "w") as f:
            json.dump({"results": [
                {"gate_name": "cfg_entropy", "score": 0.92},
                {"gate_name": "ai_resistance", "score": 0.78},
            ]}, f)

        class FakeArgs:
            build_dir = tmpdir

        args = FakeArgs()
        samples = collect_metric_samples(args)
        assert "survivability_index" in samples
        assert "gate_cfg_entropy" in samples
        assert "gate_ai_resistance" in samples
