"""
verification_bundle — Independent Verification Bundle (F177)

Purpose:
    Collects all build artefacts (source, benchmarks, traces, proofs, attack
    results), hashes them, packages them into a signed tar.gz bundle with a
    manifest, enabling independent third-party verification.

Architectural Role:
    Supply-chain integrity layer. The bundle serves as a tamper-evident
    snapshot that can be independently verified without access to the
    original build environment.

Security Relevance:
    Enables external auditors to verify that the built artefacts match the
    claimed protection properties, preventing build-system compromise from
    going undetected.
"""

from .collector import ArtifactCollector
from .bundler import VerificationBundler
from .manifest import ManifestBuilder
from .hasher import file_sha256, data_sha256, sha256_manifest
