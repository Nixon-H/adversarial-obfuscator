"""
test_assumptions.py

Tests for Assumption Tracking (Feature 171).

Test coverage:
- Positive tests verify assumption registration, checking, and reporting
- Negative tests verify empty caps, weird names, no-double-register
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.assumptions import (
    Assumption,
    AssumptionReport,
    AssumptionTracker,
    build_assumption_report,
    check_assumptions,
)
from scripts.assumptions.registry import FEATURE_ASSUMPTIONS, register_all


class TestAssumptionDataclass:
    """
    Tests for Assumption dataclass defaults, custom values, and dict output.
    """
    def test_assumption_defaults(self):
        a = Assumption(feature="test", assumption="needs X", assumption_type="OS")
        assert a.feature == "test"
        assert a.assumption == "needs X"
        assert a.assumption_type == "OS"
        assert a.required is True
        assert a.checked_at_runtime is False
        assert a.satisfied is None
        assert a.evidence is None

    def test_assumption_custom_values(self):
        a = Assumption(
            feature="SGX", assumption="Linux", assumption_type="OS",
            required=True, checked_at_runtime=True,
            satisfied=True, evidence="os=linux",
        )
        assert a.satisfied is True
        assert a.evidence == "os=linux"

    def test_assumption_to_dict(self):
        a = Assumption("F", "A", "HW", False)
        d = a.to_dict()
        assert d["feature"] == "F"
        assert d["assumption"] == "A"
        assert d["assumption_type"] == "HW"
        assert d["required"] is False
        assert d["satisfied"] is None


class TestAssumptionReport:
    """
    Tests for AssumptionReport counting, critical unsatisfied detection, and serialization.
    """
    def test_empty_report(self):
        r = AssumptionReport()
        assert r.total_count == 0
        assert r.satisfied_count == 0
        assert r.unsatisfied_count == 0
        assert r.unknown_count == 0
        assert r.critical_unsatisfied == []

    def test_report_counts(self):
        assumptions = [
            Assumption("F1", "A1", "OS", True, satisfied=True),
            Assumption("F2", "A2", "HW", True, satisfied=False),
            Assumption("F3", "A3", "SW", False, satisfied=None),
        ]
        r = AssumptionReport(assumptions=assumptions)
        assert r.total_count == 3
        assert r.satisfied_count == 1
        assert r.unsatisfied_count == 1
        assert r.unknown_count == 1
        assert len(r.critical_unsatisfied) == 1
        assert r.critical_unsatisfied[0].assumption == "A2"

    def test_report_no_critical_when_not_required(self):
        assumptions = [
            Assumption("F1", "A1", "OS", required=False, satisfied=False),
        ]
        r = AssumptionReport(assumptions=assumptions)
        assert r.critical_unsatisfied == []

    def test_report_to_dict(self):
        assumptions = [Assumption("F", "A", "OS")]
        r = AssumptionReport(assumptions=assumptions)
        d = r.to_dict()
        assert d["total_count"] == 1
        assert "timestamp" in d
        assert d["assumptions"][0]["feature"] == "F"

    def test_report_to_json(self):
        r = AssumptionReport()
        j = r.to_json()
        assert isinstance(j, str)
        d = json.loads(j)
        assert d["total_count"] == 0


class TestAssumptionTracker:
    """
    Tests for AssumptionTracker: registration, querying, runtime checking, report building.
    """
    def test_init(self):
        t = AssumptionTracker()
        assert t._assumptions == {}

    def test_register_assumption(self):
        t = AssumptionTracker()
        a = t.register_assumption("F1", "needs X", "OS")
        assert isinstance(a, Assumption)
        assert a.feature == "F1"
        assert len(t._assumptions["F1"]) == 1

    def test_register(self):
        t = AssumptionTracker()
        a = Assumption("F", "A", "HW")
        t.register(a)
        assert len(t._assumptions["F"]) == 1

    def test_get_feature_assumptions(self):
        t = AssumptionTracker()
        t.register_assumption("F1", "A1", "OS")
        t.register_assumption("F1", "A2", "HW")
        t.register_assumption("F2", "A3", "SW")
        assert len(t.get_feature_assumptions("F1")) == 2
        assert len(t.get_feature_assumptions("F2")) == 1
        assert t.get_feature_assumptions("F3") == []

    def test_get_critical_assumptions(self):
        t = AssumptionTracker()
        t.register_assumption("F1", "A1", "OS", required=True)
        t.register_assumption("F1", "A2", "HW", required=False)
        critical = t.get_critical_assumptions()
        assert len(critical) == 1
        assert critical[0].assumption == "A1"

    def test_to_dict(self):
        t = AssumptionTracker()
        t.register_assumption("F1", "A1", "OS")
        d = t.to_dict()
        assert "F1" in d
        assert d["F1"][0]["assumption"] == "A1"

    def test_build_report(self):
        t = AssumptionTracker()
        t.register(Assumption("F1", "A1", "OS", satisfied=True))
        t.register(Assumption("F2", "A2", "HW", satisfied=False))
        r = t.build_report()
        assert r.total_count == 2
        assert r.satisfied_count == 1
        assert r.unsatisfied_count == 1

    def test_check_assumptions_os_linux(self):
        t = AssumptionTracker()
        t.register_assumption("Kernel", "Linux", "OS")
        caps = {"os": {"system": "linux", "machine": "x86_64"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("Kernel")[0]
        assert a.satisfied is True
        assert a.checked_at_runtime is True

    def test_check_assumptions_os_not_linux(self):
        t = AssumptionTracker()
        t.register_assumption("SGX", "Linux", "OS")
        caps = {"os": {"system": "windows", "machine": "amd64"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("SGX")[0]
        assert a.satisfied is False

    def test_check_assumptions_x86_64_match(self):
        t = AssumptionTracker()
        t.register_assumption("SIMD", "x86_64", "hardware")
        caps = {"os": {"system": "linux", "machine": "x86_64"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("SIMD")[0]
        assert a.satisfied is True

    def test_check_assumptions_x86_64_no_match(self):
        t = AssumptionTracker()
        t.register_assumption("SIMD", "x86_64", "hardware")
        caps = {"os": {"system": "linux", "machine": "aarch64"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("SIMD")[0]
        assert a.satisfied is False

    def test_check_assumptions_direct_key(self):
        t = AssumptionTracker()
        t.register_assumption("GPU", "gpu_hardware", "hardware")
        caps = {"gpu_hardware": True, "os": {"system": "linux"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("GPU")[0]
        assert a.satisfied is True
        assert a.evidence == "True"

    def test_check_assumptions_python_module(self):
        t = AssumptionTracker()
        t.register_assumption("FHE", "python3", "software")
        caps = {"os": {"system": "linux"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("FHE")[0]
        assert a.satisfied is True  # sys always exists

    def test_check_assumptions_unknown(self):
        t = AssumptionTracker()
        t.register_assumption("Unknown", "bogus_thing", "runtime")
        caps = {"os": {"system": "linux"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("Unknown")[0]
        assert a.satisfied is None
        assert a.evidence == "not_checked"


class TestRegistry:
    """
    Tests for the FEATURE_ASSUMPTIONS registry and build_assumption_report.
    """
    def test_feaure_assumptions_has_30_plus_features(self):
        assert len(FEATURE_ASSUMPTIONS) >= 30

    def test_each_feature_has_assumptions(self):
        for feature, assumptions in FEATURE_ASSUMPTIONS.items():
            assert len(assumptions) >= 1, f"{feature} has no assumptions"

    def test_fhe_vm_has_assumptions(self):
        assert "FHE-VM" in FEATURE_ASSUMPTIONS
        assumptions = FEATURE_ASSUMPTIONS["FHE-VM"]
        assert any("python3" in a.assumption for a in assumptions)

    def test_sgx_has_linux_assumption(self):
        assert "SGX" in FEATURE_ASSUMPTIONS
        assumptions = FEATURE_ASSUMPTIONS["SGX"]
        assert any("Linux" in a.assumption for a in assumptions)

    def test_kernel_assist_has_linux_assumption(self):
        assert "Kernel-Assist" in FEATURE_ASSUMPTIONS
        assumptions = FEATURE_ASSUMPTIONS["Kernel-Assist"]
        assert any("Linux" in a.assumption for a in assumptions)

    def test_register_all_populates_tracker(self):
        t = AssumptionTracker()
        register_all(t)
        total = sum(len(v) for v in FEATURE_ASSUMPTIONS.values())
        tracked = sum(len(v) for v in t._assumptions.values())
        assert tracked == total

    def test_build_assumption_report_no_caps(self):
        r = build_assumption_report()
        assert isinstance(r, AssumptionReport)
        assert r.total_count > 0

    def test_build_assumption_report_with_caps(self):
        caps = {"os": {"system": "linux", "machine": "x86_64"}}
        r = build_assumption_report(caps)
        assert isinstance(r, AssumptionReport)
        assert r.total_count > 0

    def test_check_assumptions_function(self):
        caps = {"os": {"system": "linux", "machine": "x86_64"}}
        r = check_assumptions(caps)
        assert isinstance(r, AssumptionReport)

    def test_critical_unsatisfied_includes_required_false(self):
        t = AssumptionTracker()
        t.register_assumption("T", "gpu_hardware", "hardware", required=True)
        t.register_assumption("T", "some_optional", "HW", required=False)
        caps = {"os": {"system": "linux"}, "gpu_hardware": False}
        t.check_assumptions(caps)
        r = t.build_report()
        assert len(r.critical_unsatisfied) == 1
        assert r.critical_unsatisfied[0].assumption == "gpu_hardware"


class TestNegative:
    """
    Negative tests: double registration, empty capabilities, weird names.
    """
    def test_negative_no_double_register(self):
        t = AssumptionTracker()
        t.register_assumption("F", "A", "OS")
        t.register_assumption("F", "A", "OS")
        assert len(t.get_feature_assumptions("F")) == 2

    def test_negative_empty_caps(self):
        t = AssumptionTracker()
        t.register_assumption("F", "x86_64", "hardware")
        t.check_assumptions({})
        a = t.get_feature_assumptions("F")[0]
        assert a.checked_at_runtime is True
        assert a.satisfied is False

    def test_negative_weird_assumption_name(self):
        t = AssumptionTracker()
        t.register_assumption("F", "!!! weird name !!!", "OS")
        caps = {"os": {"system": "linux"}}
        t.check_assumptions(caps)
        a = t.get_feature_assumptions("F")[0]
        assert a.satisfied is None  # no match rule
