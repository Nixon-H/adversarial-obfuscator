"""
test_threat_coverage.py

Tests for Threat Coverage Mapping (Feature 199).

Test coverage:
- Positive tests verify script scanning, metric scanning, verification scanning, coverage matrix
- Negative tests verify no scripts dir, no tests dir, partial coverage, zero score
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestThreatCoverageMapper:
    """
    TestThreatCoverageMapper
    
    Positive test cases for threatcoveragemapper.
    """
    def test_scan_scripts_finds_features(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts")
            os.makedirs(sdir)
            fpath = os.path.join(sdir, "obfuscator.py")
            with open(fpath, "w") as f:
                f.write("def obfuscate():\n    pass\n")
            mapper = ThreatCoverageMapper(td)
            mapper.scan_scripts_for_features()
            feats = mapper._features_cache.get("reverse_engineering", set())
            assert len(feats) >= 1

    def test_scan_for_metrics(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts")
            os.makedirs(sdir)
            fpath = os.path.join(sdir, "entropy.py")
            with open(fpath, "w") as f:
                f.write("# entropy metric\n")
            mapper = ThreatCoverageMapper(td)
            mapper.scan_for_metrics()
            metrics = mapper._metrics_cache.get("reverse_engineering", set())
            assert len(metrics) >= 1

    def test_scan_for_verifications(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            tdir = os.path.join(td, "tests")
            os.makedirs(tdir)
            fpath = os.path.join(tdir, "test_redteam.py")
            with open(fpath, "w") as f:
                f.write("# test for angr analysis\n")
            mapper = ThreatCoverageMapper(td)
            mapper.scan_for_verifications()
            verifs = mapper._verifications_cache.get("reverse_engineering", set())
            assert len(verifs) >= 1

    def test_build_coverage(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts")
            tdir = os.path.join(td, "tests")
            os.makedirs(sdir)
            os.makedirs(tdir)
            with open(os.path.join(sdir, "obfuscator.py"), "w") as f:
                f.write("# obfuscation\n")
            with open(os.path.join(sdir, "entropy.py"), "w") as f:
                f.write("# entropy metric\n")
            with open(os.path.join(tdir, "test_redteam.py"), "w") as f:
                f.write("# angr test\n")
            mapper = ThreatCoverageMapper(td)
            cov = mapper.build_coverage()
            assert len(cov) == 10

    def test_get_uncovered_threats(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            mapper = ThreatCoverageMapper(td)
            mapper.build_coverage()
            uncovered = mapper.get_uncovered_threats()
            assert isinstance(uncovered, list)
            if uncovered:
                assert "missing" in uncovered[0]

    def test_coverage_score(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            mapper = ThreatCoverageMapper(td)
            mapper.build_coverage()
            score = mapper.coverage_score()
            assert 0.0 <= score <= 100.0

    def test_coverage_matrix(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts")
            tdir = os.path.join(td, "tests")
            os.makedirs(sdir)
            os.makedirs(tdir)
            with open(os.path.join(sdir, "obfuscator.py"), "w") as f:
                f.write("# obfuscation\n")
            with open(os.path.join(sdir, "entropy.py"), "w") as f:
                f.write("# entropy\n")
            with open(os.path.join(tdir, "test_redteam.py"), "w") as f:
                f.write("# angr\n")
            mapper = ThreatCoverageMapper(td)
            mapper.build_coverage()
            matrix = mapper.coverage_matrix()
            assert len(matrix) == 10

    def test_map_threat_coverage_function(self):
        from scripts.threat_coverage.mapper import map_threat_coverage
        result = map_threat_coverage()
        assert "threat_map" in result
        assert "coverage_score" in result
        assert "uncovered_threats" in result
        assert isinstance(result["threat_map"], list)

    def test_coverage_entry_dataclass(self):
        from scripts.threat_coverage.mapper import CoverageEntry
        entry = CoverageEntry(
            threat="reverse_engineering",
            features=["obfuscator.py"],
            metrics=["entropy.py"],
            verifications=["test_redteam.py"],
        )
        assert entry.is_covered() is True
        d = entry.to_dict()
        assert d["threat"] == "reverse_engineering"


class TestThreatCoverageNegative:
    """
    TestThreatCoverageNegative
    
    Negative test cases — exercises error handling and edge cases for threatcoveragenegative.
    """
    def test_no_scripts_dir(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            mapper = ThreatCoverageMapper(td)
            cov = mapper.build_coverage()
            assert len(cov) == 10
            assert all(not e.is_covered() for e in cov)

    def test_no_tests_dir(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts")
            os.makedirs(sdir)
            mapper = ThreatCoverageMapper(td)
            mapper.build_coverage()
            for entry in mapper.coverage:
                assert not entry.verifications

    def test_partial_coverage(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts")
            os.makedirs(sdir)
            with open(os.path.join(sdir, "obfuscator.py"), "w") as f:
                f.write("# obfuscation\n")
            mapper = ThreatCoverageMapper(td)
            mapper.build_coverage()
            re_entry = [e for e in mapper.coverage if e.threat == "reverse_engineering"]
            if re_entry:
                assert bool(re_entry[0].features)  # has features
                assert not re_entry[0].metrics  # no metrics

    def test_coverage_score_zero_when_empty(self):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper
        mapper = ThreatCoverageMapper()
        mapper.coverage = []
        assert mapper.coverage_score() == 0.0
