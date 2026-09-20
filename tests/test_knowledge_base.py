"""
test_knowledge_base.py

Tests for Security Knowledge Base (Feature 200).

Test coverage:
- Positive tests verify scanning assumptions, failures, attacks, verification history, regressions
- Negative tests verify no assumptions dir, no tests dir, no git repo, no attack report
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSecurityKnowledgeBase:
    """
    TestSecurityKnowledgeBase
    
    Positive test cases for securityknowledgebase.
    """
    def test_scan_assumptions(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts", "assumptions")
            os.makedirs(sdir)
            with open(os.path.join(sdir, "registry.py"), "w") as f:
                f.write(
                    'Assumption("FHE", "python3", "software", required=True)\n'
                    'Assumption("FHE", "z3", "software", required=False)\n'
                )
            kb = SecurityKnowledgeBase(td)
            kb.scan_assumptions()
            assumptions = [e for e in kb.entries if e.category == "assumption"]
            assert len(assumptions) >= 2

    def test_scan_failures(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            tdir = os.path.join(td, "tests")
            os.makedirs(tdir)
            with open(os.path.join(tdir, "test_fail.py"), "w") as f:
                f.write("def test():\n    assert False  # fail\n")
            kb = SecurityKnowledgeBase(td)
            kb.scan_failures()
            failures = [e for e in kb.entries if e.category == "failure_pattern"]
            assert len(failures) >= 1

    def test_scan_attack_discoveries(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            report_path = os.path.join(td, "attack_report.md")
            with open(report_path, "w") as f:
                f.write("## F167: Reality Score\n...\n## F168: Evidence Ledger\n...\n")
            kb = SecurityKnowledgeBase(td)
            kb.scan_attack_discoveries()
            attacks = [e for e in kb.entries if e.category == "attack_discovery"]
            assert len(attacks) >= 2

    def test_scan_verification_history(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            bdir = os.path.join(td, "build")
            os.makedirs(bdir)
            with open(os.path.join(bdir, "proof_coverage_report.json"), "w") as f:
                json.dump({"overall_coverage": 100.0}, f)
            kb = SecurityKnowledgeBase(td)
            kb.scan_verification_history()
            verifs = [e for e in kb.entries if e.category == "verification_history"]
            assert len(verifs) >= 1

    def test_scan_regressions(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            bdir = os.path.join(td, "build")
            os.makedirs(bdir)
            with open(os.path.join(bdir, "regression_report.md"), "w") as f:
                f.write("✅ PASS test1\n✅ PASS test2\n❌ FAIL test3\n")
            kb = SecurityKnowledgeBase(td)
            kb.scan_regressions()
            regs = [e for e in kb.entries if e.category == "regression"]
            assert len(regs) >= 1

    def test_build(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts", "assumptions")
            tdir = os.path.join(td, "tests")
            bdir = os.path.join(td, "build")
            os.makedirs(sdir)
            os.makedirs(tdir)
            os.makedirs(bdir)
            with open(os.path.join(sdir, "registry.py"), "w") as f:
                f.write('Assumption("TEE", "Linux", "OS", required=True)\n')
            with open(os.path.join(tdir, "test_fail.py"), "w") as f:
                f.write("def test():\n    raise Exception('fail')\n")
            with open(os.path.join(bdir, "proof_coverage_report.json"), "w") as f:
                json.dump({"overall_coverage": 100.0}, f)
            kb = SecurityKnowledgeBase(td)
            kb.build()
            assert len(kb.entries) >= 3

    def test_knowledge_coverage(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts", "assumptions")
            os.makedirs(sdir)
            with open(os.path.join(sdir, "registry.py"), "w") as f:
                f.write('Assumption("X", "y", "z", required=True)\n')
            kb = SecurityKnowledgeBase(td)
            kb.build()
            kc = kb.knowledge_coverage()
            assert kc["covered_categories"] >= 1
            assert kc["total_categories"] == 6

    def test_build_knowledge_base_function(self):
        from scripts.knowledge_base.database import build_knowledge_base
        result = build_knowledge_base()
        assert "total_entries" in result
        assert "by_category" in result
        assert "knowledge_coverage" in result

    def test_entry_dataclass(self):
        from scripts.knowledge_base.database import KnowledgeEntry
        entry = KnowledgeEntry(
            entry_id="KB-0001",
            category="assumption",
            title="Test",
            description="Test entry",
            source="test.py",
            timestamp="2026-01-01",
        )
        d = entry.to_dict()
        assert d["entry_id"] == "KB-0001"
        assert d["category"] == "assumption"


class TestSecurityKnowledgeBaseNegative:
    """
    TestSecurityKnowledgeBaseNegative
    
    Negative test cases — exercises error handling and edge cases for securityknowledgebasenegative.
    """
    def test_no_assumptions_dir(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            kb = SecurityKnowledgeBase(td)
            kb.scan_assumptions()
            assert len(kb.entries) == 0

    def test_no_tests_dir(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            kb = SecurityKnowledgeBase(td)
            kb.scan_failures()
            assert len(kb.entries) == 0

    def test_no_git_repo(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            kb = SecurityKnowledgeBase(td)
            kb.scan_fixes()
            assert len(kb.entries) == 0

    def test_no_attack_report(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            kb = SecurityKnowledgeBase(td)
            kb.scan_attack_discoveries()
            assert len(kb.entries) == 0

    def test_no_build_dir(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            kb = SecurityKnowledgeBase(td)
            kb.scan_verification_history()
            assert len(kb.entries) == 0

    def test_no_failure_patterns(self):
        from scripts.knowledge_base.database import SecurityKnowledgeBase
        with tempfile.TemporaryDirectory() as td:
            tdir = os.path.join(td, "tests")
            os.makedirs(tdir)
            with open(os.path.join(tdir, "test_clean.py"), "w") as f:
                f.write("def test_pass():\n    assert True\n")
            kb = SecurityKnowledgeBase(td)
            kb.scan_failures()
            failures = [e for e in kb.entries if e.category == "failure_pattern"]
            assert len(failures) == 0
