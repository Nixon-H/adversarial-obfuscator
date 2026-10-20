"""
audit_drift/detector.py

Purpose:
Detects "audit drift" — a condition where source files have been modified after
audit reports were generated, meaning the reports no longer reflect the actual
code. Hashes source files, inventories build reports, and produces a staleness
score.

Security Relevance:
Audit drift undermines the entire audit process. If source code changes but
audit reports are not regenerated, the reports are misleading. This detector
provides an automated check to enforce that audit artifacts stay in sync with
source.

What it misses:
- Content-only changes that produce the same SHA-256 hash (hash collision).
- Reports that are present but contain stale data (the detector only checks
  existence, not report content accuracy).
- Non-.py source files (config, YAML, JSON sources).

Dependencies:
- hashlib (standard library)

Audit check summary:
- hash_source_files: computes SHA-256 of every .py file under scripts/
- inventory_reports: lists report files (json, md, txt) in build/
- detect_drift: for each source file, checks if a corresponding report exists
- compute_staleness_score: 100.0 = fully current, 0.0 = fully stale
"""
from __future__ import annotations

import hashlib
import json  # noqa: F401 (this line binds a name used by an embedded template)
import os


_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AuditDriftDetector:
    """
    AuditDriftDetector

    Purpose:
    Detects audit drift by comparing source file hashes against report
    inventory. A file is "drifted" if no corresponding report exists.

    Lifecycle:
    Created by detect_audit_drift(); all checks run in sequence.

    Security:
    Protects against the scenario where source changes silently invalidate
    previously generated audit reports.
    """
    def __init__(self, root_dir: str | None = None, build_dir: str | None = None):
        self.root = root_dir or _ROOT
        self.build_dir = build_dir or os.path.join(self.root, "build")
        self.scripts_dir = os.path.join(self.root, "scripts")
        self.source_snapshot: dict[str, dict] = {}
        self.report_inventory: list[dict] = []
        self.drifted_files: list[dict] = []

    def hash_source_files(self) -> dict[str, dict]:
        """
        hash_source_files

        Purpose:
        Walks the scripts/ directory and computes SHA-256 hash, size, and
        mtime for every .py file.

        Inputs:
        None

        Outputs:
        Dict mapping relative path to hash/size/mtime info.
        """
        snapshot: dict[str, dict] = {}
        if not os.path.isdir(self.scripts_dir):
            return snapshot
        for root, dirs, files in os.walk(self.scripts_dir):
            dirs[:] = [d for d in dirs if not d.startswith("__") and not d.startswith(".") and d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, self.root)
                    with open(fpath, "rb") as f:
                        content = f.read()
                    snapshot[rel] = {
                        "hash": hashlib.sha256(content).hexdigest(),
                        "size": len(content),
                        "mtime": os.path.getmtime(fpath),
                    }
        self.source_snapshot = snapshot
        return snapshot

    def inventory_reports(self) -> list[dict]:
        """
        inventory_reports

        Purpose:
        Lists all JSON, MD, and TXT report files in the build/ directory.

        Inputs:
        None

        Outputs:
        List of dicts with file name, path, size, mtime, and whether the
        report contains source hashes.
        """
        inventory: list[dict] = []
        if not os.path.isdir(self.build_dir):
            self.report_inventory = inventory
            return inventory
        for fname in sorted(os.listdir(self.build_dir)):
            if fname.endswith(".json") or fname.endswith(".md") or fname.endswith(".txt"):
                fpath = os.path.join(self.build_dir, fname)
                has_baseline = self._check_baseline_in_file(fpath)
                inventory.append({
                    "file": fname,
                    "path": fpath,
                    "size": os.path.getsize(fpath),
                    "mtime": os.path.getmtime(fpath),
                    "has_source_hashes": has_baseline,
                })
        self.report_inventory = inventory
        return inventory

    def _check_baseline_in_file(self, fpath: str) -> bool:
        """
        _check_baseline_in_file

        Purpose:
        Reads the first 4096 bytes of a file to check for baseline-related
        keywords (sha256, hash, source).

        Inputs:
        fpath — path to the report file

        Outputs:
        True if baseline keywords are found.
        """
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(4096)
            return "sha256" in content or "hash" in content.lower() or "source" in content.lower()
        except Exception:
            return False

    def detect_drift(self) -> list[dict]:
        """
        detect_drift

        Purpose:
        For each source file, computes the expected report name and checks
        whether it exists in the report inventory. Files with no corresponding
        report are marked as drifted.

        Inputs:
        None (reads self.source_snapshot and self.report_inventory)

        Outputs:
        List of dicts with source_file, current_hash, matching_report,
        report_exists, status.
        """
        self.drifted_files = []
        if not self.source_snapshot:
            self.hash_source_files()
        if not self.report_inventory:
            self.inventory_reports()
        report_files = {r["file"] for r in self.report_inventory}
        for rel_path, info in self.source_snapshot.items():
            report_name = rel_path.replace("/", "_").replace(".py", "_report.json")
            if report_name not in report_files and report_name.replace("_report", "") not in " ".join(report_files):
                self.drifted_files.append({
                    "source_file": rel_path,
                    "current_hash": info["hash"],
                    "matching_report": report_name,
                    "report_exists": report_name in report_files,
                    "status": "no_corresponding_report",
                })
        return self.drifted_files

    def compute_staleness_score(self) -> float:
        """
        compute_staleness_score

        Purpose:
        Calculates a 0-100 staleness score based on the ratio of drifted
        files and report availability.

        Inputs:
        None

        Outputs:
        Float between 0.0 (fully stale) and 100.0 (fully current).
        """
        total_sources = len(self.source_snapshot)
        if total_sources == 0:
            return 0.0
        drifted = len(self.drifted_files)
        report_count = len(self.report_inventory)
        score = 100.0
        score -= (drifted / max(total_sources, 1)) * 50.0
        if report_count == 0 and total_sources > 0:
            score -= 30.0
        return max(0.0, round(score, 2))


def detect_audit_drift(root_dir: str | None = None) -> dict:
    """
    detect_audit_drift

    Purpose:
    Convenience function that creates an AuditDriftDetector and runs the full
    drift detection pipeline.

    Inputs:
    root_dir — optional root directory override

    Outputs:
    Dict with source_snapshot, report_inventory, drifted_files,
    staleness_score, and totals.

    Security:
    Module entry point for F185.
    """
    detector = AuditDriftDetector(root_dir=root_dir)
    source_snapshot = detector.hash_source_files()
    report_inventory = detector.inventory_reports()
    drifted_files = detector.detect_drift()
    staleness_score = detector.compute_staleness_score()
    return {
        "source_snapshot": {
            path: {"hash": info["hash"][:16], "size": info["size"]}
            for path, info in source_snapshot.items()
        },
        "report_inventory": [
            {"file": r["file"], "size": r["size"], "has_source_hashes": r["has_source_hashes"]}
            for r in report_inventory
        ],
        "drifted_files": drifted_files,
        "staleness_score": staleness_score,
        "total_source_files": len(source_snapshot),
        "total_reports": len(report_inventory),
        "total_drifted": len(drifted_files),
    }
