import json
import os
import tempfile
import hashlib

from scripts.certificates.certificate import Certificate, CertificateChain, emit_certificate
from scripts.certificates.collector import CertificateCollector
from scripts.certificates.integrity import hash_bytes, hash_source


def test_certificate_serialization():
    cert = Certificate(
        pass_name="test_pass",
        input_hash="abc123",
        output_hash="def456",
        equivalence_proof={"equivalent": True, "solver_time_ms": 12.5},
        duration_ms=10.0,
        timestamp="2025-01-01T00:00:00Z",
        validated=True,
    )
    json_str = cert.to_json()
    restored = Certificate.from_json(json_str)
    assert restored.pass_name == "test_pass"
    assert restored.input_hash == "abc123"
    assert restored.output_hash == "def456"
    assert restored.validated == True
    assert restored.duration_ms == 10.0
    assert restored.equivalence_proof["equivalent"] == True


def test_collector_writes_valid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = CertificateCollector(tmpdir)
        collector.record(
            pass_name="phase1",
            input_data="input text",
            output_data="output text",
            smt_result={"equivalent": True},
            duration_ms=5.0,
        )
        collector.emit_all()
        chain_path = os.path.join(tmpdir, "certificate_chain.json")
        assert os.path.exists(chain_path)
        with open(chain_path) as f:
            data = json.load(f)
        assert "certificates" in data
        assert len(data["certificates"]) == 1
        assert data["certificates"][0]["pass_name"] == "phase1"
        cert_path = os.path.join(tmpdir, "cert_0000_phase1.json")
        assert os.path.exists(cert_path)
        with open(cert_path) as f:
            cert_data = json.load(f)
        assert cert_data["pass_name"] == "phase1"


def test_hash_records_match_known():
    known = "hello world"
    expected = hashlib.sha256(known.encode()).hexdigest()
    assert hash_source(known) == expected
    assert hash_bytes(known.encode()) == expected


def test_collector_accumulates():
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = CertificateCollector(tmpdir)
        for i in range(3):
            collector.record(
                pass_name=f"phase{i}",
                input_data=f"in{i}",
                output_data=f"out{i}",
                smt_result={"equivalent": i % 2 == 0},
                duration_ms=float(i),
            )
        assert len(collector.certificates) == 3
        collector.emit_all()
        chain_path = os.path.join(tmpdir, "certificate_chain.json")
        with open(chain_path) as f:
            data = json.load(f)
        assert len(data["certificates"]) == 3


def test_certificate_chain_validation():
    cert1 = emit_certificate("pass1", "hello", "world", {"equivalent": True}, 1.0)
    cert2 = emit_certificate("pass2", "world", "done", {"equivalent": True}, 1.0)
    chain = CertificateChain(certificates=[cert1, cert2])
    assert chain.validate_chain() == True
    assert chain.chain_validated == True
    cert3 = emit_certificate("pass3", "broken", "end", {"equivalent": True}, 1.0)
    bad_chain = CertificateChain(certificates=[cert1, cert3])
    assert bad_chain.validate_chain() == False
    assert bad_chain.chain_validated == False
