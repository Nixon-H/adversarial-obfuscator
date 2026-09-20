"""
protection_roi/engine.py

Purpose:
Computes the Return on Investment (ROI) for each security protection feature
by balancing security gain (from tests, adversarial benchmarks, proof coverage)
against costs (runtime, complexity, maintenance).

Architectural Role:
Used by the meta-assurance pipeline to identify net-negative features —
protections that cost more than they provide (F194). Output feeds the release
confidence scorer (F197).

Security Relevance:
Features with negative ROI represent wasted security budget. They may also
introduce attack surface (complexity) without commensurate protection. The ROI
engine enables data-driven decisions about which features to keep, improve, or
remove.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)


@dataclass
class ProtectionROI:
    """
    ProtectionROI

    Purpose:
    Stores the ROI assessment for a single protection feature, including its
    static metrics (LOC, classes, functions, imports), test coverage, and the
    computed security gain vs. costs.

    Lifecycle:
    Created by _compute_single_roi(); aggregated in compute_protection_roi().
    """
    feature_name: str
    file_path: str
    loc: int
    num_classes: int
    num_functions: int
    num_imports: int
    test_count: int
    has_adversarial_benchmarks: bool
    has_proof_coverage: bool
    security_gain: float
    runtime_cost: float
    complexity_cost: float
    maintenance_cost: float
    roi: float
    is_net_negative: bool


class ProtectionROIEngine:
    """
    ProtectionROIEngine

    Purpose:
    Discovers protection features and computes their security ROI. Features
    are ranked by ROI; net-negative features are flagged for review.

    Lifecycle:
    Created on demand; compute_protection_roi() drives the full analysis.
    """
    def __init__(self, scripts_dir: str | None = None, tests_dir: str | None = None):
        self.scripts_dir = scripts_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
        )
        self.tests_dir = tests_dir or os.path.join(
            os.path.dirname(self.scripts_dir), "tests"
        )

    def compute_protection_roi(self) -> dict[str, Any]:
        """
        compute_protection_roi

        Purpose:
        Main entry point — discovers features, computes per-feature ROI,
        and produces a report sorted by ROI with net-negative and top
        performers highlighted.

        Inputs:
        None

        Outputs:
        Dict with per_feature_roi, net_negative_features, top_roi_features,
        overall_roi, total_features.
        """
        features = self._discover_protection_features()
        results: list[ProtectionROI] = []
        for feat in features:
            roi = self._compute_single_roi(feat)
            results.append(roi)

        sorted_by_roi = sorted(results, key=lambda r: r.roi, reverse=True)
        net_negative = [r for r in results if r.roi < 50]
        top_roi = sorted_by_roi[:5] if sorted_by_roi else []

        if results:
            avg_security = sum(r.security_gain for r in results) / len(results)
            avg_runtime = sum(r.runtime_cost for r in results) / len(results)
            avg_complexity = sum(r.complexity_cost for r in results) / len(results)
            avg_maintenance = sum(r.maintenance_cost for r in results) / len(results)
            avg_roi = sum(r.roi for r in results) / len(results)
            total_cost = avg_runtime + avg_complexity + avg_maintenance
            overall_roi = round(
                (avg_security / max(total_cost, 1)) * 100, 2
            ) if total_cost > 0 else 0.0
        else:
            overall_roi = 0.0

        return {
            "per_feature_roi": [
                {
                    "feature_name": r.feature_name,
                    "file_path": r.file_path,
                    "loc": r.loc,
                    "num_classes": r.num_classes,
                    "num_functions": r.num_functions,
                    "num_imports": r.num_imports,
                    "test_count": r.test_count,
                    "has_adversarial_benchmarks": r.has_adversarial_benchmarks,
                    "has_proof_coverage": r.has_proof_coverage,
                    "security_gain": round(r.security_gain, 2),
                    "runtime_cost": round(r.runtime_cost, 2),
                    "complexity_cost": round(r.complexity_cost, 2),
                    "maintenance_cost": round(r.maintenance_cost, 2),
                    "roi": round(r.roi, 2),
                    "is_net_negative": r.is_net_negative,
                }
                for r in sorted_by_roi
            ],
            "net_negative_features": [r.feature_name for r in net_negative],
            "top_roi_features": [
                {
                    "feature_name": r.feature_name,
                    "roi": round(r.roi, 2),
                    "security_gain": round(r.security_gain, 2),
                    "total_cost": round(r.runtime_cost + r.complexity_cost + r.maintenance_cost, 2),
                }
                for r in top_roi
            ],
            "overall_roi": overall_roi,
            "total_features": len(results),
        }

    def _discover_protection_features(self) -> list[dict[str, Any]]:
        """
        _discover_protection_features

        Purpose:
        Scans the scripts/ tree for .py files matching known protection
        feature names (obfuscation, encryption, watermark, anti_debug, etc.)
        and falls back to any .py file if no named features are found.

        Inputs:
        None

        Outputs:
        List of dicts with feature_name and file_path (max 100).
        """
        features: list[dict[str, Any]] = []
        seen: set[str] = set()
        feature_names = [
            "obfuscation", "encryption", "watermark", "diversity", "fragment",
            "vm_protect", "jit_protect", "anti_debug", "anti_tamper",
            "cfg_flatten", "mba_subs", "opaque_predicates", "bogus_exceptions",
            "history_bound", "ssa_mutation", "per_exec_recompile", "self_healing",
            "code_genome", "struct_randomization", "branch_entangle",
            "multicore_entangle", "tee", "sgx", "cpu_port", "gpu_hybrid",
            "micro_fragment", "poly_engine", "temporal_keys", "payload_dispersal",
            "flow_entangle", "proof_carrying", "provenance_poison",
            "provenance_removal", "dataflow_obfuscation",
            "variant_pool", "class_dispatch", "rolling_keys", "state_isa",
        ]

        for root, _dirs, files in os.walk(self.scripts_dir):
            for fname in files:
                if not fname.endswith(".py") or fname.startswith("__"):
                    continue
                fpath = os.path.join(root, fname)
                name = fname.replace(".py", "")
                for feat_name in feature_names:
                    if feat_name in name and name not in seen:
                        seen.add(name)
                        features.append({
                            "feature_name": name,
                            "file_path": fpath,
                        })
                        break

        if not features:
            for root, _dirs, files in os.walk(self.scripts_dir):
                for fname in files:
                    if not fname.endswith(".py") or fname.startswith("__"):
                        continue
                    fpath = os.path.join(root, fname)
                    name = fname.replace(".py", "")
                    if name not in seen and not name.startswith("__"):
                        seen.add(name)
                        features.append({
                            "feature_name": name,
                            "file_path": fpath,
                        })

        return features[:100]

    def _compute_single_roi(self, feature: dict[str, Any]) -> ProtectionROI:
        """
        _compute_single_roi

        Purpose:
        Computes ROI for a single feature by analyzing its source code
        metrics (LOC, classes, functions, imports), test coverage, and
        presence of adversarial benchmarks and proof coverage.

        Inputs:
        feature — dict with feature_name and file_path

        Outputs:
        ProtectionROI dataclass with all computed values.
        """
        fpath = feature["file_path"]
        name = feature["feature_name"]

        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=fpath)
        except (SyntaxError, OSError):
            return ProtectionROI(
                feature_name=name, file_path=fpath,
                loc=0, num_classes=0, num_functions=0, num_imports=0,
                test_count=0, has_adversarial_benchmarks=False,
                has_proof_coverage=False, security_gain=0.0,
                runtime_cost=50.0, complexity_cost=50.0,
                maintenance_cost=50.0, roi=0.0, is_net_negative=True,
            )

        loc = len(source.splitlines())
        num_classes = sum(
            1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef)
        )
        num_functions = sum(
            1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        num_imports = sum(
            1 for n in ast.walk(tree)
            if isinstance(n, (ast.Import, ast.ImportFrom))
        )

        test_count = self._count_tests(name)
        has_adversarial = self._check_adversarial_benchmarks(name)
        has_proof = self._check_proof_coverage(name)

        # Security Gain (0-100): based on tests, adversarial benchmarks, proof coverage
        test_score = min(test_count * 10, 40)
        adversarial_score = 30 if has_adversarial else 0
        proof_score = 30 if has_proof else 0
        security_gain = min(test_score + adversarial_score + proof_score, 100)

        # Runtime Cost (0-100): based on imports, complexity, benchmarks
        import_penalty = min(num_imports * 5, 30)
        complexity_penalty = min(num_classes * 10 + (num_functions // 5) * 5, 40)
        bench_penalty = 10 if has_adversarial else 0
        runtime_cost = min(import_penalty + complexity_penalty + bench_penalty, 100)

        # Complexity Cost (0-100): based on loc, classes, functions
        loc_penalty = min(loc / 20, 40)
        class_penalty = min(num_classes * 10, 30)
        func_penalty = min(num_functions * 2, 30)
        complexity_cost = min(loc_penalty + class_penalty + func_penalty, 100)

        # Maintenance Cost (0-100): estimated from complexity
        maintenance_cost = min(complexity_cost * 0.7 + 10, 100)

        total_cost = runtime_cost + complexity_cost + maintenance_cost
        roi = round((security_gain / max(total_cost, 1)) * 100, 2)
        is_net_negative = roi < 50

        return ProtectionROI(
            feature_name=name, file_path=fpath,
            loc=loc, num_classes=num_classes, num_functions=num_functions,
            num_imports=num_imports, test_count=test_count,
            has_adversarial_benchmarks=has_adversarial,
            has_proof_coverage=has_proof,
            security_gain=security_gain, runtime_cost=runtime_cost,
            complexity_cost=complexity_cost, maintenance_cost=maintenance_cost,
            roi=roi, is_net_negative=is_net_negative,
        )

    def _count_tests(self, feature_name: str) -> int:
        """
        _count_tests

        Purpose:
        Counts test and benchmark files matching a feature name.

        Inputs:
        feature_name — the feature name to match

        Outputs:
        Integer count of matching files.
        """
        count = 0
        if not os.path.isdir(self.tests_dir):
            return count
        for fname in os.listdir(self.tests_dir):
            if feature_name.replace("phase_", "") in fname or feature_name in fname:
                if fname.startswith("test_") or fname.startswith("bench_"):
                    count += 1
        return count

    def _check_adversarial_benchmarks(self, feature_name: str) -> bool:
        """
        _check_adversarial_benchmarks

        Purpose:
        Checks whether benchmark files for a feature contain adversarial or
        attack-related keywords.

        Inputs:
        feature_name — the feature name to match

        Outputs:
        True if adversarial benchmarks are found.
        """
        if not os.path.isdir(self.tests_dir):
            return False
        for fname in os.listdir(self.tests_dir):
            if "adversarial" in fname and feature_name.replace("phase_", "") in fname:
                return True
            if feature_name.replace("phase_", "") in fname and "bench" in fname:
                fpath = os.path.join(self.tests_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read()
                    if "bench" in content.lower() and (
                        "adversarial" in content.lower() or "attack" in content.lower()
                    ):
                        return True
                except OSError:
                    continue
        return False

    def _check_proof_coverage(self, feature_name: str) -> bool:
        """
        _check_proof_coverage

        Purpose:
        Checks whether any test file for the feature contains "proof" in its name.

        Inputs:
        feature_name — the feature name to match

        Outputs:
        True if proof coverage files are found.
        """
        if not os.path.isdir(self.tests_dir):
            return False
        for fname in os.listdir(self.tests_dir):
            if "proof" in fname and feature_name.replace("phase_", "") in fname:
                return True
        return False
