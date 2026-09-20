"""
test_claim_auditor.py

Tests for Claim Auditor (Feature 172).

Test coverage:
- Positive tests verify claim pattern detection, evidence checking, scoring
- Negative tests verify clean code, binary files, false positive avoidance
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.claim_auditor.detector import ClaimDetector, CLAIM_PATTERNS, scan_for_claims
from scripts.claim_auditor.auditor import audit_source, check_evidence, compute_claim_score


# =========================================================================
# Claim Pattern Tests
# =========================================================================

def test_claim_patterns_defined():
    assert len(CLAIM_PATTERNS) >= 20, f"Expected >=20 patterns, got {len(CLAIM_PATTERNS)}"
    names = [p.claim_text for p in CLAIM_PATTERNS]
    assert len(names) == len(set(names)), "Duplicate claim texts found"
    for p in CLAIM_PATTERNS:
        assert p.severity in ("critical", "high", "medium", "low")
        assert p.category in ("false_security", "overpromise", "marketing", "formal_claim")


# =========================================================================
# Detector Tests
# =========================================================================

def test_detector_finds_claims():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_source.py")
        with open(filepath, "w") as f:
            f.write('# This software is "secure" and "unbreakable"\n')
            f.write("def verify():\n")
            f.write('    """This is tamper-proof code."""\n')
            f.write("    pass\n")

        result = scan_for_claims(tmpdir)
        assert result.total_claims >= 3, f"Expected >=3 claims, got {result.total_claims}"
        claim_texts = [m.claim_text for m in result.matches]
        assert "secure" in claim_texts
        assert "unbreakable" in claim_texts
        assert "tamper-proof" in claim_texts or "tamper resistant" in claim_texts


def test_detector_finds_no_claims_on_clean_code():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "clean_source.py")
        with open(filepath, "w") as f:
            f.write("x = 42\n")
            f.write("def add(a, b):\n")
            f.write("    return a + b\n")

        result = scan_for_claims(tmpdir)
        assert result.total_claims == 0, f"Expected 0 claims, got {result.total_claims}"


def test_detector_skips_binary_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "data.bin")
        with open(filepath, "wb") as f:
            f.write(b"\x00\x01\x02secure\x03\x04")

        result = scan_for_claims(tmpdir)
        assert result.total_claims == 0, "Binary files should be skipped"


def test_detector_scans_multiple_file_types():
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in ["a.py", "b.rs", "c.md", "d.json"]:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write("# This is bulletproof secure code\n")

        result = scan_for_claims(tmpdir)
        assert result.total_claims >= 4, f"Expected across file types, got {result.total_claims}"


def test_severity_counts():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_sev.py")
        with open(filepath, "w") as f:
            f.write("# unbreakable invulnerable military-grade certified secure\n")

        result = scan_for_claims(tmpdir)
        assert result.critical_count >= 2
        assert result.high_count >= 1


# =========================================================================
# Evidence and Scoring Tests
# =========================================================================

def test_check_evidence_finds_tests():
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "source.py")
        with open(src_path, "w") as f:
            f.write("# this is secure\n")

        test_path = os.path.join(tmpdir, "test_secure.py")
        with open(test_path, "w") as f:
            f.write("def test_secure():\n    assert True\n")

        result = scan_for_claims(tmpdir)
        assert len(result.matches) > 0
        ev = check_evidence(result.matches[0], tmpdir)
        assert ev["has_test"] is True


def test_check_evidence_no_false_positive():
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "source.py")
        with open(src_path, "w") as f:
            f.write("# this is secure\n")

        result = scan_for_claims(tmpdir)
        assert len(result.matches) > 0
        ev = check_evidence(result.matches[0], tmpdir)
        assert ev["has_benchmark"] is False
        assert ev["has_proof"] is False


def test_compute_claim_score_perfect():
    score = compute_claim_score([], {})
    assert score == 100.0, "Empty matches should give perfect score"


def test_compute_claim_score_penalty():
    from scripts.claim_auditor.detector import ClaimMatch
    matches = [
        ClaimMatch(claim_text="unbreakable", pattern_regex="", category="overpromise",
                   severity="critical", description="", evidence_hint="",
                   file_match="x.py", line_number=1),
    ]
    score = compute_claim_score(matches, {0: {}})
    assert score < 100.0, "Unsupported critical claim should reduce score"


def test_compute_claim_score_with_evidence():
    from scripts.claim_auditor.detector import ClaimMatch
    matches = [
        ClaimMatch(claim_text="secure", pattern_regex="", category="false_security",
                   severity="high", description="", evidence_hint="",
                   file_match="x.py", line_number=1),
    ]
    evidence = {0: {"has_test": True, "has_benchmark": True, "has_implementation": True,
                    "has_proof": True, "has_documentation": True}}
    score = compute_claim_score(matches, evidence)
    assert score > 50.0, "Supported claims should get higher score"


# =========================================================================
# Audit Integration Tests
# =========================================================================

def test_audit_source():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "src.py")
        with open(filepath, "w") as f:
            f.write("# bulletproof unbreakable secure\n")
        testpath = os.path.join(tmpdir, "test_bulletproof.py")
        with open(testpath, "w") as f:
            f.write("def test_bulletproof():\n    pass\n")

        result = audit_source(tmpdir)
        assert result.total_claims >= 3
        assert result.score <= 100.0


def test_all_patterns_accounted():
    from scripts.claim_auditor.detector import CLAIM_PATTERNS
    pattern_names = [p.claim_text for p in CLAIM_PATTERNS]
    expected_core = {"secure", "unbreakable", "tamper-proof", "AI resistant",
                     "military grade", "unhackable"}
    for core in expected_core:
        assert core in pattern_names, f"Missing core pattern: {core}"
