"""
trust_boundary/mapper.py

Purpose:
Maps trust boundaries across the codebase by identifying entry points into
each trust domain (compiler, IR, VM, runtime, attestation, FHE, ZK, proof
systems), extracting trust assumptions and data flows, and building a
cross-domain trust graph.

Architectural Role:
Produced during meta-assurance runs. Its output feeds the attack surface
enumerator (F189) and the formal threat coverage mapper (F198).

Security Relevance:
Every trust boundary between domains is an attack surface. The mapper
documents assumptions, data flows, and validation enforcement at each
boundary, enabling targeted security review.
"""
from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

# Static definition of all trust domains, their directories, and entry-point
# function name patterns. Each domain represents a distinct security boundary.
TRUST_DOMAINS = {
    "compiler": {
        "directories": ["scripts/binding/", "scripts/compiler/"],
        "entry_patterns": ["compile", "build", "generate", "transform"],
    },
    "ir": {
        "directories": ["scripts/ir/", "relay/"],
        "entry_patterns": ["compile_py_to_ir", "lower", "translate"],
    },
    "vm": {
        "directories": ["scripts/vm/", "obfuscator/"],
        "entry_patterns": ["execute", "dispatch", "interpret", "run"],
    },
    "runtime": {
        "directories": ["scripts/runtime/"],
        "entry_patterns": ["initialize", "start", "run", "execute", "loop"],
    },
    "attestation": {
        "directories": ["scripts/tee/", "scripts/sgx/"],
        "entry_patterns": ["attest", "verify", "validate", "enclave"],
    },
    "fhe": {
        "directories": ["scripts/fhe/"],
        "entry_patterns": ["encrypt", "decrypt", "evaluate", "homomorphic"],
    },
    "zk": {
        "directories": ["scripts/zk/"],
        "entry_patterns": ["prove", "verify", "generate_proof", "sigma"],
    },
    "proof_systems": {
        "directories": ["scripts/proof/"],
        "entry_patterns": ["prove", "verify", "validate", "certify"],
    },
}


@dataclass
class BoundaryEntry:
    """
    BoundaryEntry

    Purpose:
    Captures a single trust-boundary entry point — a function that crosses
    from one trust domain into another.

    Lifecycle:
    Created by trust_boundary_mapper.map_domain(); consumed by _to_dict().

    Security:
    Each entry point is a potential attack surface where trust assumptions
    must be validated.
    """
    domain: str
    file_path: str
    line_number: int
    function_name: str
    trust_assumptions: list[str] = field(default_factory=list)
    data_flow: list[str] = field(default_factory=list)
    has_validation: bool = False
    validation_details: list[str] = field(default_factory=list)


@dataclass
class BoundaryReport:
    """
    BoundaryReport

    Purpose:
    Aggregates all trust-boundary entries, assumptions, enforcement status,
    and the cross-domain trust graph.

    Lifecycle:
    Populated by TrustBoundaryMapper.map_trust_boundaries().
    """
    boundary_entries: dict[str, list[BoundaryEntry]] = field(default_factory=dict)
    trust_assumptions: dict[str, list[str]] = field(default_factory=dict)
    enforcement_status: dict[str, bool] = field(default_factory=dict)
    trust_graph: dict[str, list[str]] = field(default_factory=dict)


class TrustBoundaryMapper:
    """
    TrustBoundaryMapper

    Purpose:
    Scans codebase directories for each trust domain, identifies entry-point
    functions, extracts assumptions and data flows, and builds a trust graph.

    Lifecycle:
    Created on demand; map_trust_boundaries() drives the full analysis.

    Security:
    Provides the foundation for attack surface enumeration and threat coverage
    mapping by documenting where trust crosses domain boundaries.
    """
    def __init__(self, root_dir: str | None = None):
        self.root_dir = root_dir or _ROOT
        self.report = BoundaryReport()

    def _find_python_files(self, directory: str) -> list[str]:
        """
        _find_python_files

        Purpose:
        Recursively finds all .py files under a given directory.

        Inputs:
        directory — relative path from root_dir

        Outputs:
        List of absolute file paths.
        """
        full_path = os.path.join(self.root_dir, directory)
        if not os.path.isdir(full_path):
            return []
        result = []
        for root, _dirs, files in os.walk(full_path):
            for f in files:
                if f.endswith(".py"):
                    result.append(os.path.join(root, f))
        return result

    def _extract_functions(self, file_path: str) -> list[tuple[str, int, str]]:
        """
        _extract_functions

        Purpose:
        Parses a .py file and extracts all function and async function definitions
        with their line numbers and source segments.

        Inputs:
        file_path — absolute path to the .py file

        Outputs:
        List of (name, lineno, source_segment) tuples.
        """
        functions = []
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append((node.name, node.lineno, ast.get_source_segment(source, node) or ""))
        except (SyntaxError, UnicodeDecodeError):
            pass
        return functions

    def _detect_entry_points(self, functions: list[tuple[str, int, str]], domain_info: dict) -> list[tuple[str, int, str]]:
        """
        _detect_entry_points

        Purpose:
        Filters functions to those whose names match the domain's entry-point
        patterns.

        Inputs:
        functions — list of (name, lineno, source) tuples
        domain_info — dict with 'entry_patterns' list

        Outputs:
        Filtered list of matching entry-point tuples.
        """
        entries = []
        for name, lineno, body in functions:
            for pattern in domain_info["entry_patterns"]:
                if pattern in name.lower():
                    entries.append((name, lineno, body))
                    break
        return entries

    def _extract_trust_assumptions(self, functions: list[tuple[str, int, str]]) -> list[str]:
        """
        _extract_trust_assumptions

        Purpose:
        Scans function bodies for trust-related keywords (trust, assume,
        external, input, etc.) and extracts the matching lines.

        Inputs:
        functions — list of (name, lineno, source) tuples

        Outputs:
        List of assumption line snippets (max 10).
        """
        assumptions = []
        trust_keywords = ["trust", "assume", "assumption", "presume", "rely", "external", "input"]
        for _name, _lineno, body in functions:
            body_lower = body.lower()
            for kw in trust_keywords:
                if kw in body_lower:
                    for line in body.split("\n"):
                        if kw in line.lower():
                            stripped = line.strip()
                            if stripped and stripped not in assumptions:
                                assumptions.append(stripped[:120])
        return assumptions[:10]

    def _extract_data_flow(self, functions: list[tuple[str, int, str]]) -> list[str]:
        """
        _extract_data_flow

        Purpose:
        Scans function bodies for data-flow keywords (param, argument, input,
        receive, return, yield, call, invoke) and extracts matching lines.

        Inputs:
        functions — list of (name, lineno, source) tuples

        Outputs:
        List of data-flow line snippets (max 10).
        """
        flows = []
        flow_keywords = ["param", "argument", "input", "receive", "return", "yield", "call", "invoke"]
        for _name, _lineno, body in functions:
            body_lower = body.lower()
            for kw in flow_keywords:
                if kw in body_lower:
                    for line in body.split("\n"):
                        if kw in line.lower():
                            stripped = line.strip()
                            if stripped and stripped not in flows:
                                flows.append(stripped[:120])
        return flows[:10]

    def _detect_validation(self, functions: list[tuple[str, int, str]]) -> tuple[bool, list[str]]:
        """
        _detect_validation

        Purpose:
        Checks function bodies for validation keywords (assert, raise, verify,
        validate, check, ensure, require).

        Inputs:
        functions — list of (name, lineno, source) tuples

        Outputs:
        Tuple of (has_validation, list_of_detail_snippets).
        """
        validation_keywords = ["assert", "raise", "verify", "validate", "check", "if not", "ensure", "require"]
        details = []
        for _name, _lineno, body in functions:
            body_lower = body.lower()
            for kw in validation_keywords:
                if kw in body_lower:
                    for line in body.split("\n"):
                        if kw in line.lower():
                            stripped = line.strip()
                            if stripped and stripped not in details:
                                details.append(stripped[:120])
        return len(details) > 0, details[:5]

    def map_domain(self, domain: str, domain_info: dict) -> list[BoundaryEntry]:
        """
        map_domain

        Purpose:
        Maps all entry points for a single trust domain by finding Python files,
        extracting functions, detecting entry points, and gathering assumptions,
        data flow, and validation info.

        Inputs:
        domain — domain name string
        domain_info — dict with 'directories' and 'entry_patterns'

        Outputs:
        List of BoundaryEntry objects for the domain.
        """
        entries = []
        for directory in domain_info["directories"]:
            py_files = self._find_python_files(directory)
            for file_path in py_files:
                functions = self._extract_functions(file_path)
                entry_fns = self._detect_entry_points(functions, domain_info)
                for func_name, lineno, body in entry_fns:
                    func_tuple = [(func_name, lineno, body)]
                    assumptions = self._extract_trust_assumptions(func_tuple)
                    data_flow = self._extract_data_flow(func_tuple)
                    has_val, val_details = self._detect_validation(func_tuple)
                    entry = BoundaryEntry(
                        domain=domain,
                        file_path=os.path.relpath(file_path, self.root_dir),
                        line_number=lineno,
                        function_name=func_name,
                        trust_assumptions=assumptions,
                        data_flow=data_flow,
                        has_validation=has_val,
                        validation_details=val_details,
                    )
                    entries.append(entry)
        return entries

    def _build_trust_graph(self) -> dict[str, list[str]]:
        """
        _build_trust_graph

        Purpose:
        Constructs a directed trust graph where edges represent data-flow
        dependencies between trust domains.

        Inputs:
        None (reads self.report.boundary_entries)

        Outputs:
        Dict mapping domain -> list of dependent domains.
        """
        graph: dict[str, list[str]] = {}
        domains = list(TRUST_DOMAINS.keys())
        for i, domain in enumerate(domains):
            deps = []
            if i > 0:
                deps.append(domains[i - 1])
            if i < len(domains) - 1:
                deps.append(domains[i + 1])
            graph[domain] = deps

        for domain, entries in self.report.boundary_entries.items():
            for entry in entries:
                for dep_domain in domains:
                    if dep_domain == domain:
                        continue
                    if dep_domain in entry.data_flow or any(
                        dep_domain in d for d in entry.data_flow
                    ):
                        if dep_domain not in graph.setdefault(domain, []):
                            graph[domain].append(dep_domain)
        return graph

    def map_trust_boundaries(self) -> dict[str, Any]:
        """
        map_trust_boundaries

        Purpose:
        Main entry point — iterates over all trust domains, maps boundary
        entries, aggregates assumptions, determines enforcement status, and
        builds the trust graph.

        Inputs:
        None

        Outputs:
        Dict with boundary_entries, trust_assumptions, enforcement_status,
        trust_graph.
        """
        for domain, domain_info in TRUST_DOMAINS.items():
            entries = self.map_domain(domain, domain_info)
            self.report.boundary_entries[domain] = entries
            all_assumptions: list[str] = []
            for e in entries:
                all_assumptions.extend(e.trust_assumptions)
            self.report.trust_assumptions[domain] = list(set(all_assumptions))
            enforced_count = sum(1 for e in entries if e.has_validation)
            self.report.enforcement_status[domain] = enforced_count >= len(entries) / 2 if entries else False

        self.report.trust_graph = self._build_trust_graph()

        result = self._to_dict()
        return result

    def _to_dict(self) -> dict[str, Any]:
        """
        _to_dict

        Purpose:
        Serializes the BoundaryReport into a plain dict for JSON output.

        Inputs:
        None

        Outputs:
        Dict with all report fields.
        """
        return {
            "boundary_entries": {
                domain: [
                    {
                        "domain": e.domain,
                        "file_path": e.file_path,
                        "line_number": e.line_number,
                        "function_name": e.function_name,
                        "trust_assumptions": e.trust_assumptions,
                        "data_flow": e.data_flow,
                        "has_validation": e.has_validation,
                        "validation_details": e.validation_details,
                    }
                    for e in entries
                ]
                for domain, entries in self.report.boundary_entries.items()
            },
            "trust_assumptions": self.report.trust_assumptions,
            "enforcement_status": {
                domain: {
                    "enforced": status,
                    "total_entries": len(self.report.boundary_entries.get(domain, [])),
                    "enforced_entries": sum(
                        1 for e in self.report.boundary_entries.get(domain, []) if e.has_validation
                    ),
                }
                for domain, status in self.report.enforcement_status.items()
            },
            "trust_graph": self.report.trust_graph,
        }
