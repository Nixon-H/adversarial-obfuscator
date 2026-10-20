"""
independent_audit/auditor.py

# TWIN AUDITORS (different scopes, do not merge): scripts/self_audit/
# auditor.py (in-pipeline ten-category gate, F180) and scripts/
# claim_auditor/auditor.py (per-claim evidence scoring, F172).

Purpose:
Provides an independent audit mechanism that examines the build pipeline for
reachability of phase functions, proof logic presence, benchmark validity,
evidence artifacts, and exaggerated security claims.

Architectural Role:
Acts as an external auditor — not part of the build pipeline itself — that
cross-checks the pipeline's own artifacts for completeness and honesty. Its
output is consumed by the meta-assurance reporting layer (F197, F200).

Security Relevance:
Detects unreachable code (dead features), missing proof logic, absent or
empty benchmark assertions, missing evidence artifacts, and exaggerated
claims that could mislead reviewers into over-trusting the system.
"""
from __future__ import annotations

import ast
import os


_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class IndependentAuditor:
    """
    IndependentAuditor

    Purpose:
    Audits the build pipeline by checking reachability, proof logic, benchmarks,
    evidence artifacts, and security claims. Each audit produces a findings list.

    Lifecycle:
    Created on demand by independent_audit(); discarded after report generation.

    Security:
    Serves as an objective third-party check that neither the pipeline nor its
    authors can easily manipulate.
    """
    def __init__(self, root_dir: str | None = None):
        self.root = root_dir or _ROOT
        self.scripts_dir = os.path.join(self.root, "scripts")
        self.build_dir = os.path.join(self.root, "build")
        self.tests_dir = os.path.join(self.root, "tests")

    def check_reachability(self) -> list[dict]:
        """
        check_reachability

        Purpose:
        Parses build.py to extract import/call references, then cross-references
        every phase_*.py file to determine whether it is reachable at runtime.

        Inputs:
        None (operates on self.scripts_dir)

        Outputs:
        List of dicts, each with phase, file, reachable flag, and detail.

        Security:
        Unreachable phase functions represent dead code that may bypass security
        guarantees.
        """
        findings: list[dict] = []
        build_py = os.path.join(self.scripts_dir, "build.py")
        if not os.path.exists(build_py):
            findings.append({"issue": "build.py not found", "file": build_py})
            return findings
        with open(build_py, encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
        imports: set[str] = set()
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add(alias.name if alias.asname is None else alias.asname)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name if alias.asname is None else alias.asname)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        phase_dir = os.path.join(self.scripts_dir, "phases")
        if os.path.isdir(phase_dir):
            for fname in sorted(os.listdir(phase_dir)):
                if fname.endswith(".py") and fname != "__init__.py":
                    fpath = os.path.join(phase_dir, fname)
                    phase_name = fname.replace(".py", "")
                    func_name = phase_name.replace("phase_", "phase_")
                    reachable = func_name in calls or func_name in imports
                    findings.append({
                        "phase": phase_name,
                        "file": fpath,
                        "reachable": reachable,
                        "detail": "imported/called in build.py" if reachable else "NOT referenced in build.py",
                    })
        return findings

    def check_proofs(self) -> list[dict]:
        """
        check_proofs

        Purpose:
        Scans the proofs/ directory for files containing proof-related keywords
        (prove, Prover, z3, solver, theorem, lemma).

        Inputs:
        None

        Outputs:
        List of dicts with file path, has_proof_logic flag, and detail.

        Security:
        Features claiming formal verification must be backed by actual proof
        logic; this check detects unsupported claims.
        """
        findings: list[dict] = []
        proofs_dir = os.path.join(self.root, "scripts", "proofs")
        if not os.path.isdir(proofs_dir):
            findings.append({"issue": "proofs directory missing", "path": proofs_dir})
            return findings
        for fname in sorted(os.listdir(proofs_dir)):
            if fname.endswith(".py") and fname != "__init__.py":
                fpath = os.path.join(proofs_dir, fname)
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                has_proof_logic = any(kw in content for kw in ["prove", "Prover", "z3", "solver", "theorem", "lemma"])
                findings.append({
                    "file": fpath,
                    "has_proof_logic": has_proof_logic,
                    "detail": "Contains proof logic" if has_proof_logic else "No proof logic detected",
                })
        return findings

    def check_benchmarks(self) -> list[dict]:
        """
        check_benchmarks

        Purpose:
        Scans the tests/ directory for bench_*.py files and checks whether they
        contain assertions and benchmark function definitions.

        Inputs:
        None

        Outputs:
        List of dicts with file path, existence, assertion flag, benchmark flag.

        Security:
        Benchmarks without assertions cannot validate security properties.
        """
        findings: list[dict] = []
        if not os.path.isdir(self.tests_dir):
            findings.append({"issue": "tests directory missing", "path": self.tests_dir})
            return findings
        for fname in sorted(os.listdir(self.tests_dir)):
            if fname.startswith("bench_") and fname.endswith(".py"):
                fpath = os.path.join(self.tests_dir, fname)
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                has_assertion = "assert" in content
                has_benchmark_fn = "bench_" in content or "def bench_" in content
                findings.append({
                    "file": fpath,
                    "exists": True,
                    "has_assertions": has_assertion,
                    "has_benchmark_fn": has_benchmark_fn,
                    "detail": f"assertions={has_assertion}, benchmark_fn={has_benchmark_fn}",
                })
        return findings

    def check_evidence(self) -> list[dict]:
        """
        check_evidence

        Purpose:
        Inventories the build/ directory for report files (json, md, txt) that
        serve as evidence artifacts.

        Inputs:
        None

        Outputs:
        List of dicts with file path, existence, and size in bytes.

        Security:
        Missing evidence artifacts indicate that the build process did not
        generate expected audit trails.
        """
        findings: list[dict] = []
        reports_dir = self.build_dir
        if not os.path.isdir(reports_dir):
            findings.append({"issue": "build directory missing", "path": reports_dir})
            return findings
        for fname in sorted(os.listdir(reports_dir)):
            if fname.endswith(".json") or fname.endswith(".md") or fname.endswith(".txt"):
                fpath = os.path.join(reports_dir, fname)
                findings.append({
                    "file": fpath,
                    "exists": True,
                    "size_bytes": os.path.getsize(fpath),
                })
        return findings

    def check_claims(self) -> list[dict]:
        """
        check_claims

        Purpose:
        Walks the entire scripts/ tree and flags lines containing exaggerated
        security claims (secure, unbreakable, tamper-proof, 100%, perfect, etc.).

        Inputs:
        None

        Outputs:
        List of dicts with file path, line number, keyword, and context.

        Security:
        Inflated language in source code may mislead auditors and reviewers
        about the true security posture.
        """
        findings: list[dict] = []
        claim_keywords = [
            "secure", "unbreakable", "tamper-proof", "100%", "perfect",
            "guaranteed", "impossible", "never", "always", "proven",
        ]
        for root_dir, dirs, files in os.walk(self.scripts_dir):
            dirs[:] = [d for d in dirs if not d.startswith("__") and not d.startswith(".")]
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root_dir, fname)
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for kw in claim_keywords:
                        for lineno, line in enumerate(content.splitlines(), 1):
                            if kw.lower() in line.lower():
                                findings.append({
                                    "file": fpath,
                                    "line": lineno,
                                    "keyword": kw,
                                    "context": line.strip()[:120],
                                })
        return findings


def independent_audit() -> dict:
    """
    independent_audit

    Purpose:
    Convenience function that instantiates IndependentAuditor and runs all
    five audit checks, returning a consolidated dict.

    Inputs:
    None

    Outputs:
    Dict with keys: reachability_audit, proof_audit, benchmark_audit,
    evidence_audit, claim_audit.

    Security:
    Entry point for the independent auditor mode (F181).
    """
    auditor = IndependentAuditor()
    result = {
        "reachability_audit": auditor.check_reachability(),
        "proof_audit": auditor.check_proofs(),
        "benchmark_audit": auditor.check_benchmarks(),
        "evidence_audit": auditor.check_evidence(),
        "claim_audit": auditor.check_claims(),
    }
    return result
