#!/usr/bin/env python3
"""Artifact signing via HMAC-SHA256 (Phase 5 hygiene).

``sign_file(path, key)`` computes HMAC-SHA256 over raw file bytes and
returns ``{'algo': 'hmac-sha256', 'hex': ...}``. ``verify_file`` uses
constant-time :func:`hmac.compare_digest`.

CLI::

    python3 -m scripts.artifact_sign <file> [--verify HEX]
"""

from __future__ import annotations

import argparse
import hmac
import os
import sys


def sign_file(path: str, key: bytes) -> dict:
    """HMAC-SHA256 sign ``path`` with ``key``; return sig dict."""
    if not isinstance(key, (bytes, bytearray)) or not key:
        raise ValueError("key must be non-empty bytes")
    with open(path, "rb") as f:
        data = f.read()
    digest = hmac.new(bytes(key), data, "sha256").hexdigest()
    return {"algo": "hmac-sha256", "hex": digest}


def verify_file(path: str, key: bytes, sig: dict) -> bool:
    """Constant-time verify of a sig dict against ``path`` + ``key``."""
    if not isinstance(sig, dict) or sig.get("algo") != "hmac-sha256":
        return False
    expected = sig.get("hex")
    if not isinstance(expected, str) or not expected:
        return False
    try:
        actual = sign_file(path, key)["hex"]
    except (OSError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HMAC-SHA256 artifact signer")
    parser.add_argument("file", help="file to sign/verify")
    parser.add_argument("--verify", metavar="HEX", default=None,
                        help="verify against this hex digest instead of signing")
    parser.add_argument("--key-env", default="NIXON_SIGN_KEY",
                        help="env var holding the hex-encoded key (default: NIXON_SIGN_KEY)")
    parser.add_argument("--key-hex", default=None,
                        help="hex-encoded key (overrides --key-env; testing only)")
    args = parser.parse_args(argv)
    if args.key_hex is not None:
        key = bytes.fromhex(args.key_hex)
    else:
        raw = os.environ.get(args.key_env, "")
        if not raw:
            parser.error(f"set --key-hex or env {args.key_env} with hex-encoded key")
            return 2
        key = bytes.fromhex(raw)
    if args.verify is None:
        sig = sign_file(args.file, key)
        sys.stdout.write(sig["hex"] + "\n")
        return 0
    ok = verify_file(args.file, key, {"algo": "hmac-sha256", "hex": args.verify})
    sys.stdout.write("OK\n" if ok else "FAIL\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
