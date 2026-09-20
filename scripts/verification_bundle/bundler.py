"""
verification_bundle/bundler.py — Verification bundle creation and verification (F177)

Purpose:
    Creates a tar.gz bundle containing all verification artefacts (source,
    benchmarks, traces, proofs, attack results) along with a SHA-256 manifest.
    Supports bundle verification by re-extracting and re-hashing.

Architectural Role:
    Orchestration layer. Coordinates the ArtifactCollector and ManifestBuilder
    to produce a self-verifying bundle archive.

Security Relevance:
    The bundle provides a tamper-evident snapshot that can be independently
    verified, enabling supply-chain integrity and external audit.
"""

from __future__ import annotations

import io
import json
import os
import tarfile
import tempfile
import time
from typing import Any

from .collector import ArtifactCollector
from .hasher import file_sha256, data_sha256
from .manifest import ManifestBuilder


class VerificationBundler:
    """Creates and verifies tamper-evident verification bundles.

    Collects build artefacts, builds a SHA-256 manifest, packages everything
    into a tar.gz archive, and provides verification against the manifest.
    """
    def __init__(self, build_dir: str, output_dir: str, payload_path: str | None = None):
        self.build_dir = build_dir
        self.output_dir = output_dir
        self.payload_path = payload_path
        self.collector = ArtifactCollector(build_dir, payload_path)
        self.manifest_builder = ManifestBuilder()
        self._bundle_path: str | None = None
        self._manifest_data: dict[str, Any] | None = None

    def build_bundle(self) -> dict[str, Any]:
        """Collect artefacts, build manifest, create tar.gz bundle, and write summary JSON.

        Returns the manifest data dict including the bundle SHA-256.
        """
        collection = self.collector.collect_all()
        os.makedirs(self.output_dir, exist_ok=True)
        bundle_name = f"verification_bundle_{int(time.time())}.tar.gz"
        bundle_path = os.path.join(self.output_dir, bundle_name)
        self._bundle_path = bundle_path

        for entry in collection["entries"]:
            local_path = entry.get("local_path", "")
            if not os.path.isfile(local_path):
                continue
            archive_path = entry.get("archive_rel", os.path.basename(local_path))
            category = entry.get("category", "generic")
            self.manifest_builder.add_entry(
                archive_path=archive_path,
                sha256_digest=entry["sha256"],
                size_bytes=entry["size_bytes"],
                category=category,
            )

        self._manifest_data = self.manifest_builder.build()
        manifest_bytes = json.dumps(self._manifest_data, indent=2).encode()

        with tarfile.open(bundle_path, "w:gz") as tar:
            for entry in collection["entries"]:
                local_path = entry.get("local_path", "")
                archive_path = entry.get("archive_rel", "")
                if os.path.isfile(local_path) and archive_path:
                    tar.add(local_path, arcname=archive_path)
            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(manifest_bytes)
            tar.addfile(info, fileobj=io.BytesIO(manifest_bytes))
        manifest_path = os.path.join(self.output_dir, "manifest.json")
        with open(manifest_path, "wb") as f:
            f.write(manifest_bytes)
        self._manifest_data["bundle_path"] = bundle_path
        self._manifest_data["bundle_sha256"] = file_sha256(bundle_path)
        self._manifest_data["total_files"] = collection["total_entries"]
        summary_path = os.path.join(self.output_dir, "bundle_summary.json")
        with open(summary_path, "w") as f:
            json.dump(self._manifest_data, f, indent=2)
        return self._manifest_data

    def verify_bundle(self, bundle_path: str | None = None) -> tuple[bool, list[str]]:
        """Verify a bundle's integrity by extracting and checking all hashes against the manifest.

        Returns (True, []) on success or (False, [error messages]) on failure.
        """
        path = bundle_path or self._bundle_path
        if not path or not os.path.isfile(path):
            return False, ["Bundle file not found"]
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with tarfile.open(path, "r:gz") as tar:
                    tar.extractall(tmpdir, filter="data")
                manifest_path = os.path.join(tmpdir, "manifest.json")
                if not os.path.isfile(manifest_path):
                    return False, ["manifest.json not found in bundle"]
                with open(manifest_path) as f:
                    manifest_data = json.load(f)
                return ManifestBuilder.verify(tmpdir, manifest_data)
        except Exception as e:
            return False, [f"Bundle verification failed: {e}"]

    @property
    def bundle_path(self) -> str | None:
        return self._bundle_path

    @property
    def manifest_data(self) -> dict[str, Any] | None:
        return self._manifest_data
