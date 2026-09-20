"""
bench_self_critique.py

Benchmarks for Self-Critique Engine (Feature 200+).

Measures critique question analysis and report generation performance.
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSelfCritiqueBenchmarks:
    @pytest.fixture
    def populated_dir(self):
        tmpdir = tempfile.mkdtemp()
        sdir = os.path.join(tmpdir, "scripts", "assumptions")
        mdir = os.path.join(tmpdir, "scripts", "metrics")
        pdir = os.path.join(tmpdir, "scripts", "proofs")
        tdir = os.path.join(tmpdir, "tests")
        bdir = os.path.join(tmpdir, "build")
        os.makedirs(sdir)
        os.makedirs(mdir)
        os.makedirs(pdir)
        os.makedirs(tdir)
        os.makedirs(bdir)

        with open(os.path.join(sdir, "registry.py"), "w") as f:
            for i in range(20):
                f.write(f'Assumption("F{i}", "dep", "software", required=True)\n')

        with open(os.path.join(mdir, "metric.py"), "w") as f:
            f.write("def compute():\n    return 42  # hardcoded\n")

        with open(os.path.join(pdir, "proof.py"), "w") as f:
            f.write("def prove():\n    return True\n")

        with open(os.path.join(tdir, "test_a.py"), "w") as f:
            f.write("class TestA:\n    pass\n")
        with open(os.path.join(tdir, "test_b.py"), "w") as f:
            f.write("class TestB1:\n    pass\nclass TestB2:\n    pass\n")

        with open(os.path.join(bdir, "evidence_report.json"), "w") as f:
            json.dump({
                "claim_coverage_pct": 60.0,
                "coverage_pct": 50.0,
                "claims_without_runtime_evidence": ["c1", "c2"],
            }, f)

        with open(os.path.join(tmpdir, "claim_validation.md"), "w") as f:
            f.write("## Claim 1\nEvidence: moderate\n## Claim 2\nEvidence: weak\n")

        yield tmpdir
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bench_evaluate(self, populated_dir, benchmark):
        from scripts.self_critique.engine import SelfCritiqueEngine

        def run():
            engine = SelfCritiqueEngine(populated_dir)
            return engine.evaluate()

        findings = benchmark(run)
        assert len(findings) == 6

    def test_bench_generate_report(self, populated_dir, benchmark):
        from scripts.self_critique.engine import SelfCritiqueEngine

        def run():
            engine = SelfCritiqueEngine(populated_dir)
            return engine.generate_report()

        report = benchmark(run)
        assert len(report.critiques) == 6

    def test_bench_generate_markdown(self, populated_dir, benchmark):
        from scripts.self_critique.engine import SelfCritiqueEngine

        engine = SelfCritiqueEngine(populated_dir)

        def run():
            return engine.generate_markdown()

        md = benchmark(run)
        assert "# Self-Critique Report" in md

    def test_bench_empty_dir(self, benchmark):
        from scripts.self_critique.engine import SelfCritiqueEngine

        def run():
            engine = SelfCritiqueEngine("/tmp/nonexistent_self_critique")
            return engine.generate_report()

        report = benchmark(run)
        assert len(report.critiques) == 6
