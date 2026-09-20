"""
certificates/certificate.py

Purpose:
Defines the Certificate and CertificateChain data structures for Proof-Carrying
Obfuscation. A Certificate binds a transformation pass name to SHA-256 hashes
of its input and output, along with the equivalence proof. The chain links
certificates input-to-output for sequential verification.

Security Relevance:
The hash chain provides integrity: if any pass is modified, replaced, or
reordered, the chain validation fails. Each certificate also carries the
actual equivalence proof (e.g., Z3 solver result) for independent re-verification.

Dependencies:
- json, hashlib (standard library)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Certificate:
    """
    Certificate

    Purpose:
    Binds a transformation pass name to the SHA-256 hashes of its input and
    output, the equivalence proof data, timing, and validation status.

    Security Relevance:
    The hashes are the integrity anchors. If input_hash or output_hash is
    computed incorrectly (e.g., wrong encoding), the chain validation is
    broken. The equivalence_proof dict carries the actual Z3 proof for
    independent re-verification.

    Chain rule:
    For a sequence of certificates c0, c1, ..., cn:
      c0.input_hash = hash(original_input)
      c[i].output_hash = c[i+1].input_hash  for all i
      cn.output_hash = hash(final_output)
    """
    pass_name: str
    input_hash: str
    output_hash: str
    equivalence_proof: dict
    duration_ms: float
    timestamp: str
    validated: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, data: str) -> 'Certificate':
        d = json.loads(data)
        return cls(
            pass_name=d["pass_name"],
            input_hash=d["input_hash"],
            output_hash=d["output_hash"],
            equivalence_proof=d["equivalence_proof"],
            duration_ms=d["duration_ms"],
            timestamp=d["timestamp"],
            validated=d["validated"],
        )


@dataclass
class CertificateChain:
    """
    CertificateChain

    Purpose:
    Links a sequence of certificates into a hash chain. Each cert's
    output_hash must equal the next cert's input_hash.

    Security Relevance:
    The chain provides tamper evidence. Breaking the chain reveals that
    the sequence of transformations was modified after certification.
    The chain_validated flag records whether validation has been run.

    What it misses:
    - A collision attack on SHA-256 could create a fake chain.
    - The chain does NOT re-run SMT proofs; it only checks hashes.
      Independent re-verification via --re-verify is recommended.
    """
    certificates: List[Certificate] = field(default_factory=list)
    chain_validated: bool = False

    def to_json(self) -> str:
        return json.dumps({
            "chain_validated": self.chain_validated,
            "certificates": [json.loads(c.to_json()) for c in self.certificates],
        }, indent=2)

    @classmethod
    def from_json(cls, data: str) -> 'CertificateChain':
        d = json.loads(data)
        certs = [Certificate.from_json(json.dumps(c)) for c in d["certificates"]]
        return cls(certificates=certs, chain_validated=d.get("chain_validated", False))

    def validate_chain(self) -> bool:
        for i in range(1, len(self.certificates)):
            prev = self.certificates[i - 1]
            curr = self.certificates[i]
            if prev.output_hash != curr.input_hash:
                self.chain_validated = False
                return False
        self.chain_validated = True
        return True


def emit_certificate(
    pass_name: str,
    input_text: str,
    output_text: str,
    equivalence_proof: dict,
    duration_ms: float,
    validated: bool = True,
) -> Certificate:
    import hashlib
    input_hash = hashlib.sha256(input_text.encode("utf-8")).hexdigest()
    output_hash = hashlib.sha256(output_text.encode("utf-8")).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()
    return Certificate(
        pass_name=pass_name,
        input_hash=input_hash,
        output_hash=output_hash,
        equivalence_proof=equivalence_proof,
        duration_ms=duration_ms,
        timestamp=timestamp,
        validated=validated,
    )
