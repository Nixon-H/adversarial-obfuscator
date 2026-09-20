"""
attack_surface/enumerator.py

Purpose:
Enumerates all potential attack surface entry points across seven categories:
CLI, runtime (dangerous calls), VM, proof verification, attestation, network,
and filesystem.

Architectural Role:
Called during meta-assurance to produce an attack surface report that feeds
threat coverage analysis (F198) and release confidence scoring (F197).

Security Relevance:
Every enumerated entry point is a potential vector for attackers. Categorization
by risk level (CRITICAL/HIGH/MEDIUM/LOW) prioritizes remediation.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

RISK_LEVELS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


@dataclass
class AttackSurfaceEntry:
    """
    AttackSurfaceEntry

    Purpose:
    Represents a single attack surface entry point found during scanning.

    Lifecycle:
    Created by enumeration methods; consumed by enumerate_attack_surfaces().

    Security:
    Each entry represents a potential vulnerability vector with a risk level.
    """
    category: str
    file_path: str
    line_number: int
    code_snippet: str
    risk_level: str
    description: str
    entry_type: str


@dataclass
class AttackSurfaceReport:
    """
    AttackSurfaceReport

    Purpose:
    Aggregates all attack surface entries, total counts, and risk summary.

    Lifecycle:
    Populated by AttackSurfaceEnumerator.enumerate_attack_surfaces().
    """
    per_category_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    total_entry_points: int = 0
    risk_summary: dict[str, int] = field(default_factory=lambda: {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0})


class AttackSurfaceEnumerator:
    """
    AttackSurfaceEnumerator

    Purpose:
    Scans the entire codebase for attack surface indicators across CLI, runtime,
    VM, proof, attestation, network, and filesystem categories.

    Lifecycle:
    Created on demand; enumerate_attack_surfaces() drives all scans.
    """
    def __init__(self, root_dir: str | None = None):
        self.root_dir = root_dir or _ROOT
        self.report = AttackSurfaceReport()

    def _find_py_files(self) -> list[str]:
        """
        _find_py_files

        Purpose:
        Recursively finds all .py files in the root directory.

        Inputs:
        None

        Outputs:
        List of absolute file paths.
        """
        result = []
        for root, _dirs, files in os.walk(self.root_dir):
            for f in files:
                if f.endswith(".py"):
                    result.append(os.path.join(root, f))
        return result

    def _find_rs_files(self) -> list[str]:
        """
        _find_rs_files

        Purpose:
        Finds all .rs files under the relay/ and runtime/ directories.

        Inputs:
        None

        Outputs:
        List of absolute file paths.
        """
        result = []
        relay_dir = os.path.join(self.root_dir, "relay")
        runtime_dir = os.path.join(self.root_dir, "runtime")
        for d in [relay_dir, runtime_dir]:
            if os.path.isdir(d):
                for root, _dirs, files in os.walk(d):
                    for f in files:
                        if f.endswith(".rs"):
                            result.append(os.path.join(root, f))
        return result

    def _read_lines(self, file_path: str) -> list[str]:
        """
        _read_lines

        Purpose:
        Reads a file and returns its lines, safely handling encoding errors.

        Inputs:
        file_path — absolute path to the file

        Outputs:
        List of strings (lines).
        """
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.readlines()
        except OSError:
            return []

    def _enumerate_cli_attack_surface(self) -> list[AttackSurfaceEntry]:
        """
        _enumerate_cli_attack_surface

        Purpose:
        Scans for CLI argument definitions and interactive input() calls.

        Inputs:
        None

        Outputs:
        List of AttackSurfaceEntry for CLI attack vectors.
        """
        entries = []
        for file_path in self._find_py_files():
            lines = self._read_lines(file_path)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if "add_argument" in stripped and "parser.add_argument" not in stripped:
                    if "--" in stripped:
                        entries.append(AttackSurfaceEntry(
                            category="cli",
                            file_path=os.path.relpath(file_path, self.root_dir),
                            line_number=i,
                            code_snippet=stripped[:120],
                            risk_level="HIGH",
                            description="CLI argument injection point",
                            entry_type="cli_argument",
                        ))
                elif "input(" in stripped or "raw_input(" in stripped:
                    entries.append(AttackSurfaceEntry(
                        category="cli",
                        file_path=os.path.relpath(file_path, self.root_dir),
                        line_number=i,
                        code_snippet=stripped[:120],
                        risk_level="CRITICAL",
                        description="Interactive input injection point",
                        entry_type="user_input",
                    ))
        return entries

    def _enumerate_runtime_attack_surface(self) -> list[AttackSurfaceEntry]:
        """
        _enumerate_runtime_attack_surface

        Purpose:
        Scans for dangerous runtime function calls (exec, eval, subprocess,
        os.system, os.popen).

        Inputs:
        None

        Outputs:
        List of AttackSurfaceEntry for runtime attack vectors.
        """
        entries = []
        dangerous_funcs = ["exec(", "eval(", "subprocess.", "os.system(", "os.popen("]
        for file_path in self._find_py_files():
            lines = self._read_lines(file_path)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                for func in dangerous_funcs:
                    if func in stripped and not stripped.startswith("#"):
                        risk = "CRITICAL" if func in ("exec(", "eval(") else "HIGH"
                        entries.append(AttackSurfaceEntry(
                            category="runtime",
                            file_path=os.path.relpath(file_path, self.root_dir),
                            line_number=i,
                            code_snippet=stripped[:120],
                            risk_level=risk,
                            description=f"Dangerous function call: {func}",
                            entry_type="dangerous_call",
                        ))
        return entries

    def _enumerate_vm_attack_surface(self) -> list[AttackSurfaceEntry]:
        """
        _enumerate_vm_attack_surface

        Purpose:
        Scans VM-related directories for entry-point functions (execute, dispatch,
        interpret, run).

        Inputs:
        None

        Outputs:
        List of AttackSurfaceEntry for VM attack vectors.
        """
        entries = []
        vm_dirs = ["scripts/vm", "obfuscator"]
        for d in vm_dirs:
            full_path = os.path.join(self.root_dir, d)
            if not os.path.isdir(full_path):
                continue
            for root, _dirs, files in os.walk(full_path):
                for f in files:
                    if f.endswith(".py"):
                        fp = os.path.join(root, f)
                        lines = self._read_lines(fp)
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            if "def " in stripped and ("execute" in stripped.lower() or "dispatch" in stripped.lower() or "interpret" in stripped.lower() or "run" in stripped.lower()):
                                entries.append(AttackSurfaceEntry(
                                    category="vm",
                                    file_path=os.path.relpath(fp, self.root_dir),
                                    line_number=i,
                                    code_snippet=stripped[:120],
                                    risk_level="HIGH",
                                    description="VM entry point that could be bypassed",
                                    entry_type="vm_entry_point",
                                ))
        return entries

    def _enumerate_proof_attack_surface(self) -> list[AttackSurfaceEntry]:
        """
        _enumerate_proof_attack_surface

        Purpose:
        Scans proof-related directories for verify/validate function definitions.

        Inputs:
        None

        Outputs:
        List of AttackSurfaceEntry for proof verification attack vectors.
        """
        entries = []
        proof_dirs = ["scripts/proof", "scripts/proofs", "scripts/validation"]
        for d in proof_dirs:
            full_path = os.path.join(self.root_dir, d)
            if not os.path.isdir(full_path):
                continue
            for root, _dirs, files in os.walk(full_path):
                for f in files:
                    if f.endswith(".py"):
                        fp = os.path.join(root, f)
                        lines = self._read_lines(fp)
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            if "def verify" in stripped.lower() or "def validate" in stripped.lower():
                                entries.append(AttackSurfaceEntry(
                                    category="proof",
                                    file_path=os.path.relpath(fp, self.root_dir),
                                    line_number=i,
                                    code_snippet=stripped[:120],
                                    risk_level="CRITICAL",
                                    description="Proof verification logic that could be bypassed",
                                    entry_type="proof_verification",
                                ))
        return entries

    def _enumerate_attestation_attack_surface(self) -> list[AttackSurfaceEntry]:
        """
        _enumerate_attestation_attack_surface

        Purpose:
        Scans TEE/SGX directories for attestation and enclave-related logic.

        Inputs:
        None

        Outputs:
        List of AttackSurfaceEntry for attestation attack vectors.
        """
        entries = []
        attest_dirs = ["scripts/tee", "scripts/sgx"]
        for d in attest_dirs:
            full_path = os.path.join(self.root_dir, d)
            if not os.path.isdir(full_path):
                continue
            for root, _dirs, files in os.walk(full_path):
                for f in files:
                    if f.endswith((".py", ".rs")):
                        fp = os.path.join(root, f)
                        lines = self._read_lines(fp)
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            if "attest" in stripped.lower() or "enclave" in stripped.lower():
                                entries.append(AttackSurfaceEntry(
                                    category="attestation",
                                    file_path=os.path.relpath(fp, self.root_dir),
                                    line_number=i,
                                    code_snippet=stripped[:120],
                                    risk_level="CRITICAL",
                                    description="Attestation logic that could be subverted",
                                    entry_type="attestation_entry",
                                ))
        return entries

    def _enumerate_network_attack_surface(self) -> list[AttackSurfaceEntry]:
        """
        _enumerate_network_attack_surface

        Purpose:
        Scans for network-related library calls (socket, requests, urlopen,
        http.client, aiohttp, websocket).

        Inputs:
        None

        Outputs:
        List of AttackSurfaceEntry for network attack vectors.
        """
        entries = []
        network_patterns = ["socket.", "requests.", "urlopen", "http.client", "aiohttp", "websocket"]
        for file_path in self._find_py_files():
            lines = self._read_lines(file_path)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                for pat in network_patterns:
                    if pat in stripped and not stripped.startswith("#"):
                        entries.append(AttackSurfaceEntry(
                            category="network",
                            file_path=os.path.relpath(file_path, self.root_dir),
                            line_number=i,
                            code_snippet=stripped[:120],
                            risk_level="HIGH",
                            description=f"Network call: {pat}",
                            entry_type="network_call",
                        ))
        return entries

    def _enumerate_filesystem_attack_surface(self) -> list[AttackSurfaceEntry]:
        """
        _enumerate_filesystem_attack_surface

        Purpose:
        Scans for filesystem access calls (open, os.remove, shutil, os.rename).

        Inputs:
        None

        Outputs:
        List of AttackSurfaceEntry for filesystem attack vectors.
        """
        entries = []
        fs_patterns = ["open(", "open(", "os.remove", "os.unlink", "shutil.", "os.rename"]
        for file_path in self._find_py_files():
            lines = self._read_lines(file_path)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                for pat in fs_patterns:
                    if pat in stripped and not stripped.startswith("#"):
                        entries.append(AttackSurfaceEntry(
                            category="filesystem",
                            file_path=os.path.relpath(file_path, self.root_dir),
                            line_number=i,
                            code_snippet=stripped[:120],
                            risk_level="MEDIUM",
                            description=f"Filesystem access: {pat}",
                            entry_type="filesystem_call",
                        ))
        return entries

    def enumerate_attack_surfaces(self) -> dict[str, Any]:
        """
        enumerate_attack_surfaces

        Purpose:
        Main entry point — runs all seven category scans, aggregates entries,
        and produces a serializable report.

        Inputs:
        None

        Outputs:
        Dict with per_category_results, total_entry_points, risk_summary.
        """
        all_entries: dict[str, list[AttackSurfaceEntry]] = {
            "cli": self._enumerate_cli_attack_surface(),
            "runtime": self._enumerate_runtime_attack_surface(),
            "vm": self._enumerate_vm_attack_surface(),
            "proof": self._enumerate_proof_attack_surface(),
            "attestation": self._enumerate_attestation_attack_surface(),
            "network": self._enumerate_network_attack_surface(),
            "filesystem": self._enumerate_filesystem_attack_surface(),
        }

        total = 0
        risk_counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        per_cat: dict[str, list[dict[str, Any]]] = {}

        for category, entries in all_entries.items():
            serialized = []
            for e in entries:
                serialized.append({
                    "category": e.category,
                    "file_path": e.file_path,
                    "line_number": e.line_number,
                    "code_snippet": e.code_snippet,
                    "risk_level": e.risk_level,
                    "description": e.description,
                    "entry_type": e.entry_type,
                })
                risk_counts[e.risk_level] = risk_counts.get(e.risk_level, 0) + 1
                total += 1
            per_cat[category] = serialized

        self.report.per_category_results = per_cat
        self.report.total_entry_points = total
        self.report.risk_summary = risk_counts

        return {
            "per_category_results": per_cat,
            "total_entry_points": total,
            "risk_summary": risk_counts,
        }
