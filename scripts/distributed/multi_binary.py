import hashlib
import multiprocessing as mp
import os
import struct
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Tuple


try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None


# ---- GF(256) utilities for Cauchy Reed-Solomon erasure coding ----

_GF256_EXP = [0] * 512
_GF256_LOG = [0] * 256

_p = 0x11B
_v = 1
for _i in range(255):
    _GF256_EXP[_i] = _v
    _GF256_LOG[_v] = _i
    _v <<= 1
    if _v & 0x100:
        _v ^= _p
for _i in range(255, 512):
    _GF256_EXP[_i] = _GF256_EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF256_EXP[_GF256_LOG[a] + _GF256_LOG[b]]


def _gf_inv(a: int) -> int:
    if a == 0:
        return 0
    return _GF256_EXP[255 - _GF256_LOG[a]]


def _gf_mat_inv(m: List[List[int]]) -> Optional[List[List[int]]]:
    n = len(m)
    aug = [row[:] + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(m)]
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if aug[row][col] != 0:
                pivot = row
                break
        if pivot is None:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        inv_pivot = _gf_inv(aug[col][col])
        for j in range(2 * n):
            aug[col][j] = _gf_mul(aug[col][j], inv_pivot)
        for row in range(n):
            if row != col and aug[row][col] != 0:
                factor = aug[row][col]
                for j in range(2 * n):
                    aug[row][j] ^= _gf_mul(factor, aug[col][j])
    return [row[n:] for row in aug]


def _build_cauchy_matrix(rows: int, cols: int) -> List[List[int]]:
    mat = []
    for i in range(rows):
        row = []
        for j in range(cols):
            x = i + cols
            y = j
            val = _gf_inv(x ^ y)
            row.append(val)
        mat.append(row)
    return mat


def _erasure_encode(data: bytes, threshold: int, num_shares: int) -> List[bytes]:
    if threshold > num_shares:
        raise ValueError("threshold must be <= num_shares")
    if threshold == num_shares:
        return [data] * num_shares
    chunk_size = (len(data) + threshold - 1) // threshold
    padded = data.ljust(threshold * chunk_size, b'\x00')
    words = [padded[i * chunk_size:(i + 1) * chunk_size] for i in range(threshold)]
    mat = _build_cauchy_matrix(num_shares, threshold)
    shares = []
    for i in range(num_shares):
        share = bytearray(chunk_size)
        for j in range(threshold):
            coeff = mat[i][j]
            if coeff == 0:
                continue
            for k in range(chunk_size):
                share[k] ^= _gf_mul(coeff, words[j][k])
        shares.append(bytes(share))
    return shares


def _erasure_decode(shares_with_indices: List[Tuple[int, bytes]], threshold: int, original_len: int) -> bytes:
    if len(shares_with_indices) < threshold:
        raise ValueError(f"need at least {threshold} shares, got {len(shares_with_indices)}")
    if threshold == len(shares_with_indices) == 1:
        return shares_with_indices[0][1][:original_len]
    selected = shares_with_indices[:threshold]
    indices, share_data = zip(*selected)
    chunk_size = len(share_data[0])
    mat = _build_cauchy_matrix(max(indices) + 1, threshold)
    sub_mat = [mat[i] for i in indices]
    inv = _gf_mat_inv(sub_mat)
    if inv is None:
        raise ValueError("singular matrix in erasure decoding")
    words = []
    for j in range(threshold):
        word = bytearray(chunk_size)
        for i in range(threshold):
            coeff = inv[j][i]
            if coeff == 0:
                continue
            for k in range(chunk_size):
                word[k] ^= _gf_mul(coeff, share_data[i][k])
        words.append(bytes(word))
    result = b''.join(words)
    return result[:original_len]


@dataclass
class EncryptedFragment:
    fragment_id: int
    binary_id: int
    share_index: int
    encrypted_data: bytes
    iv: bytes
    key_id: int
    next_fragment_id: int


@dataclass
class MasterIndex:
    binary_count: int
    fragment_count: int
    threshold: int
    fragment_map: List[Tuple[int, int]]
    cross_keys: List[bytes]
    master_secret: bytes

    def serialize(self) -> bytes:
        buf = struct.pack(">III", self.binary_count, self.fragment_count, self.threshold)
        buf += struct.pack(">I", len(self.fragment_map))
        for fid, bid in self.fragment_map:
            buf += struct.pack(">II", fid, bid)
        buf += struct.pack(">I", len(self.cross_keys))
        for k in self.cross_keys:
            buf += struct.pack(">I", len(k)) + k
        buf += struct.pack(">I", len(self.master_secret)) + self.master_secret
        return buf

    @classmethod
    def deserialize(cls, data: bytes) -> "MasterIndex":
        offset = 0
        bcount, fcount, thresh = struct.unpack(">III", data[offset:offset+12])
        offset += 12
        map_len = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        frag_map = []
        for _ in range(map_len):
            fid, bid = struct.unpack(">II", data[offset:offset+8])
            offset += 8
            frag_map.append((fid, bid))
        nkeys = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        cross_keys = []
        for _ in range(nkeys):
            klen = struct.unpack(">I", data[offset:offset+4])[0]
            offset += 4
            cross_keys.append(data[offset:offset+klen])
            offset += klen
        slen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        ms = data[offset:offset+slen]
        return cls(bcount, fcount, thresh, frag_map, cross_keys, ms)


class MultiBinaryDistributor:
    def __init__(self, master_secret: Optional[bytes] = None, mode: str = "simulation"):
        self.master_secret = master_secret or os.urandom(32)
        self.mode = mode

    def _derive_cross_key(self, binary_a: int, binary_b: int) -> bytes:
        data = self.master_secret + struct.pack(">II", binary_a, binary_b)
        return hashlib.sha256(data).digest()

    def distribute(self, fragments: List[bytes], num_binaries: int, threshold: Optional[int] = None) -> Tuple[List[bytes], MasterIndex]:
        if num_binaries < 2:
            raise ValueError("num_binaries must be >= 2")
        if not fragments:
            raise ValueError("fragments list cannot be empty")
        if threshold is None:
            threshold = num_binaries
        if threshold < 1 or threshold > num_binaries:
            raise ValueError(f"threshold must be between 1 and {num_binaries}")

        cross_keys = []
        for i in range(num_binaries):
            for j in range(i + 1, num_binaries):
                cross_keys.append(self._derive_cross_key(i, j))

        use_erasure = threshold < num_binaries

        assignments = [[] for _ in range(num_binaries)]
        frag_map = []
        for fid, frag_data in enumerate(fragments):
            if use_erasure:
                shares = _erasure_encode(frag_data, threshold, num_binaries)
            else:
                shares = [frag_data] * num_binaries
            for bid in range(num_binaries):
                iv = os.urandom(12)
                key = self._derive_cross_key(bid, (bid + 1) % num_binaries)
                share_data = shares[bid]
                if AESGCM is not None:
                    aesgcm = AESGCM(key)
                    aad = struct.pack(">III", fid, bid, bid)
                    encrypted = aesgcm.encrypt(iv, share_data, aad)
                else:
                    stretched = hashlib.pbkdf2_hmac("sha256", key, iv, 10000, dklen=len(share_data))
                    encrypted = bytes(a ^ b for a, b in zip(share_data, stretched))
                ef = EncryptedFragment(
                    fragment_id=fid,
                    binary_id=bid,
                    share_index=bid,
                    encrypted_data=encrypted,
                    iv=iv,
                    key_id=bid,
                    next_fragment_id=fid + 1 if fid + 1 < len(fragments) else 0xFFFFFFFF,
                )
                assignments[bid].append(ef)
            frag_map.append((fid, 0))

        index = MasterIndex(
            binary_count=num_binaries,
            fragment_count=len(fragments),
            threshold=threshold,
            fragment_map=frag_map,
            cross_keys=cross_keys,
            master_secret=self.master_secret,
        )

        binaries = []
        for bid in range(num_binaries):
            binary = self._pack_binary(assignments[bid], bid, index)
            binaries.append(binary)

        return binaries, index

    def _pack_binary(self, frags: List[EncryptedFragment], bid: int, index: MasterIndex) -> bytes:
        buf = b"NXMB"
        buf += struct.pack(">IIII", bid, index.binary_count, index.fragment_count, index.threshold)
        buf += struct.pack(">I", len(frags))
        for ef in frags:
            buf += struct.pack(">IIII", ef.fragment_id, ef.binary_id, ef.share_index, ef.next_fragment_id)
            buf += struct.pack(">I", len(ef.iv)) + ef.iv
            buf += struct.pack(">I", ef.key_id)
            buf += struct.pack(">I", len(ef.encrypted_data)) + ef.encrypted_data
        return buf

    def reconstruct(self, binaries: List[bytes], threshold: Optional[int] = None) -> List[bytes]:
        if not binaries:
            raise ValueError("no binaries provided")
        index = self._extract_index(binaries)
        if threshold is None:
            threshold = index.threshold
        if len(binaries) < threshold:
            raise ValueError(f"need at least {threshold} binaries, got {len(binaries)}")

        all_frags: List[List[Tuple[int, bytes]]] = [[] for _ in range(index.fragment_count)]

        for binary in binaries:
            frags = self._unpack_binary(binary)
            for ef in frags:
                fid = ef.fragment_id
                key = self._derive_cross_key(ef.binary_id, (ef.binary_id + 1) % index.binary_count)
                plain = self._decrypt_fragment(ef, key)
                if plain is not None and 0 <= fid < len(all_frags):
                    all_frags[fid].append((ef.share_index, plain))

        use_erasure = index.threshold < index.binary_count
        result = []
        for fid, shares in enumerate(all_frags):
            if not shares:
                raise ValueError(f"missing all shares for fragment {fid}")
            if use_erasure:
                if len(shares) < index.threshold:
                    raise ValueError(f"fragment {fid}: need {index.threshold} shares, have {len(shares)}")
                decoded = _erasure_decode(shares, index.threshold, len(shares[0][1]))
            else:
                decoded = shares[0][1]
            result.append(decoded)

        return result

    def _extract_index(self, binaries: List[bytes]) -> MasterIndex:
        if not binaries:
            raise ValueError("no binaries provided")
        binary = binaries[0]
        if binary[:4] != b"NXMB":
            raise ValueError("invalid binary magic")
        offset = 4
        bid, bcount, total_frag_count, bthreshold = struct.unpack(">IIII", binary[offset:offset+16])
        offset += 16
        offset += 4

        frag_map = []
        seen_fids = set()
        for b in binaries:
            for ef in self._unpack_binary(b):
                if ef.fragment_id not in seen_fids:
                    seen_fids.add(ef.fragment_id)
                    frag_map.append((ef.fragment_id, ef.binary_id))
        frag_map.sort(key=lambda x: x[0])

        cross_keys = []
        for i in range(bcount):
            for j in range(i + 1, bcount):
                data = self.master_secret + struct.pack(">II", i, j)
                cross_keys.append(hashlib.sha256(data).digest())
        return MasterIndex(bcount, total_frag_count, bthreshold, frag_map, cross_keys, self.master_secret)

    def _unpack_binary(self, binary: bytes) -> List[EncryptedFragment]:
        if binary[:4] != b"NXMB":
            raise ValueError("invalid binary magic")
        offset = 4
        bid, bcount, _, _ = struct.unpack(">IIII", binary[offset:offset+16])
        offset += 16
        frag_count = struct.unpack(">I", binary[offset:offset+4])[0]
        offset += 4
        frags = []
        for _ in range(frag_count):
            fid, binary_id, share_index, nfid = struct.unpack(">IIII", binary[offset:offset+16])
            offset += 16
            iv_len = struct.unpack(">I", binary[offset:offset+4])[0]
            offset += 4
            iv = binary[offset:offset+iv_len]
            offset += iv_len
            key_id = struct.unpack(">I", binary[offset:offset+4])[0]
            offset += 4
            enc_len = struct.unpack(">I", binary[offset:offset+4])[0]
            offset += 4
            enc_data = binary[offset:offset+enc_len]
            offset += enc_len
            frags.append(EncryptedFragment(fid, binary_id, share_index, enc_data, iv, key_id, nfid))
        return frags

    def _decrypt_fragment(self, ef: EncryptedFragment, key: bytes) -> Optional[bytes]:
        if AESGCM is not None:
            try:
                aesgcm = AESGCM(key)
                aad = struct.pack(">III", ef.fragment_id, ef.binary_id, ef.share_index)
                return aesgcm.decrypt(ef.iv, ef.encrypted_data, aad)
            except Exception:
                return None
        else:
            stretched = hashlib.pbkdf2_hmac("sha256", key, ef.iv, 10000, dklen=len(ef.encrypted_data))
            return bytes(a ^ b for a, b in zip(ef.encrypted_data, stretched))

    def distribute_to_processes(self, fragments: List[bytes], num_binaries: int,
                                 threshold: Optional[int] = None) -> Tuple[List[bytes], MasterIndex]:
        binaries, index = self.distribute(fragments, num_binaries, threshold)
        self._binary_files = []
        processes = []
        queues = []
        for bid, binary in enumerate(binaries):
            q = mp.Queue()
            tmp = tempfile.NamedTemporaryFile(prefix=f"nx_binary_{bid}_", suffix=".bin", delete=False)
            tmp.write(binary)
            tmp.close()
            self._binary_files.append(tmp.name)
            p = mp.Process(target=_binary_worker, args=(bid, tmp.name, binary, q))
            p.start()
            processes.append(p)
            queues.append(q)
        for p in processes:
            p.join()
        for q in queues:
            try:
                q.get(timeout=5)
            except Exception:
                pass
        return binaries, index

    def reconstruct_from_processes(self, num_binaries: int, threshold: Optional[int] = None) -> List[bytes]:
        if not hasattr(self, '_binary_files') or not self._binary_files:
            raise ValueError("no binary files from previous distribute_to_processes()")
        selected = sorted(self._binary_files)
        if len(selected) < num_binaries:
            raise ValueError(f"expected {num_binaries} binary files, found {len(selected)}")
        selected = selected[:num_binaries]
        if threshold is not None and len(selected) > threshold:
            selected = selected[:threshold]
        binaries = []
        for path in selected:
            with open(path, "rb") as f:
                binaries.append(f.read())
        result = self.reconstruct(binaries, threshold)
        for path in self._binary_files:
            try:
                os.unlink(path)
            except OSError:
                pass
        self._binary_files = []
        return result

    def binary_for_fragment(self, index: MasterIndex, fragment_id: int) -> int:
        for fid, bid in index.fragment_map:
            if fid == fragment_id:
                return bid
        raise ValueError(f"fragment {fragment_id} not found")

    def distribute_multiprocess(self, fragments: List[bytes], num_binaries: int,
                                 threshold: Optional[int] = None) -> Tuple[List[bytes], MasterIndex]:
        binaries, index = self.distribute(fragments, num_binaries, threshold)
        tmp_files = []
        processes = []
        for bid, binary in enumerate(binaries):
            tmp = tempfile.NamedTemporaryFile(prefix=f"nx_share_{bid}_", suffix=".bin", delete=False)
            tmp.write(binary)
            tmp.close()
            tmp_files.append(tmp.name)
            p = mp.Process(target=_share_writer, args=(bid, binary, tmp.name))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
        self._distributed_files = tmp_files
        return binaries, index

    def collect_shares_parallel(self, num_binaries: int, threshold: Optional[int] = None) -> List[bytes]:
        if not hasattr(self, '_distributed_files') or not self._distributed_files:
            raise ValueError("no prior distribute_multiprocess() call")
        selected = sorted(self._distributed_files)[:num_binaries]
        with mp.Pool(min(len(selected), mp.cpu_count())) as pool:
            binaries = pool.map(_read_binary_file, selected)
        result = self.reconstruct(binaries, threshold)
        for path in self._distributed_files:
            try:
                os.unlink(path)
            except OSError:
                pass
        self._distributed_files = []
        return result


def _share_writer(bid: int, binary: bytes, path: str):
    with open(path, "wb") as f:
        f.write(binary)


def _read_binary_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _binary_worker(bid: int, filepath: str, binary: bytes, queue):
    import hashlib
    with open(filepath, "rb") as f:
        stored = f.read()
    assert hashlib.sha256(stored).hexdigest() == hashlib.sha256(binary).hexdigest()
    queue.put(bid)
