#!/usr/bin/env python3
"""Runtime feature manifest generator for Nixon Shadow Compiler."""

import argparse
import json
import os
import secrets


def generate_manifest(
    payload_type: str = "python",
    features: list[str] | None = None,
    build_seed: str | None = None,
) -> dict:
    if features is None:
        features = ["antidbg", "integrity", "encrypt", "memguard", "selfdestruct", "exec_guard"]
    if build_seed is None:
        build_seed = secrets.token_hex(32)

    manifest: dict = {
        "version": "1.0.0",
        "payload_type": payload_type,
        "features": features,
        "build_seed": build_seed,
        "encryption": {
            "algorithm": "aes-256-ctr",
            "key_derivation": "sha256(seed + block_index)",
        },
        "integrity": {
            "algorithm": "crc32",
            "check_at": "startup",
        },
        "self_destruct": {
            "on_exit": True,
            "on_detach": True,
            "memory_scrub": True,
        },
    }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate runtime feature manifest")
    parser.add_argument("--output", default="manifest.json", help="Output path")
    parser.add_argument("--payload-type", default="python", choices=["python", "native", "hybrid"])
    parser.add_argument("--features", nargs="*", default=None)
    parser.add_argument("--build-seed", default=None)
    args = parser.parse_args()

    manifest = generate_manifest(args.payload_type, args.features, args.build_seed)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {args.output}")


if __name__ == "__main__":
    main()
