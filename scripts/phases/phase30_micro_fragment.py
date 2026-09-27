"""
phase30_micro_fragment.py

Purpose:
Splits code into small encrypted fragments (Item 50) using
MicroFragmentExecutor.  Each fragment is independently encrypted
with a master key, and the fragments are reassembled at runtime.

Architectural Role:
Post-obfuscation fragment phase — produces micro-fragment config for runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, secrets, ..common, scripts.fragment.micro_fragment

Security Relevance:
Micro-fragmentation splits code below the function level, making
reassembly without the runtime key infeasible.
"""

import json
import os
import secrets

from ..common import log, atomic_write, BUILD_DIR


def phase_micro_fragment(code: str, opts) -> dict:
    """
    Fragment the source code into encrypted micro-fragments.

    Args:
        code: source code string to fragment
        opts: argparse.Namespace with micro_fragment_size

    Returns:
        dict with master_key, fragment_size, total_fragments, enabled
    """
    log("MICRO_FRAGMENT", f"Running micro-fragment phase (Item 50)...")
    try:
        from scripts.fragment.micro_fragment import MicroFragmentExecutor
        micro_frag_key = secrets.token_bytes(32)
        fragment_size = getattr(opts, "micro_fragment_size", 64)
        executor = MicroFragmentExecutor(
            master_key=micro_frag_key,
            fragment_size=fragment_size,
        )
        executor.fragment_code(code)
        mf_config = {
            "master_key": micro_frag_key.hex(),
            "fragment_size": fragment_size,
            "total_fragments": len(executor.fragments),
            "enabled": True,
        }
        mf_config_path = os.path.join(BUILD_DIR, "micro_fragment_config.json")
        atomic_write(mf_config_path, json.dumps(mf_config, indent=2))
        log("MICRO_FRAGMENT", f"Code split into {len(executor.fragments)} fragments")
        return mf_config
    except Exception as e:
        log("ERROR", f"Micro-fragment phase failed: {e}")
        raise
