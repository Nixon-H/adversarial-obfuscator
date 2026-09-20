"""
certificates/collector.py

Purpose:
Collects certificates generated during an obfuscation pipeline run and emits
them as individual JSON files plus a combined certificate_chain.json.

Security Relevance:
The collector is the recording layer. If it drops certificates or computes
hashes incorrectly, the resulting chain will not validate. All certificates
should be collected before any transformation that could modify the pipeline
state.

Dependencies:
- scripts.certificates.certificate (Certificate, CertificateChain)
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Any

from .certificate import Certificate, CertificateChain


class CertificateCollector:
    """
    CertificateCollector

    What it does:
    Accumulates certificates from pipeline stages and writes them to disk
    as individual files plus a linked chain.

    Security impact:
    The output_dir must be protected from tampering. An attacker who can
    modify the written certificate files can forge a valid-looking chain.
    """
    def __init__(self, output_dir: str):
        self.certificates: List[Certificate] = []
        self.output_dir = output_dir

    def _compute_hash(self, data: Any) -> str:
        if isinstance(data, str):
            return hashlib.sha256(data.encode("utf-8")).hexdigest()
        if isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        return hashlib.sha256(str(data).encode("utf-8")).hexdigest()

    def record(
        self,
        pass_name: str,
        input_data: Any,
        output_data: Any,
        smt_result: dict,
        duration_ms: float,
    ) -> Certificate:
        input_hash = self._compute_hash(input_data)
        output_hash = self._compute_hash(output_data)
        timestamp = datetime.now(timezone.utc).isoformat()
        validated = smt_result.get("equivalent", False)
        cert = Certificate(
            pass_name=pass_name,
            input_hash=input_hash,
            output_hash=output_hash,
            equivalence_proof=smt_result,
            duration_ms=duration_ms,
            timestamp=timestamp,
            validated=validated,
        )
        self.certificates.append(cert)
        return cert

    def emit_all(self):
        os.makedirs(self.output_dir, exist_ok=True)
        for i, cert in enumerate(self.certificates):
            fname = f"cert_{i:04d}_{cert.pass_name}.json"
            fpath = os.path.join(self.output_dir, fname)
            with open(fpath, "w") as f:
                f.write(cert.to_json())
        chain = CertificateChain(certificates=self.certificates)
        chain.validate_chain()
        chain_path = os.path.join(self.output_dir, "certificate_chain.json")
        with open(chain_path, "w") as f:
            f.write(chain.to_json())
