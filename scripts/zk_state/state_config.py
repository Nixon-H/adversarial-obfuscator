"""
state_config.py

Purpose:
Configuration management for ZK state-bound execution. Reads settings
from CLI arguments (--zk-state, --zk-state-config) or a JSON config
file and produces a ZKStateConfig dataclass with appropriate defaults.

Architectural Role:
Bridge between the CLI argument parser and the ZK module. ZKStateConfig
is consumed by the pipeline to determine whether ZK state binding is
active, where to persist state, and how many proofs to cache.

Execution Context:
Called during pipeline initialization by load_config(args). The
config is checked for prerequisites before execution begins.

Dependencies:
- Standard library (os, dataclasses, typing, json)

Security Relevance:
Configuration controls whether ZK proofs are generated and verified.
An attacker who can disable ZK (by not passing --zk-state, or by
editing the config file) can bypass state-bound execution checks.

# Why this approach was chosen:
# Simple dataclass-based config with JSON file support. The CLI
# argument mapping is straightforward: --zk-state enables, the
# optional --zk-state-config points to a JSON file with details.

# Threat addressed:
# ZK state binding prevents execution outside the expected context.
# Disabling it (via config) removes this protection.

# Assumptions:
# - The CLI arguments come from a trusted pipeline (not user-supplied)
# - The config file (if specified) is not attacker-controlled

# Failure consequences:
# - ZK disabled: state-bound functions execute without proof generation
# - Incorrect config file: ZK silently defaults to safe values

Maintenance Notes:
- Security classification: MEASURED (configuration is read from CLI
  arguments with sensible defaults).
- THEORETICAL: runtime configuration changes are not authenticated;
  an attacker who controls the CLI arguments can disable protections.
- check_prerequisites() verifies that hashlib and secrets are
  available (always true in standard Python).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

@dataclass
class ZKStateConfig:
    """Configuration for ZK state-bound execution.

    Attributes:
        enabled: whether ZK state binding is active
        state_file: path to persistent state file (optional)
        require_online: if True, fail when state file is unavailable
        proof_cache_size: maximum number of cached proofs
    """
    enabled: bool = False
    state_file: str = ""
    require_online: bool = False
    proof_cache_size: int = 100


def load_config(args: Any) -> ZKStateConfig:
    """Load ZK state configuration from CLI arguments.

    Args:
        args: argparse namespace or dict-like object with zk_state
              and zk_state_config attributes

    Returns:
        ZKStateConfig with values populated from args (or defaults)
    """
    if isinstance(args, dict):
        enabled = args.get("zk_state", False)
        config_path = args.get("zk_state_config", "")
    else:
        enabled = getattr(args, "zk_state", False)
        config_path = getattr(args, "zk_state_config", "")

    if not enabled:
        return ZKStateConfig()

    config = ZKStateConfig(enabled=True)

    if config_path and os.path.exists(config_path):
        import json
        try:
            with open(config_path) as f:
                data = json.load(f)
            config.state_file = data.get("state_file", config_path)
            config.require_online = data.get("require_online", False)
            config.proof_cache_size = data.get("proof_cache_size", 100)
        except Exception:
            config.state_file = config_path
    elif config_path:
        config.state_file = config_path

    return config


def check_prerequisites() -> bool:
    """Verify that all prerequisites for ZK state execution are met.

    The sigma protocol uses only standard library modules (hashlib,
    secrets, os, time), so this always returns True.

    Returns:
        True if all dependencies are available
    """
    try:
        import hashlib
        import secrets
        hashlib.sha256(b"test")
        secrets.randbelow(100)
        return True
    except Exception:
        return False
