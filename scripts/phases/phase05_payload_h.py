"""
phase05_payload_h.py

Purpose:
Generates the native C/C++ header (payload.h) that embeds the obfuscated
Python payload as a byte array for the orbital-relay runtime.  Optionally
embeds crypto fragment binding data and generates the runtime manifest.

Architectural Role:
Bridge between the Python obfuscation pipeline and the Rust native runtime.
Produces payload.h consumed by the Rust build.

Execution Context:
Called from build.py after obfuscation and before native compilation.

Dependencies:
os, struct, sys, ..common, scripts.generate_payload_h, runtime.gen_manifest

Security Relevance:
Embedding the payload as a header prevents trivial file-based extraction;
crypto bindings tie execution to specific fragment hashes.
"""

import os
import struct
import sys

from ..common import log, run, ROOT, BUILD_DIR


def phase_generate_payload_h(obfuscated_py_path, opts):
    """
    Generate payload.h from the obfuscated Python payload.

    Delegates to scripts/generate_payload_h.py.  Optionally embeds
    crypto binding data if --crypto-binding is set.

    Args:
        obfuscated_py_path: path to the obfuscated .py file
        opts: argparse.Namespace with options like --crypto-binding
    """
    log("PAYLOAD_H", "Generating payload.h from obfuscated payload...")
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "generate_payload_h.py"),
           "--obfuscated-py", obfuscated_py_path,
           "--output", os.path.join(ROOT, "native", "payload.h")]
    if opts.python_dll and os.path.exists(opts.python_dll):
        cmd.extend(["--python-dll", opts.python_dll])
    if opts.rust_exe and os.path.exists(opts.rust_exe):
        cmd.extend(["--rust-exe", opts.rust_exe])
    run(cmd)
    payload_h_path = os.path.join(ROOT, "native", "payload.h")
    if os.path.exists(payload_h_path):
        size = os.path.getsize(payload_h_path)
        log("PAYLOAD_H", f"Done: {payload_h_path} ({size/1024:.1f}KB)")

    if getattr(opts, 'crypto_binding', False):
        phase_embed_crypto_binding(payload_h_path)


def phase_embed_crypto_binding(payload_h_path: str):
    """
    Embed crypto fragment binding data into payload.h.

    Reads the bound fragments binary and chain secret from BUILD_DIR
    and appends C constant arrays to the header.

    Args:
        payload_h_path: path to payload.h to modify in-place
    """
    crypto_binding_path = os.path.join(BUILD_DIR, "crypto_bound_fragments.bin")
    chain_secret_path = os.path.join(BUILD_DIR, "chain_secret.bin")

    if not os.path.exists(crypto_binding_path):
        log("CRYPTO_BINDING", f"Bound fragments not found: {crypto_binding_path}")
        return

    log("CRYPTO_BINDING", f"Embedding crypto binding data into payload.h...")

    with open(crypto_binding_path, "rb") as f:
        bound_data = f.read()

    if len(bound_data) < 4:
        log("ERROR", f"Bound fragments file too short ({len(bound_data)} bytes), skipping embed")
        return

    chain_secret = b""
    if os.path.exists(chain_secret_path):
        with open(chain_secret_path, "rb") as f:
            chain_secret = f.read()

    with open(payload_h_path, "a") as f:
        f.write("\n// ============================================================\n")
        f.write("// Crypto Fragment Binding — execution-derived cryptographic chain\n")
        f.write("// ============================================================\n\n")

        f.write(f"constexpr size_t NIXON_CRYPTO_BOUND_DATA_LEN = {len(bound_data)};\n")
        f.write(f"constexpr size_t NIXON_NUM_BOUND_FRAGMENTS = {struct.unpack('>I', bound_data[:4])[0]};\n\n")

        f.write("const uint8_t NIXON_CRYPTO_BOUND_DATA[NIXON_CRYPTO_BOUND_DATA_LEN] = {\n")
        indent = "    "
        cols = 16
        for i in range(0, len(bound_data), cols):
            chunk = bound_data[i:i + cols]
            f.write(indent + ", ".join(f"0x{b:02X}" for b in chunk) + ",\n")
        f.write("};\n\n")

        if chain_secret:
            f.write("const uint8_t NIXON_CHAIN_SECRET[32] = {\n")
            f.write(indent + ", ".join(f"0x{b:02X}" for b in chain_secret) + ",\n")
            f.write("};\n")

    log("CRYPTO_BINDING", f"Embedded {len(bound_data)} bytes of bound fragment data")


def phase_runtime_manifest(output_manifest):
    """
    Generate the runtime manifest via runtime/gen_manifest.py.

    Args:
        output_manifest: path for the generated manifest
    """
    log("RUNTIME", f"Generating {output_manifest}")
    script = os.path.join(ROOT, "runtime", "gen_manifest.py")
    if not os.path.exists(script):
        log("SKIP", f"runtime/gen_manifest.py not found, skipping")
        return
    run([sys.executable, script, "--output", output_manifest])
