"""
certificates/__main__

Purpose:
CLI entry point for certificate generation and verification. Supports three
commands:
  - generate: Build a certificate chain from a list of pass names and input.
  - verify: Validate a certificate chain JSON file.
  - verify-passes: Build and validate a chain from pass descriptions.

Security Relevance:
The CLI is the primary user interface for interacting with the certificate
system. It must correctly serialize/deserialize and validate chains.

Usage:
  python -m scripts.certificates generate --passes p1 p2 --input "src"
  python -m scripts.certificates verify chain.json
  python -m scripts.certificates verify-passes --passes p1 p2 --input "src"

Dependencies:
- scripts.certificates.certificate (Certificate, CertificateChain)
"""
from __future__ import annotations

import argparse
import json
import sys

from .certificate import CertificateChain, emit_certificate


def main() -> None:
    parser = argparse.ArgumentParser(description="Certificate generation & verification tool")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a certificate chain from pass descriptions")
    gen.add_argument("--passes", nargs="+", required=True,
                     help="Pass names, e.g. --passes pass1 pass2 pass3")
    gen.add_argument("--input", required=True, help="Initial input text")
    gen.add_argument("--output-json", help="Write chain to file instead of stdout")

    verify = sub.add_parser("verify", help="Verify a certificate chain JSON file")
    verify.add_argument("chain_file", help="Path to certificate_chain.json")

    verify_passes = sub.add_parser("verify-passes",
                                   help="Verify a chain built from sequential pass descriptions")
    verify_passes.add_argument("--passes", nargs="+", required=True,
                               help="Pass names, e.g. --passes pass1 pass2 pass3")
    verify_passes.add_argument("--input", required=True, help="Initial input text")

    args = parser.parse_args()

    if args.command == "generate":
        _do_generate(args)
    elif args.command == "verify":
        _do_verify(args)
    elif args.command == "verify-passes":
        _do_verify_passes(args)


def _do_generate(args: argparse.Namespace) -> None:
    text = args.input
    certs = []
    for idx, pname in enumerate(args.passes):
        next_text = f"{pname}({text})"
        cert = emit_certificate(pname, text, next_text, {"equivalent": True}, 1.0)
        certs.append(cert)
        text = next_text
    chain = CertificateChain(certificates=certs)
    chain.validate_chain()
    output = chain.to_json()
    if args.output_json:
        with open(args.output_json, "w") as f:
            f.write(output)
    else:
        print(output)


def _do_verify(args: argparse.Namespace) -> None:
    with open(args.chain_file) as f:
        chain = CertificateChain.from_json(f.read())
    valid = chain.validate_chain()
    if not valid:
        print(json.dumps({"valid": False, "chain_validated": False}, indent=2))
        sys.exit(1)
    print(json.dumps({"valid": True, "chain_validated": chain.chain_validated}, indent=2))


def _do_verify_passes(args: argparse.Namespace) -> None:
    text = args.input
    certs = []
    for idx, pname in enumerate(args.passes):
        next_text = f"{pname}({text})"
        cert = emit_certificate(pname, text, next_text, {"equivalent": True}, 1.0)
        certs.append(cert)
        text = next_text
    chain = CertificateChain(certificates=certs)
    valid = chain.validate_chain()
    if not valid:
        print(json.dumps({"valid": False, "chain_validated": False}, indent=2))
        sys.exit(1)
    print(json.dumps({"valid": True, "chain_validated": chain.chain_validated}, indent=2))


if __name__ == "__main__":
    main()
