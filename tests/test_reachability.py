"""
test_reachability.py

Tests for Feature Reachability Analysis (Feature 169).

Test coverage:
- Positive tests verify reachability status, CLI tracing, phase tracing
- Negative tests verify missing features, nonexistent flags, empty chains
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


from scripts.reachability.analyzer import (
    ReachabilityAnalyzer,
    ReachabilityReport,
    ReachabilityStatus,
    FeatureReachability,
)
from scripts.reachability.feature_map import ALL_FEATURES
from scripts.reachability import analyze_feature_reachability, generate_reachability_report


class TestReachabilityStatus:
    """
    Tests for the ReachabilityStatus enum values and membership.
    """
    def test_enum_values(self):
        assert ReachabilityStatus.REACHABLE.value == "REACHABLE"
        assert ReachabilityStatus.PARTIALLY_REACHABLE.value == "PARTIALLY_REACHABLE"
        assert ReachabilityStatus.UNREACHABLE.value == "UNREACHABLE"

    def test_enum_members(self):
        assert len(ReachabilityStatus) == 3


class TestFeatureReachability:
    """
    Tests for the FeatureReachability dataclass defaults and full fields.
    """
    def test_dataclass_defaults(self):
        fr = FeatureReachability(
            feature_name="test_feature",
            status=ReachabilityStatus.REACHABLE,
            cli_flag_found=True,
        )
        assert fr.feature_name == "test_feature"
        assert fr.status == ReachabilityStatus.REACHABLE
        assert fr.cli_flag_found is True
        assert fr.cli_flag_path == []
        assert fr.phase_found is False
        assert fr.import_chain == []
        assert fr.missing_links == []

    def test_dataclass_with_all_fields(self):
        fr = FeatureReachability(
            feature_name="full_feature",
            status=ReachabilityStatus.PARTIALLY_REACHABLE,
            cli_flag_found=False,
            cli_flag_path=["build.py:100"],
            phase_found=True,
            phase_path="build.py:200",
            import_chain=["mymod -> /path/to/mymod.py"],
            implementation_found=True,
            implementation_path="/path/to/mymod.py",
            runtime_paths=["/runtime/src/feature.rs"],
            test_files=["/tests/test_feature.py"],
            missing_links=["cli flag not found"],
        )
        assert fr.feature_name == "full_feature"
        assert len(fr.missing_links) == 1


class TestReachabilityReport:
    """
    Tests for ReachabilityReport counts, dict serialization.
    """
    def test_report_counts(self):
        features = {
            "a": FeatureReachability("a", ReachabilityStatus.REACHABLE, True),
            "b": FeatureReachability("b", ReachabilityStatus.PARTIALLY_REACHABLE, True),
            "c": FeatureReachability("c", ReachabilityStatus.UNREACHABLE, False),
        }
        report = ReachabilityReport(
            features=features,
            reachable_count=1,
            partially_reachable_count=1,
            unreachable_count=1,
            total_features=3,
            timestamp="2025-01-01T00:00:00+00:00",
        )
        assert report.reachable_count == 1
        assert report.partially_reachable_count == 1
        assert report.unreachable_count == 1
        assert report.total_features == 3

    def test_report_to_dict(self):
        features = {
            "test": FeatureReachability("test", ReachabilityStatus.REACHABLE, True),
        }
        report = ReachabilityReport(
            features=features,
            reachable_count=1,
            partially_reachable_count=0,
            unreachable_count=0,
            total_features=1,
            timestamp="2025-01-01T00:00:00+00:00",
        )
        d = report.to_dict()
        assert d["total_features"] == 1
        assert d["reachable_count"] == 1
        assert "test" in d["features"]
        assert d["features"]["test"]["status"] == "REACHABLE"


class TestReachabilityAnalyzer:
    """
    Tests for ReachabilityAnalyzer: CLI tracing, phase tracing,
    import chain resolution, runtime path discovery, and full analysis.
    """
    def test_init(self):
        analyzer = ReachabilityAnalyzer()
        assert analyzer.build_py_path is not None
        assert os.path.exists(analyzer.build_py_path)

    def test_trace_cli_flag_found(self):
        analyzer = ReachabilityAnalyzer()
        paths = analyzer.trace_cli_flag("--payload")
        assert len(paths) > 0
        for p in paths:
            assert "build.py" in p

    def test_trace_cli_flag_not_found(self):
        analyzer = ReachabilityAnalyzer()
        paths = analyzer.trace_cli_flag("--non-existent-flag-xyz-999")
        assert len(paths) == 0

    def test_trace_cli_flag_none(self):
        analyzer = ReachabilityAnalyzer()
        paths = analyzer.trace_cli_flag("")
        assert paths == []

    def test_trace_phase_found(self):
        analyzer = ReachabilityAnalyzer()
        path = analyzer.trace_phase("phase_obfuscate")
        assert path is not None
        assert "build.py" in path

    def test_trace_phase_not_found(self):
        analyzer = ReachabilityAnalyzer()
        path = analyzer.trace_phase("phase_nonexistent_xyz")
        assert path is None

    def test_trace_phase_none(self):
        analyzer = ReachabilityAnalyzer()
        path = analyzer.trace_phase("")
        assert path is None

    def test_trace_import_chain_resolvable(self):
        analyzer = ReachabilityAnalyzer()
        chain = analyzer.trace_import_chain("os")
        assert len(chain) > 0
        assert any("NOT FOUND" not in c for c in chain)

    def test_trace_import_chain_unresolvable(self):
        analyzer = ReachabilityAnalyzer()
        chain = analyzer.trace_import_chain("_nonexistent_module_xyz_999")
        assert len(chain) > 0
        assert any("NOT FOUND" in c or "ERROR" in c for c in chain)

    def test_trace_import_chain_none(self):
        analyzer = ReachabilityAnalyzer()
        chain = analyzer.trace_import_chain("")
        assert chain == []

    def test_trace_runtime_path_found(self):
        analyzer = ReachabilityAnalyzer()
        paths = analyzer.trace_runtime_path("cfg_mutation")
        assert isinstance(paths, list)

    def test_trace_runtime_path_not_found(self):
        analyzer = ReachabilityAnalyzer()
        paths = analyzer.trace_runtime_path("nonexistent_feature_xyz")
        assert isinstance(paths, list)

    def test_find_test_files(self):
        analyzer = ReachabilityAnalyzer()
        files = analyzer.find_test_files("obfuscation")
        assert isinstance(files, list)

    def test_find_test_files_unknown(self):
        analyzer = ReachabilityAnalyzer()
        files = analyzer.find_test_files("_nonexistent_xyz")
        assert isinstance(files, list)

    def test_analyze_feature_obfuscation(self):
        analyzer = ReachabilityAnalyzer()
        fr = analyzer.analyze_feature("obfuscation")
        assert fr.feature_name == "obfuscation"
        assert isinstance(fr.status, ReachabilityStatus)
        assert isinstance(fr.cli_flag_found, bool)

    def test_analyze_feature_with_no_metadata(self):
        analyzer = ReachabilityAnalyzer()
        fr = analyzer.analyze_feature("_nonexistent", cli_flag=None, phase_name=None, implementation_module=None)
        assert fr.feature_name == "_nonexistent"
        assert fr.status in (ReachabilityStatus.PARTIALLY_REACHABLE, ReachabilityStatus.UNREACHABLE)

    def test_analyze_all_features(self):
        analyzer = ReachabilityAnalyzer()
        results = analyzer.analyze_all_features()
        assert len(results) >= 50
        for name, fr in results.items():
            assert isinstance(fr, FeatureReachability)
            assert fr.feature_name == name

    def test_generate_report(self):
        analyzer = ReachabilityAnalyzer()
        report = analyzer.generate_report()
        assert isinstance(report, ReachabilityReport)
        assert report.total_features >= 50
        total = report.reachable_count + report.partially_reachable_count + report.unreachable_count
        assert total == report.total_features


class TestReachabilityIntegration:
    """
    Integration tests for reachability functions and report file output.
    """
    def test_analyze_feature_reachability_function(self):
        result = analyze_feature_reachability("obfuscation")
        assert isinstance(result, dict)
        assert result["feature_name"] == "obfuscation"
        assert "status" in result
        assert "cli_flag_found" in result

    def test_generate_reachability_report_function(self):
        report = generate_reachability_report()
        assert isinstance(report, ReachabilityReport)
        assert report.total_features >= 50

    def test_phase_reachability_output_files(self):
        from scripts.reachability.analyzer import ReachabilityAnalyzer
        from scripts.common import BUILD_DIR, atomic_write
        analyzer = ReachabilityAnalyzer()
        report = analyzer.generate_report()
        report_path = os.path.join(BUILD_DIR, "reachability_report.json")
        os.makedirs(BUILD_DIR, exist_ok=True)
        atomic_write(report_path, json.dumps(report.to_dict(), indent=2))
        summary_path = os.path.join(BUILD_DIR, "reachability_summary.txt")
        lines = [
            f"Total features:   {report.total_features}",
            f"REACHABLE:        {report.reachable_count}",
            f"PARTIALLY:        {report.partially_reachable_count}",
            f"UNREACHABLE:      {report.unreachable_count}",
        ]
        atomic_write(summary_path, "\n".join(lines))
        assert os.path.exists(report_path)
        assert os.path.exists(summary_path)
        with open(report_path) as f:
            data = json.load(f)
        assert "features" in data
        assert data["total_features"] >= 50

    def test_phase_reachability_with_tempdir(self):
        from scripts.reachability.analyzer import ReachabilityAnalyzer
        with tempfile.TemporaryDirectory() as tmpdir:
            import scripts.common as _sc
            orig = _sc.BUILD_DIR
            try:
                _sc.BUILD_DIR = tmpdir
                analyzer = ReachabilityAnalyzer()
                report = analyzer.generate_report()
                report_path = os.path.join(tmpdir, "reachability_report.json")
                with open(report_path, "w") as f:
                    f.write(json.dumps(report.to_dict(), indent=2))
                assert os.path.exists(report_path)
                with open(report_path) as f:
                    data = json.load(f)
                assert "features" in data
            finally:
                _sc.BUILD_DIR = orig


class TestFeatureMap:
    """
    Tests for the ALL_FEATURES registry structure and content.
    """
    def test_all_features_count(self):
        assert len(ALL_FEATURES) >= 50

    def test_all_features_structure(self):
        for name, info in ALL_FEATURES.items():
            assert isinstance(name, str)
            assert isinstance(info, dict)
            assert len(name) > 0

    def test_feature_has_at_least_one_link(self):
        for name, info in ALL_FEATURES.items():
            has_cli = info.get("cli_flag") is not None
            has_phase = info.get("phase_name") is not None
            has_impl = info.get("impl_module") is not None
            has_runtime = info.get("runtime_file") is not None
            has_test = info.get("test_file") is not None
            assert has_cli or has_phase or has_impl or has_runtime or has_test, (
                f"Feature '{name}' has no reachability links"
            )

    def test_obfuscation_feature(self):
        info = ALL_FEATURES["obfuscation"]
        assert info["cli_flag"] == "--skip-obfuscate"
        assert info["phase_name"] == "phase_obfuscate"
        assert info["impl_module"] is not None

    def test_cfg_mutation_feature(self):
        info = ALL_FEATURES["cfg_mutation"]
        assert info["cli_flag"] == "--cfg-mutation"
        assert info["runtime_file"] == "cfg_mutation.rs"

    def test_reachability_report_consistency(self):
        report = generate_reachability_report()
        feature_names = set(report.features.keys())
        map_names = set(ALL_FEATURES.keys())
        assert feature_names == map_names
