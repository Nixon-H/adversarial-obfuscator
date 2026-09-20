"""
test_attack_corpus.py

Tests for Attack Corpus (Feature 197).

Test coverage:
- Positive tests verify scanning for bypass, deobfuscation, proof failure, replay, symbolic failure
- Negative tests verify empty directories, clean files, binary files, nonexistent reports
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAttackCorpus:
    """
    TestAttackCorpus
    
    Positive test cases for attackcorpus.
    """
    def test_corpus_scan_codebase_finds_bypass(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "test_bypass.py")
            with open(fpath, "w") as f:
                f.write("# this is a bypass attempt\nx = 1\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            bypass_entries = [e for e in corpus.entries if e.category == "Bypass"]
            assert len(bypass_entries) >= 1

    def test_corpus_scan_codebase_finds_deobfuscation(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "deobfuscat.py")
            with open(fpath, "w") as f:
                f.write("def deobfuscate():\n    pass\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            entries = [e for e in corpus.entries if e.category == "Deobfuscation"]
            assert len(entries) >= 1

    def test_corpus_scan_codebase_finds_proof_failure(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "proof_fail.py")
            with open(fpath, "w") as f:
                f.write("proof.fail = True  # soundness violated\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            entries = [e for e in corpus.entries if e.category == "Proof Failure"]
            assert len(entries) >= 1

    def test_corpus_scan_codebase_finds_replay(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "replay_attack.py")
            with open(fpath, "w") as f:
                f.write("# capture.attack replay\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            entries = [e for e in corpus.entries if e.category == "Replay Attack"]
            assert len(entries) >= 1

    def test_corpus_scan_codebase_finds_symbolic_failure(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "z3_fail.py")
            with open(fpath, "w") as f:
                f.write("symbolic.fail = True\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            entries = [e for e in corpus.entries if e.category == "Symbolic Failure"]
            assert len(entries) >= 1

    def test_corpus_scan_test_files(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            tests_dir = os.path.join(td, "tests")
            os.makedirs(tests_dir)
            fpath = os.path.join(tests_dir, "test_adversarial.py")
            with open(fpath, "w") as f:
                f.write("def test_attack():\n    pass\n")
            corpus = AttackCorpus()
            corpus.scan_test_files(td)
            assert len(corpus.entries) >= 1

    def test_corpus_scan_attack_report(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            report_path = os.path.join(td, "attack_report.md")
            with open(report_path, "w") as f:
                f.write(
                    "## F167: Reality Score\n\n"
                    "| **BYPASS** | Result | **HIGH** |\n"
                    "|--------|--------|----------|\n"
                    "**Fix:** Validate scores\n"
                )
            corpus = AttackCorpus()
            corpus.scan_attack_report(report_path)
            assert len(corpus.entries) >= 1

    def test_classify_entries(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "bypass.py")
            with open(fpath, "w") as f:
                f.write("# bypass\n")
            fpath2 = os.path.join(td, "replay.py")
            with open(fpath2, "w") as f:
                f.write("# replay\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            cats = corpus.classify_entries()
            assert "Bypass" in cats
            assert "Replay Attack" in cats

    def test_severity_distribution(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "critical_bypass.py")
            with open(fpath, "w") as f:
                f.write("# critical bypass vulnerability\n")
            fpath2 = os.path.join(td, "low_evade.py")
            with open(fpath2, "w") as f:
                f.write("# low evade\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            dist = corpus.severity_distribution()
            assert isinstance(dist, dict)
            assert sum(dist.values()) == len(corpus.entries)

    def test_build_attack_corpus_function(self):
        from scripts.attack_corpus.corpus import build_attack_corpus
        result = build_attack_corpus()
        assert "corpus_entries" in result
        assert "total_attacks" in result
        assert "severity_distribution" in result
        assert isinstance(result["corpus_entries"], int)

    def test_corpus_entry_dataclass(self):
        from scripts.attack_corpus.corpus import CorpusEntry
        entry = CorpusEntry(
            attack_id="AC-0001",
            category="Bypass",
            description="Test entry",
            severity="high",
            file_path="test.py",
            line_number=10,
        )
        d = entry.to_dict()
        assert d["attack_id"] == "AC-0001"
        assert d["severity"] == "high"


class TestAttackCorpusNegative:
    """
    TestAttackCorpusNegative
    
    Negative test cases — exercises error handling and edge cases for attackcorpusnegative.
    """
    def test_empty_directory(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            assert len(corpus.entries) == 0

    def test_no_matching_patterns(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "clean.py")
            with open(fpath, "w") as f:
                f.write("x = 1\ny = 2\n")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            assert len(corpus.entries) == 0

    def test_missing_attack_report(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        corpus = AttackCorpus()
        corpus.scan_attack_report("/tmp/nonexistent_report.md")
        assert len(corpus.entries) == 0

    def test_empty_test_directory(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            tests_dir = os.path.join(td, "tests")
            os.makedirs(tests_dir)
            corpus = AttackCorpus()
            corpus.scan_test_files(td)
            assert len(corpus.entries) == 0

    def test_binary_file_handling(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "data.bin")
            with open(fpath, "wb") as f:
                f.write(b"\x00\x01\x02\x03")
            corpus = AttackCorpus()
            corpus.scan_codebase(td)
            assert len(corpus.entries) == 0

    def test_unknown_severity_defaults_to_medium(self):
        from scripts.attack_corpus.corpus import AttackCorpus
        corpus = AttackCorpus()
        sev = corpus._infer_severity("bypass", "nothing special here")
        assert sev == "medium"
