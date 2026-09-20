"""
feature_registry.py

Purpose:
Central registry of all protection features supported by the Nixon
Shadow Compiler. Each feature entry includes its name, description,
category, dependencies, and conflicts.

Architectural Role:
Single source of truth for what protections exist and how they relate.
Consumed by the knowledge graph builder (builder.py) to construct the
full relationship graph. Adding a new feature requires adding an entry
here.

Execution Context:
Imported at module load time by builder.py and __init__.py. The data
is static; no runtime computation is performed.

Dependencies:
- No imports (pure data file)

Security Relevance:
The registry encodes the complete feature ontology. Every protection
decision, conflict check, and dependency resolution references this
data. If a feature is missing here, it will be invisible to the
synthesis engine and coverage system.

Maintenance Notes:
- Each feature entry MUST have: id (unique), name, description, category,
  depends_on (list of IDs), conflicts_with (list of IDs).
- The id field is used as the canonical node identifier in the
  knowledge graph; it must be a valid graph node ID (no spaces).
- The category field determines the visual grouping in reports and
  diagrams.
- FEATURE_NAMES and FEATURE_CATEGORIES are convenience dicts derived
  from ALL_FEATURES; they are recomputed at import time.
"""

ALL_FEATURES = [
    {
        "id": "cfg_flatten",
        "name": "CFG Flattening",
        "description": "Flatten control flow graph using dispatcher-based state machine",
        "category": "control_flow",
        "depends_on": [],
        "conflicts_with": ["ssa_mutation", "history_bound_decryption"],
    },
    {
        "id": "opaque_predicates",
        "name": "Opaque Predicates",
        "description": "Insert always-true or always-false predicates obfuscating control flow",
        "category": "control_flow",
        "depends_on": [],
        "conflicts_with": ["proof_carrying"],
    },
    {
        "id": "mba_subs",
        "name": "MBA Substitutions",
        "description": "Replace arithmetic expressions with mixed Boolean-arithmetic equivalents",
        "category": "arithmetic",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "fragment_strings",
        "name": "String Fragmentation",
        "description": "Split string literals into fragmented runtime-assembled pieces",
        "category": "data",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "unicode_ids",
        "name": "Unicode Identifiers",
        "description": "Replace identifiers with Unicode homoglyphs and confusable characters",
        "category": "naming",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "control_flow_flatten",
        "name": "Control Flow Flattening (Phase2)",
        "description": "Advanced control flow flattening with multi-dispatch state machines",
        "category": "control_flow",
        "depends_on": [],
        "conflicts_with": ["ssa_mutation", "history_bound_decryption"],
    },
    {
        "id": "bogus_exceptions",
        "name": "Bogus Exception Handlers",
        "description": "Insert fake exception handling paths that are never taken",
        "category": "control_flow",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "ir_encryption",
        "name": "IR Encryption",
        "description": "Encrypt intermediate representation at rest and decrypt at runtime",
        "category": "encryption",
        "depends_on": ["rolling_keys"],
        "conflicts_with": ["proof_carrying"],
    },
    {
        "id": "vm_protection",
        "name": "VM Protection",
        "description": "Execute protected code in a custom virtual machine with ephemeral ISA",
        "category": "vm",
        "depends_on": ["state_isa"],
        "conflicts_with": ["fhe_vm"],
    },
    {
        "id": "rop_protection",
        "name": "ROP Chain Protection",
        "description": "Compile crown jewel functions into ROP chain payloads",
        "category": "exploit",
        "depends_on": [],
        "conflicts_with": ["fhe_vm"],
    },
    {
        "id": "watermark",
        "name": "Semantic Watermark",
        "description": "Embed verifiable semantic watermark into IR",
        "category": "attribution",
        "depends_on": [],
        "conflicts_with": ["fragment_strings"],
    },
    {
        "id": "fragmentation",
        "name": "Code Fragmentation",
        "description": "Split binary into micro-fragments that decrypt-execute-wipe",
        "category": "execution",
        "depends_on": ["rolling_keys", "temporal_keys"],
        "conflicts_with": ["proof_carrying"],
    },
    {
        "id": "attestation",
        "name": "Hardware-Agnostic Attestation",
        "description": "Whitebox entanglement with dynamic attestation proof generation",
        "category": "verification",
        "depends_on": ["flow_entangle"],
        "conflicts_with": [],
    },
    {
        "id": "proof_carrying",
        "name": "Proof-Carrying Obfuscation",
        "description": "Attach Z3 equivalence certificates verifying semantic preservation",
        "category": "verification",
        "depends_on": ["mba_subs"],
        "conflicts_with": ["ir_encryption", "fragmentation", "opaque_predicates"],
    },
    {
        "id": "fhe_vm",
        "name": "Fully Homomorphic VM",
        "description": "Compile crown-jewel functions into FHE circuits for computation on encrypted data",
        "category": "crypto",
        "depends_on": [],
        "conflicts_with": ["vm_protection", "rop_protection"],
    },
    {
        "id": "io_research",
        "name": "Indistinguishability Obfuscation (Research)",
        "description": "Approximate iO for critical fragments using multilinear maps",
        "category": "research",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "kernel_assist",
        "name": "Kernel-Assisted Execution",
        "description": "Use kernel modules for execution monitoring and anti-debugging",
        "category": "platform",
        "depends_on": [],
        "conflicts_with": ["tee", "sgx"],
    },
    {
        "id": "zk_state",
        "name": "ZK State-Bound Execution",
        "description": "Sigma-protocol-based state proofs bound execution to verified state transitions",
        "category": "crypto",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "microjit",
        "name": "Polymorphic Micro-JIT Reassembly",
        "description": "JIT-compile fragments with per-execution polymorphism",
        "category": "execution",
        "depends_on": ["fragmentation"],
        "conflicts_with": [],
    },
    {
        "id": "data_obfuscation",
        "name": "Data-Oriented Obfuscation",
        "description": "Obfuscate data layout, arrays, and structure access patterns",
        "category": "data",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "entropy_flatten",
        "name": "Entropy Flattening",
        "description": "Normalize byte entropy distribution to resist statistical analysis",
        "category": "statistical",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "crypto_binding",
        "name": "Cryptographic Fragment Binding",
        "description": "Chain fragments with cryptographic hash bindings enforcing execution order",
        "category": "crypto",
        "depends_on": ["rolling_keys"],
        "conflicts_with": [],
    },
    {
        "id": "flow_entangle",
        "name": "Whitebox-Flow Entanglement",
        "description": "Tie control flow to cryptographic state for entanglement-based attestation",
        "category": "crypto",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "challenge_response",
        "name": "Challenge-Response Protocol",
        "description": "Standalone challenge-response authentication for fragment integrity",
        "category": "verification",
        "depends_on": ["flow_entangle"],
        "conflicts_with": [],
    },
    {
        "id": "diversity",
        "name": "Protection Diversity",
        "description": "Generate N diversity variants with distinct protection profiles",
        "category": "diversity",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "distributed_protection",
        "name": "Distributed Protection Suite",
        "description": "Multi-binary, cross-process, multi-host distributed protection features",
        "category": "distributed",
        "depends_on": ["crypto_binding"],
        "conflicts_with": [],
    },
    {
        "id": "class_dispatch",
        "name": "Execution-Path-Specific Dispatch",
        "description": "JIT codegen dispatch based on execution path classification",
        "category": "execution",
        "depends_on": [],
        "conflicts_with": ["cfg_flatten"],
    },
    {
        "id": "rolling_keys",
        "name": "Rolling Key Schedules",
        "description": "Time-evolution-based key derivation for fragment decryption chains",
        "category": "crypto",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "state_isa",
        "name": "State-Dependent Opcode Sets",
        "description": "VM opcode meanings depend on execution history state",
        "category": "vm",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "per_exec_recompile",
        "name": "Per-Execution Recompilation",
        "description": "Recompile binary on each execution with fresh obfuscation parameters",
        "category": "execution",
        "depends_on": ["diversity"],
        "conflicts_with": [],
    },
    {
        "id": "self_healing",
        "name": "Self-Healing Runtime",
        "description": "Runtime integrity checks with redundant code copies for self-repair",
        "category": "runtime",
        "depends_on": ["fragmentation"],
        "conflicts_with": [],
    },
    {
        "id": "code_genome",
        "name": "Code Genome Evolution",
        "description": "Evolutionary algorithm generating obfuscated code genomes across generations",
        "category": "evolution",
        "depends_on": ["diversity"],
        "conflicts_with": [],
    },
    {
        "id": "struct_randomization",
        "name": "Structure Randomization",
        "description": "Randomize stack layout, heap structures, and register allocation",
        "category": "data",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "speculation_obfuscation",
        "name": "Speculation Obfuscation",
        "description": "AST-level speculation-based obfuscation via speculative code paths",
        "category": "control_flow",
        "depends_on": [],
        "conflicts_with": ["cfg_flatten"],
    },
    {
        "id": "tee",
        "name": "Trusted Execution Environment",
        "description": "Partition sensitive code into TEE-protected execution contexts",
        "category": "hardware",
        "depends_on": [],
        "conflicts_with": ["kernel_assist"],
    },
    {
        "id": "sgx",
        "name": "Intel SGX Enclave Support",
        "description": "Hardware enclave support for Intel SGX-protected execution",
        "category": "hardware",
        "depends_on": [],
        "conflicts_with": ["kernel_assist"],
    },
    {
        "id": "gpu_execution",
        "name": "GPU Fragment Execution",
        "description": "Execute protected fragments on GPU with hardware detection",
        "category": "hardware",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "branch_entangle",
        "name": "Branch Predictor Entanglement",
        "description": "Entangle control flow with branch predictor state",
        "category": "hardware",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "hpc",
        "name": "Hardware Performance Counter Integration",
        "description": "Monitor and adapt protection based on hardware performance counters",
        "category": "hardware",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "cache_bound",
        "name": "Cache-Bound Execution",
        "description": "Bind execution timing to cache latency profiles",
        "category": "hardware",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "oram",
        "name": "Oblivious RAM Controller",
        "description": "Oblivious RAM patterns to hide memory access traces",
        "category": "data",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "temporal_keys",
        "name": "Temporal Micro-Key Evolution",
        "description": "Time-window-based key chain for micro-fragment decryption",
        "category": "crypto",
        "depends_on": ["rolling_keys"],
        "conflicts_with": [],
    },
    {
        "id": "payload_dispersal",
        "name": "Payload Dispersal Execution",
        "description": "Disjoint slice execution across distributed fragments",
        "category": "distributed",
        "depends_on": ["fragmentation", "distributed_protection"],
        "conflicts_with": [],
    },
    {
        "id": "poly_engine",
        "name": "Environmental Poly-Engine",
        "description": "Environment-adapted code variants resisting fingerprinting",
        "category": "diversity",
        "depends_on": ["diversity"],
        "conflicts_with": [],
    },
    {
        "id": "challenge_response",
        "name": "Challenge-Response Attestation",
        "description": "Cryptographic challenge-response for remote integrity verification",
        "category": "verification",
        "depends_on": ["attestation"],
        "conflicts_with": [],
    },
    {
        "id": "micro_fragment",
        "name": "Micro-Fragment Execution",
        "description": "Decrypt-execute-wipe each micro-fragment individually",
        "category": "execution",
        "depends_on": ["fragmentation", "temporal_keys"],
        "conflicts_with": [],
    },
    {
        "id": "ssa_mutation",
        "name": "SSA Mutation",
        "description": "Variant instruction ordering and SSA form mutation",
        "category": "control_flow",
        "depends_on": [],
        "conflicts_with": ["cfg_flatten", "control_flow_flatten"],
    },
    {
        "id": "history_bound_decryption",
        "name": "Execution-History-Bound Decryption",
        "description": "Key derivation bound to specific execution history path",
        "category": "crypto",
        "depends_on": ["rolling_keys"],
        "conflicts_with": ["cfg_flatten", "control_flow_flatten"],
    },
    {
        "id": "cfg_mutation",
        "name": "Live CFG Mutation",
        "description": "Runtime variant basic-block ordering mutation",
        "category": "execution",
        "depends_on": [],
        "conflicts_with": [],
    },
    {
        "id": "class_dispatch",
        "name": "Execution-Path Dispatch",
        "description": "Dispatch execution paths to different JIT codegen strategies",
        "category": "execution",
        "depends_on": [],
        "conflicts_with": [],
    },
]

FEATURE_NAMES = {f["id"]: f["name"] for f in ALL_FEATURES}
FEATURE_CATEGORIES = {f["id"]: f["category"] for f in ALL_FEATURES}
