"""
costs.py

Purpose:
Protection cost database for the synthesis engine. Each entry maps
a feature ID to a ProtectionCost with security gain, overhead
percentage, size multiplier, conflicts, prerequisites, and category.

Architectural Role:
Provides the cost model that drives protection plan optimization.
The SynthesisEngine and ProtectionOptimizer read these costs to
evaluate candidate protection selections.

Execution Context:
Imported at module load time. PROTECTION_COSTS is a static dict
that is read by SynthesisEngine.load_protection_costs() and
ProtectionOptimizer.__init__().

Dependencies:
- engine (ProtectionCost dataclass)

Security Relevance:
The cost values determine which protections are selected. If a
protection's security_gain is overestimated, the plan may be
under-protected. If overhead_percent is underestimated, the plan
may impose unacceptable runtime cost.

Maintenance Notes:
- Security gains are additive (summed, capped at 100). Overhead is
  additive. Size multiplier is multiplicative.
- The conflict list uses negative flag names (e.g., "no_cfg_flatten")
  which correspond to --no-* CLI flags. This is a legacy convention;
  true feature conflicts should use feature IDs from the knowledge
  graph instead.
- Prerequisites like "skip_irgen" indicate features that require IR
  generation to be active (the inverse of the skip flag).
"""

from scripts.synthesis.engine import ProtectionCost


PROTECTION_COSTS = {
    "cfg_flatten": ProtectionCost(
        name="cfg_flatten",
        security_gain=30.0,
        overhead_percent=5.0,
        size_multiplier=1.2,
        conflicts=["no_cfg_flatten"],
        prerequisites=[],
        category="control_flow",
    ),
    "opaque_predicates": ProtectionCost(
        name="opaque_predicates",
        security_gain=20.0,
        overhead_percent=10.0,
        size_multiplier=1.5,
        conflicts=["no_opaque_predicates"],
        prerequisites=[],
        category="control_flow",
    ),
    "mba_subs": ProtectionCost(
        name="mba_subs",
        security_gain=25.0,
        overhead_percent=15.0,
        size_multiplier=2.0,
        conflicts=["no_mba_subs"],
        prerequisites=[],
        category="arithmetic",
    ),
    "bogus_exceptions": ProtectionCost(
        name="bogus_exceptions",
        security_gain=10.0,
        overhead_percent=3.0,
        size_multiplier=1.1,
        conflicts=[],
        prerequisites=[],
        category="control_flow",
    ),
    "fragment_strings": ProtectionCost(
        name="fragment_strings",
        security_gain=8.0,
        overhead_percent=2.0,
        size_multiplier=1.05,
        conflicts=[],
        prerequisites=[],
        category="data",
    ),
    "unicode_ids": ProtectionCost(
        name="unicode_ids",
        security_gain=5.0,
        overhead_percent=1.0,
        size_multiplier=1.0,
        conflicts=[],
        prerequisites=[],
        category="naming",
    ),
    "fhe_vm": ProtectionCost(
        name="fhe_vm",
        security_gain=90.0,
        overhead_percent=1000.0,
        size_multiplier=10.0,
        conflicts=[],
        prerequisites=["skip_irgen"],
        category="vm",
    ),
    "vm_protection": ProtectionCost(
        name="vm_protection",
        security_gain=50.0,
        overhead_percent=50.0,
        size_multiplier=3.0,
        conflicts=[],
        prerequisites=["skip_irgen"],
        category="vm",
    ),
    "rop_protection": ProtectionCost(
        name="rop_protection",
        security_gain=40.0,
        overhead_percent=20.0,
        size_multiplier=2.0,
        conflicts=[],
        prerequisites=["skip_llvmgen"],
        category="exploit_mitigation",
    ),
    "microjit": ProtectionCost(
        name="microjit",
        security_gain=35.0,
        overhead_percent=10.0,
        size_multiplier=1.5,
        conflicts=[],
        prerequisites=[],
        category="jit",
    ),
    "fragmentation": ProtectionCost(
        name="fragmentation",
        security_gain=45.0,
        overhead_percent=30.0,
        size_multiplier=2.5,
        conflicts=[],
        prerequisites=[],
        category="fragmentation",
    ),
    "watermark": ProtectionCost(
        name="watermark",
        security_gain=15.0,
        overhead_percent=5.0,
        size_multiplier=1.1,
        conflicts=[],
        prerequisites=["skip_irgen"],
        category="watermarking",
    ),
    "data_obfuscation": ProtectionCost(
        name="data_obfuscation",
        security_gain=28.0,
        overhead_percent=8.0,
        size_multiplier=1.3,
        conflicts=[],
        prerequisites=[],
        category="data",
    ),
    "ssa_mutation": ProtectionCost(
        name="ssa_mutation",
        security_gain=22.0,
        overhead_percent=6.0,
        size_multiplier=1.2,
        conflicts=[],
        prerequisites=[],
        category="mutation",
    ),
    "cfg_mutation": ProtectionCost(
        name="cfg_mutation",
        security_gain=38.0,
        overhead_percent=12.0,
        size_multiplier=1.6,
        conflicts=[],
        prerequisites=[],
        category="mutation",
    ),
    "struct_randomization": ProtectionCost(
        name="struct_randomization",
        security_gain=32.0,
        overhead_percent=10.0,
        size_multiplier=1.4,
        conflicts=[],
        prerequisites=[],
        category="randomization",
    ),
    "code_genome": ProtectionCost(
        name="code_genome",
        security_gain=42.0,
        overhead_percent=25.0,
        size_multiplier=2.0,
        conflicts=[],
        prerequisites=[],
        category="evolution",
    ),
    "per_exec_recompile": ProtectionCost(
        name="per_exec_recompile",
        security_gain=55.0,
        overhead_percent=80.0,
        size_multiplier=3.5,
        conflicts=[],
        prerequisites=[],
        category="runtime",
    ),
    "self_healing": ProtectionCost(
        name="self_healing",
        security_gain=48.0,
        overhead_percent=35.0,
        size_multiplier=2.8,
        conflicts=[],
        prerequisites=[],
        category="runtime",
    ),
    "history_bound_decryption": ProtectionCost(
        name="history_bound_decryption",
        security_gain=36.0,
        overhead_percent=15.0,
        size_multiplier=1.8,
        conflicts=[],
        prerequisites=[],
        category="crypto",
    ),
    "class_dispatch": ProtectionCost(
        name="class_dispatch",
        security_gain=33.0,
        overhead_percent=18.0,
        size_multiplier=2.2,
        conflicts=[],
        prerequisites=[],
        category="dispatch",
    ),
    "rolling_keys": ProtectionCost(
        name="rolling_keys",
        security_gain=44.0,
        overhead_percent=22.0,
        size_multiplier=1.9,
        conflicts=[],
        prerequisites=[],
        category="crypto",
    ),
    "state_isa": ProtectionCost(
        name="state_isa",
        security_gain=52.0,
        overhead_percent=40.0,
        size_multiplier=2.5,
        conflicts=[],
        prerequisites=["skip_irgen"],
        category="vm",
    ),
    "ephemeral_isa": ProtectionCost(
        name="ephemeral_isa",
        security_gain=34.0,
        overhead_percent=12.0,
        size_multiplier=1.5,
        conflicts=[],
        prerequisites=[],
        category="vm",
    ),
    "oram": ProtectionCost(
        name="oram",
        security_gain=60.0,
        overhead_percent=200.0,
        size_multiplier=4.0,
        conflicts=[],
        prerequisites=["skip_irgen"],
        category="memory",
    ),
    "adversarial_injection": ProtectionCost(
        name="adversarial_injection",
        security_gain=18.0,
        overhead_percent=4.0,
        size_multiplier=1.2,
        conflicts=[],
        prerequisites=[],
        category="deception",
    ),
    "provenance_poison": ProtectionCost(
        name="provenance_poison",
        security_gain=16.0,
        overhead_percent=3.0,
        size_multiplier=1.15,
        conflicts=[],
        prerequisites=[],
        category="deception",
    ),
    "llm_resilient": ProtectionCost(
        name="llm_resilient",
        security_gain=26.0,
        overhead_percent=8.0,
        size_multiplier=1.3,
        conflicts=[],
        prerequisites=[],
        category="obfuscation",
    ),
    "reasoning_traps": ProtectionCost(
        name="reasoning_traps",
        security_gain=12.0,
        overhead_percent=2.0,
        size_multiplier=1.1,
        conflicts=[],
        prerequisites=[],
        category="deception",
    ),
    "function_intent": ProtectionCost(
        name="function_intent",
        security_gain=14.0,
        overhead_percent=5.0,
        size_multiplier=1.2,
        conflicts=[],
        prerequisites=[],
        category="obfuscation",
    ),
    "llm_fingerprint": ProtectionCost(
        name="llm_fingerprint",
        security_gain=7.0,
        overhead_percent=1.0,
        size_multiplier=1.05,
        conflicts=[],
        prerequisites=[],
        category="watermarking",
    ),
    "payload_dispersal": ProtectionCost(
        name="payload_dispersal",
        security_gain=46.0,
        overhead_percent=28.0,
        size_multiplier=2.2,
        conflicts=[],
        prerequisites=[],
        category="fragmentation",
    ),
    "micro_fragment": ProtectionCost(
        name="micro_fragment",
        security_gain=43.0,
        overhead_percent=25.0,
        size_multiplier=2.0,
        conflicts=[],
        prerequisites=[],
        category="fragmentation",
    ),
    "poly_engine": ProtectionCost(
        name="poly_engine",
        security_gain=37.0,
        overhead_percent=15.0,
        size_multiplier=1.8,
        conflicts=[],
        prerequisites=[],
        category="polymorphism",
    ),
    "temporal_keys": ProtectionCost(
        name="temporal_keys",
        security_gain=39.0,
        overhead_percent=20.0,
        size_multiplier=1.7,
        conflicts=[],
        prerequisites=[],
        category="crypto",
    ),
    "flow_entangle": ProtectionCost(
        name="flow_entangle",
        security_gain=41.0,
        overhead_percent=18.0,
        size_multiplier=1.6,
        conflicts=[],
        prerequisites=[],
        category="crypto",
    ),
}
