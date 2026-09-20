"""
certificates/__init__

Purpose:
Certificate infrastructure for Proof-Carrying Obfuscation. Each
transformation pass emits a Certificate (pass name, input/output hashes,
equivalence proof). Certificates are linked into a CertificateChain where
each cert's output_hash must match the next cert's input_hash.

Security Relevance:
The certificate chain provides tamper evidence: any modification to the
transformation pipeline breaks the hash chain, and the verifier detects it.
Certificates are the public-facing proof artifacts.

Dependencies:
- scripts.certificates.certificate (Certificate, CertificateChain)
- scripts.certificates.collector   (CertificateCollector)
- scripts.certificates.integrity   (hash helpers)
"""
from .certificate import Certificate, CertificateChain, emit_certificate
from .collector import CertificateCollector
from .integrity import hash_ast, hash_ir, hash_bytes

__all__ = [
    "Certificate", "CertificateChain", "emit_certificate",
    "CertificateCollector",
    "hash_ast", "hash_ir", "hash_bytes",
]
