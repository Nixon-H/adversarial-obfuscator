"""
phase_verification_bundle.py

Purpose:
Generates an independent verification bundle — a self-contained archive
of all build artifacts, hashes, and a manifest that can be independently
verified by a third party.

Architectural Role:
Release/audit phase — produces the verification artifact.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.verification_bundle.*

Security Relevance:
Independent verification bundles are the foundation for external audits
and reproducible-security claims.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.verification_bundle.bundler import VerificationBundler
from scripts.verification_bundle.collector import ArtifactCollector
from scripts.verification_bundle.manifest import ManifestBuilder
from scripts.verification_bundle.hasher import file_sha256, data_sha256


def phase_verification_bundle(args: Any) -> dict:
    """
    Generate independent verification bundle for third-party audit.

    Args:
        args: argparse.Namespace

    Returns:
        dict with bundle_path, sha256, and verification status
    """
    log("VERIFICATION_BUNDLE", "Starting independent verification bundle generation...")

    build_dir = getattr(args, "build_dir", BUILD_DIR)
    payload_path = getattr(args, "payload", None)
    output_dir = getattr(args, "verification_bundle_output", None) or os.path.join(build_dir, "verification_bundle")

    bundler = VerificationBundler(
        build_dir=build_dir,
        output_dir=output_dir,
        payload_path=payload_path,
    )

    manifest = bundler.build_bundle()

    bundle_path = manifest.get("bundle_path", "")
    bundle_sha = manifest.get("bundle_sha256", "N/A")
    total_files = manifest.get("total_files", 0)
    file_count = manifest.get("file_count", 0)

    ok, errors = bundler.verify_bundle()
    verification_status = "PASS" if ok else "FAIL"

    print()
    print("=" * 60)
    print("  INDEPENDENT VERIFICATION BUNDLE")
    print("=" * 60)
    print(f"  Bundle:            {bundle_path}")
    print(f"  SHA256:            {bundle_sha}")
    print(f"  Files in manifest: {file_count}")
    print(f"  Total entries:     {total_files}")
    print(f"  Self-verify:       {verification_status}")
    if not ok:
        print(f"  Errors ({len(errors)}):")
        for err in errors[:10]:
            print(f"    ✗ {err}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    print("=" * 60)
    print()

    log("VERIFICATION_BUNDLE", f"Bundle written to {bundle_path}")
    log("VERIFICATION_BUNDLE", f"Bundle SHA256: {bundle_sha}")
    log("VERIFICATION_BUNDLE", f"Manifest entries: {file_count}")
    log("VERIFICATION_BUNDLE", f"Self-verification: {verification_status}")

    if not ok:
        log("VERIFICATION_BUNDLE", f"Verification errors: {len(errors)}")

    summary = {
        "bundle_path": bundle_path,
        "bundle_sha256": bundle_sha,
        "manifest_entry_count": file_count,
        "total_collected": total_files,
        "self_verify": ok,
        "verification_errors": errors if not ok else [],
        "manifest": manifest,
    }

    summary_path = os.path.join(output_dir, "verification_bundle_summary.json")
    os.makedirs(output_dir, exist_ok=True)
    atomic_write(summary_path, json.dumps(summary, indent=2))
    log("VERIFICATION_BUNDLE", f"Summary → {summary_path}")

    return summary
