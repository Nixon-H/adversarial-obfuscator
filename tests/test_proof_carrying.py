import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import z3
from scripts.proofs.proof_carrying import ProofCarryingObfuscator
from scripts.certificates.certificate import CertificateChain


def test_prove_bv_identity():
    obf = ProofCarryingObfuscator(timeout_ms=30000)
    cert = obf.prove_bv_identity("identity", 64)
    assert cert.equivalent is True
    assert cert.transformation_name == "identity"
    assert cert.solver_time_ms >= 0


def test_prove_equivalence_same_expression():
    obf = ProofCarryingObfuscator(timeout_ms=30000)
    x = z3.BitVec("x", 32)
    y = z3.BitVec("y", 32)
    original = x + y
    transformed = x + y
    cert = obf.prove_equivalence("add_id", original, transformed, [x, y])
    assert cert.equivalent is True


def test_prove_equivalence_different_expressions():
    obf = ProofCarryingObfuscator(timeout_ms=30000)
    x = z3.BitVec("x", 32)
    original = x
    transformed = x + 1
    cert = obf.prove_equivalence("neq", original, transformed, [x])
    assert cert.equivalent is False
    assert cert.proof_json.get("counterexample") is not None


def test_verify_certificate():
    obf = ProofCarryingObfuscator(timeout_ms=30000)
    x = z3.BitVec("x", 64)
    cert = obf.prove_equivalence("verify_test", x, x, [x])
    assert obf.verify_certificate(cert) is True


def test_get_summary():
    obf = ProofCarryingObfuscator(timeout_ms=30000)
    x = z3.BitVec("x", 32)
    obf.prove_equivalence("t1", x, x, [x])
    obf.prove_equivalence("t2", x, x + 1, [x])
    summary = obf.get_summary()
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1


def test_prove_ir_transformations_returns_chain():
    obf = ProofCarryingObfuscator(timeout_ms=30000)
    chain = obf.prove_ir_transformations(
        "def foo(x): return x",
        ["flatten_cfg", "opaque_predicates", "mba_subs"],
    )
    assert isinstance(chain, CertificateChain)
    assert len(chain.certificates) == 3
    assert chain.validate_chain() is True


def test_embed_proof_section_creates_marker():
    obf = ProofCarryingObfuscator(timeout_ms=30000)
    chain = obf.prove_ir_transformations("def f(): pass", ["t1"])
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        f.write("# test\n")
        tmp_path = f.name
    try:
        payload = obf.embed_proof_section(tmp_path, chain)
        assert "__NIXON_PROOF_BEGIN__" in payload
        assert "__NIXON_PROOF_END__" in payload
        with open(tmp_path, "rb") as f:
            content = f.read()
        assert b"__NIXON_PROOF_BEGIN__" in content
    finally:
        os.unlink(tmp_path)
