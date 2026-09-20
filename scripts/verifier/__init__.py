"""
verifier/__init__

Purpose:
Proof-Carrying Obfuscation (PCO) verifier. Extracts proof certificates from
obfuscated binaries and independently validates them. This is the tool that
enables trustless verification: the verifier does not need to trust the
obfuscator, only the proof.

Security Relevance:
The verifier is the final line of defense. If the verifier accepts a bad
proof, the system's integrity is compromised. The verifier MUST be kept
simple, auditable, and independent of the obfuscation pipeline.

Dependencies:
- scripts.verifier.standalone_verifier (main verification logic)
- scripts.verifier.binary_reader       (proof section extraction)
"""
from .standalone_verifier import StandaloneVerifier, VerificationResult
from .binary_reader import BinaryReader

__all__ = ["StandaloneVerifier", "VerificationResult", "BinaryReader"]
