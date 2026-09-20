import hashlib
import multiprocessing as mp
import os
import struct
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple


@dataclass
class WatermarkShare:
    share_id: int
    total_shares: int
    data: bytes
    checksum: bytes
    index: int

    def serialize(self) -> bytes:
        buf = struct.pack(">III", self.share_id, self.total_shares, self.index)
        buf += struct.pack(">I", len(self.data)) + self.data
        buf += struct.pack(">I", len(self.checksum)) + self.checksum
        return buf

    @classmethod
    def deserialize(cls, data: bytes) -> "WatermarkShare":
        offset = 0
        sid, total, idx = struct.unpack(">III", data[offset:offset+12])
        offset += 12
        dlen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        raw = data[offset:offset+dlen]
        offset += dlen
        clen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        cksum = data[offset:offset+clen]
        return cls(sid, total, raw, cksum, idx)


# GF(256) arithmetic for Shamir's Secret Sharing
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256


def _gf_mult_no_table(a: int, b: int) -> int:
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        high_bit = a & 0x80
        a = (a << 1) & 0xFF
        if high_bit:
            a ^= 0x1D
        b >>= 1
    return result


def _gf_init():
    x = 1
    for i in range(255):
        _GF_EXP[i] = x
        _GF_LOG[x] = i
        x = _gf_mult_no_table(x, 2)
    _GF_EXP[255] = 1
    for i in range(255, 512):
        _GF_EXP[i] = _GF_EXP[i - 255]
    return True


_gf_init()


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _gf_add(a: int, b: int) -> int:
    return a ^ b


def _gf_inv(a: int) -> int:
    if a == 0:
        return 0
    return _GF_EXP[255 - _GF_LOG[a]]


def _eval_poly(poly: List[int], x: int) -> int:
    result = poly[-1]
    for i in range(len(poly) - 2, -1, -1):
        result = _gf_add(_gf_mul(result, x), poly[i])
    return result


def _lagrange_interpolate(shares: List[Tuple[int, int]], x: int) -> int:
    result = 0
    for i, (xi, yi) in enumerate(shares):
        num = 1
        den = 1
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            num = _gf_mul(num, _gf_add(x, xj))
            den = _gf_mul(den, _gf_add(xi, xj))
        term = _gf_mul(yi, _gf_mul(num, _gf_inv(den)))
        result = _gf_add(result, term)
    return result


def _split_byte(byte_val: int, threshold: int, num_shares: int) -> List[int]:
    poly = [byte_val] + [os.urandom(1)[0] for _ in range(threshold - 1)]
    return [_eval_poly(poly, s + 1) for s in range(num_shares)]


def _reconstruct_byte(shares: List[Tuple[int, int]], threshold: int) -> int:
    return _lagrange_interpolate(shares[:threshold], 0)


def _shamir_split(secret: bytes, threshold: int, num_shares: int) -> List[bytes]:
    if threshold < 2:
        raise ValueError("threshold must be >= 2")
    if num_shares < threshold:
        raise ValueError("num_shares must be >= threshold")
    if num_shares > 255:
        raise ValueError("num_shares must be <= 255")

    share_bytes = [bytearray(len(secret)) for _ in range(num_shares)]
    for i, b in enumerate(secret):
        vals = _split_byte(b, threshold, num_shares)
        for s in range(num_shares):
            share_bytes[s][i] = vals[s]

    return [bytes(sb) for sb in share_bytes]


def _shamir_reconstruct(shares: List[Tuple[int, bytes]], threshold: int) -> bytes:
    if len(shares) < threshold:
        raise ValueError("not enough shares")

    ref_len = len(shares[0][1])
    result = bytearray(ref_len)
    for i in range(ref_len):
        points = [(sid + 1, sdata[i]) for sid, sdata in shares]
        result[i] = _reconstruct_byte(points, threshold)
    return bytes(result)


class DistributedWatermark:
    def __init__(self, watermark_secret: Optional[bytes] = None, mode: str = "simulation", threshold: int = 2):
        self.watermark_secret = watermark_secret or os.urandom(32)
        self.mode = mode
        self.threshold = threshold

    def _compute_share_checksum(self, share_id: int, data: bytes, index: int, nonce: bytes) -> bytes:
        h = hashlib.sha256()
        h.update(self.watermark_secret)
        h.update(struct.pack(">II", share_id, index))
        h.update(nonce)
        h.update(data)
        return h.digest()

    def _encrypt_share_data(self, share_id: int, data: bytes) -> bytes:
        key = hashlib.sha256(self.watermark_secret + struct.pack(">I", share_id)).digest()
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ key[i % len(key)]
        return bytes(result)

    def shard_watermark(self, watermark: bytes, num_shares: int) -> List[WatermarkShare]:
        if num_shares < 2:
            raise ValueError("num_shares must be >= 2")
        if self.threshold > num_shares:
            raise ValueError("threshold cannot exceed num_shares")
        if self.threshold < 2:
            raise ValueError("threshold must be >= 2")

        if self.mode == "shamir":
            share_plaintexts = _shamir_split(watermark, self.threshold, num_shares)
        else:
            total_len = len(watermark)
            base_size = total_len // num_shares
            remainder = total_len % num_shares
            share_plaintexts = []
            offset = 0
            for i in range(num_shares):
                size = base_size + (1 if i < remainder else 0)
                share_plaintexts.append(watermark[offset:offset+size])
                offset += size

        shares = []
        for i in range(num_shares):
            nonce = os.urandom(8)
            encrypted_data = self._encrypt_share_data(i, share_plaintexts[i])
            cksum = self._compute_share_checksum(i, encrypted_data, i, nonce)
            ws = WatermarkShare(
                share_id=i,
                total_shares=num_shares,
                data=encrypted_data + nonce,
                checksum=cksum,
                index=i,
            )
            shares.append(ws)

        return shares

    def verify_share(self, share: WatermarkShare) -> bool:
        nonce = share.data[-8:]
        encrypted_data = share.data[:-8]
        expected_cksum = self._compute_share_checksum(share.share_id, encrypted_data, share.index, nonce)
        return share.checksum == expected_cksum

    def _decrypt_share_data(self, share_id: int, encrypted_data: bytes) -> bytes:
        key = hashlib.sha256(self.watermark_secret + struct.pack(">I", share_id)).digest()
        result = bytearray(len(encrypted_data))
        for i in range(len(encrypted_data)):
            result[i] = encrypted_data[i] ^ key[i % len(key)]
        return bytes(result)

    def extract_from_shares(self, shares: List[WatermarkShare]) -> Optional[bytes]:
        if not shares:
            return None

        valid = []
        for s in shares:
            if not self.verify_share(s):
                return None
            decrypted = self._decrypt_share_data(s.share_id, s.data[:-8])
            valid.append((s.share_id, decrypted))

        if self.mode == "shamir":
            if len(valid) < self.threshold:
                return None
            return _shamir_reconstruct(valid, self.threshold)
        else:
            if len(valid) < 2:
                return None
            sorted_shares = sorted(valid, key=lambda s: s[0])
            total = shares[0].total_shares
            if len(sorted_shares) < total:
                return None
            return b"".join(s[1] for s in sorted_shares)

    def extract_partial(self, shares: List[WatermarkShare]) -> Optional[List[bytes]]:
        results = []
        for s in shares:
            if not self.verify_share(s):
                return None
            decrypted = self._decrypt_share_data(s.share_id, s.data[:-8])
            results.append(decrypted)
        if not results:
            return None
        return results

    def extract_full(self, shares: List[WatermarkShare]) -> Optional[bytes]:
        return self.extract_from_shares(shares)

    def split_with_threshold(self, watermark: bytes, num_shares: int, threshold: int) -> List[WatermarkShare]:
        saved = self.threshold
        self.threshold = threshold
        saved_mode = self.mode
        self.mode = "shamir"
        try:
            return self.shard_watermark(watermark, num_shares)
        finally:
            self.threshold = saved
            self.mode = saved_mode

    def shard_and_distribute(self, watermark: bytes, num_shares: int) -> List[WatermarkShare]:
        shares = self.shard_watermark(watermark, num_shares)
        if self.mode != "multiprocess":
            return shares
        processes = []
        queues = []
        for s in shares:
            q = mp.Queue()
            p = mp.Process(target=_watermark_holder, args=(s, q))
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
        return shares

    def extract_multiprocess(self, shares: List[WatermarkShare]) -> Optional[bytes]:
        queues = []
        processes = []
        for s in shares:
            q = mp.Queue()
            p = mp.Process(target=_watermark_holder, args=(s, q))
            p.start()
            processes.append(p)
            queues.append(q)
        collected = []
        for q in queues:
            try:
                share_data = q.get(timeout=5)
                collected.append(share_data)
            except Exception:
                pass
        for p in processes:
            if p.is_alive():
                p.terminate()
            p.join(timeout=1)
        if not collected:
            return None
        return self.extract_full(collected)


def _watermark_holder(share: WatermarkShare, queue):
    queue.put(share)
