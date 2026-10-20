"""
benchmark_integrity/integrity.py

Purpose:
Verifies the integrity of benchmark test files by computing SHA-256 hashes,
fingerprinting the runtime environment, and detecting tampering, replay
(identical content across files), and environment modification.

Architectural Role:
Called by the release confidence scorer (F197) and the audit drift detector
(F185). Provides a quantitative integrity score (0-100) for benchmark files.

Security Relevance:
Ensures benchmark results are reproducible and have not been tampered with
since baseline. Detects replay attacks where the same benchmark is reused
under different names.
"""
from __future__ import annotations

import hashlib
import os
import platform
import sys
import importlib.metadata


_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BenchmarkIntegrityVerifier:
    """
    BenchmarkIntegrityVerifier

    Purpose:
    Verifies benchmark integrity via file hashing, environment fingerprinting,
    tamper detection, replay detection, and environment modification detection.

    Lifecycle:
    Created by verify_benchmark_integrity(); all checks run in sequence.

    Security:
    Provides assurance that benchmark results are reproducible and have not
    been tampered with since baseline recording.
    """
    def __init__(self, root_dir: str | None = None):
        self.root = root_dir or _ROOT
        self.tests_dir = os.path.join(self.root, "tests")
        self.file_hashes: dict[str, str] = {}
        self.env_fingerprint: dict = {}
        self.tamper_detection: list[dict] = []
        self.replay_detection: list[dict] = []
        self.modification_detection: list[dict] = []

    def hash_file(self, fpath: str) -> str:
        """
        hash_file

        Purpose:
        Computes SHA-256 hash of a file, reading in 64 KB chunks.

        Inputs:
        fpath — absolute path to the file

        Outputs:
        Hex digest string.

        Security:
        SHA-256 provides collision resistance for integrity verification.
        """
        h = hashlib.sha256()
        with open(fpath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def finger_print_environment(self) -> dict:
        """
        finger_print_environment

        Purpose:
        Captures Python version, platform, architecture, processor, and list
        of installed packages as an environment fingerprint.

        Inputs:
        None

        Outputs:
        Dict with fingerprint fields.

        Security:
        Environment changes can invalidate benchmark reproducibility.
        """
        installed = {}
        try:
            installed = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}
        except Exception:
            pass
        self.env_fingerprint = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
            "installed_packages": installed,
        }
        return self.env_fingerprint

    def hash_benchmark_files(self) -> dict[str, str]:
        """
        hash_benchmark_files

        Purpose:
        Finds all bench_*.py files in the tests/ directory and computes their
        SHA-256 hashes.

        Inputs:
        None

        Outputs:
        Dict mapping filename to hash string.
        """
        self.file_hashes = {}
        if not os.path.isdir(self.tests_dir):
            return {}
        for fname in sorted(os.listdir(self.tests_dir)):
            if fname.startswith("bench_") and fname.endswith(".py"):
                fpath = os.path.join(self.tests_dir, fname)
                self.file_hashes[fname] = self.hash_file(fpath)
        return self.file_hashes

    def detect_tampering(self, previous_hashes: dict[str, str] | None = None) -> list[dict]:
        """
        detect_tampering

        Purpose:
        Compares current file hashes against a previous baseline to detect
        added, removed, or tampered benchmark files.

        Inputs:
        previous_hashes — optional baseline dict; if None, records the current
                          state as the baseline.

        Outputs:
        List of dicts with file, status, and hash fields.
        """
        self.tamper_detection = []
        current = self.hash_benchmark_files()
        if previous_hashes is None:
            for fname, h in current.items():
                self.tamper_detection.append({
                    "file": fname,
                    "current_hash": h,
                    "status": "baseline_set",
                })
            return self.tamper_detection
        all_files = set(current.keys()) | set(previous_hashes.keys())
        for fname in sorted(all_files):
            entry: dict = {"file": fname}
            if fname not in current:
                entry["status"] = "removed"
                entry["previous_hash"] = previous_hashes.get(fname, "")
            elif fname not in previous_hashes:
                entry["status"] = "added"
                entry["current_hash"] = current[fname]
            elif current[fname] != previous_hashes[fname]:
                entry["status"] = "tampered"
                entry["previous_hash"] = previous_hashes[fname]
                entry["current_hash"] = current[fname]
            else:
                entry["status"] = "intact"
                entry["hash"] = current[fname]
            self.tamper_detection.append(entry)
        return self.tamper_detection

    def detect_replay(self) -> list[dict]:
        """
        detect_replay

        Purpose:
        Detects identical hashes across different benchmark files, which
        suggests content replay.

        Inputs:
        None

        Outputs:
        List of dicts with hash, files list, and status.
        """
        self.replay_detection = []
        hashes_seen: dict[str, list[str]] = {}
        for fname, h in self.file_hashes.items():
            hashes_seen.setdefault(h, []).append(fname)
        for h, files in hashes_seen.items():
            if len(files) > 1:
                self.replay_detection.append({
                    "hash": h,
                    "files": files,
                    "status": "potential_replay",
                })
        return self.replay_detection

    def detect_modification(self, previous_fingerprint: dict | None = None) -> list[dict]:
        """
        detect_modification

        Purpose:
        Compares the current environment fingerprint against a previous one
        to detect changes in Python version, platform, or architecture.

        Inputs:
        previous_fingerprint — optional baseline dict

        Outputs:
        List of dicts with status and optional changes list.
        """
        self.modification_detection = []
        current_fp = self.finger_print_environment()
        if previous_fingerprint is None:
            self.modification_detection.append({
                "status": "baseline_set",
                "current_fingerprint": current_fp,
            })
            return self.modification_detection
        changed_keys = []
        for key in ["python_version", "platform", "architecture"]:
            if current_fp.get(key) != previous_fingerprint.get(key):
                changed_keys.append({
                    "key": key,
                    "previous": previous_fingerprint.get(key),
                    "current": current_fp.get(key),
                })
        if changed_keys:
            self.modification_detection.append({
                "status": "modified",
                "changes": changed_keys,
            })
        else:
            self.modification_detection.append({
                "status": "intact",
            })
        return self.modification_detection

    def compute_integrity_score(self) -> float:
        """
        compute_integrity_score

        Purpose:
        Calculates a 0-100 integrity score by applying penalties for tampered,
        removed, replayed, and modified detections.

        Inputs:
        None (reads self.tamper_detection, self.replay_detection,
              self.modification_detection)

        Outputs:
        Float between 0.0 and 100.0.
        """
        score = 100.0
        tampered = sum(1 for t in self.tamper_detection if t.get("status") == "tampered")
        removed = sum(1 for t in self.tamper_detection if t.get("status") == "removed")
        replayed = len(self.replay_detection)
        modified = sum(1 for m in self.modification_detection if m.get("status") == "modified")
        score -= tampered * 20.0
        score -= removed * 15.0
        score -= replayed * 10.0
        score -= modified * 25.0
        return max(0.0, score)


def verify_benchmark_integrity(benchmark_dir: str | None = None) -> dict:
    """
    verify_benchmark_integrity

    Purpose:
    Convenience function that runs the full integrity verification pipeline
    and returns a consolidated dict.

    Inputs:
    benchmark_dir — optional root directory override

    Outputs:
    Dict with file_hashes, env_fingerprint, tamper_detection,
    replay_detection, modification_detection, integrity_score.

    Security:
    Module entry point for F183.
    """
    verifier = BenchmarkIntegrityVerifier(root_dir=benchmark_dir)
    file_hashes = verifier.hash_benchmark_files()
    env_fp = verifier.finger_print_environment()
    tamper = verifier.detect_tampering()
    replay = verifier.detect_replay()
    modify = verifier.detect_modification()
    score = verifier.compute_integrity_score()
    return {
        "file_hashes": file_hashes,
        "env_fingerprint": env_fp,
        "tamper_detection": tamper,
        "replay_detection": replay,
        "modification_detection": modify,
        "integrity_score": round(score, 2),
    }
