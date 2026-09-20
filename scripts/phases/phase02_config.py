"""
phase02_config.py

Purpose:
Generates the minimal build config file and loads the full advanced
protection configuration (aka "phase2") from default.json, merging
in CLI overrides for features such as adversarial injection, ephemeral
ISA, micro-JIT, ORAM, and ROP compilation.

Architectural Role:
Early pipeline phase — writes orbital-relay.json and provides a merged
config dict consumed by downstream phases that check feature flags.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, ..common (log, atomic_write, CONFIG_FILE, DEFAULT_CONFIG)

Security Relevance:
Central configuration hub — controls which protection features are
enabled for the entire build pipeline.
"""

import json
import os

from ..common import log, atomic_write, CONFIG_FILE, DEFAULT_CONFIG


def phase_generate_config(opts):
    """
    Write a minimal config file to disk and return the empty dict.

    Args:
        opts: argparse.Namespace (unused here, kept for interface compat)

    Returns:
        dict (empty, the real config comes from load_advanced_protection_config)
    """
    log("CONFIG", "Generating minimal config")
    cfg = {}
    atomic_write(CONFIG_FILE, json.dumps(cfg, indent=2))
    log("CONFIG", f"Written to {CONFIG_FILE}")
    return cfg


def load_advanced_protection_config(opts) -> dict:
    """
    Load and merge advanced protection configuration from default.json and CLI flags.

    Reads shadow_compiler.advanced_protection (or fallback phase2) from the
    default config, then applies CLI overrides for individual features.

    Args:
        opts: argparse.Namespace with feature-enable flags

    Returns:
        dict with merged "features" sub-dict and optional "extras"
    """
    cfg = {}
    if os.path.exists(DEFAULT_CONFIG):
        try:
            with open(DEFAULT_CONFIG, "r") as f:
                default = json.load(f)
            advanced = default.get("shadow_compiler", {}).get("advanced_protection", {})
            fallback = default.get("shadow_compiler", {}).get("phase2", {})
            cfg = advanced if advanced else fallback
        except (json.JSONDecodeError, KeyError):
            cfg = {}

    if opts.advanced_protection or opts.phase2:
        cfg["enabled"] = True

    if opts.advanced_protection_only or opts.phase2_only:
        enabled_features = {f.strip() for f in (opts.advanced_protection_only or opts.phase2_only).split(",") if f.strip()}
        if "features" not in cfg:
            cfg["features"] = {}
        for feature in cfg.get("features", {}):
            cfg["features"][feature] = feature in enabled_features

    extras = default.get("shadow_compiler", {}).get("phase2_extras", {})
    if extras:
        cfg["extras"] = extras

    if opts.phase2_extras:
        cfg["extras"] = cfg.get("extras", {})
        cfg["extras"]["enabled"] = True

    if "features" not in cfg:
        cfg["features"] = {}

    full_cfg = {}
    if os.path.exists(DEFAULT_CONFIG):
        try:
            with open(DEFAULT_CONFIG, "r") as f:
                full_cfg = json.load(f).get("shadow_compiler", {})
        except (json.JSONDecodeError, KeyError):
            pass

    if opts.adversarial_injection:
        cfg["features"]["adversarial"] = True

    vm_cfg = full_cfg.get("vm", {})
    if vm_cfg.get("ephemeral_isa", False) or opts.ephemeral_isa:
        cfg["features"]["ephemeral_isa"] = True

    runtime_cfg = full_cfg.get("runtime", {})
    if runtime_cfg.get("microjit", False) or opts.microjit:
        cfg["features"]["microjit"] = True

    oram_cfg = runtime_cfg.get("oram", {})
    if oram_cfg.get("enabled", False) or opts.oram:
        cfg["features"]["oram"] = True

    llvmgen_cfg = full_cfg.get("llvmgen", {})
    rop_cfg = llvmgen_cfg.get("rop", {})
    if rop_cfg.get("enabled", False) or opts.rop:
        cfg["features"]["rop"] = True

    return cfg


# Backward compat alias
load_phase2_config = load_advanced_protection_config
