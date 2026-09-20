"""
verification_bundle/hasher.py — SHA-256 hashing utilities for verification bundle (F177)

Purpose:
    Provides simple SHA-256 hashing functions for files, data, manifest records,
    and individual verification of bundle entries.

Architectural Role:
    Low-level hashing layer consumed by the ManifestBuilder and ArtifactCollector.
    Ensures all bundle entries have verifiable content digests.

Security Relevance:
    Hash verification is the foundation of bundle integrity. Every entry in the
    bundle has a SHA-256 digest that can be independently recomputed.
"""

from __future__ import annotations

import hashlib
import json
import os


def file_sha256(path: str) -> str:
    """Compute the SHA-256 hex digest of a file, reading in 64 KiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def data_sha256(data: bytes) -> str:
    """Compute the SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_manifest(entries: dict[str, str]) -> str:
    """Compute a combined manifest hash from a dict of path → SHA-256 mappings."""
    lines = []
    for path, digest in sorted(entries.items()):
        lines.append(f"{digest}  {path}")
    raw = "\n".join(lines) + "\n"
    return data_sha256(raw.encode())


def build_manifest_entry(local_path: str, archive_rel: str) -> dict:
    """Build a standard manifest entry dict with local path, archive path, SHA-256, and file size."""
    return {
        "local_path": local_path,
        "archive_rel": archive_rel,
        "sha256": file_sha256(local_path),
        "size_bytes": os.path.getsize(local_path),
    }


def verify_manifest_entry(file_path: str, expected_sha256: str) -> bool:
    """Verify a single file matches its expected SHA-256 digest."""
    if not os.path.isfile(file_path):
        return False
    return file_sha256(file_path) == expected_sha256
