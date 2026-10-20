"""
proofs/semantic_preservation.py

Purpose:
Proves that a Python source-to-source transformation preserves semantics by
translating both ASTs to Z3 SMT formulas and checking equivalence. Supports
variable renaming, statement reordering, expression substitution, and
commutative reordering.

Security Relevance:
All obfuscation passes that operate on Python-level source or AST must be
proven semantics-preserving. Without this, the entire obfuscation pipeline
lacks a correctness guarantee at the highest abstraction level.

Dependencies:
- scripts.validation.ast_to_smt   (AST -> Z3 translation)
- scripts.validation.equivalence   (Z3 equivalence checking)
- scripts.certificates.certificate (proof certification)
"""
from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from scripts.validation.ast_to_smt import ASTToSMT
from scripts.validation.equivalence import CheckResult, EquivalenceChecker
from scripts.certificates.certificate import Certificate, emit_certificate


@dataclass
class PreservationProof:
    """
    PreservationProof

    What is proven:
    Two Python source snippets (before, after) produce the same Z3 output
    expression for all Z3 BitVec inputs.

    Why:
    Source-level transformations are the first stage in the pipeline. If
    they are not proven correct, all downstream proofs (IR, VM, fragments)
    operate on a corrupted base.

    Assumptions:
    - AST-to-Z3 translation faithfully models Python semantics for the
      subset of Python used (integer BitVecs, conditionals, assignments).
    - Variable renaming is normalized before comparison.

    Limitations:
    - Does NOT model: recursion, I/O, exceptions, floating point,
      objects, heap mutation, or non-termination.
    - Equivalence is checked per-function; cross-function call effects
      are not modeled (calls return 0).

    Verification Path:
    prove_equivalence(before, after) -> proof.equivalent
    """
    equivalent: bool
    transformation_type: str
    check_result: Optional[CheckResult] = None
    error: Optional[str] = None
    solver_time_ms: float = 0.0

    def to_certificate_dict(self) -> Dict[str, Any]:
        return {
            "equivalent": self.equivalent,
            "transformation": self.transformation_type,
            "solver_time_ms": self.solver_time_ms,
            "error": self.error,
            "validated": self.equivalent,
        }


class NameNormalizer(ast.NodeTransformer):
    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping

    def visit_Name(self, node: ast.Name):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node


def _collect_store_names(tree: ast.AST) -> Set[str]:
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return names


def _collect_load_names(tree: ast.AST) -> Set[str]:
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return names


def _build_renaming(
    src_names: Set[str], dst_names: Set[str],
    src_load: Set[str], dst_load: Set[str],
) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    src_list = sorted(src_names)
    dst_list = sorted(dst_names)
    for s, d in zip(src_list, dst_list):
        mapping[d] = s
    src_load_list = sorted(src_load - src_names)
    dst_load_list = sorted(dst_load - dst_names)
    for s, d in zip(src_load_list, dst_load_list):
        mapping[d] = s
    return mapping


def _normalize_names(
    source_before: str, source_after: str,
) -> Tuple[str, str]:
    tree_before = ast.parse(source_before, mode="exec")
    tree_after = ast.parse(source_after, mode="exec")
    before_store = _collect_store_names(tree_before)
    after_store = _collect_store_names(tree_after)
    before_load = _collect_load_names(tree_before)
    after_load = _collect_load_names(tree_after)
    mapping = _build_renaming(before_store, after_store, before_load, after_load)
    if mapping:
        normalizer = NameNormalizer(mapping)
        normalizer.visit(tree_after)
        ast.fix_missing_locations(tree_after)
    return source_before, ast.unparse(tree_after)


def _same_name_count(
    source_before: str, source_after: str,
) -> bool:
    tree_before = ast.parse(source_before, mode="exec")
    tree_after = ast.parse(source_after, mode="exec")
    return len(_collect_store_names(tree_before)) == len(_collect_store_names(tree_after))


class SemanticPreservationProver:
    """
    SemanticPreservationProver

    What is proven:
    Python source-level transformations are semantics-preserving.

    Why:
    Source-level correctness is the foundation of the proof hierarchy.

    Assumptions:
    AST-to-Z3 translation covers the language subset used.

    Limitations:
    No heap, I/O, FP, or cross-function verification.

    Verification Path:
    prove_equivalence(src_before, src_after) -> PreservationProof.equivalent
    """
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.checker = EquivalenceChecker(timeout_ms=timeout_ms)
        self.proofs: List[PreservationProof] = []

    def prove_equivalence(
        self,
        source_before: str,
        source_after: str,
        transformation_type: str = "general",
    ) -> PreservationProof:
        start = time.time()
        try:
            if _same_name_count(source_before, source_after):
                _, source_after = _normalize_names(source_before, source_after)
            tree_before = ast.parse(source_before, mode="exec")
            tree_after = ast.parse(source_after, mode="exec")
            t_before = ASTToSMT()
            t_after = ASTToSMT()
            f_before = t_before.translate(tree_before)
            f_after = t_after.translate(tree_after)
            out_before = t_before.get_output_var()
            out_after = t_after.get_output_var()
            all_inputs = list(
                set(t_before.get_input_vars()) | set(t_after.get_input_vars())
            )
            check_result = self.checker.check_with_formulas(
                f_before, f_after,
                out_before, out_after,
                all_inputs,
            )
            elapsed = (time.time() - start) * 1000
            result = PreservationProof(
                equivalent=check_result.equivalent,
                transformation_type=transformation_type,
                check_result=check_result,
                solver_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            result = PreservationProof(
                equivalent=False,
                transformation_type=transformation_type,
                error=str(e),
                solver_time_ms=elapsed,
            )
        self.proofs.append(result)
        return result

    def prove_variable_renaming(
        self, source_before: str, source_after: str,
    ) -> PreservationProof:
        return self.prove_equivalence(source_before, source_after, "variable_renaming")

    def prove_statement_reordering(
        self, source_before: str, source_after: str,
    ) -> PreservationProof:
        return self.prove_equivalence(source_before, source_after, "statement_reordering")

    def prove_expression_substitution(
        self, source_before: str, source_after: str,
    ) -> PreservationProof:
        return self.prove_equivalence(source_before, source_after, "expression_substitution")

    def prove_commutative_reordering(
        self, source: str, var_a: str, var_b: str,
    ) -> PreservationProof:
        tree = ast.parse(source, mode="exec")
        statements = tree.body
        swapped = []
        for stmt in statements:
            swapped.append(stmt)
        swaps = []
        for i in range(len(swapped) - 1):
            for j in range(i + 1, len(swapped)):
                if self._are_commutative(swapped[i], swapped[j], var_a, var_b):
                    swapped[i], swapped[j] = swapped[j], swapped[i]
                    swaps.append((i, j))
        if not swaps:
            return self.prove_equivalence(source, source, "commutative_reordering")
        swapped_source = ast.unparse(ast.Module(body=swapped, type_ignores=[]))
        return self.prove_equivalence(source, swapped_source, "commutative_reordering")

    def _are_commutative(
        self, s1: ast.AST, s2: ast.AST, var_a: str, var_b: str,
    ) -> bool:
        if not isinstance(s1, ast.Assign) or not isinstance(s2, ast.Assign):
            return False
        if len(s1.targets) != 1 or len(s2.targets) != 1:
            return False
        t1 = s1.targets[0]
        t2 = s2.targets[0]
        if not isinstance(t1, ast.Name) or not isinstance(t2, ast.Name):
            return False
        return (t1.id == var_a and t2.id == var_b) or (t1.id == var_b and t2.id == var_a)

    def to_certificate(self, proof: PreservationProof, input_text: str, output_text: str) -> Certificate:
        return emit_certificate(
            pass_name=proof.transformation_type,
            input_text=input_text,
            output_text=output_text,
            equivalence_proof=proof.to_certificate_dict(),
            duration_ms=proof.solver_time_ms,
            validated=proof.equivalent,
        )

    def prove_and_certify(
        self, source_before: str, source_after: str, transformation_type: str = "general",
    ) -> Tuple[PreservationProof, Optional[Certificate]]:
        proof = self.prove_equivalence(source_before, source_after, transformation_type)
        try:
            cert = self.to_certificate(proof, source_before, source_after)
            return proof, cert
        except Exception:
            return proof, None

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.proofs)
        eq = sum(1 for p in self.proofs if p.equivalent)
        return {"total": total, "equivalent": eq, "nonequivalent": total - eq}
