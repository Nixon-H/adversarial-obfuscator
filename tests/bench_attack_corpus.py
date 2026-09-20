"""
bench_attack_corpus.py

Benchmarks for Attack Corpus (Feature 197).

Measures corpus scanning speed across different attack categories.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAttackCorpusBenchmarks:
    @pytest.fixture
    def corp_dir(self):
        tmpdir = tempfile.mkdtemp()
        for i in range(20):
            fpath = os.path.join(tmpdir, f"file_{i}.py")
            with open(fpath, "w") as f:
                f.write(f"# bypass attempt {i}\nx = {i}\n")
        for i in range(10):
            fpath = os.path.join(tmpdir, f"deob_{i}.py")
            with open(fpath, "w") as f:
                f.write(f"# deobfuscation function {i}\n")
        for i in range(5):
            fpath = os.path.join(tmpdir, f"test_adversarial_{i}.py")
            with open(fpath, "w") as f:
                f.write(f"def test_attack_{i}():\n    pass\n")
        yield tmpdir
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bench_scan_codebase(self, corp_dir, benchmark):
        from scripts.attack_corpus.corpus import AttackCorpus

        def run():
            corpus = AttackCorpus()
            corpus.scan_codebase(corp_dir)
            return len(corpus.entries)

        count = benchmark(run)
        assert count >= 20

    def test_bench_scan_test_files(self, corp_dir, benchmark):
        from scripts.attack_corpus.corpus import AttackCorpus

        def run():
            corpus = AttackCorpus()
            corpus.scan_test_files(corp_dir)
            return len(corpus.entries)

        count = benchmark(run)
        assert count >= 0

    def test_bench_classify_entries(self, corp_dir, benchmark):
        from scripts.attack_corpus.corpus import AttackCorpus

        corpus = AttackCorpus()
        corpus.scan_codebase(corp_dir)

        def run():
            return corpus.classify_entries()

        cats = benchmark(run)
        assert isinstance(cats, dict)

    def test_bench_build_full(self, corp_dir, benchmark):
        from scripts.attack_corpus.corpus import AttackCorpus

        def run():
            corpus = AttackCorpus()
            corpus.scan_codebase(corp_dir)
            corpus.scan_test_files(corp_dir)
            return len(corpus.entries)

        count = benchmark(run)
        assert count > 0
