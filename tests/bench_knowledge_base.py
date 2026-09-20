"""
bench_knowledge_base.py

Benchmarks for Security Knowledge Base (Feature 200).

Measures scanning speed for assumptions, failures, and attack history.
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestKnowledgeBaseBenchmarks:
    @pytest.fixture
    def kb_dir(self):
        tmpdir = tempfile.mkdtemp()
        sdir = os.path.join(tmpdir, "scripts", "assumptions")
        tdir = os.path.join(tmpdir, "tests")
        bdir = os.path.join(tmpdir, "build")
        os.makedirs(sdir)
        os.makedirs(tdir)
        os.makedirs(bdir)

        with open(os.path.join(sdir, "registry.py"), "w") as f:
            for i in range(50):
                f.write(f'Assumption("F{i}", "dep_{i}", "software", required=True)\n')

        for i in range(20):
            with open(os.path.join(tdir, f"test_{i}.py"), "w") as f:
                f.write(f"def test_{i}():\n    assert False  # fail\n")

        with open(os.path.join(bdir, "proof_coverage_report.json"), "w") as f:
            json.dump({"overall_coverage": 100.0}, f)

        with open(os.path.join(tmpdir, "attack_report.md"), "w") as f:
            for i in range(10):
                f.write(f"## F{i}: Feature {i}\n...\n")

        yield tmpdir
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bench_build(self, kb_dir, benchmark):
        from scripts.knowledge_base.database import SecurityKnowledgeBase

        def run():
            kb = SecurityKnowledgeBase(kb_dir)
            kb.build()
            return len(kb.entries)

        count = benchmark(run)
        assert count > 0

    def test_bench_by_category(self, kb_dir, benchmark):
        from scripts.knowledge_base.database import SecurityKnowledgeBase

        kb = SecurityKnowledgeBase(kb_dir)
        kb.build()

        def run():
            return kb.by_category()

        cats = benchmark(run)
        assert isinstance(cats, dict)

    def test_bench_knowledge_coverage(self, kb_dir, benchmark):
        from scripts.knowledge_base.database import SecurityKnowledgeBase

        kb = SecurityKnowledgeBase(kb_dir)
        kb.build()

        def run():
            return kb.knowledge_coverage()

        kc = benchmark(run)
        assert "coverage_pct" in kc

    def test_bench_empty_dir(self, benchmark):
        from scripts.knowledge_base.database import SecurityKnowledgeBase

        def run():
            kb = SecurityKnowledgeBase("/tmp/nonexistent_kb")
            kb.build()
            return len(kb.entries)

        count = benchmark(run)
        assert count == 0
