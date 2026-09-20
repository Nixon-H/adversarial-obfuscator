"""
__init__.py

Purpose:
Package initializer for the zero-knowledge state-bound execution module.
Exports the sigma protocol implementation, state machine with provable
transitions, state-bound prover/verifier, and configuration management.

Architectural Role:
Provides ZK proof capabilities to the protection pipeline. State-bound
execution ensures that code runs in the expected execution context by
requiring zero-knowledge proofs of state knowledge at each transition.

Execution Context:
Activated when --zk-state is enabled. The prover generates proofs during
execution; the verifier checks proofs before accepting state transitions.
Both prover and verifier share the same group parameters.

Dependencies:
- sigma_protocol (SigmaProver, SigmaVerifier, generate_parameters)
- state_machine (StateMachine, StateProof)
- prover (StateBoundProver, ExecutionProof)
- verifier (StateBoundVerifier, VerificationResult)
- state_config (ZKStateConfig, load_config, check_prerequisites)

Security Relevance:
Zero-knowledge proofs bind execution to a specific state without
revealing the state itself. This prevents attackers from executing
protected code in an un-authorized context (e.g., a debugger or
emulator). The sigma protocol provides honest-verifier ZK only.

Maintenance Notes:
- All files in this module carry a "Security classification: MEASURED"
  header comment documenting known limitations.
- THEORETICAL caveats are documented per-class; these are known
  limitations that do not affect the current threat model but may
  become relevant under stronger attackers.
"""

from .sigma_protocol import SigmaProver, SigmaVerifier, generate_parameters
from .state_machine import StateMachine, StateProof
from .prover import StateBoundProver, ExecutionProof
from .verifier import StateBoundVerifier, VerificationResult
from .state_config import ZKStateConfig, load_config, check_prerequisites

__all__ = [
    "SigmaProver",
    "SigmaVerifier",
    "generate_parameters",
    "StateMachine",
    "StateProof",
    "StateBoundProver",
    "ExecutionProof",
    "StateBoundVerifier",
    "VerificationResult",
    "ZKStateConfig",
    "load_config",
    "check_prerequisites",
]
