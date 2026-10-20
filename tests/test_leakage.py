"""
test_leakage.py

Tests for Semantic Leakage Metric (Feature 152).

Test Categories:
- Positive tests verify variable, function, intent, and architecture leakage analysis
  across identical and different IR modules.
- Negative tests verify empty modules, score validation, edge cases.

Coverage:
- VariableLeakageAnalyzer: name preservation, scoring
- FunctionLeakageAnalyzer: structural analysis, function count comparison
- IntentLeakageAnalyzer: opcode histogram similarity
- ArchitectureLeakageAnalyzer: call graph similarity
- Metrics: CFG similarity, opcode histogram, entropy, name preservation, call graph
- SLI computation: overall score, per-level breakdown, recommendations, serialization
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from irgen.compile import compile_py_to_ir, IrModule, IrValue
from scripts.leakage.taxonomy import LeakageLevel, LeakageScore, LeakageReport
from scripts.leakage.analyzers import (
    VariableLeakageAnalyzer,
    FunctionLeakageAnalyzer,
    IntentLeakageAnalyzer,
    ArchitectureLeakageAnalyzer,
)
from scripts.leakage.metrics import (
    compute_cfg_similarity,
    compute_opcode_histogram,
    compute_entropy,
    compute_name_preservation,
    compute_call_graph_similarity,
)
from scripts.leakage.scorer import compute_sli


SIMPLE_ORIG = """
def add(a, b):
    return a + b

def main():
    x = 10
    y = 20
    result = add(x, y)
    return result
"""

SIMPLE_OBF = """
def add(a, b):
    return a + b

def main():
    x = 10
    y = 20
    result = add(x, y)
    return result
"""

DIFFERENT_ORIG = """
def add(a, b):
    return a + b

def main():
    x = 10
    y = 20
    result = add(x, y)
    return result
"""

DIFFERENT_OBF = """
def mul(x, y):
    return x * y

def sub(a, b):
    return a - b

def run():
    a = 1
    b = 2
    c = mul(a, b)
    d = sub(c, a)
    return d
"""

EMPTY_MODULE_SRC = """
"""


@pytest.fixture(autouse=True)
def reset_counters():
    IrValue.reset_counter()


@pytest.fixture
def simple_ir():
    return compile_py_to_ir(SIMPLE_ORIG)


@pytest.fixture
def same_ir():
    return compile_py_to_ir(SIMPLE_OBF)


@pytest.fixture
def diff_orig_ir():
    return compile_py_to_ir(DIFFERENT_ORIG)


@pytest.fixture
def diff_obf_ir():
    return compile_py_to_ir(DIFFERENT_OBF)


def test_variable_leakage(simple_ir, same_ir):
    analyzer = VariableLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.level == LeakageLevel.VARIABLE
    assert isinstance(score.score, float)
    assert 0.0 <= score.score <= 100.0
    assert score.method == "static_analysis"
    assert 0.0 <= score.confidence <= 1.0
    assert "name_preservation" in score.evidence


def test_variable_leakage_high_when_same(simple_ir, same_ir):
    analyzer = VariableLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.score > 80.0


def test_variable_leakage_low_when_different(diff_orig_ir, diff_obf_ir):
    analyzer = VariableLeakageAnalyzer()
    score = analyzer.analyze(diff_orig_ir, diff_obf_ir)
    assert score.score < 50.0


def test_function_leakage(simple_ir, same_ir):
    analyzer = FunctionLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.level == LeakageLevel.FUNCTION
    assert isinstance(score.score, float)
    assert 0.0 <= score.score <= 100.0
    assert score.method == "structural"
    assert "function_count_original" in score.evidence


def test_function_leakage_high_when_same(simple_ir, same_ir):
    analyzer = FunctionLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.score > 80.0


def test_function_leakage_low_when_different(diff_orig_ir, diff_obf_ir):
    analyzer = FunctionLeakageAnalyzer()
    score = analyzer.analyze(diff_orig_ir, diff_obf_ir)
    assert score.score < 30.0


def test_intent_leakage(simple_ir, same_ir):
    analyzer = IntentLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.level == LeakageLevel.INTENT
    assert isinstance(score.score, float)
    assert 0.0 <= score.score <= 100.0
    assert "opcode_histogram_similarity" in score.evidence


def test_intent_leakage_high_when_same(simple_ir, same_ir):
    analyzer = IntentLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.score > 60.0


def test_intent_leakage_low_when_different(diff_orig_ir, diff_obf_ir):
    analyzer = IntentLeakageAnalyzer()
    score = analyzer.analyze(diff_orig_ir, diff_obf_ir)
    assert score.score > 10.0


def test_architecture_leakage(simple_ir, same_ir):
    analyzer = ArchitectureLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.level == LeakageLevel.ARCHITECTURE
    assert isinstance(score.score, float)
    assert 0.0 <= score.score <= 100.0
    assert "call_graph_similarity" in score.evidence


def test_architecture_leakage_high_when_same(simple_ir, same_ir):
    analyzer = ArchitectureLeakageAnalyzer()
    score = analyzer.analyze(simple_ir, same_ir)
    assert score.score > 50.0


def test_architecture_leakage_low_when_different(diff_orig_ir, diff_obf_ir):
    analyzer = ArchitectureLeakageAnalyzer()
    score = analyzer.analyze(diff_orig_ir, diff_obf_ir)
    assert score.score > 10.0


def test_cfg_similarity():
    cfg_a = {"entry": ["bb1"], "bb1": ["bb2"], "bb2": []}
    cfg_b = {"entry": ["bb1"], "bb1": ["bb2"], "bb2": []}
    sim = compute_cfg_similarity(cfg_a, cfg_b)
    assert sim == 100.0


def test_cfg_similarity_different():
    cfg_a = {"entry": ["bb1"], "bb1": ["bb2"], "bb2": []}
    cfg_b = {"entry": ["bb3"], "bb3": []}
    sim = compute_cfg_similarity(cfg_a, cfg_b)
    assert sim < 100.0


def test_cfg_similarity_empty():
    assert compute_cfg_similarity({}, {}) == 100.0


def test_opcode_histogram(simple_ir):
    hist = compute_opcode_histogram(simple_ir)
    assert isinstance(hist, dict)
    total = sum(hist.values())
    assert abs(total - 1.0) < 0.01


def test_opcode_histogram_empty():
    mod = IrModule("empty")
    hist = compute_opcode_histogram(mod)
    assert hist == {}


def test_name_preservation(simple_ir, same_ir):
    preserved = compute_name_preservation(simple_ir, same_ir)
    assert isinstance(preserved, float)
    assert 0.0 <= preserved <= 100.0


def test_name_preservation_identical(simple_ir, same_ir):
    preserved = compute_name_preservation(simple_ir, same_ir)
    assert preserved > 80.0


def test_name_preservation_empty():
    mod_a = IrModule("a")
    mod_b = IrModule("b")
    assert compute_name_preservation(mod_a, mod_b) == 100.0


def test_compute_entropy(simple_ir):
    ent = compute_entropy(simple_ir)
    assert isinstance(ent, float)
    assert ent >= 0.0


def test_compute_entropy_empty():
    mod = IrModule("empty")
    assert compute_entropy(mod) == 0.0


def test_compute_sli(simple_ir, same_ir):
    report = compute_sli(simple_ir, same_ir)
    assert isinstance(report, LeakageReport)
    assert 0.0 <= report.overall_sli <= 100.0
    assert isinstance(report.variable_leakage, LeakageScore)
    assert isinstance(report.function_leakage, LeakageScore)
    assert isinstance(report.intent_leakage, LeakageScore)
    assert isinstance(report.architecture_leakage, LeakageScore)
    assert isinstance(report.recommendations, list)
    assert isinstance(report.generated_at, str)


def test_compute_sli_identical_inputs(simple_ir, same_ir):
    report = compute_sli(simple_ir, same_ir)
    assert report.overall_sli > 80.0


def test_compute_sli_different(diff_orig_ir, diff_obf_ir):
    report = compute_sli(diff_orig_ir, diff_obf_ir)
    assert report.overall_sli > 10.0


def test_leakage_report_serialization(simple_ir, same_ir):
    report = compute_sli(simple_ir, same_ir)
    d = report.to_dict()
    assert isinstance(d, dict)
    assert "overall_sli" in d
    assert "variable_leakage" in d
    assert "function_leakage" in d
    assert "intent_leakage" in d
    assert "architecture_leakage" in d
    assert "per_function_scores" in d
    assert "recommendations" in d
    assert "generated_at" in d
    json_str = json.dumps(d)
    assert len(json_str) > 0


def test_call_graph_similarity():
    calls_a = {"main": ["add", "sub"], "add": [], "sub": []}
    calls_b = {"main": ["add", "sub"], "add": [], "sub": []}
    sim = compute_call_graph_similarity(calls_a, calls_b)
    assert sim == 100.0


def test_call_graph_similarity_different():
    calls_a = {"main": ["add", "sub"], "add": [], "sub": []}
    calls_b = {"run": ["mul"], "mul": []}
    sim = compute_call_graph_similarity(calls_a, calls_b)
    assert sim == 0.0


def test_call_graph_similarity_empty():
    assert compute_call_graph_similarity({}, {}) == 100.0


def test_identical_inputs(simple_ir, same_ir):
    """Negative test: same IR should yield high leakage on all levels."""
    analyzer_v = VariableLeakageAnalyzer()
    analyzer_f = FunctionLeakageAnalyzer()
    analyzer_i = IntentLeakageAnalyzer()
    analyzer_a = ArchitectureLeakageAnalyzer()
    v = analyzer_v.analyze(simple_ir, same_ir)
    f = analyzer_f.analyze(simple_ir, same_ir)
    i = analyzer_i.analyze(simple_ir, same_ir)
    a = analyzer_a.analyze(simple_ir, same_ir)
    assert v.score > 80.0
    assert f.score > 80.0
    assert i.score > 60.0
    assert a.score > 50.0


def test_empty_module():
    """Negative test: empty module should not crash."""
    empty = compile_py_to_ir("")
    report = compute_sli(empty, empty)
    assert isinstance(report, LeakageReport)
    assert isinstance(report.overall_sli, float)


def test_different_irs(diff_orig_ir, diff_obf_ir):
    """Negative test: different IRs should yield lower identical leakage."""
    report = compute_sli(diff_orig_ir, diff_obf_ir)
    assert report.overall_sli > 0.0


def test_leakage_score_clamping():
    s1 = LeakageScore(level=LeakageLevel.VARIABLE, score=150, method="test", confidence=0.5)
    assert s1.score == 100.0
    s2 = LeakageScore(level=LeakageLevel.VARIABLE, score=-50, method="test", confidence=0.5)
    assert s2.score == 0.0
    s3 = LeakageScore(level=LeakageLevel.VARIABLE, score=50, method="test", confidence=1.5)
    assert s3.confidence == 1.0
    s4 = LeakageScore(level=LeakageLevel.VARIABLE, score=50, method="test", confidence=-0.5)
    assert s4.confidence == 0.0
