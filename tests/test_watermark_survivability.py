import z3

from scripts.proofs.watermark_survivability import (
    WatermarkSurvivabilityProver, WatermarkProof,
    IDENTITY, RENAME, DEADCODE, CFG_FLATTEN, ZERO_WATERMARK, SHIFT_WATERMARK,
    _identity_transform, _rename_transform, _deadcode_add_transform,
    _zero_watermark_transform, _shift_watermark_transform,
)


def test_rename_survives():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pass("NixonCorp-Secret", RENAME)
    assert proof.survived, "Watermark should survive rename transformation"
    assert proof.transformation == "rename"


def test_deadcode_survives():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pass("NixonCorp-Secret", DEADCODE)
    assert proof.survived, "Watermark should survive deadcode insertion"
    assert proof.transformation == "deadcode_insertion"


def test_cfg_flatten_survives():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pass("NixonCorp-Secret", CFG_FLATTEN)
    assert proof.survived, "Watermark should survive CFG flattening"
    assert proof.transformation == "cfg_flattening"


def test_identity_survives():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pass("test-identity", IDENTITY)
    assert proof.survived
    assert proof.transformation == "identity"


def test_pipeline_survives():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    pipeline = [RENAME, DEADCODE, CFG_FLATTEN]
    proof = prover.prove_survives_pipeline("NixonCorp-Pipeline", pipeline)
    assert proof.survived, "Watermark should survive full pipeline"
    assert "pipeline" in proof.transformation or "->" in proof.transformation


def test_empty_pipeline():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pipeline("test-empty", [])
    assert proof.survived


def test_long_watermark():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    long_wm = "A" * 100
    proof = prover.prove_survives_pass(long_wm, IDENTITY)
    assert proof.survived


def test_watermark_proof_dataclass():
    proof = WatermarkProof(
        pass_name="test", watermark="test-wm",
        transformation="test-trf", survived=True, solver_time_ms=1.0
    )
    assert proof.pass_name == "test"
    assert proof.watermark == "test-wm"
    assert proof.transformation == "test-trf"
    assert proof.survived is True
    assert proof.timestamp != ""
    assert proof.proof_hash != ""


def test_proof_certificate_format():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pass("test-cert", IDENTITY)
    cert = proof.to_certificate_dict()
    assert "pass_name" in cert
    assert "input_hash" in cert
    assert "output_hash" in cert
    assert "equivalence_proof" in cert
    assert "validated" in cert
    assert "survived" in cert["equivalence_proof"]


def test_transformation_functions():
    state = {"wm_value": 42, "other": "keep"}
    renamed = _rename_transform(state)
    assert "wm_renamed_value" in renamed
    assert "other" in renamed
    assert renamed["other"] == "keep"

    dead = _deadcode_add_transform(state)
    assert "wm_value" in dead
    assert "dead_var" in dead

    identity = _identity_transform(state)
    assert identity["wm_value"] == 42


def test_zero_watermark_does_not_survive():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pass("NixonCorp-Secret", ZERO_WATERMARK)
    assert not proof.survived, "Watermark should NOT survive zeroing transform"
    assert proof.transformation == "zero_watermark"


def test_shift_watermark_does_not_survive():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    proof = prover.prove_survives_pass("NixonCorp-Secret", SHIFT_WATERMARK)
    assert not proof.survived, "Watermark should NOT survive shifting transform"
    assert proof.transformation == "shift_watermark"


def test_negative_pipeline_detected():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    pipeline = [IDENTITY, ZERO_WATERMARK]
    proof = prover.prove_survives_pipeline("NixonCorp-Pipeline", pipeline)
    assert not proof.survived, "Pipeline with zero_watermark should NOT survive"


def test_zero_transform_function():
    state = {"wm_value": z3.BitVecVal(42, 64), "other": "keep"}
    zeroed = _zero_watermark_transform(state)
    assert z3.simplify(zeroed["wm_value"]).as_long() == 0
    assert zeroed["other"] == "keep"


def test_shift_transform_function():
    state = {"wm_value": z3.BitVecVal(42, 64), "other": "keep"}
    shifted = _shift_watermark_transform(state)
    assert z3.simplify(shifted["wm_value"]).as_long() == 43
    assert shifted["other"] == "keep"


def test_intermediate_proofs_recorded():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    pipeline = [IDENTITY, RENAME, DEADCODE]
    prover.prove_survives_pipeline("intermediate-test", pipeline)
    intermediate = [p for p in prover.proofs if "intermediate" in p.pass_name]
    assert len(intermediate) == len(pipeline), \
        f"Expected {len(pipeline)} intermediate proofs, got {len(intermediate)}"
    for ip in intermediate:
        assert ip.survived is True


def test_intermediate_proofs_catch_failure():
    prover = WatermarkSurvivabilityProver(timeout_ms=30000)
    pipeline = [IDENTITY, ZERO_WATERMARK, IDENTITY]
    prover.prove_survives_pipeline("intermediate-fail", pipeline)
    intermediate = {p.transformation: p.survived for p in prover.proofs if "intermediate" in p.pass_name}
    assert intermediate.get("identity", True) is True
    assert intermediate.get("zero_watermark", True) is False
