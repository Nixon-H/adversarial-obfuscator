"""
assumptions/registry.py — Feature assumption definitions (F171)

Purpose:
    Defines the FEATURE_ASSUMPTIONS mapping: for each feature (FHE-VM,
    Kernel-Assist, ZK-State, SGX, TEE, GPU, HPC, etc.), lists the OS,
    hardware, software, and runtime assumptions required.

Architectural Role:
    Data layer. The registry is populated at import time and consumed by
    the AssumptionTracker to check each assumption at runtime.

Security Relevance:
    Explicitly encoding assumptions makes them auditable and testable,
    preventing silent failures when a feature's dependencies are missing.
"""

from __future__ import annotations

from typing import Dict, List

from .tracker import Assumption, AssumptionTracker

FEATURE_ASSUMPTIONS: Dict[str, List[Assumption]] = {
    "FHE-VM": [
        Assumption("FHE-VM", "python3", "software", required=True),
        Assumption("FHE-VM", "z3", "software", required=True),
        Assumption("FHE-VM", "numpy", "software", required=False),
        Assumption("FHE-VM", "integer-arithmetic", "runtime", required=True),
    ],
    "Kernel-Assist": [
        Assumption("Kernel-Assist", "Linux", "OS", required=True),
        Assumption("Kernel-Assist", "userfaultfd", "OS", required=False),
        Assumption("Kernel-Assist", "seccomp", "OS", required=False),
        Assumption("Kernel-Assist", "/proc", "OS", required=True),
    ],
    "ZK-State": [
        Assumption("ZK-State", "python3", "software", required=True),
        Assumption("ZK-State", "hashlib", "software", required=True),
        Assumption("ZK-State", "sha256-acceleration", "hardware", required=False),
    ],
    "SGX": [
        Assumption("SGX", "Linux", "OS", required=True),
        Assumption("SGX", "SGX-hardware", "hardware", required=True),
        Assumption("SGX", "aesm-service", "runtime", required=True),
        Assumption("SGX", "CPUID-SGX-flag", "hardware", required=True),
    ],
    "TEE": [
        Assumption("TEE", "Linux", "OS", required=True),
        Assumption("TEE", "TEE-hardware", "hardware", required=True),
        Assumption("TEE", "enclave-memory", "runtime", required=True),
    ],
    "GPU": [
        Assumption("GPU", "OpenCL-or-CUDA", "software", required=True),
        Assumption("GPU", "GPU-hardware", "hardware", required=True),
        Assumption("GPU", "GPU-driver", "runtime", required=True),
    ],
    "HPC": [
        Assumption("HPC", "Linux", "OS", required=True),
        Assumption("HPC", "perf_event_open", "OS", required=True),
        Assumption("HPC", "PMC-registers", "hardware", required=True),
    ],
    "Branch-Entangle": [
        Assumption("Branch-Entangle", "x86_64", "hardware", required=True),
        Assumption("Branch-Entangle", "RDTSCP", "hardware", required=True),
        Assumption("Branch-Entangle", "branch-predictor", "hardware", required=False),
    ],
    "SIMD-VM": [
        Assumption("SIMD-VM", "x86_64", "hardware", required=True),
        Assumption("SIMD-VM", "SSE", "hardware", required=False),
        Assumption("SIMD-VM", "AVX", "hardware", required=False),
        Assumption("SIMD-VM", "AVX2", "hardware", required=False),
    ],
    "Distributed": [
        Assumption("Distributed", "TCP/IP", "runtime", required=True),
        Assumption("Distributed", "multi-host", "configuration", required=True),
        Assumption("Distributed", "clock-sync", "runtime", required=False),
    ],
    "LLM": [
        Assumption("LLM", "OpenAI-API-key", "configuration", required=False),
        Assumption("LLM", "Anthropic-API-key", "configuration", required=False),
        Assumption("LLM", "DeepSeek-API-key", "configuration", required=False),
        Assumption("LLM", "network-access", "runtime", required=True),
    ],
    "angr": [
        Assumption("angr", "python3", "software", required=True),
        Assumption("angr", "angr-package", "software", required=True),
    ],
    "Ghidra": [
        Assumption("Ghidra", "Java", "software", required=True),
        Assumption("Ghidra", "Ghidra-installation", "software", required=True),
    ],
    "CFG-Mutation": [
        Assumption("CFG-Mutation", "python3", "software", required=True),
        Assumption("CFG-Mutation", "basic-block-analysis", "runtime", required=True),
    ],
    "SSA-Mutation": [
        Assumption("SSA-Mutation", "python3", "software", required=True),
        Assumption("SSA-Mutation", "SSA-form", "runtime", required=True),
    ],
    "ROP-Compile": [
        Assumption("ROP-Compile", "x86_64", "hardware", required=True),
        Assumption("ROP-Compile", "gadget-finder", "software", required=True),
    ],
    "Crypto-Binding": [
        Assumption("Crypto-Binding", "python3", "software", required=True),
        Assumption("Crypto-Binding", "AES-NI", "hardware", required=False),
        Assumption("Crypto-Binding", "OS-entropy", "runtime", required=True),
    ],
    "SGX-Enclave": [
        Assumption("SGX-Enclave", "Linux", "OS", required=True),
        Assumption("SGX-Enclave", "SGX2", "hardware", required=False),
        Assumption("SGX-Enclave", "EDMM", "hardware", required=False),
    ],
    "TEE-SEV": [
        Assumption("TEE-SEV", "Linux", "OS", required=True),
        Assumption("TEE-SEV", "AMD-SEV-hardware", "hardware", required=True),
    ],
    "Multi-Core-Entangle": [
        Assumption("Multi-Core-Entangle", "multi-core-CPU", "hardware", required=True),
        Assumption("Multi-Core-Entangle", "shared-L3-cache", "hardware", required=False),
    ],
    "Cache-Bound": [
        Assumption("Cache-Bound", "x86_64", "hardware", required=True),
        Assumption("Cache-Bound", "CLFLUSH", "hardware", required=True),
        Assumption("Cache-Bound", "cache-timing", "runtime", required=False),
    ],
    "HW-Entropy": [
        Assumption("HW-Entropy", "RDRAND", "hardware", required=True),
        Assumption("HW-Entropy", "RDSEED", "hardware", required=False),
    ],
    "Micro-Fragment": [
        Assumption("Micro-Fragment", "python3", "software", required=True),
        Assumption("Micro-Fragment", "mprotect", "OS", required=True),
    ],
    "Poly-Engine": [
        Assumption("Poly-Engine", "python3", "software", required=True),
        Assumption("Poly-Engine", "platform-profile", "runtime", required=True),
    ],
    "Temporal-Keys": [
        Assumption("Temporal-Keys", "python3", "software", required=True),
        Assumption("Temporal-Keys", "HKDF", "software", required=True),
        Assumption("Temporal-Keys", "clock", "runtime", required=True),
    ],
    "Payload-Dispersal": [
        Assumption("Payload-Dispersal", "python3", "software", required=True),
        Assumption("Payload-Dispersal", "multi-thread", "runtime", required=False),
    ],
    "Proof-Carrying": [
        Assumption("Proof-Carrying", "python3", "software", required=True),
        Assumption("Proof-Carrying", "z3", "software", required=True),
    ],
    "Whitebox-Flow-Entangle": [
        Assumption("Whitebox-Flow-Entangle", "python3", "software", required=True),
        Assumption("Whitebox-Flow-Entangle", "crypto-primitives", "software", required=True),
    ],
    "Attestation": [
        Assumption("Attestation", "Linux", "OS", required=True),
        Assumption("Attestation", "TPM", "hardware", required=False),
    ],
    "Data-Obfuscation": [
        Assumption("Data-Obfuscation", "python3", "software", required=True),
        Assumption("Data-Obfuscation", "data-flow-analysis", "runtime", required=True),
    ],
    "EPHEMERAL-ISA": [
        Assumption("EPHEMERAL-ISA", "python3", "software", required=True),
        Assumption("EPHEMERAL-ISA", "deterministic-RNG", "runtime", required=True),
    ],
    "ORAM": [
        Assumption("ORAM", "python3", "software", required=True),
        Assumption("ORAM", "oblivious-primitives", "software", required=True),
    ],
    "LLM-Fingerprint": [
        Assumption("LLM-Fingerprint", "python3", "software", required=True),
        Assumption("LLM-Fingerprint", "AST-manipulation", "software", required=True),
    ],
    "Reasoning-Traps": [
        Assumption("Reasoning-Traps", "python3", "software", required=True),
        Assumption("Reasoning-Traps", "circular-dependency", "runtime", required=False),
    ],
    "Function-Intent": [
        Assumption("Function-Intent", "python3", "software", required=True),
        Assumption("Function-Intent", "name-mangling", "software", required=True),
    ],
    "Intel-PT": [
        Assumption("Intel-PT", "Linux", "OS", required=True),
        Assumption("Intel-PT", "Intel-Processor-Trace", "hardware", required=True),
        Assumption("Intel-PT", "perf_event_open", "OS", required=True),
    ],
    "eBPF": [
        Assumption("eBPF", "Linux", "OS", required=True),
        Assumption("eBPF", "BPF-syscall", "OS", required=True),
        Assumption("eBPF", "kernel-BPF-support", "OS", required=True),
    ],
    "CPU-Port-Entangle": [
        Assumption("CPU-Port-Entangle", "x86_64", "hardware", required=True),
        Assumption("CPU-Port-Entangle", "execution-ports", "hardware", required=False),
    ],
    "GPU-Hybrid": [
        Assumption("GPU-Hybrid", "OpenCL-or-CUDA", "software", required=True),
        Assumption("GPU-Hybrid", "GPU-hardware", "hardware", required=True),
        Assumption("GPU-Hybrid", "CPU-GPU-coherency", "hardware", required=False),
    ],
}


def register_all(assumption_tracker: AssumptionTracker) -> None:
    """Register every assumption from FEATURE_ASSUMPTIONS into the given tracker instance."""
    for feature, assumptions in FEATURE_ASSUMPTIONS.items():
        for a in assumptions:
            assumption_tracker.register(a)
