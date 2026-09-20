"""
bench_threat_coverage.py

Benchmarks for Threat Coverage Mapping (Feature 199).

Measures script scanning, metric scanning, and coverage matrix generation.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestThreatCoverageBenchmarks:
    @pytest.fixture
    def code_dir(self):
        tmpdir = tempfile.mkdtemp()
        sdir = os.path.join(tmpdir, "scripts")
        tdir = os.path.join(tmpdir, "tests")
        os.makedirs(sdir)
        os.makedirs(tdir)
        for i in range(30):
            with open(os.path.join(sdir, f"mod_{i}.py"), "w") as f:
                f.write(f"# obfuscation entropy proof module {i}\n")
        for i in range(20):
            with open(os.path.join(tdir, f"test_{i}.py"), "w") as f:
                f.write(f"# test for angr redteam proof coverage {i}\n")
        yield tmpdir
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bench_build_coverage(self, code_dir, benchmark):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper

        def run():
            mapper = ThreatCoverageMapper(code_dir)
            return mapper.build_coverage()

        cov = benchmark(run)
        assert len(cov) == 10

    def test_bench_coverage_matrix(self, code_dir, benchmark):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper

        mapper = ThreatCoverageMapper(code_dir)
        mapper.build_coverage()

        def run():
            return mapper.coverage_matrix()

        matrix = benchmark(run)
        assert len(matrix) == 10

    def test_bench_scan_scripts_for_features(self, code_dir, benchmark):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper

        mapper = ThreatCoverageMapper(code_dir)

        def run():
            mapper.scan_scripts_for_features()
            return len(mapper._features_cache)

        n = benchmark(run)
        assert n > 0

    def test_bench_empty_dir(self, benchmark):
        from scripts.threat_coverage.mapper import ThreatCoverageMapper

        def run():
            mapper = ThreatCoverageMapper("/tmp/nonexistent_threat")
            return mapper.build_coverage()

        cov = benchmark(run)
        assert len(cov) == 10
