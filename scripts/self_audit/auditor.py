"""
self_audit/auditor.py — Self-audit orchestration across ten categories (F180)

Purpose:
    Implements the SelfAuditor class that runs audits across source, tests,
    reachability, proofs, benchmarks, claims/evidence, metrics, debt,
    assumptions, and reality. Each audit category is a separate method.

Architectural Role:
    Core orchestration layer. Reads pipeline reports from the build directory
    and runs heuristic checks to produce an AuditReport with overall score.

Security Relevance:
    Provides a single holistic score representing the project's security
    posture health. A failing grade prevents releases with known gaps.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, ROOT, log
from scripts.self_audit import AuditFinding, AuditCategory, AuditReport, score_to_grade


class SelfAuditor:
    """Orchestrates a ten-category self-audit and produces an AuditReport.

    Audit categories: source, tests, reachability, proofs, benchmarks,
    claims (evidence), metrics, debt (technical debt), assumptions, reality.
    Each returns an AuditCategory with score and findings.
    """
    def __init__(self, build_dir: str = BUILD_DIR):
        self.build_dir = build_dir
        self.findings: List[AuditFinding] = []
        self.source_path: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Source audit
    # ------------------------------------------------------------------ #
    def audit_source(self, payload_path: Optional[str] = None) -> AuditCategory:
        """Audit source code quality: syntax, function count, line count, TODOs, unsafe imports."""
        cat = AuditCategory(name="source", score=0, max_score=100)
        findings: List[AuditFinding] = []

        if payload_path and os.path.isfile(payload_path):
            self.source_path = payload_path
            with open(payload_path) as f:
                source = f.read()
            try:
                tree = ast.parse(source)
            except SyntaxError as e:
                findings.append(AuditFinding(
                    category="source", severity="critical",
                    title="Syntax error in source",
                    description=f"Payload source has syntax errors: {e}",
                    recommendation="Fix syntax errors before building",
                    file=payload_path,
                ))
                cat.max_score = 20
                cat.findings = findings
                cat.score = 0.0
                return cat

            fn_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
            cls_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            line_count = len(source.splitlines())

            cat.max_score = 100
            score = 100.0

            if fn_count == 0:
                findings.append(AuditFinding(
                    category="source", severity="major",
                    title="No functions in source",
                    description="Source contains zero function definitions",
                    recommendation="Ensure the payload defines at least one function",
                    file=payload_path,
                    metric_name="function_count", metric_value=0.0, threshold=1.0,
                ))
                score -= 30.0

            if line_count > 5000:
                findings.append(AuditFinding(
                    category="source", severity="minor",
                    title="Large source file",
                    description=f"Source has {line_count} lines, may impact build performance",
                    recommendation="Consider splitting into modules",
                    file=payload_path,
                    metric_name="line_count", metric_value=float(line_count), threshold=5000.0,
                ))
                score -= 5.0

            todo_count = len(re.findall(r"#.*TODO|#.*FIXME|#.*HACK", source))
            if todo_count > 5:
                findings.append(AuditFinding(
                    category="source", severity="minor",
                    title="Unresolved TODOs",
                    description=f"Found {todo_count} TODO comments in source",
                    recommendation="Address all TODOs before release",
                    file=payload_path,
                    metric_name="todo_count", metric_value=float(todo_count), threshold=5.0,
                ))
                score -= 5.0

            imports = [n.names[0].name if hasattr(n, 'names') and n.names and hasattr(n.names[0], 'name') else ''
                       for n in ast.walk(tree) if isinstance(n, ast.Import)]
            unsafe = [i for i in imports if i in ('pickle', 'marshal', 'shelve', 'subprocess', 'os', 'eval', 'exec', '__import__')]
            if unsafe:
                findings.append(AuditFinding(
                    category="source", severity="major",
                    title="Potentially unsafe imports",
                    description=f"Source imports: {', '.join(unsafe)}",
                    recommendation="Consider sandboxing or replacing unsafe modules",
                    file=payload_path,
                ))
                score -= 15.0

            cat.score = max(0.0, score)
        else:
            cat.max_score = 20
            findings.append(AuditFinding(
                category="source", severity="major",
                title="No source payload available",
                description="Payload path not provided or file not found",
                recommendation="Supply a valid --payload argument",
            ))
            cat.score = 0.0

        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Tests audit
    # ------------------------------------------------------------------ #
    def audit_tests(self) -> AuditCategory:
        """Audit test coverage: test file count, benchmark file count, test function count."""
        cat = AuditCategory(name="tests", score=0, max_score=100)
        findings: List[AuditFinding] = []
        tests_dir = os.path.join(_ROOT, "tests")
        score = 100.0

        if not os.path.isdir(tests_dir):
            findings.append(AuditFinding(
                category="tests", severity="critical",
                title="Tests directory missing",
                description=f"No tests/ directory found at {tests_dir}",
                recommendation="Create a tests/ directory with unit tests",
            ))
            cat.max_score = 20
            cat.score = 0.0
            cat.findings = findings
            return cat

        test_files = [f for f in os.listdir(tests_dir) if f.startswith("test_") and f.endswith(".py")]
        bench_files = [f for f in os.listdir(tests_dir) if f.startswith("bench_") and f.endswith(".py")]

        if len(test_files) == 0:
            findings.append(AuditFinding(
                category="tests", severity="critical",
                title="No test files",
                description="No test_*.py files found in tests/",
                recommendation="Add unit test files",
                metric_name="test_file_count", metric_value=0.0, threshold=1.0,
            ))
            score -= 50.0
        elif len(test_files) < 5:
            findings.append(AuditFinding(
                category="tests", severity="major",
                title="Low test file count",
                description=f"Only {len(test_files)} test files found, expected at least 5",
                recommendation="Add more test coverage",
                metric_name="test_file_count", metric_value=float(len(test_files)), threshold=5.0,
            ))
            score -= 20.0

        if len(bench_files) == 0:
            findings.append(AuditFinding(
                category="tests", severity="major",
                title="No benchmark files",
                description="No bench_*.py files found in tests/",
                recommendation="Add benchmark files to track performance",
                metric_name="bench_file_count", metric_value=0.0, threshold=1.0,
            ))
            score -= 15.0

        total_tests = 0
        for tf in test_files:
            tfp = os.path.join(tests_dir, tf)
            try:
                with open(tfp) as f:
                    content = f.read()
                total_tests += content.count("def test_")
            except Exception:
                pass

        if total_tests == 0:
            findings.append(AuditFinding(
                category="tests", severity="critical",
                title="No test functions",
                description="Zero test functions across all test files",
                recommendation="Implement test functions using pytest",
                metric_name="test_function_count", metric_value=0.0, threshold=1.0,
            ))
            score -= 30.0
        elif total_tests < 20:
            findings.append(AuditFinding(
                category="tests", severity="major",
                title="Low test function count",
                description=f"Only {total_tests} test functions found, expected at least 20",
                recommendation="Increase test coverage",
                metric_name="test_function_count", metric_value=float(total_tests), threshold=20.0,
            ))
            score -= 10.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Reachability audit
    # ------------------------------------------------------------------ #
    def audit_reachability(self, reachability_report: Optional[dict] = None) -> AuditCategory:
        """Audit feature reachability: loads reachability_report.json and checks unreachable/partial feature ratios."""
        cat = AuditCategory(name="reachability", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0

        if reachability_report is None:
            rp = os.path.join(self.build_dir, "reachability_report.json")
            if os.path.isfile(rp):
                try:
                    with open(rp, "rb") as f:
                        raw = f.read()
                    hash_before = hashlib.sha256(raw).hexdigest()
                    reachability_report = json.loads(raw)
                    with open(rp, "rb") as f:
                        raw_after = f.read()
                    hash_after = hashlib.sha256(raw_after).hexdigest()
                    if hash_before != hash_after:
                        findings.append(AuditFinding(
                            category="reachability", severity="critical",
                            title="Reachability report modified during audit",
                            description="File content changed between reads (SHA-256 mismatch)",
                            recommendation="Ensure no concurrent writes to reachability_report.json",
                            file=rp,
                        ))
                except (json.JSONDecodeError, OSError):
                    pass

        if not reachability_report:
            findings.append(AuditFinding(
                category="reachability", severity="major",
                title="No reachability report",
                description="Reachability report not available, build with --reachability-report",
                recommendation="Run the pipeline with --reachability-report flag",
            ))
            cat.max_score = 50
            cat.score = 0.0
            cat.findings = findings
            return cat

        unreachable = reachability_report.get("unreachable", []) or []
        partial = reachability_report.get("partially_reachable", []) or []
        total = reachability_report.get("total_features", 0) or 1

        unreachable_pct = len(unreachable) / total * 100
        partial_pct = len(partial) / total * 100

        cat.max_score = 100

        if unreachable_pct > 10:
            findings.append(AuditFinding(
                category="reachability", severity="critical",
                title=f"High unreachable feature ratio: {unreachable_pct:.1f}%",
                description=f"{len(unreachable)} of {total} features are unreachable",
                recommendation="Ensure all features have CLI flags wired in build.py",
                metric_name="unreachable_pct", metric_value=unreachable_pct, threshold=10.0,
            ))
            score -= 40.0
        elif unreachable_pct > 0:
            findings.append(AuditFinding(
                category="reachability", severity="major",
                title=f"Some unreachable features: {unreachable_pct:.1f}%",
                description=f"{len(unreachable)} of {total} features are unreachable",
                recommendation="Wire missing features into build.py",
                metric_name="unreachable_pct", metric_value=unreachable_pct, threshold=0.0,
            ))
            score -= 20.0

        if partial_pct > 30:
            findings.append(AuditFinding(
                category="reachability", severity="major",
                title=f"High partially-reachable feature ratio: {partial_pct:.1f}%",
                description=f"{len(partial)} of {total} features are only partially reachable",
                recommendation="Ensure complete wiring for partially reachable features",
                metric_name="partial_pct", metric_value=partial_pct, threshold=30.0,
            ))
            score -= 15.0

        reachable = reachability_report.get("reachable", []) or []
        if len(reachable) < total / 2:
            findings.append(AuditFinding(
                category="reachability", severity="critical",
                title="Less than half of features are fully reachable",
                description=f"Only {len(reachable)}/{total} features are fully reachable",
                recommendation="Audit wiring for all features",
                metric_name="reachable_count", metric_value=float(len(reachable)), threshold=total / 2,
            ))
            score -= 30.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Proofs audit
    # ------------------------------------------------------------------ #
    def audit_proofs(self) -> AuditCategory:
        """Audit proof certificates: count total/failed proofs, check for missing proof categories."""
        cat = AuditCategory(name="proofs", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0
        proofs_dir = os.path.join(self.build_dir, "proofs")

        if not os.path.isdir(proofs_dir):
            findings.append(AuditFinding(
                category="proofs", severity="major",
                title="No proofs directory",
                description=f"No proofs/ directory in build artifacts at {proofs_dir}",
                recommendation="Run pipeline with --prove-vm, --prove-fragments, --verify-mutations, etc.",
            ))
            cat.max_score = 40
            cat.score = 0.0
            cat.findings = findings
            return cat

        proof_categories: Dict[str, int] = {}
        total_proofs = 0
        failed_proofs = 0

        for root, dirs, files in os.walk(proofs_dir):
            for fn in files:
                if fn.endswith(".json"):
                    fp = os.path.join(root, fn)
                    try:
                        with open(fp) as f:
                            data = json.load(f)
                        total_proofs += 1
                        validated = data.get("validated", data.get("equivalent", data.get("passed", False)))
                        if not validated:
                            failed_proofs += 1
                        pcat = os.path.basename(root)
                        proof_categories[pcat] = proof_categories.get(pcat, 0) + 1
                    except Exception:
                        pass

        if total_proofs == 0:
            findings.append(AuditFinding(
                category="proofs", severity="major",
                title="No proof certificates found",
                description="Zero proof JSON files in proofs/ directory",
                recommendation="Run pipeline with proof-related flags",
            ))
            cat.max_score = 40
            cat.score = 0.0
            cat.findings = findings
            return cat

        cat.max_score = 100

        if failed_proofs > 0:
            fail_pct = failed_proofs / total_proofs * 100
            findings.append(AuditFinding(
                category="proofs", severity="critical" if fail_pct > 10 else "major",
                title=f"{failed_proofs}/{total_proofs} proofs failed ({fail_pct:.1f}%)",
                description=f"Failed proofs across categories: {', '.join(proof_categories.keys())}",
                recommendation="Investigate and fix failing proofs",
                metric_name="failed_proof_pct", metric_value=fail_pct, threshold=10.0,
            ))
            score -= min(fail_pct * 2, 50.0)

        missing_cats = {"vm", "fragment", "watermark", "mutation", "jit", "proof_carrying"} - set(proof_categories.keys())
        if missing_cats:
            findings.append(AuditFinding(
                category="proofs", severity="minor",
                title=f"Missing proof categories: {', '.join(sorted(missing_cats))}",
                description=f"Proofs not generated for: {', '.join(sorted(missing_cats))}",
                recommendation="Enable proof generation for missing categories",
            ))
            score -= 10.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Benchmarks audit
    # ------------------------------------------------------------------ #
    def audit_benchmarks(self) -> AuditCategory:
        """Audit benchmark results: check overall score and sub-scores against thresholds."""
        cat = AuditCategory(name="benchmarks", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0

        benchmark_report = None
        brp = os.path.join(self.build_dir, "benchmark_report.json")
        if os.path.isfile(brp):
            try:
                with open(brp) as f:
                    benchmark_report = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        if not benchmark_report:
            findings.append(AuditFinding(
                category="benchmarks", severity="major",
                title="No benchmark report",
                description="benchmark_report.json not found in build artifacts",
                recommendation="Run pipeline with --benchmark flag",
            ))
            cat.max_score = 40
            cat.score = 0.0
            cat.findings = findings
            return cat

        cat.max_score = 100
        overall = benchmark_report.get("overall", benchmark_report.get("overall_score", 0))
        if isinstance(overall, str):
            try:
                overall = float(overall)
            except (ValueError, TypeError):
                overall = 0.0
        else:
            overall = float(overall) if overall else 0.0

        if overall < 1.0:
            findings.append(AuditFinding(
                category="benchmarks", severity="major",
                title="Low benchmark overall score",
                description=f"Overall benchmark score is {overall:.2f}",
                recommendation="Improve obfuscation effectiveness",
                metric_name="benchmark_overall", metric_value=overall, threshold=1.0,
            ))
            score -= 20.0

        sub_scores = benchmark_report.get("subscores", benchmark_report.get("metrics", {}))
        if isinstance(sub_scores, dict):
            for k, v in sub_scores.items():
                if isinstance(v, dict):
                    vs = v.get("score", v.get("value", 0))
                else:
                    vs = v
                try:
                    vs = float(vs)
                except (ValueError, TypeError):
                    continue
                if vs < 0.3:
                    findings.append(AuditFinding(
                        category="benchmarks", severity="minor",
                        title=f"Low benchmark sub-score: {k}",
                        description=f"Sub-score '{k}' is {vs:.2f}, below 0.3 threshold",
                        recommendation=f"Investigate and improve {k}",
                        metric_name=f"bench_{k}", metric_value=vs, threshold=0.3,
                    ))
                    score -= 5.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Claims / Evidence audit
    # ------------------------------------------------------------------ #
    def audit_claims(self) -> AuditCategory:
        """Audit evidence/claims from evidence_report.json: unverified claims, evidence coverage, total claims."""
        cat = AuditCategory(name="claims", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0

        evidence_report = None
        erp = os.path.join(self.build_dir, "evidence_report.json")
        if os.path.isfile(erp):
            try:
                with open(erp) as f:
                    evidence_report = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        if not evidence_report:
            findings.append(AuditFinding(
                category="claims", severity="major",
                title="No evidence report",
                description="evidence_report.json not found — run with --evidence-ledger",
                recommendation="Run pipeline with --evidence-ledger to build evidence",
            ))
            cat.max_score = 40
            cat.score = 0.0
            cat.findings = findings
            return cat

        cat.max_score = 100

        total_claims = evidence_report.get("total_claims", 0)
        verified = evidence_report.get("verified_evidence", evidence_report.get("verified", 0))
        total_evidence = evidence_report.get("total_evidence", 0)
        coverage_pct = evidence_report.get("coverage_pct", evidence_report.get("evidence_coverage", 0))
        unverified = evidence_report.get("unverified_claims", evidence_report.get("claims_without_evidence", []))

        if isinstance(unverified, list) and len(unverified) > 0:
            findings.append(AuditFinding(
                category="claims", severity="major",
                title=f"{len(unverified)} unverified claims",
                description=f"Claims without supporting evidence: {', '.join(unverified[:5])}",
                recommendation="Add evidence (source, tests, benchmarks) for all claims",
                metric_name="unverified_claims", metric_value=float(len(unverified)), threshold=0.0,
            ))
            score -= 20.0

        if total_claims == 0:
            findings.append(AuditFinding(
                category="claims", severity="critical",
                title="No claims registered",
                description="Evidence ledger contains zero claims",
                recommendation="Register protection claims in the evidence ledger",
                metric_name="total_claims", metric_value=0.0, threshold=1.0,
            ))
            score -= 30.0

        if total_evidence == 0 and total_claims > 0:
            findings.append(AuditFinding(
                category="claims", severity="critical",
                title="Claims with no evidence",
                description=f"{total_claims} claims exist but zero evidence entries",
                recommendation="Attach source files, tests, and runtime traces to claims",
                metric_name="total_evidence", metric_value=0.0, threshold=1.0,
            ))
            score -= 30.0

        if isinstance(coverage_pct, (int, float)) and coverage_pct < 50:
            findings.append(AuditFinding(
                category="claims", severity="major",
                title=f"Low evidence coverage: {coverage_pct:.1f}%",
                description=f"Only {coverage_pct:.1f}% of evidence is verified",
                recommendation="Increase evidence verification coverage",
                metric_name="coverage_pct", metric_value=float(coverage_pct), threshold=50.0,
            ))
            score -= 15.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Metrics audit
    # ------------------------------------------------------------------ #
    def audit_metrics(self) -> AuditCategory:
        """Audit resilience metrics from metrics_report.json: check overall resilience score."""
        cat = AuditCategory(name="metrics", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0

        metrics_report = None
        mrp = os.path.join(self.build_dir, "metrics_report.json")
        if os.path.isfile(mrp):
            try:
                with open(mrp) as f:
                    metrics_report = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        if not metrics_report:
            findings.append(AuditFinding(
                category="metrics", severity="major",
                title="No metrics report",
                description="metrics_report.json not found — run with --metrics",
                recommendation="Run pipeline with --metrics flag",
            ))
            cat.max_score = 40
            cat.score = 0.0
            cat.findings = findings
            return cat

        cat.max_score = 100
        overall = metrics_report.get("overall", metrics_report.get("overall_score", 0))
        try:
            overall = float(overall) if overall else 0.0
        except (ValueError, TypeError):
            overall = 0.0

        if overall < 0.5:
            findings.append(AuditFinding(
                category="metrics", severity="critical",
                title=f"Low resilience metrics: {overall:.3f}",
                description=f"Overall resilience score is {overall:.3f}, below 0.5 threshold",
                recommendation="Increase obfuscation intensity or use --min-resilience",
                metric_name="resilience_overall", metric_value=overall, threshold=0.5,
            ))
            score -= 40.0
        elif overall < 0.8:
            findings.append(AuditFinding(
                category="metrics", severity="major",
                title=f"Below-target resilience: {overall:.3f}",
                description=f"Overall resilience score is {overall:.3f}, below 0.8 target",
                recommendation="Consider tuning obfuscation parameters",
                metric_name="resilience_overall", metric_value=overall, threshold=0.8,
            ))
            score -= 20.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Debt audit (technical debt indicators)
    # ------------------------------------------------------------------ #
    def audit_debt(self) -> AuditCategory:
        """Audit technical debt: count stub functions, pass statements, NotImplementedErrors, TODO markers in all scripts."""
        cat = AuditCategory(name="debt", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0
        scripts_dir = os.path.join(_ROOT, "scripts")

        stub_count = 0
        pass_count = 0
        todo_count = 0
        notimpl_count = 0
        total_files = 0

        for root, dirs, files in os.walk(scripts_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fn in files:
                if fn.endswith(".py"):
                    total_files += 1
                    fp = os.path.join(root, fn)
                    try:
                        with open(fp, encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if "def " in content:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                                        stub_count += 1
                                    if len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and node.body[0].value.value and "TODO" in str(node.body[0].value.value):
                                        todo_count += 1
                    except (SyntaxError, Exception):
                        pass

            for fn in files:
                if fn.endswith(".py"):
                    fp = os.path.join(root, fn)
                    try:
                        with open(fp, encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if "pass" in content:
                            pc = len(re.findall(r"^\s+pass\s*$", content, re.MULTILINE))
                            pass_count += pc
                        if "NotImplementedError" in content:
                            notimpl_count += content.count("NotImplementedError")
                        if "TODO" in content or "FIXME" in content:
                            todo_count += len(re.findall(r"(TODO|FIXME|HACK|XXX)", content))
                    except Exception:
                        pass

        cat.max_score = 100

        if stub_count > 5:
            findings.append(AuditFinding(
                category="debt", severity="major",
                title=f"{stub_count} stub functions detected",
                description=f"Found {stub_count} functions with only 'pass' body",
                recommendation="Implement stub functions or mark as explicit stubs",
                metric_name="stub_functions", metric_value=float(stub_count), threshold=5.0,
            ))
            score -= min(stub_count * 5.0, 30.0)

        if pass_count > 50:
            findings.append(AuditFinding(
                category="debt", severity="minor",
                title=f"High pass statement count: {pass_count}",
                description=f"Found {pass_count} 'pass' statements across scripts",
                recommendation="Review and replace unnecessary pass statements",
                metric_name="pass_statements", metric_value=float(pass_count), threshold=50.0,
            ))
            score -= 5.0

        if notimpl_count > 3:
            findings.append(AuditFinding(
                category="debt", severity="major",
                title=f"{notimpl_count} NotImplementedError references",
                description=f"Found {notimpl_count} references to NotImplementedError",
                recommendation="Implement the missing functionality",
                metric_name="not_implemented", metric_value=float(notimpl_count), threshold=3.0,
            ))
            score -= 15.0

        if todo_count > 10:
            findings.append(AuditFinding(
                category="debt", severity="minor",
                title=f"High TODO/FIXME count: {todo_count}",
                description=f"Found {todo_count} TODO/FIXME/HACK/XXX markers",
                recommendation="Resolve all unfinished work markers",
                metric_name="todo_markers", metric_value=float(todo_count), threshold=10.0,
            ))
            score -= 5.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Assumptions audit
    # ------------------------------------------------------------------ #
    def audit_assumptions(self) -> AuditCategory:
        """Audit runtime assumptions from assumption_report.json: critical unsatisfied, unknown, and total."""
        cat = AuditCategory(name="assumptions", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0

        assumption_report = None
        arp = os.path.join(self.build_dir, "assumption_report.json")
        if os.path.isfile(arp):
            try:
                with open(arp) as f:
                    assumption_report = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        if not assumption_report:
            findings.append(AuditFinding(
                category="assumptions", severity="major",
                title="No assumption report",
                description="assumption_report.json not found — run with --assumptions-report",
                recommendation="Run pipeline with --assumptions-report flag",
            ))
            cat.max_score = 40
            cat.score = 0.0
            cat.findings = findings
            return cat

        cat.max_score = 100

        total = assumption_report.get("total_count", assumption_report.get("total", 0))
        unsatisfied = assumption_report.get("unsatisfied_count", assumption_report.get("unsatisfied", 0))
        critical = assumption_report.get("critical_unsatisfied", [])
        if isinstance(critical, int):
            critical_unsatisfied = critical
        elif isinstance(critical, list):
            critical_unsatisfied = len(critical)
        else:
            critical_unsatisfied = 0
        unknown = assumption_report.get("unknown_count", assumption_report.get("unknown", 0))

        if critical_unsatisfied > 0:
            findings.append(AuditFinding(
                category="assumptions", severity="critical",
                title=f"{critical_unsatisfied} critical unsatisfied assumptions",
                description=f"Critical assumptions that are not met in the runtime environment",
                recommendation="Fix critical assumptions or document the gaps",
                metric_name="critical_unsatisfied", metric_value=float(critical_unsatisfied), threshold=0.0,
            ))
            score -= 40.0

        if unsatisfied > critical_unsatisfied:
            minor_unsat = unsatisfied - critical_unsatisfied
            findings.append(AuditFinding(
                category="assumptions", severity="major",
                title=f"{minor_unsat} non-critical unsatisfied assumptions",
                description=f"Assumptions not met: {minor_unsat}",
                recommendation="Review and address unsatisfied assumptions",
                metric_name="unsatisfied_assumptions", metric_value=float(unsatisfied), threshold=0.0,
            ))
            score -= 15.0

        if unknown > 0:
            findings.append(AuditFinding(
                category="assumptions", severity="minor",
                title=f"{unknown} assumptions in unknown state",
                description=f"Assumptions that could not be verified: {unknown}",
                recommendation="Add runtime capability checks for unknown assumptions",
                metric_name="unknown_assumptions", metric_value=float(unknown), threshold=0.0,
            ))
            score -= 5.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Reality audit
    # ------------------------------------------------------------------ #
    def audit_reality(self) -> AuditCategory:
        """Audit reality scores from reality_report.json: overall score, critical gaps."""
        cat = AuditCategory(name="reality", score=0, max_score=100)
        findings: List[AuditFinding] = []
        score = 100.0

        reality_report = None
        rrp = os.path.join(self.build_dir, "reality_report.json")
        if os.path.isfile(rrp):
            try:
                with open(rrp) as f:
                    reality_report = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        if not reality_report:
            findings.append(AuditFinding(
                category="reality", severity="major",
                title="No reality score report",
                description="reality_report.json not found — run with --reality-score",
                recommendation="Run pipeline with --reality-score flag",
            ))
            cat.max_score = 40
            cat.score = 0.0
            cat.findings = findings
            return cat

        cat.max_score = 100

        overall_reality = reality_report.get("overall_reality_score", reality_report.get("score", 0))
        try:
            overall_reality = float(overall_reality)
        except (ValueError, TypeError):
            overall_reality = 0.0

        if overall_reality < 50:
            findings.append(AuditFinding(
                category="reality", severity="critical",
                title=f"Low reality score: {overall_reality:.1f}/100",
                description="Reality score measures how grounded each feature is in actual implementation",
                recommendation="Improve reality scores by adding implementations, tests, and evidence",
                metric_name="reality_score", metric_value=overall_reality, threshold=50.0,
            ))
            score -= 40.0
        elif overall_reality < 75:
            findings.append(AuditFinding(
                category="reality", severity="major",
                title=f"Below-target reality score: {overall_reality:.1f}/100",
                description="Target is 75+ for a credible security posture",
                recommendation="Strengthen implementation and evidence for weak features",
                metric_name="reality_score", metric_value=overall_reality, threshold=75.0,
            ))
            score -= 20.0

        critical_gaps = reality_report.get("critical_gaps", [])
        if isinstance(critical_gaps, list) and len(critical_gaps) > 0:
            findings.append(AuditFinding(
                category="reality", severity="critical",
                title=f"{len(critical_gaps)} critical reality gaps",
                description=f"Features with reality score < 25: {', '.join(critical_gaps[:5])}",
                recommendation="Focus on features with critical reality gaps",
                metric_name="critical_gaps", metric_value=float(len(critical_gaps)), threshold=0.0,
            ))
            score -= 30.0

        cat.score = max(0.0, score)
        cat.findings = findings
        self.findings.extend(findings)
        return cat

    # ------------------------------------------------------------------ #
    # Run full audit
    # ------------------------------------------------------------------ #
    def run(self, payload_path: Optional[str] = None) -> AuditReport:
        """Run all ten audit categories and produce a composite AuditReport with overall score and grade."""
        categories: Dict[str, AuditCategory] = {}
        categories["source"] = self.audit_source(payload_path)
        categories["tests"] = self.audit_tests()
        categories["reachability"] = self.audit_reachability()
        categories["proofs"] = self.audit_proofs()
        categories["benchmarks"] = self.audit_benchmarks()
        categories["claims"] = self.audit_claims()
        categories["metrics"] = self.audit_metrics()
        categories["debt"] = self.audit_debt()
        categories["assumptions"] = self.audit_assumptions()
        categories["reality"] = self.audit_reality()

        total_score = sum(c.score for c in categories.values())
        total_max = sum(c.max_score for c in categories.values())
        overall_score = (total_score / total_max * 100) if total_max else 0.0

        critical = sum(1 for f in self.findings if f.severity == "critical")
        major = sum(1 for f in self.findings if f.severity == "major")
        minor = sum(1 for f in self.findings if f.severity == "minor")

        return AuditReport(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            overall_score=round(overall_score, 1),
            overall_grade=score_to_grade(overall_score),
            categories=categories,
            total_findings=len(self.findings),
            critical_findings=critical,
            major_findings=major,
            minor_findings=minor,
        )
