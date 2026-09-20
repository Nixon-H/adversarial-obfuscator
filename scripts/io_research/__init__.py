from .np_obfuscation import MatrixBranchingProgram, randomize_bp, evaluate_bp
from .obfuscator import IndistinguishabilityObfuscator
from .equivalence import verify_equivalence, compute_equivalence_score
from .metrics import compute_program_distance, compute_entropy, indistinguishability_score
from .ir_adapter import is_io_compatible, ir_to_branching_program
