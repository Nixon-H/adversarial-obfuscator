"""
crypto_binding.py

Purpose:
Implements cryptographic binding of code fragments to specific
execution contexts. Provides the Fragment → BoundFragment transform
that encrypts fragment payloads with keys derived from the target
context's identity.

Architectural Role:
Core binding layer in the fragment protection system. Transforms
raw Fragment objects into BoundFragment objects that carry
encrypted payloads tied to a specific binding identity (hardware,
VM, temporal epoch). The binding ensures that a fragment can only
be decrypted and executed in the intended context.
(Sibling: temporal_key.py — epoch-ratcheting sub-keys consumed by
this binder's rolling/history-bound modes. Different layer — key
schedule vs. fragment transform; do not merge.)
(Sibling: scripts/fragment/fragment_compiler.py — chained
decrypt→execute→wipe bytecode splitting; that module owns fragment
granularity, this one owns context binding; do not merge.)

Security Relevance:
This is the primary cryptography layer for fragment-level
protection. Key properties:
- Uses SHA-256 for key derivation from binding identity.
- Uses AES-256-CTR with a random IV for payload encryption,
  providing semantic security (same plaintext → different ciphertexts).
- The IV is prepended to the ciphertext and stored alongside the
  fragment, enabling decryption without external key state.
- AES-256-CTR was chosen over AES-256-CBC because CTR mode does
  not require padding (avoiding padding oracle attacks) and
  supports parallel encryption/decryption.
- Fragment IDs are short (first 8 bytes of SHA-256 digest),
  providing a compact unique identifier with negligible collision
  probability under realistic fragment counts (< 10^12 fragments).

Threat model: Unauthorized extraction of fragment payloads,
fragment replay, cross-context execution.

What happens on duplication: bind() overwrites any existing
encrypted payload in the BoundFragment if the same fragment_id
is bound again. Caller should check BoundFragment.is_bound() or
use a unique fragment_id per binding operation.
"""

import hashlib
import hmac
import os
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Fragment:
    """
    An unprotected code fragment with metadata.

    fragment_id: Unique identifier (first 8 bytes of SHA-256).
    payload: Raw bytes of the fragment (plaintext).
    metadata: Arbitrary key-value annotations for the pipeline.
    """
    fragment_id: str
    payload: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BoundFragment:
    """
    A cryptographically bound fragment with encrypted payload.

    After bind(), payload_ciphertext contains AES-256-CTR output
    with the IV prepended. The binding_identity records which
    context this fragment is bound to. decrypting_identity
    records who successfully decrypted it (set at decryption time).

    The metadata survives the binding process unchanged.
    """
    fragment_id: str
    payload_ciphertext: bytes
    binding_identity: str
    decrypting_identity: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_bound(self) -> bool:
        """Check whether this fragment has a non-empty ciphertext."""
        return len(self.payload_ciphertext) > 0

    def serialize(self) -> bytes:
        """Serialize this bound fragment to bytes for storage or transport."""
        parts = [
            struct.pack(">I", len(self.fragment_id)),
            self.fragment_id.encode(),
            struct.pack(">I", len(self.payload_ciphertext)),
            self.payload_ciphertext,
            struct.pack(">I", len(self.binding_identity)),
            self.binding_identity.encode(),
        ]
        if self.decrypting_identity:
            parts.append(struct.pack(">I", len(self.decrypting_identity)))
            parts.append(self.decrypting_identity.encode())
        else:
            parts.append(struct.pack(">I", 0))
        return b"".join(parts)

    @staticmethod
    def deserialize(data: bytes) -> "BoundFragment":
        """Reconstruct a BoundFragment from serialized bytes."""
        offset = 0
        fid_len = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        fid = data[offset:offset + fid_len].decode()
        offset += fid_len
        ct_len = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        ct = data[offset:offset + ct_len]
        offset += ct_len
        bid_len = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        bid = data[offset:offset + bid_len].decode()
        offset += bid_len
        did_len = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        did = data[offset:offset + did_len].decode() if did_len > 0 else None
        return BoundFragment(
            fragment_id=fid,
            payload_ciphertext=ct,
            binding_identity=bid,
            decrypting_identity=did,
        )


class CryptoFragmentBinder:
    """
    Binds fragments to execution contexts using cryptographic keys.

    Provides bind() and unbind() operations that encrypt/decrypt
    fragment payloads with a key derived from a binding identity.
    The identity can be a hardware fingerprint, VM name, or
    temporal epoch label.

    Design decision: Key derivation uses SHA-256(binding_identity)
    rather than a KDF like PBKDF2 because (a) binding identities
    are high-entropy internal labels, not low-entropy passwords,
    and (b) we want deterministic key derivation for the same
    identity across runs. If binding identities are user-supplied
    low-entropy strings, replace with PBKDF2 or Argon2.
    """

    def __init__(self, master_key: Optional[bytes] = None,
                 chain_secret: Optional[bytes] = None,
                 rolling_key_mode: bool = False,
                 history_bound_mode: bool = False):
        """
        Initialize the binder with an optional master key.

        If no master key is provided, a random 32-byte key is
        generated using os.urandom (cryptographically secure).
        The master key is XORed with the identity-derived key
        as a form of key diversification.
        """
        if master_key is None:
            master_key = chain_secret or os.urandom(32)
        self._master_key = master_key
        self._rolling_key_mode = rolling_key_mode
        self._history_bound_mode = history_bound_mode
        self._accumulated_hash = hashlib.sha256(b"EXECUTION_HISTORY_V1").digest()
        self._roll_counter = 0
        self._rolling_key: Optional[bytes] = None

    def bind_fragments(self, fragments: List[Fragment]) -> List[BoundFragment]:
        """Bind a list of fragments into a cryptographically chained sequence."""
        bound = []
        prev_hash = hashlib.sha256(b"GENESIS").digest()
        for i, frag in enumerate(fragments):
            nonce = os.urandom(16)
            key = derive_fragment_key(prev_hash, self._master_key, i, nonce,
                                      accumulated_hash=self._accumulated_hash if self._history_bound_mode else None)
            iv = os.urandom(12)
            ct, tag = encrypt_fragment(frag.payload, key, iv, i, i + 1 if i + 1 < len(fragments) else -1)
            out_hash = compute_output_hash(ct)
            bf = BoundFragment(
                fragment_id=frag.fragment_id,
                payload_ciphertext=ct,
                binding_identity=f"chain:{i}",
            )
            bf.iv = iv
            bf.expected_input_hash = prev_hash
            bf.output_signature = out_hash
            bf.next_fragment_id = i + 1 if i + 1 < len(fragments) else -1
            bf.key_derivation_nonce = nonce
            bf.tag = tag
            bf.accumulated_hash = self._accumulated_hash if self._history_bound_mode else None
            bound.append(bf)
            prev_hash = out_hash
            self._roll_counter += 1
            self._rolling_key = key
        return bound

    def verify_chain(self, bound: List[BoundFragment]) -> bool:
        """Verify that a list of bound fragments forms a valid cryptographic chain."""
        prev_hash = hashlib.sha256(b"GENESIS").digest()
        for i, bf in enumerate(bound):
            expected_next = i + 1 if i + 1 < len(bound) else -1
            if bf.next_fragment_id != expected_next:
                return False
            key = derive_fragment_key(prev_hash, self._master_key, i, bf.key_derivation_nonce,
                                      accumulated_hash=self._accumulated_hash if self._history_bound_mode else None)
            result = decrypt_fragment(bf.payload_ciphertext, key, bf.iv, bf.tag, i, expected_next)
            if result is None:
                return False
            out_hash = compute_output_hash(bf.payload_ciphertext)
            prev_hash = out_hash
        return True

    def decrypt_fragment_by_index(self, bound: List[BoundFragment], index: int,
                                    prev_output_hash: Optional[bytes] = None) -> Optional[bytes]:
        """Decrypt a single fragment from a bound chain by its index."""
        if index < 0 or index >= len(bound):
            return None
        bf = bound[index]
        prev = prev_output_hash if prev_output_hash is not None else bf.expected_input_hash
        key = derive_fragment_key(prev, self._master_key, index, bf.key_derivation_nonce,
                                  accumulated_hash=self._accumulated_hash if self._history_bound_mode else None)
        expected_next = index + 1 if index + 1 < len(bound) else -1
        return decrypt_fragment(bf.payload_ciphertext, key, bf.iv, bf.tag, index, expected_next)

    def _derive_key(self, binding_identity: str) -> bytes:
        """
        Derive a per-identity key from the master key.

        key = SHA-256(SHA-256(binding_identity) || master_key)

        The double hash of the identity prevents length-extension
        attacks on SHA-256 and ensures the identity is hashed to
        a fixed-length input before combining with the master key.
        """
        identity_hash = hashlib.sha256(binding_identity.encode()).digest()
        combined = identity_hash + self._master_key
        return hashlib.sha256(combined).digest()

    def bind(self, fragment: Fragment, binding_identity: str) -> BoundFragment:
        """
        Encrypt a fragment's payload for a specific binding identity.

        Encrypts with AES-256-CTR: a random 16-byte IV is generated,
        the payload is XOR'd with the keystream, and the IV is
        prepended to the ciphertext.

        CTR mode properties relevant to security:
        - Parallelizable: IV reuse is catastrophic (XOR of two
          ciphertexts reveals XOR of plaintexts). The 16-byte random
          IV ensures collision probability < 2^-64 after 2^32 bindings.
        - No padding: avoids padding oracle attacks entirely.
        """
        per_identity_key = self._derive_key(binding_identity)
        iv = os.urandom(16)

        keystream = self._aes_ctr_keystream(per_identity_key, iv, len(fragment.payload))
        ciphertext = bytes(p ^ k for p, k in zip(fragment.payload, keystream))

        tag = hmac.new(per_identity_key, iv + ciphertext, hashlib.sha256).digest()

        bound = BoundFragment(
            fragment_id=fragment.fragment_id,
            payload_ciphertext=iv + ciphertext + tag,
            binding_identity=binding_identity,
            metadata=fragment.metadata.copy(),
        )
        return bound

    def unbind(self, bound: BoundFragment, decrypting_identity: str) -> Optional[Fragment]:
        """
        Decrypt a bound fragment if the identity matches.

        The decrypting_identity must match the binding_identity
        recorded during bind(). If they differ, None is returned
        (no decryption attempted).

        Security note: Identity comparison uses == on strings.
        For case-insensitive or normalized identities, normalize
        both sides before calling bind/unbind.
        """
        if bound.binding_identity != decrypting_identity:
            return None

        per_identity_key = self._derive_key(decrypting_identity)

        if len(bound.payload_ciphertext) < 48:
            return None

        iv = bound.payload_ciphertext[:16]
        tag = bound.payload_ciphertext[-32:]
        ciphertext = bound.payload_ciphertext[16:-32]

        expected_tag = hmac.new(per_identity_key, iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            return None

        keystream = self._aes_ctr_keystream(per_identity_key, iv, len(ciphertext))
        plaintext = bytes(c ^ k for c, k in zip(ciphertext, keystream))

        return Fragment(
            fragment_id=bound.fragment_id,
            payload=plaintext,
            metadata=bound.metadata.copy(),
        )

    def _aes_ctr_keystream(self, key: bytes, iv: bytes, length: int) -> bytes:
        """
        Generate a CTR-mode keystream using AES-256.

        Implements a naive byte-at-a-time CTR keystream for
        educational/demonstration purposes. The counter block is
        iv || counter (16 bytes total, with the last 4 bytes as
        big-endian counter), encrypted with AES-256-ECB.

        WARNING: This implementation is SLOW and NOT constant-time.
        It is suitable only for prototyping and understanding.
        For production, replace with a proper library like
        cryptography.hazmat.primitives.ciphers.CTR.

        Security note: The counter wraps at 2^32 blocks. For
        fragments larger than ~64 GiB, this implementation will
        repeat keystream blocks, compromising confidentiality.
        The protection pipeline does not produce fragments that
        large, but this is a documented limitation.
        """
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        ctr_cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        encryptor = ctr_cipher.encryptor()
        return encryptor.update(b"\x00" * length) + encryptor.finalize()


# =========================================================================
# Module-level helper functions for fragment chain binding
# =========================================================================

def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """Simple HKDF-Expand using HMAC-SHA256."""
    return hmac.new(prk, info, hashlib.sha256).digest()[:length]


def derive_fragment_key(prev_hash: Optional[bytes], chain_secret: bytes,
                         fragment_id: int, nonce: bytes,
                         accumulated_hash: Optional[bytes] = None) -> bytes:
    """Derive a fragment-specific key from chain state."""
    if prev_hash is None:
        seed = hashlib.sha256(chain_secret + b"GENESIS").digest()
    else:
        seed = prev_hash
    info = seed + struct.pack(">I", fragment_id) + nonce
    if accumulated_hash is not None:
        info += accumulated_hash
    return hkdf_expand(chain_secret, info, 32)


def encrypt_fragment(plaintext: bytes, key: bytes, iv: bytes,
                      fragment_id: int, next_fragment_id: int) -> Tuple[bytes, bytes]:
    """Encrypt a fragment payload with AES-256-GCM-like binding."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aesgcm = AESGCM(key)
    aad = struct.pack(">ii", fragment_id, next_fragment_id)
    ct = aesgcm.encrypt(iv, plaintext, aad)
    return ct, ct[-16:] if len(ct) >= 16 else ct


def decrypt_fragment(ciphertext: bytes, key: bytes, iv: bytes, tag: bytes,
                      fragment_id: int, next_fragment_id: int) -> Optional[bytes]:
    """Decrypt a fragment payload, returning None on failure.

    Fail-closed: AESGCM.encrypt appends the 16-byte tag to the ciphertext
    (see encrypt_fragment), so a stored ``tag`` that is not the
    ciphertext suffix means the (ciphertext, tag) pair is inconsistent —
    reject before attempting decryption.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        if not ciphertext.endswith(tag):
            return None
        aesgcm = AESGCM(key)
        aad = struct.pack(">ii", fragment_id, next_fragment_id)
        return aesgcm.decrypt(iv, ciphertext, aad)
    except Exception:
        return None


def compute_output_hash(data: bytes) -> bytes:
    """Compute the chaining hash of a fragment's CIPHERTEXT for chain linking.

    NOTE (honest semantics): despite the historical "decrypted fragment"
    wording, both call sites — bind_fragments() and verify_chain() — hash
    the ciphertext (``ct`` / ``bf.payload_ciphertext``). Chaining over the
    ciphertext is the correct binding: it commits to the exact bytes an
    attacker would have to reproduce, and decryption is verified
    separately per fragment via decrypt_fragment(). Changing this to hash
    plaintext would break chain compatibility with all bound artifacts.
    """
    return hashlib.sha256(data).digest()


def evolve_key(current_key: bytes, output_hash: bytes,
                fragment_id: int, nonce: int) -> bytes:
    """Evolve a rolling key based on the previous output."""
    info = output_hash + struct.pack(">II", fragment_id, nonce)
    return hkdf_expand(current_key, info, 32)
