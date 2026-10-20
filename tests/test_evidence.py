"""
test_evidence.py

Tests for Evidence Ledger (Feature 168).

Test coverage:
- Positive tests verify claim registration, evidence addition, hash computation, verification
- Negative tests verify nonexistent claims, missing files, modified/deleted evidence
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evidence.ledger import (
    ClaimEntry,
    EvidenceEntry,
    EvidenceLedger,
    build_evidence_ledger,
    verify_evidence,
    generate_evidence_report,
)
from scripts.evidence.collector import EvidenceCollector


# =========================================================================
# ClaimEntry tests
# =========================================================================

def test_claim_entry_creation():
    entry = ClaimEntry(
        claim="Encrypted execution",
        feature="FHE-VM",
        claim_type="security",
        confidence="measured",
    )
    assert entry.claim == "Encrypted execution"
    assert entry.feature == "FHE-VM"
    assert entry.claim_type == "security"
    assert entry.confidence == "measured"


def test_claim_entry_to_dict():
    entry = ClaimEntry(
        claim="Test claim",
        feature="test",
        claim_type="correctness",
        confidence="estimated",
    )
    d = entry.to_dict()
    assert d["claim"] == "Test claim"
    assert d["feature"] == "test"
    assert d["claim_type"] == "correctness"
    assert d["confidence"] == "estimated"


def test_claim_entry_all_types():
    for ct in ("security", "performance", "correctness", "coverage"):
        entry = ClaimEntry(claim="c", feature="f", claim_type=ct, confidence="measured")
        assert entry.claim_type == ct
    for conf in ("measured", "theoretical", "estimated"):
        entry = ClaimEntry(claim="c", feature="f", claim_type="security", confidence=conf)
        assert entry.confidence == conf


# =========================================================================
# EvidenceEntry tests
# =========================================================================

def test_evidence_entry_creation():
    entry = EvidenceEntry(
        claim="Test",
        evidence_type="source_code",
        evidence_path="/tmp/test.py",
        evidence_hash="abc123",
        verified=False,
        verified_at="",
    )
    assert entry.claim == "Test"
    assert entry.evidence_type == "source_code"
    assert not entry.verified


def test_evidence_entry_to_dict():
    entry = EvidenceEntry(
        claim="Test",
        evidence_type="test",
        evidence_path="/tmp/test.py",
        evidence_hash="def456",
        verified=True,
        verified_at="2024-01-01T00:00:00",
    )
    d = entry.to_dict()
    assert d["verified"] is True
    assert d["evidence_hash"] == "def456"


def test_evidence_entry_all_types():
    for et in ("source_code", "test", "benchmark", "runtime_trace", "metric"):
        entry = EvidenceEntry(claim="c", evidence_type=et, evidence_path="/p", evidence_hash="h")
        assert entry.evidence_type == et


# =========================================================================
# EvidenceLedger tests
# =========================================================================

def test_ledger_init():
    ledger = EvidenceLedger()
    assert ledger.claims == {}
    assert ledger.evidence == {}


def test_register_claim():
    ledger = EvidenceLedger()
    entry = ledger.register_claim("Encrypted execution", "FHE-VM", "security", "measured")
    assert isinstance(entry, ClaimEntry)
    assert "Encrypted execution" in ledger.claims
    assert ledger.claims["Encrypted execution"].feature == "FHE-VM"


def test_register_duplicate_claim():
    ledger = EvidenceLedger()
    ledger.register_claim("Claim 1", "feature1", "security", "measured")
    ledger.register_claim("Claim 2", "feature2", "performance", "estimated")
    ledger.register_claim("Claim 1", "feature1", "security", "measured")
    assert len(ledger.claims) == 2


def test_add_evidence(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Test claim", "test", "security", "measured")
    ev_file = tmp_path / "evidence.txt"
    ev_file.write_text("evidence data")
    result = ledger.add_evidence("Test claim", "source_code", str(ev_file))
    assert result is not None
    assert result.evidence_type == "source_code"
    assert len(ledger.evidence["Test claim"]) == 1


def test_add_evidence_nonexistent_claim():
    ledger = EvidenceLedger()
    result = ledger.add_evidence("No claim", "test", "/nonexistent")
    assert result is None


def test_add_evidence_nonexistent_file():
    ledger = EvidenceLedger()
    ledger.register_claim("Test claim", "test", "security", "measured")
    result = ledger.add_evidence("Test claim", "test", "/nonexistent/file.txt")
    assert result is None
    assert ledger.evidence.get("Test claim") == []


def test_add_evidence_computes_hash(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Hash claim", "test", "correctness", "measured")
    ev_file = tmp_path / "hash_test.txt"
    ev_file.write_text("compute my hash")
    expected_hash = hashlib.sha256(b"compute my hash").hexdigest()
    result = ledger.add_evidence("Hash claim", "test", str(ev_file))
    assert result is not None
    assert result.evidence_hash == expected_hash


def test_verify_evidence_success(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Verify claim", "test", "security", "measured")
    ev_file = tmp_path / "verify.txt"
    ev_file.write_text("verify me")
    ledger.add_evidence("Verify claim", "test", str(ev_file))
    results = ledger.verify_evidence("Verify claim")
    assert len(results) == 1
    assert results[0].verified is True
    assert results[0].verified_at != ""


def test_verify_evidence_file_modified(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Modified claim", "test", "security", "measured")
    ev_file = tmp_path / "modified.txt"
    ev_file.write_text("original content")
    ledger.add_evidence("Modified claim", "test", str(ev_file))
    ev_file.write_text("modified content")
    results = ledger.verify_evidence("Modified claim")
    assert len(results) == 1
    assert results[0].verified is False


def test_verify_evidence_file_deleted(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Deleted claim", "test", "security", "measured")
    ev_file = tmp_path / "deleted.txt"
    ev_file.write_text("will be deleted")
    ledger.add_evidence("Deleted claim", "test", str(ev_file))
    os.remove(str(ev_file))
    results = ledger.verify_evidence("Deleted claim")
    assert len(results) == 1
    assert results[0].verified is False


def test_verify_evidence_no_evidence():
    ledger = EvidenceLedger()
    ledger.register_claim("No evidence", "test", "security", "measured")
    results = ledger.verify_evidence("No evidence")
    assert results == []


def test_verify_all(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("C1", "f1", "security", "measured")
    ledger.register_claim("C2", "f2", "performance", "estimated")
    f1 = tmp_path / "f1.txt"
    f1.write_text("data1")
    f2 = tmp_path / "f2.txt"
    f2.write_text("data2")
    ledger.add_evidence("C1", "test", str(f1))
    ledger.add_evidence("C2", "test", str(f2))
    results = ledger.verify_all()
    assert "C1" in results
    assert "C2" in results
    assert results["C1"][0].verified is True
    assert results["C2"][0].verified is True


def test_get_unverified_claims():
    ledger = EvidenceLedger()
    ledger.register_claim("Has evidence", "f1", "security", "measured")
    ledger.register_claim("No evidence", "f2", "performance", "estimated")
    assert "No evidence" in ledger.get_unverified_claims()
    assert "Has evidence" in ledger.get_unverified_claims()


def test_get_unverified_claims_with_evidence(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Has evidence", "f1", "security", "measured")
    ledger.register_claim("No evidence", "f2", "performance", "estimated")
    ev_file = tmp_path / "ev.txt"
    ev_file.write_text("data")
    ledger.add_evidence("Has evidence", "test", str(ev_file))
    unverified = ledger.get_unverified_claims()
    assert "No evidence" in unverified
    assert "Has evidence" not in unverified


def test_get_claims_without_runtime(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Needs runtime", "f1", "security", "measured")
    ledger.register_claim("Has runtime", "f2", "security", "measured")
    ev_file = tmp_path / "runtime.c"
    ev_file.write_text("runtime code")
    ledger.add_evidence("Has runtime", "runtime_trace", str(ev_file))
    missing = ledger.get_claims_without_runtime()
    assert "Needs runtime" in missing
    assert "Has runtime" not in missing


def test_to_dict(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Test claim", "test", "correctness", "measured")
    ev_file = tmp_path / "test.txt"
    ev_file.write_text("data")
    ledger.add_evidence("Test claim", "test", str(ev_file))
    d = ledger.to_dict()
    assert "claims" in d
    assert "evidence" in d
    assert "Test claim" in d["claims"]
    assert d["claims"]["Test claim"]["claim_type"] == "correctness"


def test_to_json(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("JSON claim", "test", "security", "measured")
    json_path = tmp_path / "ledger.json"
    ledger.to_json(str(json_path))
    assert json_path.exists()
    with open(str(json_path)) as f:
        data = json.load(f)
    assert "claims" in data
    assert "JSON claim" in data["claims"]


def test_from_build_artifacts():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root, "build")
    os.makedirs(build_dir, exist_ok=True)
    ledger = EvidenceLedger()
    result = ledger.from_build_artifacts(build_dir)
    assert isinstance(result, EvidenceLedger)
    assert len(result.claims) > 0
    assert sum(len(v) for v in result.evidence.values()) > 0


def test_build_evidence_ledger():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root, "build")
    os.makedirs(build_dir, exist_ok=True)
    ledger = build_evidence_ledger(build_dir)
    assert isinstance(ledger, EvidenceLedger)
    assert len(ledger.claims) > 0


def test_verify_evidence_function(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("V claim", "test", "security", "measured")
    ev_file = tmp_path / "v.txt"
    ev_file.write_text("data")
    ledger.add_evidence("V claim", "test", str(ev_file))
    result = verify_evidence(ledger, "V claim")
    assert "V claim" in result
    assert result["V claim"][0].verified is True


def test_verify_evidence_all(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("C1", "f1", "security", "measured")
    ledger.register_claim("C2", "f2", "correctness", "measured")
    f1 = tmp_path / "c1.txt"
    f1.write_text("d1")
    f2 = tmp_path / "c2.txt"
    f2.write_text("d2")
    ledger.add_evidence("C1", "test", str(f1))
    ledger.add_evidence("C2", "test", str(f2))
    result = verify_evidence(ledger)
    assert "C1" in result
    assert "C2" in result


def test_generate_evidence_report(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Report claim", "test", "security", "measured")
    ev_file = tmp_path / "report.txt"
    ev_file.write_text("report data")
    ledger.add_evidence("Report claim", "test", str(ev_file))
    ledger.verify_evidence("Report claim")
    report = generate_evidence_report(ledger)
    assert report["total_claims"] >= 1
    assert report["total_evidence"] >= 1
    assert "evidence_by_type" in report
    assert "coverage_pct" in report
    assert "claim_coverage_pct" in report


def test_generate_evidence_report_empty():
    ledger = EvidenceLedger()
    report = generate_evidence_report(ledger)
    assert report["total_claims"] == 0
    assert report["total_evidence"] == 0
    assert report["coverage_pct"] == 0.0


def test_generate_evidence_report_full(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("C1", "f1", "security", "measured")
    ledger.register_claim("C2", "f2", "performance", "estimated")
    f1 = tmp_path / "e1.txt"
    f1.write_text("d1")
    f2 = tmp_path / "e2.txt"
    f2.write_text("d2")
    ledger.add_evidence("C1", "source_code", str(f1))
    ledger.add_evidence("C2", "benchmark", str(f2))
    ledger.verify_all()
    report = generate_evidence_report(ledger)
    assert report["total_claims"] == 2
    assert report["total_evidence"] == 2
    assert report["verified_evidence"] == 2


# =========================================================================
# EvidenceCollector tests
# =========================================================================

def test_collector_init():
    collector = EvidenceCollector("/tmp/build")
    assert collector.build_dir == "/tmp/build"
    assert len(collector.ledger.claims) == 0


def test_collector_collect_from_phase():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root, "build")
    collector = EvidenceCollector(build_dir)
    collector.collect_from_phase("phase01_obfuscate", None)
    assert len(collector.ledger.claims) >= 1


def test_collector_collect_from_test():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root, "build")
    collector = EvidenceCollector(build_dir)
    test_path = os.path.join(root, "tests", "test_obfuscator.py")
    if os.path.isfile(test_path):
        collector.collect_from_test(test_path)
        assert len(collector.ledger.evidence) >= 1


def test_collector_collect_from_benchmark():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root, "build")
    collector = EvidenceCollector(build_dir)
    bench_path = os.path.join(root, "tests", "bench_conflicts.py")
    if os.path.isfile(bench_path):
        collector.collect_from_benchmark(bench_path)
        assert len(collector.ledger.evidence) >= 1


def test_collector_collect_all(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root, "build")
    collector = EvidenceCollector(build_dir)
    ledger = collector.collect_all(build_dir)
    assert len(ledger.claims) > 0
    assert sum(len(v) for v in ledger.evidence.values()) > 0


def test_collector_collect_from_nonexistent():
    collector = EvidenceCollector("/tmp/nonexistent")
    collector.collect_from_test("/tmp/nonexistent/test.py")
    collector.collect_from_benchmark("/tmp/nonexistent/bench.py")
    collector.collect_from_runtime("/tmp/nonexistent/runtime.c")
    assert len(collector.ledger.claims) == 0


def test_ledger_multiple_evidence_per_claim(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Multi evidence", "test", "security", "measured")
    f1 = tmp_path / "src.py"
    f1.write_text("source")
    f2 = tmp_path / "test.py"
    f2.write_text("test")
    f3 = tmp_path / "bench.py"
    f3.write_text("bench")
    ledger.add_evidence("Multi evidence", "source_code", str(f1))
    ledger.add_evidence("Multi evidence", "test", str(f2))
    ledger.add_evidence("Multi evidence", "benchmark", str(f3))
    assert len(ledger.evidence["Multi evidence"]) == 3
    types = [e.evidence_type for e in ledger.evidence["Multi evidence"]]
    assert "source_code" in types
    assert "test" in types
    assert "benchmark" in types


def test_serialization_roundtrip(tmp_path):
    ledger = EvidenceLedger()
    ledger.register_claim("Roundtrip", "test", "correctness", "measured")
    f = tmp_path / "data.txt"
    f.write_text("data")
    ledger.add_evidence("Roundtrip", "test", str(f))
    json_path = tmp_path / "out.json"
    ledger.to_json(str(json_path))
    with open(str(json_path)) as fp:
        data = json.load(fp)
    assert data["claims"]["Roundtrip"]["claim_type"] == "correctness"
    assert len(data["evidence"]["Roundtrip"]) == 1
