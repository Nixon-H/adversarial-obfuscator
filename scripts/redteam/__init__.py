"""
__init__.py

Purpose:
Package initializer for the autonomous red-team attack pipeline.
Each build automatically attacks itself using five analysis tools
(angr, Ghidra, Binary Ninja, LLM, symbolic) and produces a combined
security score.

Architectural Role:
Orchestrator for adversarial evaluation. The red-team pipeline runs
after all protections are applied and before the security regression
gates. The combined score feeds into the gate thresholds.

Execution Context:
Invoked by the build pipeline (scripts/build.py) with a --red-team
flag. Results are written to build/redteam/attack_report.json.

Dependencies:
- unified_attack (orchestrator)
- angr_runner, ghidra_runner, bninja_runner, llm_runner, symbolic_runner

Security Relevance:
This is the "adversarial oracle" — it simulates what a real attacker
would do. The combined security score is a key gating metric. If the
score drops below threshold, the build fails.

Maintenance Notes:
- Adding a new attack runner requires: (1) a new _runner.py file,
  (2) an import here, (3) registration in unified_attack.__init__'s
  attacks_to_run list and _run_attack dispatch method.
- Each runner must gracefully handle ImportError (tool not installed).
"""
from .unified_attack import run_redteam_attack, RedTeamConfig, RedTeamReport
from .angr_runner import run_angr_attack
from .ghidra_runner import run_ghidra_attack
from .bninja_runner import run_binaryninja_attack
from .llm_runner import run_llm_attack
from .symbolic_runner import run_symbolic_attack
