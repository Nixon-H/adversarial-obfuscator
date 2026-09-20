"""
bench_zk_state.py

Benchmarks for ZK State-Bound Execution.

Measures proof generation, verification, and state transition latency.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from scripts.zk_state.sigma_protocol import SigmaProver, SigmaVerifier, generate_parameters
from scripts.zk_state.state_machine import StateMachine
from scripts.zk_state.prover import StateBoundProver
from scripts.zk_state.verifier import StateBoundVerifier


@pytest.fixture(scope="module")
def bench_params():
    return generate_parameters(1024)


@pytest.fixture(scope="module")
def bench_keypair(bench_params):
    prover = SigmaProver(bench_params)
    secret, public_key = prover.generate_keypair()
    return prover, secret, public_key


def test_bench_sigma_proof_generation(benchmark, bench_params):
    prover = SigmaProver(bench_params)
    secret, _ = prover.generate_keypair()
    state_commitment = 0xABCD
    benchmark(prover.prove_state, state_commitment, secret)


def test_bench_sigma_verification(benchmark, bench_params):
    prover = SigmaProver(bench_params)
    verifier = SigmaVerifier(bench_params)
    secret, _ = prover.generate_keypair()
    state_commitment = 0xABCD
    proof = prover.prove_state(state_commitment, secret)
    benchmark(verifier.verify_state, proof, state_commitment)


def test_bench_state_machine_transition(benchmark, bench_params):
    sm = StateMachine(initial_state=0, group=bench_params)

    def _run():
        sp = sm.transition(100)
        assert sm.verify_transition(sp)

    benchmark(_run)


def test_bench_proof_serialization_size(benchmark, bench_params):
    prover = SigmaProver(bench_params)
    secret, _ = prover.generate_keypair()
    state_commitment = 0xABCD
    proof = prover.prove_state(state_commitment, secret)

    def _serialize():
        import json
        json.dumps({
            "commitment": proof.commitment,
            "challenge": proof.challenge,
            "response": proof.response,
            "public_key": proof.public_key,
        })

    benchmark(_serialize)


def test_bench_full_roundtrip(benchmark):
    prover = StateBoundProver()
    verifier = StateBoundVerifier(group=prover.group)
    state = 0xCAFE
    inputs = {"_function": "bench_fn", "x": 42, "_i": 0}

    def _run():
        p = prover.prove_execution(inputs, state)
        verifier.verify_execution(p, state)

    benchmark(_run)
