"""
__init__.py

Purpose:
Package initializer for the FHE VM module. Exports the BGV encryption
scheme, FHE circuit representation, SSA-to-circuit adapter, and FHE
executor for evaluating functions under homomorphic encryption.

Architectural Role:
Provides fully homomorphic encryption capabilities to the protection
pipeline. Crown-jewel functions can be compiled into FHE circuits that
execute on encrypted data without ever decrypting.

Execution Context:
Called by the protection pipeline when --fhe-vm is enabled. The FHE
executor generates keys, encrypts inputs, evaluates the circuit, and
decrypts outputs. Equivalence verification confirms the circuit matches
the original function.

Dependencies:
- scheme (BGVScheme, BGVKeyPair, BGVParameters)
- circuit (FHECircuit, CircuitEvaluator, build_circuit_from_ir)
- ir_adapter (SSAToFHECircuit, is_fhe_compatible)
- executor (FHEExecutor, verify_equivalence)

Security Relevance:
FHE provides the strongest theoretical security guarantee: computation
on encrypted data. However, the BGV implementation here uses small
parameters for demonstration; production use requires larger parameters
with formal security proofs.

Maintenance Notes:
- This is a real leveled BGV scheme, not a placeholder. The parameters
  in BGVParameters (n=8, t=7, q~2^30) are for demonstration only.
- For production, use n >= 4096, q >= 2^120, and secure parameter
  selection from the HomomorphicEncryption.org standards.
"""

from .scheme import BGVScheme, BGVKeyPair, BGVParameters
from .circuit import FHECircuit, CircuitEvaluator, build_circuit_from_ir
from .ir_adapter import SSAToFHECircuit, is_fhe_compatible
from .executor import FHEExecutor, verify_equivalence

# Re-exported names: listed explicitly so the intent is
# unambiguous and the unused-import check does not flag them.
__all__ = [
    "BGVKeyPair",
    "BGVParameters",
    "BGVScheme",
    "CircuitEvaluator",
    "FHECircuit",
    "FHEExecutor",
    "SSAToFHECircuit",
    "build_circuit_from_ir",
    "is_fhe_compatible",
    "verify_equivalence",
]
