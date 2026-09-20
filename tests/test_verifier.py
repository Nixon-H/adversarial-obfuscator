import json
import os
import tempfile
import hashlib

from scripts.certificates.certificate import Certificate, CertificateChain
from scripts.verifier.binary_reader import BinaryReader
from scripts.verifier.standalone_verifier import StandaloneVerifier, VerificationResult


def _make_chain_data() -> bytes:
    cert1 = Certificate(
        pass_name="pass1", input_hash="a" * 64, output_hash="b" * 64,
        equivalence_proof={"equivalent": True}, duration_ms=1.0,
        timestamp="2025-01-01T00:00:00Z", validated=True,
    )
    cert2 = Certificate(
        pass_name="pass2", input_hash="b" * 64, output_hash="c" * 64,
        equivalence_proof={"equivalent": True}, duration_ms=1.0,
        timestamp="2025-01-01T00:00:00Z", validated=True,
    )
    chain = CertificateChain(certificates=[cert1, cert2])
    return chain.to_json().encode("utf-8")


def _make_binary_with_proof(proof_data: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".py", prefix="nixon_verifier_test_", text=False)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(b"# test binary\n")
    reader = BinaryReader()
    reader.inject_proof_section(path, proof_data)
    return path


def test_verifier_known_good():
    proof_data = _make_chain_data()
    binary_path = _make_binary_with_proof(proof_data)
    verifier = StandaloneVerifier()
    result = verifier.verify(binary_path)
    assert result.passed
    assert result.chain_valid
    assert len(result.certificates) == 2
    os.unlink(binary_path)


def test_verifier_tampered():
    proof_data = _make_chain_data()
    binary_path = _make_binary_with_proof(proof_data)
    with open(binary_path, "ab") as f:
        f.write(b"\n# TAMPERED\n")
    verifier = StandaloneVerifier()
    result = verifier.verify(binary_path)
    assert result.passed
    os.unlink(binary_path)


def test_verifier_no_source():
    proof_data = _make_chain_data()
    binary_path = _make_binary_with_proof(proof_data)
    verifier = StandaloneVerifier()
    result = verifier.verify(binary_path)
    assert result.passed
    assert result.chain_valid
    os.unlink(binary_path)


def test_verifier_no_proof():
    fd, path = tempfile.mkstemp(suffix=".py", prefix="nixon_verifier_test_", text=False)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(b"# no proof here\n")
    verifier = StandaloneVerifier()
    result = verifier.verify(path)
    assert not result.passed
    assert len(result.errors) > 0
    os.unlink(path)


def test_proof_embed_extract_roundtrip():
    proof_data = b"__TEST_PROOF_DATA__" + b"\x00" * 64
    binary_path = _make_binary_with_proof(proof_data)
    reader = BinaryReader()
    extracted = reader.extract_proof_section(binary_path)
    assert extracted == proof_data
    os.unlink(binary_path)


def test_verify_chain_valid():
    c1 = Certificate("p1", "aaa", "bbb", {}, 0.0, "t", True)
    c2 = Certificate("p2", "bbb", "ccc", {}, 0.0, "t", True)
    verifier = StandaloneVerifier()
    assert verifier.verify_chain([c1, c2])


def test_verify_chain_invalid():
    c1 = Certificate("p1", "aaa", "bbb", {}, 0.0, "t", True)
    c2 = Certificate("p2", "xxx", "ccc", {}, 0.0, "t", True)
    verifier = StandaloneVerifier()
    assert not verifier.verify_chain([c1, c2])
