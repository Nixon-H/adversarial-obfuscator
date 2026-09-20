"""
verification_bundle/collector.py — Artefact collection for verification bundles (F177)

Purpose:
    Walks the repository and build directory to discover and hash all artefacts
    eligible for inclusion in a verification bundle: source files, benchmarks,
    trace files, proof certificates, and attack results.

Architectural Role:
    Discovery layer. Consumed by VerificationBundler to populate the bundle
    with a complete, hashed snapshot of all relevant build outputs.

Security Relevance:
    Systematic artefact collection ensures no relevant build output is missed.
    Every collected file is SHA-256 hashed for integrity verification.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .hasher import file_sha256, build_manifest_entry

# File extensions and glob patterns for artefact discovery.
SOURCE_EXTS = {".py", ".c", ".h", ".rs", ".toml", ".json", ".yaml", ".yml", ".cfg", ".ir", ".ll", ".s", ".S"}
BENCHMARK_GLOBS = {"benchmark_report.json", "benchmark_results.json", "benchmark/*.json", "benchmarks/*.json"}
TRACE_GLOBS = {"trace*.json", "traces/*.json", "*.prof", "pipeline*.prof"}
PROOF_GLOBS = {"proofs/**/*.json", "certificates/**/*.json", "ledger*.json", "evidence_ledger.json"}
ATTACK_GLOBS = {"redteam/**/*.json", "attacks/**/*.json", "adversarial_bench_report.json"}


class ArtifactCollector:
    """Discovers and hashes build artefacts for verification bundle inclusion.

    Collects source references, benchmark reports, execution traces, proof
    certificates, and attack results from the build directory and repository.
    """

    def __init__(self, build_dir: str, payload_path: str | None = None):
        self.build_dir = build_dir
        self.payload_path = payload_path
        self._entries: list[dict] = []
        self._source_refs: list[dict] = []
        self._benchmarks: list[dict] = []
        self._traces: list[dict] = []
        self._proof_artifacts: list[dict] = []
        self._attack_artifacts: list[dict] = []

    def collect_all(self) -> dict[str, Any]:
        """Run all collectors and return a summary dict with categorized entries."""
        self._collect_source_references()
        self._collect_benchmarks()
        self._collect_traces()
        self._collect_proofs()
        self._collect_attacks()
        return self.summary()

    def _walk_and_match(self, patterns: set[str]) -> list[str]:
        """Walk build_dir and return file paths matching any pattern in the set (glob-based)."""
        matched = []
        for root, _dirs, files in os.walk(self.build_dir):
            for fn in files:
                fpath = os.path.join(root, fn)
                rel = os.path.relpath(fpath, self.build_dir)
                for pat in patterns:
                    if "/" in pat:
                        prefix = pat.split("**")[0].rstrip("/")
                        if rel.startswith(prefix) and rel.endswith(".json"):
                            matched.append(fpath)
                            break
                        if prefix and rel.startswith(prefix):
                            matched.append(fpath)
                            break
                    else:
                        if fn == pat or fn.endswith(pat.strip("*")):
                            matched.append(fpath)
                            break
        return matched

    def _collect_source_references(self) -> None:
        """Walk known source directories (scripts, obfuscator, irgen, etc.) and collect matching source files."""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        src_dirs = []
        for candidate in ["scripts", "obfuscator", "irgen", "llvmgen", "vm", "relay", "native", "runtime", "config"]:
            p = os.path.join(root, candidate)
            if os.path.isdir(p):
                src_dirs.append(p)
        seen = set()
        for sd in src_dirs:
            for root_dir, _dirs, files in os.walk(sd):
                for fn in files:
                    ext = os.path.splitext(fn)[1]
                    if ext in SOURCE_EXTS:
                        fpath = os.path.join(root_dir, fn)
                        if fpath not in seen:
                            seen.add(fpath)
                            rel = os.path.relpath(fpath, root)
                            entry = build_manifest_entry(fpath, f"sources/{rel}")
                            entry["archive_rel"] = f"sources/{rel}"
                            entry["category"] = "source"
                            self._source_refs.append(entry)
                            self._entries.append(entry)
        if self.payload_path and os.path.isfile(self.payload_path):
            entry = build_manifest_entry(self.payload_path, f"sources/{os.path.basename(self.payload_path)}")
            entry["archive_rel"] = f"sources/{os.path.basename(self.payload_path)}"
            entry["category"] = "source"
            self._source_refs.append(entry)
            self._entries.append(entry)

    def _collect_benchmarks(self) -> None:
        """Collect benchmark report files matching BENCHMARK_GLOBS patterns."""
        for fpath in self._walk_and_match(BENCHMARK_GLOBS):
            rel = os.path.relpath(fpath, self.build_dir)
            entry = build_manifest_entry(fpath, f"benchmarks/{os.path.basename(fpath)}")
            entry["archive_rel"] = f"benchmarks/{os.path.basename(fpath)}"
            entry["category"] = "benchmark"
            self._benchmarks.append(entry)
            self._entries.append(entry)

    def _collect_traces(self) -> None:
        """Collect trace/profile files matching TRACE_GLOBS patterns."""
        for fpath in self._walk_and_match(TRACE_GLOBS):
            rel = os.path.relpath(fpath, self.build_dir)
            entry = build_manifest_entry(fpath, f"traces/{os.path.basename(fpath)}")
            entry["archive_rel"] = f"traces/{os.path.basename(fpath)}"
            entry["category"] = "trace"
            self._traces.append(entry)
            self._entries.append(entry)

    def _collect_proofs(self) -> None:
        """Collect proof and certificate files matching PROOF_GLOBS patterns."""
        for fpath in self._walk_and_match(PROOF_GLOBS):
            rel = os.path.relpath(fpath, self.build_dir)
            entry = build_manifest_entry(fpath, f"proofs/{os.path.basename(fpath)}")
            entry["archive_rel"] = f"proofs/{os.path.basename(fpath)}"
            entry["category"] = "proof"
            self._proof_artifacts.append(entry)
            self._entries.append(entry)

    def _collect_attacks(self) -> None:
        """Collect attack/red-team result files matching ATTACK_GLOBS patterns."""
        for fpath in self._walk_and_match(ATTACK_GLOBS):
            rel = os.path.relpath(fpath, self.build_dir)
            entry = build_manifest_entry(fpath, f"attacks/{os.path.basename(fpath)}")
            entry["archive_rel"] = f"attacks/{os.path.basename(fpath)}"
            entry["category"] = "attack"
            self._attack_artifacts.append(entry)
            self._entries.append(entry)

    def summary(self) -> dict[str, Any]:
        """Return a complete summary dict with all collected entries and per-category counts."""
        return {
            "total_entries": len(self._entries),
            "source_references": len(self._source_refs),
            "benchmarks": len(self._benchmarks),
            "traces": len(self._traces),
            "proof_artifacts": len(self._proof_artifacts),
            "attack_artifacts": len(self._attack_artifacts),
            "entries": self._entries,
            "source_refs": self._source_refs,
            "benchmarks_list": self._benchmarks,
            "traces_list": self._traces,
            "proofs_list": self._proof_artifacts,
            "attacks_list": self._attack_artifacts,
        }

    def entries_for_bundle(self) -> list[tuple[str, str]]:
        """Return list of (local_path, sha256) tuples for all collected entries."""
        return [(e["local_path"], e["sha256"]) for e in self._entries]
