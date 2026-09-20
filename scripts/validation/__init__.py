"""
validation/__init__

Purpose:
Validation toolkit for formal program equivalence. Provides AST-to-Z3 and
IR-to-Z3 translators, an equivalence checker, MBA (Mixed Boolean-Arithmetic)
validation, and an SMT validator that cross-checks AST against IR.

Security Relevance:
Every prover in the pipeline depends on these validators. A bug in the
translator or checker invalidates all proofs.

Dependencies:
- scripts.validation.smt_validator  (AST-vs-IR cross validation)
- scripts.validation.equivalence    (core SMT equivalence engine)
- scripts.validation.ast_to_smt     (Python AST -> Z3)
- scripts.validation.ir_to_smt      (IR -> Z3)
- scripts.validation.mba_validator  (MBA identity validation)
"""
from .smt_validator import SMTValidator, ValidationResult
from .equivalence import EquivalenceChecker, CheckResult
from .ast_to_smt import ASTToSMT
from .ir_to_smt import IRToSMT
from .mba_validator import MBAValidator

__all__ = [
    "SMTValidator", "ValidationResult",
    "EquivalenceChecker", "CheckResult",
    "ASTToSMT", "IRToSMT",
    "MBAValidator",
]
