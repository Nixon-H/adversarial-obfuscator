"""
threat_coverage/mapper.py

Purpose:
Maps security features, metrics, and verifications to a formal threat taxonomy.
Each threat (reverse engineering, code tampering, debugging, etc.) is checked
for corresponding features, metrics, and verifications in the codebase.

Architectural Role:
Core component of the meta-assurance pipeline. Produces a coverage matrix
and uncovered-threat list consumed by the release confidence scorer (F197).

Security Relevance:
Threat coverage is the most direct measure of security completeness.
Uncovered threats represent blind spots where the system offers no protection.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ThreatDef:
    """
    ThreatDef

    Purpose:
    Defines a single threat category with its name and description.
    """
    name: str
    description: str


@dataclass
class CoverageEntry:
    """
    CoverageEntry

    Purpose:
    Stores the coverage status for one threat — which features, metrics,
    and verifications exist in the codebase for that threat.

    Lifecycle:
    Created by build_coverage().
    """
    threat: str
    features: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    verifications: list[str] = field(default_factory=list)

    def is_covered(self) -> bool:
        return bool(self.features) and bool(self.metrics) and bool(self.verifications)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# The formal threat taxonomy: 10 threat categories with descriptions.
THREAT_TAXONOMY: list[ThreatDef] = [
    ThreatDef("reverse_engineering", "Reverse engineering of obfuscated code"),
    ThreatDef("code_tampering", "Unauthorized modification of protected code"),
    ThreatDef("debugging", "Dynamic analysis via debuggers"),
    ThreatDef("memory_analysis", "Memory dump and analysis attacks"),
    ThreatDef("side_channel", "Timing, power, and EM side-channel attacks"),
    ThreatDef("fhe_attacks", "Attacks on FHE/VHE cryptographic operations"),
    ThreatDef("vm_attacks", "Attacks on custom VM bytecode/opcodes"),
    ThreatDef("proof_system_attacks", "Attacks on proof-carrying code"),
    ThreatDef("network_attacks", "Network-based interception and tampering"),
    ThreatDef("supply_chain", "Supply chain attacks on build artifacts"),
]


# Keywords in source code that indicate a feature protecting against a given threat.
FEATURE_KEYWORDS: dict[str, list[str]] = {
    "reverse_engineering": [
        "obfuscat",
        "flatten",
        "mba",
        "junk",
        "entangl",
        "opaque",
        "anti",
        "trap",
        "decoy",
    ],
    "code_tampering": [
        "integrity",
        "hash",
        "sign",
        "checksum",
        "tamper",
        "watermark",
        "bind",
    ],
    "debugging": ["anti.debug", "ptrace", "anti_debug", "debug_detect", "trap"],
    "memory_analysis": [
        "encrypt",
        "memory",
        "scramble",
        "protect",
        "shield",
    ],
    "side_channel": [
        "side",
        "channel",
        "timing",
        "constant",
        "cache",
        "bound",
    ],
    "fhe_attacks": ["fhe", "homomorph", "encrypt", "crypto", "he"],
    "vm_attacks": ["vm", "bytecode", "opcode", "virtual", "isa"],
    "proof_system_attacks": [
        "proof",
        "soundness",
        "verif",
        "z3",
        "smt",
        "valid",
    ],
    "network_attacks": [
        "network",
        "tls",
        "ssl",
        "channel",
        "remote",
    ],
    "supply_chain": ["artifact", "bundle", "manifest", "reproduc", "packag"],
}

# Keywords in source code that indicate a metric measuring protection against a threat.
METRIC_KEYWORDS: dict[str, list[str]] = {
    "reverse_engineering": [
        "entropy",
        "resilience",
        "classif",
        "divers",
    ],
    "code_tampering": [
        "integrity",
        "watermark",
        "binding",
    ],
    "debugging": ["speed", "evasion", "anti."],
    "memory_analysis": ["exposure", "leakage"],
    "side_channel": ["side", "channel", "cache", "timing"],
    "fhe_attacks": ["fhe", "latency", "throughput"],
    "vm_attacks": ["vm", "bytecode", "opcode"],
    "proof_system_attacks": [
        "proof",
        "coverage",
        "soundness",
    ],
    "network_attacks": ["network", "remote"],
    "supply_chain": ["reproduc", "artifact"],
}

# Keywords in test files that indicate verification of protection against a threat.
VERIFICATION_KEYWORDS: dict[str, list[str]] = {
    "reverse_engineering": [
        "redteam",
        "angr",
        "ghidra",
        "bninja",
        "adversarial",
    ],
    "code_tampering": [
        "test.*integrity",
        "test.*tamper",
        "test.*watermark",
    ],
    "debugging": ["test.*debug", "test.*anti"],
    "memory_analysis": ["test.*exposure", "test.*leakage", "test.*memory"],
    "side_channel": ["test.*cache", "test.*side", "test.*timing"],
    "fhe_attacks": ["test.*fhe", "test.*encrypt", "test.*homomorph"],
    "vm_attacks": ["test.*vm", "test.*bytecode", "test.*opcode"],
    "proof_system_attacks": [
        "test.*proof",
        "test.*soundness",
        "test.*valid",
    ],
    "network_attacks": ["test.*network"],
    "supply_chain": [
        "test.*reproduc",
        "test.*artifact",
        "test.*bundle",
    ],
}


def _scan_tree_for_keywords(root: str, dirname: str,
                            keyword_map: dict[str, list[str]],
                            *, test_files_only: bool = False) -> dict[str, set[str]]:
    """Scan ``root/dirname`` once and bucket files by matching keyword set.

    The mapper used to re-read every file once per threat (ten passes per
    scan, thirty passes for a full coverage build).  In a container with
    generated evidence present that pushed the release-gate probe past its
    60-second budget even though the scan itself is simple.  Reading each
    file once preserves the same keyword semantics without the repeated I/O.
    """
    base = os.path.join(root, dirname)
    results: dict[str, set[str]] = {key: set() for key in keyword_map}
    if not os.path.isdir(base):
        return results
    compiled = {
        key: [re.compile(kw, re.IGNORECASE) for kw in keywords]
        for key, keywords in keyword_map.items()
    }
    for root_dir, _dirs, files in os.walk(base):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            if test_files_only and not (
                    filename.startswith("test_") or filename.startswith("bench_")):
                continue
            fpath = os.path.join(root_dir, filename)
            rel = os.path.relpath(fpath, root)
            try:
                with open(fpath, "r", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue
            for key, patterns in compiled.items():
                if any(pattern.search(content) for pattern in patterns):
                    results[key].add(rel)
    return results


class ThreatCoverageMapper:
    """
    ThreatCoverageMapper

    Purpose:
    Maps codebase features, metrics, and pytest test verifications to a formal
    threat taxonomy, producing a coverage matrix.

    Lifecycle:
    Created on demand; build_coverage() drives all three scans.
    """
    def __init__(self, root: str = "") -> None:
        self.root = root or _ROOT
        self.coverage: list[CoverageEntry] = []
        self._features_cache: dict[str, set[str]] = {}
        self._metrics_cache: dict[str, set[str]] = {}
        self._verifications_cache: dict[str, set[str]] = {}

    def scan_scripts_for_features(self) -> None:
        """
        scan_scripts_for_features

        Purpose:
        Scans all .py files in scripts/ for feature keywords matching each
        threat category.

        Inputs:
        None

        Outputs:
        None (populates self._features_cache)
        """
        self._features_cache = _scan_tree_for_keywords(
            self.root, "scripts", FEATURE_KEYWORDS)

    def scan_for_metrics(self) -> None:
        """
        scan_for_metrics

        Purpose:
        Scans all .py files in scripts/ for metric keywords matching each
        threat category.

        Inputs:
        None

        Outputs:
        None (populates self._metrics_cache)
        """
        self._metrics_cache = _scan_tree_for_keywords(
            self.root, "scripts", METRIC_KEYWORDS)

    def scan_for_verifications(self) -> None:
        """
        scan_for_verifications

        Purpose:
        Scans pytest-collected ``test_*.py``/``bench_*.py`` files for verification keywords
        matching each threat category. Generated fixture artefacts are not
        verification evidence and are deliberately not scanned.

        Inputs:
        None

        Outputs:
        None (populates self._verifications_cache)
        """
        self._verifications_cache = _scan_tree_for_keywords(
            self.root, "tests", VERIFICATION_KEYWORDS, test_files_only=True)

    def build_coverage(self) -> list[CoverageEntry]:
        """
        build_coverage

        Purpose:
        Main entry point — runs all three scans and builds the coverage list
        by matching each threat to its features, metrics, and verifications.

        Inputs:
        None

        Outputs:
        List of CoverageEntry (one per threat).
        """
        self.scan_scripts_for_features()
        self.scan_for_metrics()
        self.scan_for_verifications()

        self.coverage = []
        for threat in THREAT_TAXONOMY:
            entry = CoverageEntry(
                threat=threat.name,
                features=sorted(self._features_cache.get(threat.name, set())),
                metrics=sorted(self._metrics_cache.get(threat.name, set())),
                verifications=sorted(
                    self._verifications_cache.get(threat.name, set())
                ),
            )
            self.coverage.append(entry)
        return self.coverage

    def get_uncovered_threats(self) -> list[dict[str, Any]]:
        """
        get_uncovered_threats

        Purpose:
        Returns a list of threats missing features, metrics, or verifications.

        Inputs:
        None

        Outputs:
        List of dicts with threat name and list of missing categories.
        """
        uncovered: list[dict[str, Any]] = []
        for entry in self.coverage:
            missing: list[str] = []
            if not entry.features:
                missing.append("feature")
            if not entry.metrics:
                missing.append("metric")
            if not entry.verifications:
                missing.append("verification")
            if missing:
                uncovered.append(
                    {
                        "threat": entry.threat,
                        "missing": missing,
                    }
                )
        return uncovered

    def coverage_score(self) -> float:
        """
        coverage_score

        Purpose:
        Computes the percentage of threats that are fully covered
        (features + metrics + verifications).

        Inputs:
        None

        Outputs:
        Float between 0.0 and 100.0.
        """
        if not self.coverage:
            return 0.0
        covered = sum(1 for e in self.coverage if e.is_covered())
        return round(covered / len(self.coverage) * 100, 1)

    def coverage_matrix(self) -> dict[str, dict[str, bool]]:
        """
        coverage_matrix

        Purpose:
        Builds a boolean matrix showing which threats have features, metrics,
        and verifications.

        Inputs:
        None

        Outputs:
        Dict mapping threat -> {has_features, has_metrics, has_verifications}.
        """
        matrix: dict[str, dict[str, bool]] = {}
        for entry in self.coverage:
            matrix[entry.threat] = {
                "has_features": bool(entry.features),
                "has_metrics": bool(entry.metrics),
                "has_verifications": bool(entry.verifications),
            }
        return matrix

    def to_dict(self) -> dict[str, Any]:
        """
        to_dict

        Purpose:
        Serializes the full coverage analysis to a dict.

        Inputs:
        None

        Outputs:
        Dict with coverage_score, coverage_matrix, uncovered_threats, threat_map.
        """
        return {
            "coverage_score": self.coverage_score(),
            "coverage_matrix": self.coverage_matrix(),
            "uncovered_threats": self.get_uncovered_threats(),
            "threat_map": [e.to_dict() for e in self.coverage],
        }


def map_threat_coverage(root: str = "") -> dict:
    """
    map_threat_coverage

    Purpose:
    Convenience function that creates a ThreatCoverageMapper and builds the
    full threat coverage map.

    Inputs:
    root — optional root directory override

    Outputs:
    Dict with threat_map, coverage_matrix, uncovered_threats, coverage_score.

    Security:
    Module entry point for F198.
    """
    mapper = ThreatCoverageMapper(root)
    mapper.build_coverage()
    return {
        "threat_map": [e.to_dict() for e in mapper.coverage],
        "coverage_matrix": mapper.coverage_matrix(),
        "uncovered_threats": mapper.get_uncovered_threats(),
        "coverage_score": mapper.coverage_score(),
    }
