"""
phase06_package.py

Purpose:
Packages build artifacts into BUILD_DIR: copies the obfuscated payload,
optionally the original, and the config.  Also applies optional extras
such as timing traps, silent degradation, ledger integrity, attestation,
HPC entanglement, replay poison, and ORAM configuration.

Architectural Role:
Post-processing phase that organizes build output and generates
supplementary runtime configuration files.

Execution Context:
Called from build.py after payload generation and before cleanup.

Dependencies:
json, os, shutil, ..common, obfuscator.*, scripts.*

Security Relevance:
Optional extras harden runtime resilience (timing traps, attestation,
replay poisoning) and provide integrity proofs.
"""

import json
import os
import shutil

from ..common import log, atomic_write, BUILD_DIR, CONFIG_FILE


def phase_package(payload, obfuscated_output, obfuscated_name, opts):
    """
    Copy artifacts into BUILD_DIR and optionally include the original.

    Args:
        payload: original source path
        obfuscated_output: temp obfuscated file to move
        obfuscated_name: destination filename in BUILD_DIR
        opts: argparse.Namespace (checks include_original)
    """
    log("PACKAGE", "Packaging build artifacts...")
    log("PACKAGE", "Packaging build artifacts...")
    os.makedirs(BUILD_DIR, exist_ok=True)

    if os.path.exists(obfuscated_output):
        dst = os.path.join(BUILD_DIR, obfuscated_name)
        shutil.copy2(obfuscated_output, dst)
        log("PACKAGE", f"  Payload: {dst}")
        os.remove(obfuscated_output)
        # Phase-4 wiring: optional artifact signing sidecar (best-effort,
        # never fails the build). --sign-key-env names an env var holding
        # a hex key; the packaged payload is signed to <file>.sig.json.
        try:
            _sign_env = str(getattr(opts, "sign_key_env", "") or "")
            if _sign_env:
                from scripts.artifact_sign import sign_file as _phase4_sign
                _raw_key = os.environ.get(_sign_env, "")
                if _raw_key:
                    try:
                        _sig = _phase4_sign(dst, bytes.fromhex(_raw_key))
                        with open(dst + ".sig.json", "w", encoding="utf-8") as _sf:
                            json.dump({"algo": _sig.get("algo"), "hex": _sig.get("hex"),
                                       "file": os.path.basename(dst)}, _sf)
                        log("PACKAGE", f"  Signed: {dst}.sig.json")
                    except Exception as _se:
                        log("PACKAGE", f"  Signing failed (non-fatal): {_se}")
                else:
                    log("PACKAGE", f"  Sign key env {_sign_env!r} empty/unset (skipping signing)")
        except Exception:
            pass

    if opts.include_original:
        dst = os.path.join(BUILD_DIR, f"original_{os.path.basename(payload)}")
        shutil.copy2(payload, dst)
        log("PACKAGE", f"  Original: {dst}")

    if os.path.exists(CONFIG_FILE):
        dst = os.path.join(BUILD_DIR, "orbital-relay.json")
        shutil.copy2(CONFIG_FILE, dst)
        log("PACKAGE", f"  Config: {dst}")

    log("PACKAGE", f"  Build dir: {BUILD_DIR}")
    for f in sorted(os.listdir(BUILD_DIR)):
        fp = os.path.join(BUILD_DIR, f)
        if os.path.isfile(fp) and not f.endswith(".so"):
            log("PACKAGE", f"    {f:40s} {os.path.getsize(fp)/1024:.1f}KB")


def phase_optional_extras(cfg):
    """
    Apply optional build extras from the pipeline configuration.

    Iterates enabled features in cfg["extras"]["features"] and calls
    the corresponding private helper for each.

    Args:
        cfg: pipeline configuration dict
    """
    extras = cfg.get("extras", {})
    if not extras.get("enabled", False):
        log("SKIP", "Optional extras not enabled")
        return

    log("EXTRAS", "Applying optional extras...")

    features = extras.get("features", {})
    for feature, enabled in features.items():
        if enabled:
            log("EXTRAS", f"  + {feature}")

            if feature == "timing_traps":
                _run_extra_timing_traps(cfg)
            elif feature == "silent_degradation":
                _run_extra_silent_degradation(cfg)
            elif feature == "ledger_integrity":
                _run_extra_ledger_integrity(cfg)
            elif feature == "hpc_entanglement":
                _run_extra_hpc_entanglement(cfg)
            elif feature == "attestation":
                _run_extra_attestation(cfg)
            elif feature == "replay_poison":
                _run_extra_replay_poison(cfg)
            elif feature == "oram":
                _run_extra_oram(cfg)
        else:
            log("EXTRAS", f"  - {feature} (disabled)")


def _run_extra_timing_traps(cfg):
    log("EXTRAS", "  Generating RDTSC timing traps...")
    try:
        from obfuscator.timing_traps import generate_rdtsc_ir_pattern
        pattern = generate_rdtsc_ir_pattern({"threshold": 1000})
        trap_path = os.path.join(BUILD_DIR, "timing_trap.ir")
        atomic_write(trap_path, pattern)
        log("EXTRAS", f"  Timing trap IR written to {trap_path}")
    except ImportError:
        log("SKIP", "obfuscator.timing_traps not available")


def _run_extra_silent_degradation(cfg):
    log("EXTRAS", "  Generating silent degradation config...")
    deg_config = {
        "enabled": True,
        "corruption_mode": "bit_flip",
        "trigger": "timing_violation",
    }
    deg_path = os.path.join(BUILD_DIR, "degradation_config.json")
    atomic_write(deg_path, json.dumps(deg_config, indent=2))
    log("EXTRAS", f"  Degradation config written to {deg_path}")


def _run_extra_ledger_integrity(cfg):
    log("EXTRAS", "  Generating ledger integrity proof...")
    try:
        from scripts.ledger_proof import compute_text_proof, generate_proof_payload
        binary_path = os.path.join(BUILD_DIR, "program.o")
        if os.path.exists(binary_path):
            proof = compute_text_proof(binary_path)
            build_seed = os.urandom(32)
            payload = generate_proof_payload(proof, build_seed)
            proof_path = os.path.join(BUILD_DIR, "ledger_proof.bin")
            atomic_write(proof_path, payload, mode="wb")
            log("EXTRAS", f"  Ledger proof written to {proof_path} ({len(payload)} bytes)")
        else:
            log("SKIP", f"  Binary not found at {binary_path}, skipping ledger proof")
    except ImportError:
        log("SKIP", "scripts.ledger_proof not available")


def _run_extra_attestation(cfg):
    log("EXTRAS", "  Generating attestation engine config...")
    att_config = {
        "enabled": True,
        "entangled_rounds": 10,
        "challenge_interval_us": (1000, 5000),
        "self_destruct_on_fail": True,
        "whitebox_branch_tags": True,
        "region_hash_bits": 64,
    }
    att_path = os.path.join(BUILD_DIR, "attestation_config.json")
    atomic_write(att_path, json.dumps(att_config, indent=2))
    log("EXTRAS", f"  Attestation config written to {att_path}")


def _run_extra_hpc_entanglement(cfg):
    log("EXTRAS", "  Generating HPC entanglement config...")
    hpc_config = {
        "enabled": True,
        "hpc_seed": int.from_bytes(os.urandom(8), "big"),
        "detection_mode": "cache_misses",
    }
    hpc_path = os.path.join(BUILD_DIR, "hpc_config.json")
    atomic_write(hpc_path, json.dumps(hpc_config, indent=2))
    log("EXTRAS", f"  HPC config written to {hpc_path}")


def _run_extra_replay_poison(cfg):
    log("EXTRAS", "  Generating replay poison config...")
    try:
        from obfuscator.replay_poison import inject_entropy_branches, generate_rdrand_ir_stub
        stub = generate_rdrand_ir_stub()
        stub_path = os.path.join(BUILD_DIR, "rdrand_stub.ll")
        atomic_write(stub_path, stub)
        log("EXTRAS", f"  RDRAND IR stub written to {stub_path}")
    except ImportError:
        log("SKIP", "  obfuscator.replay_poison not available")
    rp_config = {"enabled": True, "poison_probability": 1.0 / 1024.0}
    rp_path = os.path.join(BUILD_DIR, "replay_poison_config.json")
    atomic_write(rp_path, json.dumps(rp_config, indent=2))
    log("EXTRAS", f"  Replay poison config written to {rp_path}")


def _run_extra_oram(cfg):
    log("EXTRAS", "  Generating ORAM config...")
    oram_config = {
        "enabled": True,
        "tree_height": 8,
        "block_size": 64,
        "num_blocks": 256,
    }
    try:
        from irgen.oram import generate_oram_config
        oram_config = generate_oram_config([], 256)
    except ImportError:
        pass
    oram_path = os.path.join(BUILD_DIR, "oram_config.json")
    atomic_write(oram_path, json.dumps(oram_config, indent=2))
    log("EXTRAS", f"  ORAM config written to {oram_path}")
