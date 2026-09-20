"""
verifier/binary_reader.py

Purpose:
Extracts/injects proof certificate sections from binary files. Proof data
is stored as base64-encoded blobs delimited by markers
(__NIXON_PROOF_BEGIN__ / __NIXON_PROOF_END__) appended to the binary.

Security Relevance:
The binary reader is the extraction interface. If it fails to find a proof
section (or finds the wrong one), verification will incorrectly fail or
pass. The three search strategies (marker, begin/end markers, regex)
provide defense-in-depth against minor format variations.

Dependencies:
- base64 (encoding)
"""
from __future__ import annotations

import base64
import os
import re
from typing import Optional


class BinaryReader:
    """
    BinaryReader

    What it validates:
    That a proof section exists in the binary and can be decoded.

    Security impact:
    If extraction silently returns garbage (e.g., wrong marker, truncated
    base64), the verifier will either reject a valid binary or accept an
    invalid proof.

    Failure mode:
    ValueError("No proof section found") — safe rejection.
    base64.b64decode error — caught as ValueError, safe rejection.
    """
    PROOF_MARKER = b"__NIXON_PROOF__"
    PROOF_START = b"__NIXON_PROOF_BEGIN__"
    PROOF_END = b"__NIXON_PROOF_END__"

    def extract_proof_section(self, binary_path: str) -> bytes:
        with open(binary_path, "rb") as f:
            data = f.read()
        start = data.find(self.PROOF_MARKER)
        if start >= 0:
            after = data[start + len(self.PROOF_MARKER):]
            proof_b64 = after.split(b"\n")[0].strip()
            return base64.b64decode(proof_b64)
        start = data.find(self.PROOF_START)
        end = data.find(self.PROOF_END)
        if start >= 0 and end > start:
            proof_b64 = data[start + len(self.PROOF_START):end].strip()
            return base64.b64decode(proof_b64)
        try:
            text = data.decode("utf-8", errors="ignore")
            m = re.search(r"#\s*__NIXON_PROOF__\s*:\s*([A-Za-z0-9+/=]+)", text)
            if m:
                return base64.b64decode(m.group(1))
        except Exception:
            pass
        raise ValueError(f"No proof section found in {binary_path}")

    def inject_proof_section(self, binary_path: str, proof_data: bytes):
        proof_b64 = base64.b64encode(proof_data).decode("ascii")
        marker = self.PROOF_START.decode("ascii")
        end = self.PROOF_END.decode("ascii")
        payload = f"\n# {marker}:{proof_b64}:{end}\n"
        with open(binary_path, "ab") as f:
            f.write(payload.encode("ascii"))
