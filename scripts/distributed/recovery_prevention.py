import hashlib
import math
import multiprocessing as mp
import os
import random
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class NodeSlice:
    node_id: int
    instruction_count: int
    visible_ops: List[str]
    local_data: bytes
    noise_traffic: int


@dataclass
class TrafficMessage:
    source: int
    destination: int
    payload: bytes
    is_noise: bool
    timestamp: float
    length: int


class ExecutionRecoveryPreventer:
    def __init__(self, num_nodes: int = 5, mode: str = "simulation"):
        if num_nodes < 3:
            raise ValueError("num_nodes must be >= 3")
        self.num_nodes = num_nodes
        self.mode = mode
        self._node_slices: Dict[int, NodeSlice] = {}
        self._traffic_log: List[TrafficMessage] = []
        self._lock = threading.Lock()
        self._full_algorithm: Optional[str] = None
        self._node_fragments: Dict[int, List[str]] = {}
        self._traffic_key = os.urandom(32)

        for nid in range(num_nodes):
            self._node_fragments[nid] = []

    def _derive_noise_key(self, source: int, dest: int, counter: int) -> bytes:
        data = self._traffic_key + struct.pack(">III", source, dest, counter)
        return hashlib.sha256(data).digest()

    def partition_algorithm(self, algorithm_ops: List[str]) -> Dict[int, NodeSlice]:
        if len(algorithm_ops) < 10:
            raise ValueError("algorithm must have at least 10 operations for meaningful partitioning")

        total_ops = len(algorithm_ops)
        ops_per_node = max(1, total_ops // self.num_nodes)

        partitions: Dict[int, NodeSlice] = {}
        for nid in range(self.num_nodes):
            if self.mode == "interleaved":
                visible = [algorithm_ops[i] for i in range(total_ops) if i % self.num_nodes == nid]
            else:
                start = nid * ops_per_node
                end = start + ops_per_node if nid < self.num_nodes - 1 else total_ops
                visible = algorithm_ops[start:end]
            local_data = os.urandom(32)

            self._node_fragments[nid] = visible

            partitions[nid] = NodeSlice(
                node_id=nid,
                instruction_count=len(visible),
                visible_ops=visible,
                local_data=local_data,
                noise_traffic=0,
            )

        self._node_slices = partitions
        self._full_algorithm = "\n".join(algorithm_ops)
        return partitions

    def generate_noise_traffic(self, density: int = 10) -> List[TrafficMessage]:
        now = time.time()
        messages = []

        for nid in range(self.num_nodes):
            for _ in range(density):
                dest = random.choice([d for d in range(self.num_nodes) if d != nid])
                key = self._derive_noise_key(nid, dest, len(self._traffic_log))
                payload = hashlib.sha256(key + struct.pack(">d", now)).digest()

                msg = TrafficMessage(
                    source=nid,
                    destination=dest,
                    payload=payload,
                    is_noise=True,
                    timestamp=now + random.uniform(-0.001, 0.001),
                    length=32,
                )
                messages.append(msg)

        return messages

    def generate_real_traffic(self, source: int, dest: int, data: bytes, timestamp: Optional[float] = None) -> TrafficMessage:
        return TrafficMessage(
            source=source,
            destination=dest,
            payload=data,
            is_noise=False,
            timestamp=timestamp if timestamp is not None else time.time(),
            length=len(data),
        )

    def mix_traffic(self, real_messages: List[TrafficMessage], noise_messages: List[TrafficMessage]) -> List[TrafficMessage]:
        mixed = real_messages + noise_messages
        random.shuffle(mixed)

        with self._lock:
            for msg in mixed:
                if msg.is_noise and msg.source in self._node_slices:
                    self._node_slices[msg.source].noise_traffic += 1
            self._traffic_log.extend(mixed)

        return mixed

    def get_constant_time_traffic(self, num_nodes: int, batch_size: int = 5) -> List[TrafficMessage]:
        now = time.time()
        traffic = []

        for i in range(batch_size):
            for src in range(num_nodes):
                for dst in range(num_nodes):
                    if src == dst:
                        continue
                    key = self._derive_noise_key(src, dst, i)
                    payload = hashlib.sha256(key + struct.pack(">II", src, dst)).digest()
                    msg = TrafficMessage(
                        source=src,
                        destination=dst,
                        payload=payload,
                        is_noise=True,
                        timestamp=now,
                        length=32,
                    )
                    traffic.append(msg)

        return traffic

    def attempt_reconstruct_from_single_node(self, node_id: int) -> Optional[str]:
        fragment = self._node_fragments.get(node_id, [])
        if not fragment:
            return None

        return "\n".join(fragment)

    def attempt_reconstruct_from_traffic(self) -> Optional[str]:
        with self._lock:
            if not self._traffic_log:
                return None

            noise_count = sum(1 for m in self._traffic_log if m.is_noise)
            total_count = len(self._traffic_log)
            noise_ratio = noise_count / total_count if total_count > 0 else 0

            if noise_ratio < 0.3:
                return None

            if self._full_algorithm:
                recovered_ops = set()
                for msg in self._traffic_log:
                    if not msg.is_noise:
                        try:
                            payload_str = msg.payload.decode()
                            if payload_str and len(payload_str) > 3:
                                recovered_ops.add(payload_str)
                        except Exception:
                            pass

                recovered_ops = sorted(recovered_ops)
                if recovered_ops and len(recovered_ops) >= 3:
                    reconstructed = "\n".join(recovered_ops)
                    full_len = len(self._full_algorithm)
                    recon_len = len(reconstructed)
                    if recon_len > 0 and (recon_len / max(full_len, 1)) > 0.1:
                        return reconstructed

                noise_pattern = hashlib.sha256(self._traffic_key).digest()
                distinguishing = []
                for msg in self._traffic_log:
                    if not msg.is_noise and msg.payload != noise_pattern:
                        try:
                            candidate = msg.payload.decode()
                            if candidate and all(c.isprintable() or c in "\n\r\t" for c in candidate):
                                distinguishing.append(candidate)
                        except Exception:
                            pass
                if distinguishing:
                    return "\n".join(distinguishing)

        return None

    def is_traffic_indistinguishable(self) -> Tuple[bool, float]:
        with self._lock:
            if not self._traffic_log:
                # Fail-closed: no traffic observed proves nothing about
                # indistinguishability. (False, 0.0), never a vacuous pass.
                return False, 0.0

            noise_msgs = [m for m in self._traffic_log if m.is_noise]
            real_msgs = [m for m in self._traffic_log if not m.is_noise]

            if not real_msgs:
                # Fail-closed: nothing real to hide is not evidence of
                # cover (a misconfigured run logs noise only).
                return False, 0.0

            if not noise_msgs:
                return False, 0.0

            noise_lengths = [m.length for m in noise_msgs]
            real_lengths = [m.length for m in real_msgs]

            avg_noise_len = sum(noise_lengths) / len(noise_lengths)
            avg_real_len = sum(real_lengths) / len(real_lengths)
            length_ratio = min(avg_noise_len, avg_real_len) / max(avg_noise_len, avg_real_len) if max(avg_noise_len, avg_real_len) > 0 else 1.0

            noise_times = sorted([m.timestamp for m in noise_msgs])
            real_times = sorted([m.timestamp for m in real_msgs])

            def _compute_freq_and_jitter(timestamps):
                if len(timestamps) < 2:
                    return 0.0, 0.0
                intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
                avg_interval = sum(intervals) / len(intervals)
                jitter = sum(abs(iv - avg_interval) for iv in intervals) / len(intervals) / max(avg_interval, 1e-9) if avg_interval > 0 else 0
                return 1.0 / max(avg_interval, 1e-9), jitter

            noise_freq, noise_jitter = _compute_freq_and_jitter(noise_times)
            real_freq, real_jitter = _compute_freq_and_jitter(real_times)

            freq_ratio = min(noise_freq, real_freq) / max(noise_freq, real_freq) if max(noise_freq, real_freq) > 0 else 1.0
            jitter_diff = abs(noise_jitter - real_jitter)

            def _entropy(data):
                if not data:
                    return 0.0
                freq = {}
                for b in data:
                    freq[b] = freq.get(b, 0) + 1
                ent = 0.0
                for count in freq.values():
                    p = count / len(data)
                    if p > 0:
                        ent -= p * math.log2(p)
                return ent

            noise_entropy = sum(_entropy(m.payload) for m in noise_msgs) / max(len(noise_msgs), 1)
            real_entropy = sum(_entropy(m.payload) for m in real_msgs) / max(len(real_msgs), 1)
            entropy_ratio = min(noise_entropy, real_entropy) / max(noise_entropy, real_entropy) if max(noise_entropy, real_entropy) > 0 else 1.0

            combined_ratio = (length_ratio + freq_ratio + entropy_ratio) / 3.0
            combined_ratio = combined_ratio * (1.0 - min(jitter_diff, 0.5))

            return combined_ratio > 0.6, combined_ratio

    def is_constant_time_traffic(self) -> bool:
        with self._lock:
            if not self._traffic_log:
                # Fail-closed: an empty log is not constant-time traffic.
                return False

            msgs_per_source: Dict[int, List[float]] = {}
            for msg in self._traffic_log:
                msgs_per_source.setdefault(msg.source, []).append(msg.timestamp)

            for src, timestamps in msgs_per_source.items():
                if len(timestamps) < 2:
                    continue
                intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
                if not intervals:
                    continue
                avg = sum(intervals) / len(intervals)
                for interval in intervals:
                    if avg > 0 and abs(interval - avg) / avg > 0.5:
                        return False

            return True

    def run_multiprocess(self, algorithm_ops: List[str]) -> bool:
        partitions = self.partition_algorithm(algorithm_ops)
        processes = []
        queues = []
        noise_queues = []
        for nid in range(self.num_nodes):
            q = mp.Queue()
            nq = mp.Queue()
            queues.append(q)
            noise_queues.append(nq)
            visible = self._node_fragments.get(nid, [])
            p = mp.Process(target=_slice_process, args=(nid, visible, q, nq))
            processes.append(p)
            p.start()

        for nid in range(self.num_nodes):
            try:
                _ = queues[nid].get(timeout=5)
            except Exception:
                pass

        for nid in range(self.num_nodes):
            try:
                noise_data = noise_queues[nid].get(timeout=5)
                if noise_data:
                    for payload in noise_data:
                        self._traffic_log.append(TrafficMessage(
                            source=nid,
                            destination=random.choice([d for d in range(self.num_nodes) if d != nid]),
                            payload=payload,
                            is_noise=True,
                            timestamp=time.time() + random.uniform(-0.001, 0.001),
                            length=32,
                        ))
            except Exception:
                pass

        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)

        noise = self.generate_noise_traffic(density=10)
        self.mix_traffic([], noise)
        return True


def _slice_process(node_id: int, visible_ops: List[str], queue, noise_queue):
    import hashlib
    import os
    import struct
    import time
    local_data = os.urandom(16)
    checksum = hashlib.sha256(local_data + "\n".join(visible_ops).encode()).digest()

    noise_payloads = []
    ops_executed = []
    for op in visible_ops:
        op_hash = hashlib.sha256(op.encode()).digest()
        xored = bytes(a ^ b for a, b in zip(op_hash, local_data[:len(op_hash)]))
        ops_executed.append(xored)
        noise_payloads.append(hashlib.sha256(xored + struct.pack(">I", node_id)).digest())

    result = hashlib.sha256(b"".join(ops_executed) + checksum).digest()
    queue.put((node_id, len(visible_ops), result))
    noise_queue.put(noise_payloads)
