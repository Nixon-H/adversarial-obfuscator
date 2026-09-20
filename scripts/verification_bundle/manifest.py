"""
verification_bundle/manifest.py — Manifest generation and verification (F177)

Purpose:
    Builds a versioned manifest listing every file in the verification bundle
    with its SHA-256 digest and size. Supports verification by re-hashing
    extracted files against the manifest.

Architectural Role:
    Data layer for the VerificationBundler. The manifest is the source of
    truth for bundle contents and their integrity digests.

Security Relevance:
    The manifest hash (manifest_sha256) covers all file entries, making
    any tampering detectable.
"""

from __future__ import annotations

import json
import time
from typing import Any

from .hasher import data_sha256, sha256_manifest


class ManifestBuilder:
    """Builds and verifies bundle manifests with SHA-256 file digests.

    Supports incremental entry addition, manifest building with a combined
    hash, and static verification of an extracted bundle directory.
    """
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self._record: dict[str, str] = {}

    def add_entry(self, archive_path: str, sha256_digest: str, size_bytes: int, category: str = "generic") -> None:
        """Add a single entry to the manifest with its archive path, digest, size, and category."""
        self.entries.append({
            "path": archive_path,
            "sha256": sha256_digest,
            "size_bytes": size_bytes,
            "category": category,
        })
        self._record[archive_path] = sha256_digest

    def add_entries(self, entry_list: list[dict[str, Any]]) -> None:
        """Bulk-add entries from a list of dicts (each must have path, sha256, size_bytes, category)."""
        for e in entry_list:
            archive_path = e.get("path", "")
            sha = e.get("sha256", "")
            size = e.get("size_bytes", 0)
            cat = e.get("category", "generic")
            self.add_entry(archive_path, sha, size, cat)

    def build(self) -> dict[str, Any]:
        """Finalize the manifest: compute the combined manifest SHA-256 and return the manifest dict."""
        manifest_hash = sha256_manifest(self._record)
        return {
            "manifest_version": "1.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "algorithm": "SHA-256",
            "manifest_sha256": manifest_hash,
            "file_count": len(self.entries),
            "files": sorted(self.entries, key=lambda x: x["path"]),
        }

    def build_json(self, indent: int = 2) -> str:
        """Build the manifest and serialize to JSON string."""
        return json.dumps(self.build(), indent=indent)

    @staticmethod
    def verify(bundle_dir: str, manifest_data: dict) -> tuple[bool, list[str]]:
        """Verify all files in bundle_dir match the manifest. Returns (pass, error_list)."""
        import os
        errors = []
        expected_hash = manifest_data.get("manifest_sha256", "")
        records: dict[str, str] = {}
        for fe in manifest_data.get("files", []):
            archive_path = fe["path"]
            expected_digest = fe["sha256"]
            records[archive_path] = expected_digest
            abs_path = os.path.join(bundle_dir, archive_path)
            if not os.path.isfile(abs_path):
                errors.append(f"MISSING: {archive_path}")
                continue
            from .hasher import file_sha256
            actual = file_sha256(abs_path)
            if actual != expected_digest:
                errors.append(f"HASH_MISMATCH: {archive_path} (expected {expected_digest}, got {actual})")
        expected = sha256_manifest(records)
        if expected != expected_hash:
            errors.append(f"MANIFEST_HASH_MISMATCH: computed {expected}, manifest says {expected_hash}")
        return len(errors) == 0, errors
