"""Tests for Context Window Saturation Metrics (Item 76)."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.metrics.context_saturation import ContextSaturationMetrics


SIMPLE_CODE = """
def add(a, b):
    return a + b
"""

POISONED_CODE = """
def add(a, b):
    _nx_gc_enabled = True
    _nx_crypto_init = True
    _nx_vm_ready = True
    _nx_license_valid = True
    _nx_hw_bound = True
    _nx_self_check = True
    _nx_integrity_ok = True
    _nx_tamper_protect = True
    _nx_debug_mode = True
    _nx_fork_safe = True
    _nx_dc_0_1234 = 42
    _nx_dc_1_5678 = _nx_dc_0_1234 ^ 3
    _nx_dc_2_9012 = _nx_dc_1_5678 + 7
    _nx_dc_3_3456 = _nx_dc_2_9012 & 15
    _nx_dc_4_7890 = _nx_dc_3_3456 | 31
    if not _nx_gc_enabled:
        pass
    if not _nx_crypto_init:
        pass
    if not _nx_vm_ready:
        pass
    if not _nx_license_valid:
        pass
    if not _nx_hw_bound:
        pass
    if 42 * 7 + 42 == 42 * (7 + 1):
        if 12 * 9 + 12 == 12 * (9 + 1):
            if 88 * 3 + 88 == 88 * (3 + 1):
                try:
                    return a + b
                except Exception:
                    pass
    return a + b
"""


def test_token_utilization_higher_for_poisoned():
    m = ContextSaturationMetrics()
    simple_util = m.measure_token_utilization(SIMPLE_CODE)
    poisoned_util = m.measure_token_utilization(POISONED_CODE)
    assert poisoned_util > simple_util, (
        f"Poisoned {poisoned_util} should be > simple {simple_util}"
    )


def test_attention_degradation():
    m = ContextSaturationMetrics()
    simple_deg = m.measure_attention_degradation(SIMPLE_CODE)
    poisoned_deg = m.measure_attention_degradation(POISONED_CODE)
    assert poisoned_deg > simple_deg, (
        f"Poisoned {poisoned_deg} should be > simple {simple_deg}"
    )


def test_context_collapse():
    m = ContextSaturationMetrics()
    simple_coll = m.measure_context_collapse(SIMPLE_CODE)
    poisoned_coll = m.measure_context_collapse(POISONED_CODE)
    assert poisoned_coll > simple_coll, (
        f"Poisoned {poisoned_coll} should be > simple {simple_coll}"
    )


def test_saturation_score_range():
    m = ContextSaturationMetrics()
    score = m.compute_saturation_score(SIMPLE_CODE)
    assert 0 <= score <= 100, f"Score {score} out of range"
    poisoned_score = m.compute_saturation_score(POISONED_CODE)
    assert 0 <= poisoned_score <= 100
    assert poisoned_score >= score, (
        f"Poisoned {poisoned_score} should be >= simple {score}"
    )


def test_zero_code():
    m = ContextSaturationMetrics()
    util = m.measure_token_utilization("")
    assert 0.0 <= util <= 1.0
    deg = m.measure_attention_degradation("")
    assert 0.0 <= deg <= 1.0
    coll = m.measure_context_collapse("")
    assert 0.0 <= coll <= 1.0
    score = m.compute_saturation_score("")
    assert 0 <= score <= 100
