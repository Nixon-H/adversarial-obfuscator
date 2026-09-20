import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.analyst_time import AnalystTimeEstimator


def test_estimate_returns_structured_result():
    estimator = AnalystTimeEstimator()
    orig = "x = 1\ny = 2\nz = x + y"
    prot = """
if 1:
    x = 1
else:
    x = 0
if True or False:
    y = 2
else:
    y = 0
z = x + y
"""
    result = estimator.estimate(orig, prot)
    assert "static_analysis_hours" in result
    assert "dynamic_analysis_hours" in result
    assert "deobfuscation_hours" in result
    assert "total_hours" in result
    assert result["total_hours"] > 0
    assert "confidence_interval" in result
    assert "cost_class" in result


def test_estimate_larger_protected_increases_hours():
    estimator = AnalystTimeEstimator()
    orig = "x = 1\ny = 2"
    simple_prot = "x = 1\ny = 2"
    complex_prot = """
if True:
    x = 1
else:
    x = 0
if False:
    y = 99
else:
    y = 2
if True or False:
    z = x + y
else:
    z = 0
"""
    r1 = estimator.estimate(orig, simple_prot)
    r2 = estimator.estimate(orig, complex_prot)
    assert r2["total_hours"] >= r1["total_hours"]


def test_cost_classification():
    estimator = AnalystTimeEstimator()
    orig = "x = 1"
    prot = """
if True:
    if False:
        if 1:
            pass
    else:
        x = 1
else:
    x = 0
"""
    result = estimator.estimate(orig, prot)
    assert result["cost_class"] in ("LOW", "MEDIUM", "HIGH", "EXTREME")


# Coffman-Macdiarmid model tests

def test_estimate_with_skill_junior():
    estimator = AnalystTimeEstimator()
    orig = "x = 1\ny = 2"
    prot = """
if True:
    x = 1
else:
    x = 0
y = 2
"""
    result = estimator.estimate_with_skill(orig, prot, skill_level="junior")
    assert "skill_level" in result
    assert result["skill_level"] == "junior"
    assert result["hourly_rate"] == 50.0
    assert "adjusted_hours" in result
    assert "estimated_cost" in result
    assert result["adjusted_hours"] >= result["total_hours"]


def test_estimate_with_skill_senior():
    estimator = AnalystTimeEstimator()
    orig = "x = 1"
    prot = "x = 1"
    result = estimator.estimate_with_skill(orig, prot, skill_level="senior")
    assert result["skill_level"] == "senior"
    assert result["hourly_rate"] == 200.0
    assert result["adjusted_hours"] <= result["total_hours"]


def test_estimate_with_skill_mid():
    estimator = AnalystTimeEstimator()
    orig = "x = 1"
    prot = "x = 1"
    result = estimator.estimate_with_skill(orig, prot, skill_level="mid")
    assert result["skill_level"] == "mid"
    assert result["hourly_rate"] == 100.0


def test_estimate_with_skill_has_coffman_factor():
    estimator = AnalystTimeEstimator()
    orig = "x = 1"
    prot = """
if True:
    if False:
        x = 1
    else:
        x = 0
"""
    result = estimator.estimate_with_skill(orig, prot, skill_level="mid")
    assert "coffman_factor" in result
    assert result["coffman_factor"] >= 1.0
    assert "cost_model_hours" in result


def test_estimate_with_skill_default_skill():
    estimator = AnalystTimeEstimator()
    orig = "x = 1"
    prot = "x = 1"
    result = estimator.estimate_with_skill(orig, prot)
    assert result["skill_level"] == "mid"
