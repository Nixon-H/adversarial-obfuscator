import hashlib
import hmac
import multiprocessing
import os
import struct
from dataclasses import dataclass, field
from multiprocessing.shared_memory import SharedMemory
from typing import List, Optional, Tuple


@dataclass
class FragmentState:
    fragment_id: int
    data: bytes
    process_id: int
    process_entropy: int


@dataclass
class CrossProcessChain:
    fragments: List[FragmentState]
    shared_memory_key: bytes
    key_bindings: List[Tuple[int, int, bytes]]

    def serialize(self) -> bytes:
        buf = struct.pack(">I", len(self.fragments))
        for fs in self.fragments:
            buf += struct.pack(">IIQ", fs.fragment_id, fs.process_id, fs.process_entropy)
            buf += struct.pack(">I", len(fs.data)) + fs.data
        buf += struct.pack(">I", len(self.shared_memory_key)) + self.shared_memory_key
        buf += struct.pack(">I", len(self.key_bindings))
        for pid, fid, key in self.key_bindings:
            buf += struct.pack(">II", pid, fid)
            buf += struct.pack(">I", len(key)) + key
        return buf

    @classmethod
    def deserialize(cls, data: bytes) -> "CrossProcessChain":
        offset = 0
        nfrags = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        frags = []
        for _ in range(nfrags):
            fid, pid, pent = struct.unpack(">IIQ", data[offset:offset+16])
            offset += 16
            dlen = struct.unpack(">I", data[offset:offset+4])[0]
            offset += 4
            fdata = data[offset:offset+dlen]
            offset += dlen
            frags.append(FragmentState(fid, fdata, pid, pent))
        klen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        smk = data[offset:offset+klen]
        offset += klen
        nbinds = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        binds = []
        for _ in range(nbinds):
            pid, fid = struct.unpack(">II", data[offset:offset+8])
            offset += 8
            klen2 = struct.unpack(">I", data[offset:offset+4])[0]
            offset += 4
            key = data[offset:offset+klen2]
            offset += klen2
            binds.append((pid, fid, key))
        return cls(frags, smk, binds)


class CrossProcessBinder:
    def __init__(self, shared_secret: Optional[bytes] = None):
        self.shared_secret = shared_secret or os.urandom(32)

    def _process_entropy(self) -> int:
        return int.from_bytes(os.urandom(8), "big")

    def _derive_process_key(self, pid: int, entropy: int, fragment_id: int) -> bytes:
        data = self.shared_secret + struct.pack(">IQQ", pid, entropy, fragment_id)
        return hashlib.sha256(data).digest()

    def _shared_memory_name(self, pid_a: int, pid_b: int) -> str:
        low = min(pid_a, pid_b)
        high = max(pid_a, pid_b)
        h = hashlib.sha256(struct.pack(">II", low, high)).hexdigest()[:16]
        return f"nx_shm_{h}"

    def bind_across_processes(self, fragments: List[Tuple[bytes, int]]) -> CrossProcessChain:
        if not fragments:
            raise ValueError("no fragments provided")

        chain_fragments = []
        key_bindings = []

        for fid, (data, pid) in enumerate(fragments):
            entropy = self._process_entropy()
            key = self._derive_process_key(pid, entropy, fid)
            fs = FragmentState(
                fragment_id=fid,
                data=data,
                process_id=pid,
                process_entropy=entropy,
            )
            chain_fragments.append(fs)
            key_bindings.append((pid, fid, key))

        transport_key = hashlib.sha256(self.shared_secret + b"SHARED_MEMORY").digest()

        return CrossProcessChain(
            fragments=chain_fragments,
            shared_memory_key=transport_key,
            key_bindings=key_bindings,
        )

    def verify_process_binding(self, chain: CrossProcessChain, pid: int, fragment_id: int) -> bool:
        for ps in chain.fragments:
            if ps.fragment_id == fragment_id:
                expected_pid = ps.process_id
                if expected_pid != pid:
                    return False
                expected_key = self._derive_process_key(pid, ps.process_entropy, fragment_id)
                for bind_pid, bind_fid, bind_key in chain.key_bindings:
                    if bind_pid == pid and bind_fid == fragment_id:
                        return bind_key == expected_key
                return False
        return False

    def _shm_name(self, tag: str) -> str:
        h = hashlib.sha256(self.shared_secret + tag.encode()).hexdigest()[:16]
        return f"nx_cross_{h}"

    def _write_shm(self, name: str, data: bytes) -> SharedMemory:
        size = len(data) + 8
        shm = SharedMemory(name=name, create=True, size=size)
        struct.pack_into(">Q", shm.buf, 0, len(data))
        shm.buf[8:8 + len(data)] = data
        return shm

    def _read_shm(self, name: str) -> Optional[bytes]:
        try:
            shm = SharedMemory(name=name, create=False)
            data_len = struct.unpack(">Q", shm.buf[:8])[0]
            data = bytes(shm.buf[8:8 + data_len])
            shm.close()
            return data
        except FileNotFoundError:
            return None

    def _close_shm(self, name: str, shm: SharedMemory):
        shm.close()
        try:
            shm.unlink()
        except FileNotFoundError:
            pass

    def _worker_process(self, shm_name: str, fragment_id: int, data: bytes,
                        pid_val: int, entropy: int, shared_secret_bytes: bytes,
                        result_shm_name: str):
        key_derived = hashlib.sha256(
            shared_secret_bytes + struct.pack(">IQQ", pid_val, entropy, fragment_id)
        ).digest()
        xored = bytes(a ^ b for a, b in zip(data, key_derived[:len(data)]))
        shm = SharedMemory(name=shm_name, create=False)
        stored_len = struct.unpack(">Q", shm.buf[:8])[0]
        stored_data = bytes(shm.buf[8:8 + stored_len])
        xored_size = len(xored)
        combined_size = 8 + stored_len + xored_size
        result_shm = SharedMemory(name=result_shm_name, create=True, size=combined_size + 8)
        struct.pack_into(">Q", result_shm.buf, 0, combined_size)
        struct.pack_into(">Q", result_shm.buf, 8, stored_len)
        result_shm.buf[16:16 + stored_len] = stored_data
        result_shm.buf[16 + stored_len:16 + stored_len + xored_size] = xored
        result_shm.close()
        shm.close()

    def bind_and_execute(self, fragments: List[Tuple[bytes, int]]) -> List[bytes]:
        chain = self.bind_across_processes(fragments)
        processes = []
        shm_names = []
        result_names = []

        for fs in chain.fragments:
            shm_name = self._shm_name(f"frag_{fs.fragment_id}_{fs.process_id}")
            shm_names.append(shm_name)
            shm = self._write_shm(shm_name, fs.data)
            shm.close()

            result_name = self._shm_name(f"result_{fs.fragment_id}_{fs.process_id}")
            result_names.append(result_name)

            p = multiprocessing.Process(
                target=self._worker_process,
                args=(
                    shm_name, fs.fragment_id, fs.data,
                    fs.process_id, fs.process_entropy,
                    self.shared_secret, result_name,
                ),
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        results = []
        for i, fs in enumerate(chain.fragments):
            data = self._read_shm(result_names[i])
            if data is None:
                raise RuntimeError(f"failed to read result for fragment {fs.fragment_id}")
            stored_len = struct.unpack(">Q", data[:8])[0]
            xored_start = 8 + stored_len
            results.append(data[xored_start:])
            try:
                shm = SharedMemory(name=result_names[i])
                self._close_shm(result_names[i], shm)
            except FileNotFoundError:
                pass
            try:
                shm2 = SharedMemory(name=shm_names[i])
                self._close_shm(shm_names[i], shm2)
            except FileNotFoundError:
                pass

        return results

    def transfer_state(self, chain: CrossProcessChain, from_pid: int, to_pid: int, fragment_id: int) -> Optional[bytes]:
        source = None
        for ps in chain.fragments:
            if ps.fragment_id == fragment_id and ps.process_id == from_pid:
                source = ps.data
                break
        if source is None:
            return None

        if not self.verify_process_binding(chain, from_pid, fragment_id):
            return None

        sm_name = self._shared_memory_name(from_pid, to_pid)
        state = source + sm_name.encode()
        key = hashlib.sha256(self.shared_secret + struct.pack(">II", from_pid, to_pid)).digest()
        h = hmac.new(key, state, hashlib.sha256).digest()
        return source + h

    def receive_state(self, chain: CrossProcessChain, pid: int, fragment_id: int, state: bytes) -> Optional[bytes]:
        if not self.verify_process_binding(chain, pid, fragment_id):
            return None
        if len(state) < 32:
            return None
        data = state[:-32]
        received_mac = state[-32:]
        expected_sm_name = self._shared_memory_name(pid, pid)
        key = hashlib.sha256(self.shared_secret + struct.pack(">II", pid, pid)).digest()
        expected_mac = hmac.new(key, data + expected_sm_name.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(received_mac, expected_mac):
            return None
        return data
