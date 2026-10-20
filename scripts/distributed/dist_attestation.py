"""
Distributed attestation orchestration (cross-host challenges).

TWIN: runtime/src/sw_attestation.rs (in-artifact challenge/response core)
— that module answers challenges inside one artifact; this module
coordinates them between hosts. Do not merge.
"""
import hashlib
import os
import random
import struct
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class AttestationChallenge:
    challenger_id: int
    challenge_data: bytes
    timestamp: float
    deadline: float


@dataclass
class AttestationResponse:
    responder_id: int
    response_data: bytes
    timestamp: float
    success: bool


@dataclass
class NodeState:
    node_id: int
    secret: bytes
    alive: bool
    attestation_count: int
    failed_attestations: int


class DistributedAttestation:
    def __init__(self, num_nodes: int = 5, challenge_timeout: float = 5.0, max_failures: int = 3, mode: str = "simulation"):
        if num_nodes < 2:
            raise ValueError("num_nodes must be >= 2")
        self.num_nodes = num_nodes
        self.challenge_timeout = challenge_timeout
        self.max_failures = max_failures
        self.mode = mode
        self._nodes: Dict[int, NodeState] = {}
        self._lock = threading.Lock()
        self._self_destructed = False
        self._self_destruct_reason: Optional[str] = None

        for nid in range(num_nodes):
            self._nodes[nid] = NodeState(
                node_id=nid,
                secret=os.urandom(32),
                alive=True,
                attestation_count=0,
                failed_attestations=0,
            )

    def _derive_pair_secret(self, node_a: int, node_b: int) -> bytes:
        secret_a = self._nodes.get(node_a)
        secret_b = self._nodes.get(node_b)
        if secret_a is None or secret_b is None:
            return b""
        combined = bytearray(64)
        combined[:32] = secret_a.secret
        combined[32:] = secret_b.secret
        return hashlib.sha256(bytes(combined) + struct.pack(">II", node_a, node_b)).digest()

    def create_challenge(self, challenger_id: int, responder_id: int) -> Optional[AttestationChallenge]:
        if self._self_destructed:
            return None
        with self._lock:
            challenger = self._nodes.get(challenger_id)
            responder = self._nodes.get(responder_id)
            if challenger is None or responder is None:
                return None
            if not challenger.alive or not responder.alive:
                return None

            pair_secret = self._derive_pair_secret(challenger_id, responder_id)
            if not pair_secret:
                return None

            nonce = os.urandom(16)
            challenge_data = struct.pack(">II", challenger_id, responder_id) + nonce
            challenge_sig = hashlib.sha256(pair_secret + challenge_data).digest()
            full_challenge = challenge_data + challenge_sig

            jitter = random.uniform(0, max(0.001, self.challenge_timeout * 0.1))
            deadline = time.time() + self.challenge_timeout + jitter

            return AttestationChallenge(
                challenger_id=challenger_id,
                challenge_data=full_challenge,
                timestamp=time.time(),
                deadline=deadline,
            )

    def respond_to_challenge(self, responder_id: int, challenge: AttestationChallenge) -> Optional[AttestationResponse]:
        if self._self_destructed:
            return None
        jitter = random.uniform(0, 0.01)
        time.sleep(jitter)

        with self._lock:
            responder = self._nodes.get(responder_id)
            challenger = self._nodes.get(challenge.challenger_id)
            if responder is None or challenger is None:
                return AttestationResponse(responder_id, b"", time.time(), False)

            if time.time() > challenge.deadline:
                responder.failed_attestations += 1
                self._check_self_destruct(responder_id)
                return AttestationResponse(responder_id, b"", time.time(), False)

            pair_secret = self._derive_pair_secret(challenge.challenger_id, responder_id)
            if not pair_secret:
                responder.failed_attestations += 1
                self._check_self_destruct(responder_id)
                return AttestationResponse(responder_id, b"", time.time(), False)

            challenge_data = challenge.challenge_data[:-32]
            challenge_sig = challenge.challenge_data[-32:]
            expected_sig = hashlib.sha256(pair_secret + challenge_data).digest()
            if challenge_sig != expected_sig:
                responder.failed_attestations += 1
                self._check_self_destruct(responder_id)
                return AttestationResponse(responder_id, b"", time.time(), False)

            response_nonce = os.urandom(16)
            response_data = challenge_data + response_nonce
            response_sig = hashlib.sha256(pair_secret + response_data + b"OK").digest()

            responder.attestation_count += 1
            return AttestationResponse(
                responder_id=responder_id,
                response_data=response_data + response_sig,
                timestamp=time.time(),
                success=True,
            )

    def verify_response(self, challenger_id: int, response: AttestationResponse) -> bool:
        if self._self_destructed:
            return False
        with self._lock:
            challenger = self._nodes.get(challenger_id)
            if challenger is None or not challenger.alive:
                return False

            if time.time() > response.timestamp + self.challenge_timeout:
                return False

            if not response.success:
                return False

            pair_secret = self._derive_pair_secret(challenger_id, response.responder_id)
            if not pair_secret:
                return False

            response_data = response.response_data[:-32]
            response_sig = response.response_data[-32:]
            expected_sig = hashlib.sha256(pair_secret + response_data + b"OK").digest()
            return response_sig == expected_sig

    def run_pairwise_attestation(self) -> Dict[Tuple[int, int], bool]:
        if self.mode == "multiprocess":
            return self._run_multiprocess()
        results = {}
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                if self._self_destructed:
                    break
                challenge = self.create_challenge(i, j)
                if challenge is None:
                    results[(i, j)] = False
                    continue
                response = self.respond_to_challenge(j, challenge)
                if response is None:
                    results[(i, j)] = False
                    continue
                verified = self.verify_response(i, response)
                results[(i, j)] = verified
        return results

    def _run_multiprocess(self) -> Dict[Tuple[int, int], bool]:
        import multiprocessing as mp
        processes = []
        in_queues = {}
        out_queues = {}
        for nid in range(self.num_nodes):
            in_queues[nid] = mp.Queue()
            out_queues[nid] = mp.Queue()

        for nid in range(self.num_nodes):
            secret = self._nodes[nid].secret
            p = mp.Process(
                target=_attest_node,
                args=(nid, secret, in_queues[nid], out_queues[nid],
                      self.challenge_timeout, self.max_failures),
            )
            processes.append(p)
            p.start()

        results = {}
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                if self._self_destructed:
                    results[(i, j)] = False
                    continue

                challenge = self.create_challenge(i, j)
                if challenge is None:
                    results[(i, j)] = False
                    continue

                pair_secret = self._derive_pair_secret(i, j)
                in_queues[j].put((challenge, j, pair_secret))

                try:
                    response = out_queues[j].get(timeout=self.challenge_timeout + 2)
                    verified = self.verify_response(i, response)
                    results[(i, j)] = verified
                except Exception:
                    results[(i, j)] = False

        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)

        any_failed = not all(results.values())
        if any_failed:
            self._self_destruct("multiprocess attestation failed")
        return results

    def run_consensus_protocol(self) -> bool:
        results = self.run_pairwise_attestation()
        all_passed = all(results.values())
        if not all_passed:
            self._self_destruct("consensus protocol: pairwise attestation failed")
        return all_passed

    def _check_self_destruct(self, node_id: int):
        node = self._nodes.get(node_id)
        if node and node.failed_attestations >= self.max_failures:
            self._self_destruct(f"node {node_id} exceeded max failed attestations")

    def _self_destruct(self, reason: str):
        self._self_destructed = True
        self._self_destruct_reason = reason
        for node in self._nodes.values():
            node.alive = False

    def is_self_destructed(self) -> bool:
        return self._self_destructed

    def get_self_destruct_reason(self) -> Optional[str]:
        return self._self_destruct_reason

    def simulate_node_failure(self, node_id: int):
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.alive = False

    def recover_node(self, node_id: int):
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.alive = True
                node.failed_attestations = 0


def _attest_node(node_id: int, secret: bytes, in_queue, out_queue,
                 challenge_timeout: float, max_failures: int):
    import hashlib
    import os
    import random
    import time

    failed = 0
    while True:
        try:
            msg = in_queue.get(timeout=challenge_timeout + 1)
        except Exception:
            return

        if msg is None:
            return

        challenge, expected_id, pair_secret = msg

        if expected_id != node_id:
            resp = AttestationResponse(node_id, b"", time.time(), False)
            out_queue.put(resp)
            continue

        jitter = random.uniform(0, 0.01)
        time.sleep(jitter)

        now = time.time()
        if now > challenge.deadline:
            failed += 1
            resp = AttestationResponse(node_id, b"", now, False)
            out_queue.put(resp)
            if failed >= max_failures:
                return
            continue

        challenge_data = challenge.challenge_data[:-32]
        challenge_sig = challenge.challenge_data[-32:]
        expected_sig = hashlib.sha256(pair_secret + challenge_data).digest()

        if challenge_sig != expected_sig:
            failed += 1
            resp = AttestationResponse(node_id, b"", time.time(), False)
            out_queue.put(resp)
            if failed >= max_failures:
                return
            continue

        response_nonce = os.urandom(16)
        response_data = challenge_data + response_nonce
        response_sig = hashlib.sha256(pair_secret + response_data + b"OK").digest()

        resp = AttestationResponse(
            responder_id=node_id,
            response_data=response_data + response_sig,
            timestamp=time.time(),
            success=True,
        )
        out_queue.put(resp)
