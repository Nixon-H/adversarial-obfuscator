"""
verifier/__main__

Purpose:
CLI entry point for the proof-carrying obfuscation verifier. Takes a binary
with embedded proofs, extracts the certificate chain, validates it, and
prints the result.

Security Relevance:
This is the user-facing verification tool. It should be the only interface
that external parties use to check proof validity. The exit code must be
non-zero on verification failure.

Usage:
  python -m scripts.verifier <binary> [--verbose] [--re-verify]

Dependencies:
- scripts.verifier.standalone_verifier
"""

#!/usr/bin/env python3
import argparse
import sys

from scripts.verifier import StandaloneVerifier


def main():
    parser = argparse.ArgumentParser(
        description="Proof-Carrying Obfuscation Verifier"
    )
    parser.add_argument("binary", help="Path to obfuscated binary/script")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    parser.add_argument(
        "--re-verify", action="store_true",
        help="Re-run SMT validation on extracted proofs",
    )
    opts = parser.parse_args()

    verifier = StandaloneVerifier(re_verify_proofs=opts.re_verify)
    result = verifier.verify(opts.binary)

    if result.passed:
        print(f"VERIFICATION PASSED: {opts.binary}")
    else:
        print(f"VERIFICATION FAILED: {opts.binary}")
    if opts.verbose:
        print(f"  Certificates: {len(result.certificates)}")
        print(f"  Chain valid:  {result.chain_valid}")
        for err in result.errors:
            print(f"  Error: {err}")
        for cert in result.certificates:
            print(f"    {cert.pass_name}: "
                  f"input={cert.input_hash[:12]}... "
                  f"output={cert.output_hash[:12]}... "
                  f"validated={cert.validated}")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
