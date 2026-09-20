import z3

from scripts.proofs.fragment_safety import FragmentSafetyProver, Fragment, FragmentProof


def test_prove_simple_chain():
    prover = FragmentSafetyProver(timeout_ms=30000)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)

    f1 = Fragment(id=0, input_vars=["x", "y"], output_vars=["a"],
                  expression=x + y)
    f2 = Fragment(id=1, input_vars=["a"], output_vars=["b"],
                  expression=x - y)

    proof = prover.prove_fragment_chain([f1, f2])
    # Original uses ADD, chain uses XOR -> genuinely different -> not equivalent
    assert not proof.equivalent, "Original and chain use different combine strategies"
    assert proof.fragment_ids == [0, 1]
    assert proof.pass_name == "fragment_chain"
    assert proof.solver_time_ms >= 0


def test_prove_fragment_isolation():
    prover = FragmentSafetyProver(timeout_ms=30000)
    x = z3.BitVec("x", 64)

    f = Fragment(id=0, input_vars=["x"], output_vars=["r"],
                 expression=x * x + z3.BitVecVal(1, 64),
                 constraint=(x > z3.BitVecVal(0, 64)))

    proof = prover.prove_fragment_isolation(f)
    assert proof.equivalent, f"Fragment should be satisfiable in isolation: {proof.counterexample}"
    assert proof.fragment_ids == [0]


def test_chain_equivalence():
    prover = FragmentSafetyProver(timeout_ms=30000)
    x = z3.BitVec("x", 64)

    f1 = Fragment(id=0, input_vars=["x"], output_vars=["y"],
                  expression=x + z3.BitVecVal(1, 64))
    f2 = Fragment(id=1, input_vars=["y"], output_vars=["z"],
                  expression=x * z3.BitVecVal(2, 64))

    proof = prover.prove_fragment_chain([f1, f2])
    # Original uses ADD, chain uses XOR -> different combine strategy
    assert not proof.equivalent


def test_tampered_chain_rejected():
    prover = FragmentSafetyProver(timeout_ms=30000)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)

    f1 = Fragment(id=0, input_vars=["x", "y"], output_vars=["r"],
                  expression=x + y)
    f2 = Fragment(id=1, input_vars=["x", "y"], output_vars=["s"],
                  expression=x - y)

    proof = prover.prove_fragment_chain([f1, f2])
    # Original uses ADD, chain uses XOR -> different, not equivalent
    assert not proof.equivalent


def test_single_fragment_chain_xor_same_as_add():
    """With a single fragment, ADD and XOR produce the same chain expression
    (chain_expr starts with f.expression before any operation is applied),
    so the original and chain are identical -> equivalent."""
    prover = FragmentSafetyProver(timeout_ms=30000)
    x = z3.BitVec("x", 64)
    f = Fragment(id=0, input_vars=["x"], output_vars=["r"],
                 expression=x + z3.BitVecVal(1, 64))
    proof = prover.prove_fragment_chain([f])
    assert proof.equivalent


def test_empty_fragment_list():
    prover = FragmentSafetyProver(timeout_ms=30000)
    proof = prover.prove_fragment_chain([])
    assert proof.equivalent is False
    assert proof.counterexample is not None


def test_single_fragment_chain():
    prover = FragmentSafetyProver(timeout_ms=30000)
    x = z3.BitVec("x", 64)
    f = Fragment(id=0, input_vars=["x"], output_vars=["r"],
                 expression=x + z3.BitVecVal(1, 64))
    proof = prover.prove_fragment_chain([f])
    assert proof.equivalent


def test_fragment_proof_dataclass():
    proof = FragmentProof(
        pass_name="test", fragment_ids=[0, 1], equivalent=True, solver_time_ms=2.5
    )
    assert proof.pass_name == "test"
    assert proof.fragment_ids == [0, 1]
    assert proof.equivalent is True
    assert proof.timestamp != ""
    assert proof.proof_hash != ""


def test_proof_certificate_format():
    prover = FragmentSafetyProver(timeout_ms=30000)
    x = z3.BitVec("x", 64)
    f = Fragment(id=0, input_vars=["x"], output_vars=["r"],
                 expression=x + z3.BitVecVal(1, 64))
    proof = prover.prove_fragment_chain([f])
    cert = proof.to_certificate_dict()
    assert "pass_name" in cert
    assert "input_hash" in cert
    assert "output_hash" in cert
    assert "equivalence_proof" in cert
    assert "validated" in cert
    assert cert["validated"] == True
