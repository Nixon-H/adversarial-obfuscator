"""Tests for feature classification (Phase 5).

The classifier used to return "IMPLEMENTED" for every feature and
report 126 implemented / 3 partial, on evidence no stronger than a
filename match.  These tests pin the replacement contract: independent
evidence dimensions, a verdict that names the gap, and no LIVE verdict
without artefact evidence.
"""
import json
import os
import sys
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CLASSES = ("LIVE", "LIVE (unverified)", "ENABLED-UNEXERCISED",
           "GATED-OFF", "COMPILED-UNREACHABLE", "DEAD CODE")


def _report():
    result = subprocess.run(
        [sys.executable, "scripts/classify_features.py", "--json"],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


class TestClassifyFeatures:
    def test_classify_script_runs(self):
        result = subprocess.run(
            [sys.executable, "scripts/classify_features.py", "--report"],
            capture_output=True, text=True, timeout=180,
        )
        assert result.returncode == 0

    def test_classify_script_outputs_json(self):
        out_path = os.path.join(tempfile.gettempdir(), "test_feature_classification.json")
        try:
            result = subprocess.run(
                [sys.executable, "scripts/classify_features.py", "--output", out_path],
                capture_output=True, text=True, timeout=180,
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
        report = _report()
        assert len(report["features"]) == 129
        for f in report["features"]:
            assert f["classification"] in CLASSES, \
                f"Item {f['id']} has invalid classification: {f['classification']}"

    def test_every_feature_has_five_dimensions(self):
        report = _report()
        for f in report["features"]:
            ev = f["evidence"]
            for dim in ("implemented", "compiled", "reachable", "enabled", "exercised"):
                assert dim in ev, f"Item {f['id']} missing dimension {dim}"

    def test_no_live_without_a_manifest(self):
        """Without artefact evidence nothing may be reported LIVE."""
        report = _report()
        if report.get("artefact_manifest"):
            return
        live = [f["id"] for f in report["features"] if f["classification"] == "LIVE"]
        assert live == [], f"LIVE claimed with no artefact evidence: {live}"

    def test_live_requires_exercised_true(self):
        report = _report()
        for f in report["features"]:
            if f["classification"] == "LIVE":
                assert f["evidence"]["exercised"] is True, \
                    f"Item {f['id']} LIVE but not exercised"

    def test_not_everything_is_implemented(self):
        """The old classifier returned 126/129 IMPLEMENTED. Guard that
        regression: a report where everything is LIVE is a name list."""
        report = _report()
        live = sum(1 for f in report["features"] if f["classification"] == "LIVE")
        assert live < 129

    def test_summary_totals(self):
        s = _report()["summary"]
        total = sum(s.get(k, 0) for k in (
            "live", "live_unverified", "enabled-unexercised",
            "gated-off", "compiled-unreachable", "dead_code"))
        assert total == 129, f"Sum of categories ({total}) != 129"


class TestArchivedRuntimeFeatures:
    """The Runtime Evolution features were compiled, gated by a flag that
    RuntimeConfig::default left false, and set by nothing. They are
    archived now — no module, no handler, no flag — so the report must
    call them dead rather than "a flag with that name exists"."""

    ARCHIVED = {53, 80, 81, 83, 84, 85, 86}

    def test_they_are_reported_dead(self):
        report = _report()
        dead = {f["id"] for f in report["features"] if f["classification"] == "DEAD CODE"}
        assert self.ARCHIVED <= dead, \
            f"expected {sorted(self.ARCHIVED)} dead, got {sorted(dead)}"

    def test_the_reason_names_the_archived_module(self):
        report = _report()
        for f in report["features"]:
            if f["id"] in self.ARCHIVED:
                assert "archived" in f["reason"], f"Item {f['id']}: {f['reason']}"

    def test_nothing_is_gated_off_any_more(self):
        """GATED-OFF meant "compiled, flag false, nothing sets it" — the
        state these seven were in. With them gone the category is empty."""
        report = _report()
        off = [f["id"] for f in report["features"] if f["classification"] == "GATED-OFF"]
        assert off == [], f"still gated off: {off}"


class TestWiredDetection:
    """Flags consumed through the opts namespace in a phase module, or
    through a helper named after them, must not be reported unwired.

    Regression guard: an early version checked only ``opts.<name>`` in
    build.py and reported eight genuinely wired flags as unwired.
    """

    WIRED = ("--fragment-strings", "--unicode-ids", "--advanced-protection",
             "--phase2", "--include-original", "--phase2-extras",
             "--data-obfuscation", "--llm-resilient", "--adversarial-level")

    def test_known_wired_flags_are_wired(self):
        from scripts import classify_features as cf
        unwired = [f for f in self.WIRED if not cf.wired(f)]
        assert unwired == [], f"reported unwired but consumed: {unwired}"

    def test_nonexistent_flag_is_not_wired(self):
        from scripts import classify_features as cf
        assert cf.wired("--definitely-not-a-real-flag") is False
