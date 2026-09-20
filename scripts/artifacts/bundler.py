"""
bundler.py

Purpose:
Creates a self-contained reproducibility bundle (tar.gz or zip)
containing all build artifacts, a manifest with SHA-256 hashes,
and metrics/reports metadata. Enables independent verification
of build outputs.

Architectural Role:
Packaging layer for the artifacts module. The bundle includes all
output files, a manifest.json with file hashes, and optional
metrics/reports. The bundle can be verified with verify_bundle().

Execution Context:
Called by ArtifactBuilder._bundle_reproducibility_package() at build
completion. The bundle is written to build/artifacts/bundle/.

Dependencies:
- Standard library only (hashlib, json, os, shutil, tarfile, time, zipfile)

Security Relevance:
The reproducibility bundle provides cryptographic proof of what was
built. The manifest SHA-256 chain (file hashes -> manifest hash)
ensures tamper detection. verify_bundle() verifies the entire chain.

Maintenance Notes:
- The bundle format is tar.gz by default; .zip is used if the
  output path ends in .zip.
- The verify_bundle() method extracts to a temporary directory
  (.bundle_verify) which is cleaned up in the finally block.
- File hashing uses 64KB chunks for memory efficiency.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import time
import zipfile


class ReproducibilityBundle:
    def __init__(self, bundle_dir: str):
        self.bundle_dir = bundle_dir
        self._files: list[dict] = []
        self._metrics: dict = {}
        self._reports: dict[str, dict] = {}
        self._manifest: dict | None = None
        os.makedirs(bundle_dir, exist_ok=True)

    def add_file(self, source_path: str, bundle_relative_path: str) -> None:
        if not os.path.isfile(source_path):
            raise FileNotFoundError(f"Source file does not exist: {source_path}")
        dest = os.path.join(self.bundle_dir, bundle_relative_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(source_path, dest)
        sha256 = self._hash_file(dest)
        self._files.append({
            "source": source_path,
            "bundle_path": bundle_relative_path,
            "size_bytes": os.path.getsize(dest),
            "sha256": sha256,
        })

    def add_metrics(self, metrics_dict: dict) -> None:
        self._metrics.update(metrics_dict)

    def add_report(self, report_dict: dict, name: str) -> None:
        self._reports[name] = report_dict

    def _hash_file(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def _hash_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def generate_manifest(self) -> dict:
        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "bundle_version": "1.0.0",
            "files": self._files,
            "metrics": self._metrics,
            "reports": {k: self._hash_bytes(json.dumps(v, sort_keys=True).encode()) for k, v in self._reports.items()},
            "file_count": len(self._files),
            "total_size_bytes": sum(f["size_bytes"] for f in self._files),
        }
        manifest_str = json.dumps(manifest, sort_keys=True)
        manifest["manifest_sha256"] = self._hash_bytes(manifest_str.encode())
        self._manifest = manifest
        manifest_path = os.path.join(self.bundle_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        return manifest

    def bundle(self, output_path: str) -> str:
        self.generate_manifest()
        if output_path.endswith(".zip"):
            self._create_zip(output_path)
        else:
            if not output_path.endswith(".tar.gz"):
                output_path = output_path + ".tar.gz"
            self._create_tar_gz(output_path)
        return output_path

    def _create_tar_gz(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(self.bundle_dir, arcname=os.path.basename(self.bundle_dir))

    def _create_zip(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(self.bundle_dir):
                for fn in files:
                    file_path = os.path.join(root, fn)
                    arcname = os.path.relpath(file_path, os.path.dirname(self.bundle_dir))
                    zf.write(file_path, arcname)

    @staticmethod
    def verify_bundle(bundle_path: str) -> dict:
        if not os.path.isfile(bundle_path):
            return {"valid": False, "error": f"Bundle file not found: {bundle_path}"}

        extract_dir = os.path.join(os.path.dirname(bundle_path), ".bundle_verify")
        if os.path.isdir(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)

        try:
            if bundle_path.endswith(".zip"):
                with zipfile.ZipFile(bundle_path, "r") as zf:
                    zf.extractall(extract_dir)
            else:
                with tarfile.open(bundle_path, "r:gz") as tar:
                    tar.extractall(extract_dir)

            bundle_contents = os.listdir(extract_dir)
            if not bundle_contents:
                return {"valid": False, "error": "Bundle is empty"}

            bundle_dir = os.path.join(extract_dir, bundle_contents[0])
            manifest_path = os.path.join(bundle_dir, "manifest.json")
            if not os.path.isfile(manifest_path):
                manifest_path = os.path.join(extract_dir, "manifest.json")

            if not os.path.isfile(manifest_path):
                return {"valid": False, "error": "Manifest not found in bundle"}

            with open(manifest_path) as f:
                manifest = json.load(f)

            stored_sha256 = manifest.get("manifest_sha256", "")
            manifest_copy = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
            computed = hashlib.sha256(json.dumps(manifest_copy, sort_keys=True).encode()).hexdigest()
            if computed != stored_sha256:
                return {
                    "valid": False,
                    "error": "Manifest integrity check failed",
                    "expected_sha256": stored_sha256,
                    "computed_sha256": computed,
                }

            for fentry in manifest.get("files", []):
                rel_path = fentry.get("bundle_path", "")
                expected_hash = fentry.get("sha256", "")
                full_path = os.path.join(bundle_dir, rel_path)
                if not os.path.isfile(full_path):
                    return {"valid": False, "error": f"File missing from bundle: {rel_path}"}
                h = hashlib.sha256()
                with open(full_path, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                if h.hexdigest() != expected_hash:
                    return {
                        "valid": False,
                        "error": f"SHA256 mismatch for file: {rel_path}",
                        "expected": expected_hash,
                        "computed": h.hexdigest(),
                    }

            return {
                "valid": True,
                "file_count": len(manifest.get("files", [])),
                "total_size_bytes": manifest.get("total_size_bytes", 0),
                "manifest_sha256": stored_sha256,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}
        finally:
            if os.path.isdir(extract_dir):
                shutil.rmtree(extract_dir)
