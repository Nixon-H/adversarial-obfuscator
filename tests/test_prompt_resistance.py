"""Tests for Prompt Reconstruction Resistance (Item 77)."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.metrics.prompt_resistance import PromptResistanceMetrics


SIMPLE_ORIG = """
def add(a, b):
    return a + b
"""

SIMPLE_PROTECTED = """
def _nx_op_a1b2(x, y):
    return x + y
"""


def test_intent_obscurity_increases():
    m = PromptResistanceMetrics()
    low_obs = m.measure_intent_obscurity(SIMPLE_ORIG, SIMPLE_ORIG)
    high_obs = m.measure_intent_obscurity(SIMPLE_ORIG, SIMPLE_PROTECTED)
    assert high_obs >= low_obs, (
        f"Expected obscurity to increase, got {high_obs} vs {low_obs}"
    )


def test_semantic_recoverability_decreases():
    m = PromptResistanceMetrics()
    recoverable = m.measure_semantic_recoverability("def process(x): return x * 2")
    less_recoverable = m.measure_semantic_recoverability("def _nx_a1b2(b): return b * 2")
    assert less_recoverable <= recoverable + 1e-9


def test_prompt_resistance_score():
    m = PromptResistanceMetrics()
    score = m.compute_prompt_resistance_score(SIMPLE_ORIG, SIMPLE_PROTECTED)
    assert 0 <= score <= 100, f"Score {score} out of range"


def test_identity_transformation_low_resistance():
    m = PromptResistanceMetrics()
    score = m.compute_prompt_resistance_score(SIMPLE_ORIG, SIMPLE_ORIG)
    assert score < 50, (
        f"Identity transformation should give low resistance, got {score}"
    )


def test_different_code_higher_resistance():
    m = PromptResistanceMetrics()
    orig = """
def decrypt(data, key):
    result = data ^ key
    return result
"""
    obf = """
def compress_buffer(x_buf, y_tmp):
    _nx_gc = True
    _nx_ctx = x_buf ^ y_tmp
    return _nx_ctx
"""
    identity_score = m.compute_prompt_resistance_score(orig, orig)
    obf_score = m.compute_prompt_resistance_score(orig, obf)
    assert obf_score > identity_score, (
        f"Obfuscated {obf_score} should have higher resistance than identity {identity_score}"
    )


def test_measure_intent_obscurity_range():
    m = PromptResistanceMetrics()
    obs = m.measure_intent_obscurity(SIMPLE_ORIG, SIMPLE_PROTECTED)
    assert 0.0 <= obs <= 1.0


def test_measure_semantic_recoverability_range():
    m = PromptResistanceMetrics()
    rec = m.measure_semantic_recoverability(SIMPLE_ORIG)
    assert 0.0 <= rec <= 1.0
