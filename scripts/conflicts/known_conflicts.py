"""
known_conflicts.py

Purpose:
Database of known protection conflicts in the Nixon Shadow Compiler.
Each entry defines two conflicting flags, the conflict type, severity,
description, and resolution advice.

Architectural Role:
Authoritative conflict rules consumed by ConflictDetector. This file
is the single source of truth for what protection combinations are
incompatible.

Execution Context:
Imported at module load time by __init__.py. The KNOWN_CONFLICTS list
is passed to ConflictDetector.check_flags() during CLI validation.

Dependencies:
- detector (Conflict, ConflictType, Severity)

Security Relevance:
Missing conflict rules can lead to silently broken builds (e.g.,
--skip-irgen with --fhe-vm). The conflict rules encode domain
knowledge about which features cannot coexist and why.

Maintenance Notes:
- Add new conflicts in the appropriate section group (by feature area).
- Each conflict MUST have all fields: flag_a, flag_b, conflict_type,
  severity, description, resolution.
- The flag names must match the CLI argument dest names exactly
  (after -- is converted to _).
- The INCOMPATIBLE type is symmetric; REQUIRES is directional
  (flag_a requires flag_b).
"""

from scripts.conflicts.detector import Conflict, ConflictType, Severity

from scripts.conflicts.detector import Conflict, ConflictType, Severity

KNOWN_CONFLICTS = [
    # --skip-obfuscate vs obfuscation features
    Conflict(
        flag_a="obfuscate",
        flag_b="skip_obfuscate",
        conflict_type=ConflictType.INCOMPATIBLE,
        severity=Severity.ERROR,
        description="Cannot both enable and skip obfuscation",
        resolution="Remove --skip-obfuscate to enable obfuscation, or do not request obfuscation-enabling features",
    ),
    Conflict(
        flag_a="skip_obfuscate",
        flag_b="speculation_obfuscation",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="Speculation obfuscation requires AST obfuscation to be enabled",
        resolution="Remove --skip-obfuscate to use --speculation-obfuscation",
    ),
    Conflict(
        flag_a="skip_obfuscate",
        flag_b="function_intent",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.WARNING,
        description="Function intent obfuscation requires AST obfuscation",
        resolution="Remove --skip-obfuscate to use --function-intent",
    ),
    Conflict(
        flag_a="skip_obfuscate",
        flag_b="verify_mutations",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.WARNING,
        description="Mutation verification requires obfuscation passes to run",
        resolution="Remove --skip-obfuscate to use --verify-mutations",
    ),

    # --skip-irgen vs IR-requiring features
    Conflict(
        flag_a="skip_irgen",
        flag_b="fhe_vm",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="FHE-VM requires IR generation; --skip-irgen disables IR",
        resolution="Remove --skip-irgen to use --fhe-vm",
    ),
    Conflict(
        flag_a="skip_irgen",
        flag_b="io_research",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="iO research requires IR generation",
        resolution="Remove --skip-irgen to use --io-research",
    ),
    Conflict(
        flag_a="skip_irgen",
        flag_b="verify_preservation",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.WARNING,
        description="Preservation verification requires IR generation for cross-stage checks",
        resolution="Remove --skip-irgen or skip preservation verification",
    ),
    Conflict(
        flag_a="skip_irgen",
        flag_b="prove_vm",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="VM correctness proofs require IR generation",
        resolution="Remove --skip-irgen to use --prove-vm",
    ),
    Conflict(
        flag_a="skip_irgen",
        flag_b="distributed_vm",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="Distributed VM execution requires IR compilation",
        resolution="Remove --skip-irgen to use --distributed-vm",
    ),
    Conflict(
        flag_a="skip_irgen",
        flag_b="kernel_assist",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="Kernel-assisted execution requires IR compilation",
        resolution="Remove --skip-irgen to use --kernel-assist",
    ),
    Conflict(
        flag_a="skip_irgen",
        flag_b="zk_state",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="ZK state-bound execution requires IR compilation",
        resolution="Remove --skip-irgen to use --zk-state",
    ),
    Conflict(
        flag_a="skip_irgen",
        flag_b="watermark",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.WARNING,
        description="Semantic watermarking operates on IR; --skip-irgen disables IR",
        resolution="Remove --skip-irgen to use --watermark, or accept watermark on AST only",
    ),

    # --skip-llvmgen vs LLVM-requiring features
    Conflict(
        flag_a="skip_llvmgen",
        flag_b="rop",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="ROP compilation requires LLVM codegen",
        resolution="Remove --skip-llvmgen to use --rop",
    ),
    Conflict(
        flag_a="skip_llvmgen",
        flag_b="multi_binary",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="Multi-binary fragment distribution requires LLVM codegen for each binary",
        resolution="Remove --skip-llvmgen to use --multi-binary",
    ),
    Conflict(
        flag_a="skip_llvmgen",
        flag_b="gpu_execution",
        conflict_type=ConflictType.REQUIRES,
        severity=Severity.ERROR,
        description="GPU fragment execution requires LLVM codegen for GPU kernels",
        resolution="Remove --skip-llvmgen to use --gpu-execution",
    ),

    # Positive/negative toggle pairs (conceptual conflicts)
    Conflict(
        flag_a="no_cfg_flatten",
        flag_b="cfg_flatten",
        conflict_type=ConflictType.INCOMPATIBLE,
        severity=Severity.ERROR,
        description="--no-cfg-flatten and --cfg-flatten are mutually exclusive",
        resolution="Use only one of --cfg-flatten or --no-cfg-flatten",
    ),
    Conflict(
        flag_a="no_opaque_predicates",
        flag_b="opaque_predicates",
        conflict_type=ConflictType.INCOMPATIBLE,
        severity=Severity.ERROR,
        description="--no-opaque-predicates and --opaque-predicates are mutually exclusive",
        resolution="Use only one of --opaque-predicates or --no-opaque-predicates",
    ),
    Conflict(
        flag_a="no_mba_subs",
        flag_b="mba_subs",
        conflict_type=ConflictType.INCOMPATIBLE,
        severity=Severity.ERROR,
        description="--no-mba-subs and --mba-subs are mutually exclusive",
        resolution="Use only one of --mba-subs or --no-mba-subs",
    ),

    # Encrypt toggles
    Conflict(
        flag_a="encrypt",
        flag_b="skip_encrypt",
        conflict_type=ConflictType.INCOMPATIBLE,
        severity=Severity.ERROR,
        description="Cannot both enable and skip encryption",
        resolution="Remove --skip-encrypt to enable encryption, or do not request encryption-enabling features",
    ),

    # Subsumption relationships
    Conflict(
        flag_a="tee",
        flag_b="sgx",
        conflict_type=ConflictType.SUBSUMES,
        severity=Severity.WARNING,
        description="SGX is a specific TEE implementation; --sgx is redundant when --tee is active",
        resolution="Use --tee alone, or remove --tee and use --sgx with --tee-type sgx",
    ),
    Conflict(
        flag_a="gpu_execution",
        flag_b="cpu_gpu_hybrid",
        conflict_type=ConflictType.SUBSUMES,
        severity=Severity.WARNING,
        description="--gpu-execution is a subset of --cpu-gpu-hybrid protection",
        resolution="Use --cpu-gpu-hybrid for combined CPU/GPU paths, or --gpu-execution for GPU only",
    ),
    Conflict(
        flag_a="phase2",
        flag_b="phase2_only",
        conflict_type=ConflictType.SUBSUMES,
        severity=Severity.WARNING,
        description="--phase2 subsumes --phase2-only; phase2-only is redundant when --phase2 is active",
        resolution="Use --phase2 or --phase2-only, not both",
    ),

    # Distributed mode incompatibilities
    Conflict(
        flag_a="multi_binary",
        flag_b="single_binary",
        conflict_type=ConflictType.INCOMPATIBLE,
        severity=Severity.ERROR,
        description="Multi-binary and single-binary execution modes are incompatible",
        resolution="Choose either --multi-binary or single-binary deployment mode",
    ),
]
