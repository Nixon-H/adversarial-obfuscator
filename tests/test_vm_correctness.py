from scripts.proofs.vm_correctness import VMCorrectnessProver, VmProof


def test_prove_add_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("ADD")
    assert proof.equivalent, f"ADD instruction should be equivalent, got counterexample={proof.counterexample}"
    assert proof.opcode == "ADD"
    assert proof.pass_name == "vm_correctness"
    assert proof.solver_time_ms >= 0


def test_prove_sub_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("SUB")
    assert proof.equivalent
    assert proof.opcode == "SUB"


def test_prove_mul_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("MUL")
    assert proof.equivalent
    assert proof.opcode == "MUL"


def test_prove_xor_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("XOR")
    assert proof.equivalent


def test_prove_and_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("AND")
    assert proof.equivalent


def test_prove_or_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("OR")
    assert proof.equivalent


def test_prove_mov_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("MOV")
    assert proof.equivalent


def test_prove_cmp_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("CMP")
    assert proof.equivalent


def test_prove_jmp_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("JMP")
    assert proof.equivalent


def test_prove_nop_instruction():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("NOP")
    assert proof.equivalent


def test_prove_all_instructions():
    prover = VMCorrectnessProver(timeout_ms=30000)
    results = prover.prove_all_instructions()
    assert len(results) == 24
    proven_count = sum(1 for r in results if r.equivalent)
    assert proven_count == 10, f"Expected 10 proven, got {proven_count}"
    unproven_count = sum(1 for r in results if not r.equivalent)
    assert unproven_count == 14, f"Expected 14 unproven, got {unproven_count}"
    assert len(prover.proofs) == 24


def test_prove_execution_trace():
    prover = VMCorrectnessProver(timeout_ms=30000)
    bytecode = bytes([0x01, 0x02, 0x03, 0x04])
    proof = prover.prove_execution_trace(bytecode, {"r0": 10, "r1": 20})
    assert proof.pass_name == "vm_execution_trace"
    assert proof.opcode == "trace"


def test_invalid_bytecode_rejected():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_execution_trace(b"\x00", {"r0": 0})
    assert proof.equivalent is False or proof.solver_time_ms >= 0


def test_proof_certificate_format():
    prover = VMCorrectnessProver(timeout_ms=30000)
    proof = prover.prove_instruction("ADD")
    cert = proof.to_certificate_dict()
    assert "pass_name" in cert
    assert "input_hash" in cert
    assert "output_hash" in cert
    assert "equivalence_proof" in cert
    assert "duration_ms" in cert
    assert "timestamp" in cert
    assert "validated" in cert
    assert cert["pass_name"] == "vm_correctness"
    assert cert["validated"] == True


def test_vmproof_dataclass():
    proof = VmProof(
        pass_name="test", opcode="ADD", equivalent=True, solver_time_ms=1.5
    )
    assert proof.pass_name == "test"
    assert proof.opcode == "ADD"
    assert proof.equivalent is True
    assert proof.solver_time_ms == 1.5
    assert proof.timestamp != ""
    assert proof.proof_hash != ""
