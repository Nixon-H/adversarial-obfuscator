"""Tests for ZK State-Bound Execution package.

All tests verify functional correctness, negative cases (invalid proofs,
tampered proofs, replay attacks), and configuration defaults.
"""

from __future__ import annotations

import os
import sys
import time
import json
import tempfile


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.zk_state.sigma_protocol import (
    SigmaProver, SigmaVerifier, generate_parameters,
)
from scripts.zk_state.state_machine import StateMachine
from scripts.zk_state.prover import StateBoundProver
from scripts.zk_state.verifier import StateBoundVerifier
from scripts.zk_state.state_config import ZKStateConfig, load_config, check_prerequisites


# =========================================================================
# Sigma Protocol Tests
# =========================================================================


def test_sigma_protocol():
    """Positive test: prover creates a valid proof, verifier accepts."""
    params = generate_parameters(1024)
    prover = SigmaProver(params)
    verifier = SigmaVerifier(params)

    secret, public_key = prover.generate_keypair()
    state_commitment = 0xABCD1234

    proof = prover.prove_state(state_commitment, secret)

    assert proof.commitment > 0
    assert proof.challenge >= 0
    assert proof.response >= 0
    assert proof.public_key == public_key

    valid = verifier.verify_state(proof, state_commitment)
    assert valid, "Sigma protocol proof should be valid"


def test_sigma_protocol_invalid():
    """Negative test: invalid proof is rejected."""
    params = generate_parameters(1024)
    prover = SigmaProver(params)
    verifier = SigmaVerifier(params)

    secret, _ = prover.generate_keypair()
    state_commitment = 0xABCD1234
    proof = prover.prove_state(state_commitment, secret)

    # Verify against a different state commitment
    valid = verifier.verify_state(proof, 0xDEADBEEF)
    assert not valid, "Proof should be invalid for different state commitment"


def test_sigma_protocol_tampered():
    """Negative test: tampered proof is rejected."""
    params = generate_parameters(1024)
    prover = SigmaProver(params)
    verifier = SigmaVerifier(params)

    secret, _ = prover.generate_keypair()
    state_commitment = 0xABCD1234
    proof = prover.prove_state(state_commitment, secret)

    from dataclasses import replace

    tampered = replace(proof, response=proof.response ^ 0xFF)
    valid = verifier.verify_state(tampered, state_commitment)
    assert not valid, "Tampered proof should be invalid"


# =========================================================================
# State Machine Tests
# =========================================================================


def test_state_machine_transition():
    """Positive test: valid state transition is accepted."""
    sm = StateMachine(initial_state=42)
    state_proof = sm.transition(100)

    assert sm.get_state_commitment() is not None
    assert state_proof.nonce == 1

    valid = sm.verify_transition(state_proof)
    assert valid, "Valid transition should be accepted"


def test_state_machine_invalid_transition():
    """Negative test: invalid transition (wrong secret) is rejected."""
    params = generate_parameters(1024)
    sm = StateMachine(initial_state=42, group=params)

    from scripts.zk_state.sigma_protocol import SigmaProver
    from scripts.zk_state.state_machine import StateProof
    import hashlib

    h = hashlib.sha256()
    h.update(str(100).encode())
    h.update(str(sm.get_public_key()).encode())
    wrong_commitment = int.from_bytes(h.digest(), "big")

    wrong_prover = SigmaProver(params)
    wrong_secret, _ = wrong_prover.generate_keypair()
    wrong_proof = wrong_prover.prove_state(wrong_commitment, wrong_secret)

    fake_proof = StateProof(
        state_commitment=wrong_commitment,
        transition_proof=wrong_proof,
        timestamp=time.time(),
        nonce=999,
    )

    valid = sm.verify_transition(fake_proof)
    assert not valid, "Invalid transition should be rejected"


def test_state_machine_replay():
    """Negative test: replay attack is detected."""
    sm = StateMachine(initial_state=42)
    state_proof = sm.transition(100)

    valid_first = sm.verify_transition(state_proof)
    assert valid_first, "First verification should pass"

    valid_replay = sm.verify_transition(state_proof)
    assert not valid_replay, "Replay should be rejected (same StateProof)"

    from dataclasses import replace
    proof_copy = replace(state_proof)
    valid_copy = sm.verify_transition(proof_copy)
    assert not valid_copy, "Direct replay of a copy should also be rejected"


def test_state_machine_wrong_state_commitment():
    """Negative test: proof with a different state commitment (same secret key) is rejected."""
    params = generate_parameters(1024)
    prover = SigmaProver(params)
    secret, public_key = prover.generate_keypair()

    sm = StateMachine(initial_state=42, group=params, secret=secret)
    sm.transition(100)

    wrong_commitment = 0xBADBAD
    wrong_proof = prover.prove_state(wrong_commitment, secret)

    from scripts.zk_state.state_machine import StateProof
    import time

    fake_proof = StateProof(
        state_commitment=wrong_commitment,
        transition_proof=wrong_proof,
        timestamp=time.time(),
        nonce=999,
    )

    valid = sm.verify_transition(fake_proof)
    assert not valid, "Proof with wrong state commitment should be rejected"


def test_cross_verifier_replay():
    """Negative test: proof from one SM is rejected by another SM with same key."""
    params = generate_parameters(1024)
    prover = SigmaProver(params)
    secret, public_key = prover.generate_keypair()

    sm1 = StateMachine(initial_state=42, group=params, secret=secret)
    state_proof = sm1.transition(100)

    valid = sm1.verify_transition(state_proof)
    assert valid, "SM1 should accept its own proof"

    sm2 = StateMachine(initial_state=999, group=params, secret=secret)
    valid_cross = sm2.verify_transition(state_proof)
    assert not valid_cross, "SM2 (different state) should reject SM1's proof"


# =========================================================================
# Phase ZK State Integration Tests
# =========================================================================


def test_phase_zk_state_runs():
    """Integration test: phase_zk_state with --zk-state=True returns valid manifest."""
    from scripts.phases.phase_zk_state import phase_zk_state

    class FakeArgs:
        zk_state = True
        zk_state_config = ""
        build_dir = "/tmp"

    manifest = phase_zk_state(FakeArgs())
    assert manifest is not None, "Should return a manifest when enabled"
    assert manifest["zk_state"] is True
    assert manifest["state_machine"]["transition_valid"] is True
    assert manifest["latency_ms"]["total"] > 0


def test_phase_zk_state_disabled():
    """Integration test: phase_zk_state with --zk-state=False returns None."""
    from scripts.phases.phase_zk_state import phase_zk_state

    class FakeArgs:
        zk_state = False

    manifest = phase_zk_state(FakeArgs())
    assert manifest is None, "Should return None when disabled"


# =========================================================================
# Prover/Verifier Roundtrip Tests
# =========================================================================


def test_prover_verifier_roundtrip():
    """Positive test: full prover → verifier roundtrip works."""
    prover = StateBoundProver()
    verifier = StateBoundVerifier(group=prover.group)

    state = 0xCAFE
    inputs = {"_function": "test_fn", "x": 42, "y": "hello"}

    execution_proof = prover.prove_execution(inputs, state)
    result = verifier.verify_execution(execution_proof, state)

    assert result.valid, "Execution proof should be valid"
    assert result.state_match, "State commitment should match"
    assert result.replay_safe, "Nonce should be fresh"
    assert result.latency_ms >= 0.0, "Latency should be non-negative"


def test_prover_invalid_state():
    """Negative test: invalid state is rejected by verifier."""
    prover = StateBoundProver()
    verifier = StateBoundVerifier(group=prover.group)

    state = 0xCAFE
    inputs = {"_function": "test_fn", "x": 42}
    execution_proof = prover.prove_execution(inputs, state)

    result = verifier.verify_execution(execution_proof, 0xBEEF)
    assert not result.valid, "Proof for different state should be invalid"
    assert not result.state_match, "State should not match"


def test_verifier_replay_detection():
    """Positive test: replay detection works."""
    prover = StateBoundProver()
    verifier = StateBoundVerifier(group=prover.group)

    state = 0xCAFE
    inputs = {"_function": "test_fn", "x": 1}

    proof1 = prover.prove_execution(inputs, state)
    result1 = verifier.verify_execution(proof1, state)
    assert result1.replay_safe, "First use should be replay-safe"

    proof2 = prover.prove_execution(inputs, state)
    result2 = verifier.verify_execution(proof2, state)
    assert result2.replay_safe, "Second use (different nonce) should be safe"

    replay_check = verifier.check_replay(proof1)
    assert not replay_check, "Already-seen nonce should be rejected"


# =========================================================================
# Configuration Tests
# =========================================================================


def test_config_defaults():
    """Test that default config is disabled with safe defaults."""
    config = ZKStateConfig()
    assert config.enabled is False
    assert config.state_file == ""
    assert config.require_online is False
    assert config.proof_cache_size == 100


def test_config_loading():
    """Test loading config from args."""
    class FakeArgs:
        zk_state = True
        zk_state_config = ""

    config = load_config(FakeArgs())
    assert config.enabled is True
    assert config.state_file == ""
    assert config.require_online is False


def test_config_disabled():
    """Test config remains disabled when flag not set."""
    class FakeArgs:
        zk_state = False
        zk_state_config = ""

    config = load_config(FakeArgs())
    assert config.enabled is False


def test_config_from_file():
    """Test loading config from a JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"state_file": "/tmp/zk.state", "require_online": True, "proof_cache_size": 50}, f)
        config_path = f.name

    try:
        class FakeArgs:
            zk_state = True
            zk_state_config = config_path

        config = load_config(FakeArgs())
        assert config.enabled is True
        assert config.state_file == "/tmp/zk.state"
        assert config.require_online is True
        assert config.proof_cache_size == 50
    finally:
        os.unlink(config_path)


def test_offline_mode():
    """Test that ZK state works in offline mode (no state file)."""
    class FakeArgs:
        zk_state = True
        zk_state_config = ""

    config = load_config(FakeArgs())
    assert config.enabled is True
    assert config.state_file == ""

    prover = StateBoundProver()
    verifier = StateBoundVerifier(group=prover.group)

    state = 42
    inputs = {"_function": "offline_test", "data": "test"}
    proof = prover.prove_execution(inputs, state)
    result = verifier.verify_execution(proof, state)
    assert result.valid, "Offline mode should work"


def test_check_prerequisites():
    """Test that prerequisites check passes."""
    assert check_prerequisites() is True
