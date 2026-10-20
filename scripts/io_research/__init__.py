from .np_obfuscation import MatrixBranchingProgram, randomize_bp, evaluate_bp
from .obfuscator import IndistinguishabilityObfuscator
from .equivalence import verify_equivalence, compute_equivalence_score
from .metrics import compute_program_distance, compute_entropy, indistinguishability_score
from .ir_adapter import is_io_compatible, ir_to_branching_program

# Re-exported names: listed explicitly so the intent is
# unambiguous and the unused-import check does not flag them.
__all__ = [
    "IndistinguishabilityObfuscator",
    "MatrixBranchingProgram",
    "compute_entropy",
    "compute_equivalence_score",
    "compute_program_distance",
    "evaluate_bp",
    "indistinguishability_score",
    "ir_to_branching_program",
    "is_io_compatible",
    "randomize_bp",
    "verify_equivalence",
]
