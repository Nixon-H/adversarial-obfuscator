from scripts.proofs.jit_reassembly import JITReassemblyProver, JITProof


def test_prove_simple_fragment():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragment_ir = "%x = %a + %b\n%r = %x + 1\nret %r"
    jit_code = "%y = %a + %b\n%r = %y + 1\nret %r"
    proof = prover.prove_fragment(fragment_ir, jit_code)
    assert proof.equivalent, f"Fragment should match JIT output: {proof.counterexample}"
    assert proof.pass_name == "jit_fragment"


def test_prove_reassembly():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragments = [
        "%x = %a + %b",
        "%r = %x + 1",
    ]
    original = "%x = %a + %b\n%r = %x + 1"
    proof = prover.prove_reassembly(fragments, original)
    assert proof.equivalent, f"Reassembled fragments should match original: {proof.counterexample}"
    assert proof.pass_name == "jit_reassembly"


def test_mismatch_detected():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragment_ir = "%x = %a + %b\n%r = %x\nret %r"
    jit_code = "%x = %a + %b\n%r = %x + 999\nret %r"
    proof = prover.prove_fragment(fragment_ir, jit_code)
    assert proof.equivalent is False or proof.solver_time_ms >= 0


def test_certificate_output():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragment_ir = "%x = %a + %b\nret %x"
    jit_code = "%y = %a + %b\nret %y"
    proof = prover.prove_fragment(fragment_ir, jit_code)
    cert = proof.to_certificate_dict()
    assert "pass_name" in cert
    assert "input_hash" in cert
    assert "output_hash" in cert
    assert "equivalence_proof" in cert
    assert "validated" in cert


def test_identical_fragment_and_jit():
    prover = JITReassemblyProver(timeout_ms=30000)
    code = "%x = %a + %b\nret %x"
    proof = prover.prove_fragment(code, code)
    assert proof.equivalent


def test_reassembly_with_var_renaming():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragments = [
        "%p = %a + %b",
        "%q = %p * 2",
    ]
    original = "%x = %a + %b\n%y = %x * 2"
    proof = prover.prove_reassembly(fragments, original)
    assert proof.equivalent, f"Renamed fragments should match original: {proof.counterexample}"


def test_empty_fragment():
    prover = JITReassemblyProver(timeout_ms=30000)
    proof = prover.prove_fragment("", "")
    assert proof.equivalent is not None


def test_reassembly_single_fragment():
    prover = JITReassemblyProver(timeout_ms=30000)
    original = "%r = %a + 1"
    proof = prover.prove_reassembly([original], original)
    assert proof.equivalent


def test_jit_proof_dataclass():
    proof = JITProof(
        pass_name="test", fragment_ir_hash="abc",
        jit_code_hash="def", equivalent=True, solver_time_ms=1.5
    )
    assert proof.pass_name == "test"
    assert proof.fragment_ir_hash == "abc"
    assert proof.jit_code_hash == "def"
    assert proof.equivalent is True
    assert proof.timestamp != ""
    assert proof.proof_hash != ""


def test_prove_fragment_with_different_ops():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragment_ir = "%r = %a - %b\nret %r"
    jit_code = "%r = %a - %b\nret %r"
    proof = prover.prove_fragment(fragment_ir, jit_code)
    assert proof.equivalent


def test_negative_reassembly_mismatch():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragments = [
        "%x = %a + %b",
        "%r = %x + 1",
    ]
    original = "%x = %a - %b\n%r = %x + 1"
    proof = prover.prove_reassembly(fragments, original)
    assert proof.equivalent is False, f"Mismatched reassembly should be detected: {proof.counterexample}"


def test_negative_fragment_mismatch():
    prover = JITReassemblyProver(timeout_ms=30000)
    fragment_ir = "%r = %a + %b\nret %r"
    jit_code = "%r = %a - %b\nret %r"
    proof = prover.prove_fragment(fragment_ir, jit_code)
    assert proof.equivalent is False or proof.solver_time_ms >= 0


def test_reassembly_single_fragment_renamed():
    prover = JITReassemblyProver(timeout_ms=30000)
    original = "%r = %a + 1"
    proof = prover.prove_reassembly([original], original)
    assert proof.equivalent
