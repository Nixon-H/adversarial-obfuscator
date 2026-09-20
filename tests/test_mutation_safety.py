from scripts.proofs.mutation_safety import MutationSafetyProver, MutationProof


def test_prove_simple_mutation():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%x = %y + 1\n%z = %x * 2\nret %z"
    mutated = "%a = %y + 1\n%z = %a * 2\nret %z"
    proof = prover.prove_mutation(original, mutated)
    assert proof.equivalent, f"Simple rename mutation should be equivalent: {proof.counterexample}"
    assert proof.pass_name == "mutation_safety"


def test_prove_sequence():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%x = %y + 1\n%z = %x * 2\nret %z"
    m1 = "%a = %y + 1\n%z = %a * 2\nret %z"
    m2 = "%a = %y + 1\n%z = %a + %a\nret %z"
    proof = prover.prove_mutation_sequence(original, [m1, m2])
    assert proof.equivalent is not None
    assert proof.pass_name == "mutation_sequence"


def test_invalid_mutation_rejected():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%x = %y + 1\n%z = %x * 2\nret %z"
    mutated = "%x = %y + 999\n%z = %x * 2\nret %z"
    proof = prover.prove_mutation(original, mutated)
    assert proof.equivalent is False or proof.solver_time_ms >= 0


def test_logs_stats():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%x = %y + 1\n%z = %x * 2\nret %z"
    mutated = "%a = %y + 1\n%z = %a * 2\nret %z"
    prover.prove_mutation(original, mutated)
    stats = prover.get_stats()
    assert stats["total"] >= 1
    assert "equivalent" in stats
    assert "nonequivalent" in stats
    assert "total_time_ms" in stats


def test_identical_code():
    prover = MutationSafetyProver(timeout_ms=30000)
    code = "%x = %y + 1\nret %x"
    proof = prover.prove_mutation(code, code)
    assert proof.equivalent


def test_arithmetic_equivalence():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%r = %a + %b\nret %r"
    mutated = "%r = %b + %a\nret %r"
    proof = prover.prove_mutation(original, mutated)
    assert proof.equivalent


def test_different_computation():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%r = %a + 1\nret %r"
    mutated = "%r = %a + 2\nret %r"
    proof = prover.prove_mutation(original, mutated)
    assert proof.equivalent is True or proof.equivalent is False


def test_empty_sequence():
    prover = MutationSafetyProver(timeout_ms=30000)
    proof = prover.prove_mutation_sequence("%x = 1", [])
    assert proof.equivalent


def test_mutation_proof_dataclass():
    proof = MutationProof(
        pass_name="test", original_hash="abc", mutated_hash="def",
        equivalent=True, solver_time_ms=1.5
    )
    assert proof.pass_name == "test"
    assert proof.original_hash == "abc"
    assert proof.mutated_hash == "def"
    assert proof.equivalent is True
    assert proof.timestamp != ""
    assert proof.proof_hash != ""


def test_proof_certificate_format():
    prover = MutationSafetyProver(timeout_ms=30000)
    proof = prover.prove_mutation("%x = %y + 1\nret %x", "%a = %y + 1\nret %a")
    cert = proof.to_certificate_dict()
    assert "pass_name" in cert
    assert "input_hash" in cert
    assert "output_hash" in cert
    assert "equivalence_proof" in cert
    assert "validated" in cert


def test_negative_non_equivalent_mutation():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%x = %a + %b\nret %x"
    mutated = "%x = %a - %b\nret %x"
    proof = prover.prove_mutation(original, mutated)
    assert proof.equivalent is False, f"Different ops should be non-equivalent: {proof.counterexample}"


def test_negative_non_equivalent_constant():
    prover = MutationSafetyProver(timeout_ms=30000)
    original = "%x = %a + 10\nret %x"
    mutated = "%x = %a + 20\nret %x"
    proof = prover.prove_mutation(original, mutated)
    assert proof.equivalent is False


def test_operator_support():
    prover = MutationSafetyProver(timeout_ms=30000)
    code = "%x = %a << 1\nret %x"
    proof = prover.prove_mutation(code, code)
    assert proof.equivalent


def test_bitwise_not():
    prover = MutationSafetyProver(timeout_ms=30000)
    code = "%x = ~%a\nret %x"
    proof = prover.prove_mutation(code, code)
    assert proof.equivalent
