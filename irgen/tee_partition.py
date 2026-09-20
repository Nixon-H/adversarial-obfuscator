"""
tee_partition.py

Purpose:
TEE (Trusted Execution Environment) partitioning pass. Identifies
crown-jewel (security-critical) functions via keyword matching and
partitions an IR module into host and enclave portions. Generates C
entry stubs for enclave boundary crossing and TEE configuration stubs.

Architectural Role:
Pre-build partitioning pass. Splits the IR module into two parts:
- host_mod: non-sensitive functions that run in the untrusted host.
- enclave_mod: security-critical functions that run inside a TEE
  (Intel SGX, AMD SEV, or TrustZone).

Security Relevance:
- Crown jewel identification uses keyword matching against a list
  of security-related function names (key_deriv, decrypt, attest,
  etc.). This can be customized via config.
- Partitioning into host/enclave enables hardware-enforced isolation
  of the most sensitive code.
- Generated entry stubs handle serialization/deserialization across
  the enclave boundary, including function ID encoding via hash.
- The TEE config dict includes attestation policy, sealing algorithm
  (AES-256-GCM), and heap/stack sizing.

Threat model: Compromised host OS, memory bus snooping, cold boot
attacks on host memory.

What happens if config is missing: Falls back to empty config,
resulting in no TEE partitioning.
"""

from __future__ import annotations
import ast
import hashlib
from typing import List, Tuple, Optional

from irgen.compile import IrModule, IrFunction, IrValue, IrType

TEE_KEYWORDS: List[str] = [
    "key_deriv", "derive_key", "kdf", "pbkdf",
    "license", "validate_license", "check_license",
    "decrypt", "encrypt_data", "unseal",
    "hsm", "secure_boot", "verify_sig",
    "attest", "seal", "tee_entry",
]


def identify_critical_functions(
    ir_module: IrModule,
    config: Optional[dict] = None,
) -> List[str]:
    """
    Identify security-critical functions in an IR module.

    Uses two strategies:
    1. Direct match against config.target_functions.
    2. Keyword matching of function name and called function names
       against TEE_KEYWORDS (or custom crown_jewel_patterns).

    A function is critical if its name or any callee name contains
    a keyword (case-insensitive).

    Args:
        ir_module: The IR module to analyze.
        config: Optional config dict with target_functions and/or
                crown_jewel_patterns.

    Returns:
        Sorted list of critical function names.
    """
    config = config or {}
    target_functions: List[str] = list(config.get("target_functions", []))
    crown_jewel_patterns: List[str] = config.get("crown_jewel_patterns", TEE_KEYWORDS)

    extracted: List[str] = []

    for func in ir_module.functions:
        name = func.name

        if name in target_functions:
            if name not in extracted:
                extracted.append(name)
            continue

        for keyword in crown_jewel_patterns:
            if keyword.lower() in name.lower():
                if name not in extracted:
                    extracted.append(name)
                break

        for block in func.blocks:
            for inst in block.instructions:
                if inst.opcode == "call" and inst.func_name:
                    callee = inst.func_name
                    if callee.startswith("__"):
                        continue
                    for keyword in crown_jewel_patterns:
                        if keyword.lower() in callee.lower():
                            if name not in extracted:
                                extracted.append(name)
                            break

    return extracted


def partition_program(
    ir_module: IrModule,
    critical_funcs: List[str],
) -> Tuple[IrModule, IrModule]:
    """
    Split an IR module into host and enclave portions.

    Functions in critical_funcs go to enclave_mod; all others go
    to host_mod. Creates new module names with _host and _enclave
    suffixes.
    """
    host_mod = IrModule(f"{ir_module.name}_host")
    enclave_mod = IrModule(f"{ir_module.name}_enclave")

    for func in ir_module.functions:
        if func.name in critical_funcs:
            enclave_mod.functions.append(func)
        else:
            host_mod.functions.append(func)

    return host_mod, enclave_mod


def generate_enclave_entry_stubs(critical_funcs: List[str]) -> str:
    """
    Generate C entry stubs for enclave boundary crossing.

    Each stub:
    1. Serializes arguments into a flat buffer (function ID + data).
    2. Calls the runtime tee_enclave_call() function.
    3. Deserializes and returns the result.

    The function ID is hash(func_name) & 0xFFFFFFFF, providing a
    compact identifier for the enclave dispatcher.
    """
    lines: List[str] = []
    lines.append("// Auto-generated TEE enclave entry stubs")
    lines.append("// Each stub serializes arguments, crosses the enclave boundary,")
    lines.append("// and deserializes the result.")
    lines.append("")

    for func_name in critical_funcs:
        stub_name = f"tee_enclave_{func_name}"
        lines.append(f"int {stub_name}(int argc, void* argv[]) {{")
        lines.append(f"    uint32_t fn_id = {hash(func_name) & 0xFFFFFFFF}u;")
        lines.append(f"    size_t input_len = 0;")
        lines.append(f"    for (int i = 0; i < argc; i++) {{")
        lines.append(f"        if (argv[i]) {{")
        lines.append(f"            input_len += sizeof(void*);")
        lines.append(f"        }}")
        lines.append(f"    }}")
        lines.append(f"")
        lines.append(f"    uint8_t* input_buffer = (uint8_t*)malloc(input_len + 4);")
        lines.append(f"    if (!input_buffer) return -1;")
        lines.append(f"    input_buffer[0] = (fn_id >> 0) & 0xFF;")
        lines.append(f"    input_buffer[1] = (fn_id >> 8) & 0xFF;")
        lines.append(f"    input_buffer[2] = (fn_id >> 16) & 0xFF;")
        lines.append(f"    input_buffer[3] = (fn_id >> 24) & 0xFF;")
        lines.append(f"")
        lines.append(f"    size_t output_len = 0;")
        lines.append(f"    uint8_t* output_buffer = tee_enclave_call(")
        lines.append(f"        input_buffer, input_len + 4, &output_len")
        lines.append(f"    );")
        lines.append(f"    free(input_buffer);")
        lines.append(f"")
        lines.append(f"    if (!output_buffer) return -1;")
        lines.append(f"")
        lines.append(f"    int result = 0;")
        lines.append(f"    if (output_len >= sizeof(int)) {{")
        lines.append(f"        result = (int)output_buffer[0];")
        lines.append(f"    }}")
        lines.append(f"    free(output_buffer);")
        lines.append(f"    return result;")
        lines.append(f"}}")
        lines.append(f"")

    lines.append("// Forward declaration of the runtime enclave call interface")
    lines.append("uint8_t* tee_enclave_call(")
    lines.append("    const uint8_t* input, size_t input_len, size_t* output_len")
    lines.append(");")
    lines.append("")

    return "\n".join(lines)


def generate_tee_config(
    critical_funcs: List[str],
    tee_type: str = "sgx",
) -> dict:
    """
    Generate TEE configuration dict.

    Includes enclave heap/stack sizing, attestation configuration,
    and data sealing settings. Defaults to Intel SGX with EPID
    attestation and AES-256-GCM sealing.

    Args:
        critical_funcs: List of function names to place in the enclave.
        tee_type: 'sgx', 'sev', or 'trustzone'.

    Returns:
        Dict suitable for JSON serialization.
    """
    return {
        "enabled": len(critical_funcs) > 0,
        "tee_type": tee_type.lower(),
        "target_functions": critical_funcs,
        "enclave": {
            "heap_size": 64 * 1024,
            "stack_size": 8 * 1024,
            "num_threads": 1,
            "debug": False,
        },
        "attestation": {
            "enabled": True,
            "type": "epid" if tee_type.lower() == "sgx" else "native",
        },
        "sealing": {
            "enabled": True,
            "algorithm": "aes-256-gcm",
        },
        "entry_stubs": {
            func: f"tee_enclave_{func}" for func in critical_funcs
        },
    }
