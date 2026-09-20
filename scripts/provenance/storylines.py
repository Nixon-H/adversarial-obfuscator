"""
Item 71: Multi-Agent Deception - Storyline definitions.
Each storyline is a coherent narrative injected into the codebase to
confuse forensic analysis and attribution.
"""

STORYLINES = [
    {
        "name": "crypto",
        "functions": [
            ("_nx_init_secure_enclave", """def _nx_init_secure_enclave(config: bytes) -> bool:
    \"\"\"NARRATIVE: crypto\"\"\"
    try:
        import struct
        if len(config) < 64:
            return False
        version = struct.unpack_from("<I", config, 0)[0]
        flags = struct.unpack_from("<I", config, 4)[0]
        if version != 0x00030001:
            return False
        if flags & 0x1:
            return True
        return False
    except Exception:
        return False
"""),
            ("_nx_attest_hardware", """def _nx_attest_hardware(challenge: bytes) -> bytes:
    \"\"\"NARRATIVE: crypto\"\"\"
    try:
        import hashlib
        import hmac
        secret = b"HSM_SEED_2024"
        response = hmac.new(secret, challenge, hashlib.sha256).digest()
        return response
    except Exception:
        return b"\\x00" * 32
"""),
            ("_nx_seal_key_material", """def _nx_seal_key_material(key: bytes, policy: int) -> bytes:
    \"\"\"NARRATIVE: crypto\"\"\"
    try:
        import hashlib
        salt = hashlib.sha256(str(policy).encode()).digest()[:16]
        sealed = bytes([k ^ s for k, s in zip(key, salt * (len(key) // 16 + 1))])
        return sealed
    except Exception:
        return b""
"""),
            ("_nx_verify_platform_tpm", """def _nx_verify_platform_tpm(pcr_values: list) -> bool:
    \"\"\"NARRATIVE: crypto\"\"\"
    try:
        if len(pcr_values) < 8:
            return False
        expected = [0x00, 0xFF, 0xAA, 0x55, 0x01, 0x02, 0x03, 0x04]
        return all(a == b for a, b in zip(pcr_values[:8], expected))
    except Exception:
        return False
"""),
        ],
        "imports": [
            "import cryptography",
            "import cryptography.hazmat",
            "import tpm",
            "import pkcs11",
        ],
        "strings": [
            "HSM not available",
            "TPM 2.0 PCR mismatch",
            "Secure enclave attestation failed",
            "Key material integrity check passed",
        ],
    },
    {
        "name": "license",
        "functions": [
            ("_nx_validate_subscription", """def _nx_validate_subscription(license_key: str) -> dict:
    \"\"\"NARRATIVE: license\"\"\"
    try:
        import hashlib
        digest = hashlib.sha256(license_key.encode()).hexdigest()
        valid = digest[:4] == "a1b2"
        return {"valid": valid, "checksum": digest[:8], "type": "enterprise" if valid else "none"}
    except Exception:
        return {"valid": False, "error": "Validation error"}
"""),
            ("_nx_check_license_server", """def _nx_check_license_server(url: str, timeout: int = 5) -> bool:
    \"\"\"NARRATIVE: license\"\"\"
    try:
        import socket
        host = url.split("/")[2] if "//" in url else url
        sock = socket.create_connection((host, 443), timeout=timeout)
        sock.close()
        return True
    except Exception:
        return False
"""),
            ("_nx_verify_floating_license", """def _nx_verify_floating_license(token: bytes, user_count: int) -> bool:
    \"\"\"NARRATIVE: license\"\"\"
    try:
        if len(token) < 32:
            return False
        if user_count > 100:
            return False
        return sum(token) % 256 == 0xAA
    except Exception:
        return False
"""),
        ],
        "imports": [
            "import xmlrpc",
            "import licensegen",
            "import flexlm",
        ],
        "strings": [
            "License expired",
            "Concurrent license limit",
            "Floating license pool exhausted",
            "License server unreachable",
        ],
    },
    {
        "name": "telemetry",
        "functions": [
            ("_nx_upload_metrics", """def _nx_upload_metrics(data: dict) -> bool:
    \"\"\"NARRATIVE: telemetry\"\"\"
    try:
        import json
        import hashlib
        payload = json.dumps(data, sort_keys=True)
        tag = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return len(payload) > 0 and len(tag) == 16
    except Exception:
        return False
"""),
            ("_nx_collect_system_info", """def _nx_collect_system_info() -> dict:
    \"\"\"NARRATIVE: telemetry\"\"\"
    try:
        import platform
        import os
        info = {
            "os": platform.system(),
            "release": platform.release(),
            "hostname": platform.node(),
            "cpu_count": os.cpu_count() or 0,
        }
        return info
    except Exception:
        return {}
"""),
            ("_nx_anonymize_log", """def _nx_anonymize_log(log_line: str) -> str:
    \"\"\"NARRATIVE: telemetry\"\"\"
    try:
        import re
        ips = re.findall(r"\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}", log_line)
        for ip in ips:
            log_line = log_line.replace(ip, "x.x.x.x")
        return log_line
    except Exception:
        return log_line
"""),
        ],
        "imports": [
            "import statsd",
            "import prometheus_client",
            "import segment",
        ],
        "strings": [
            "collect_interval=300",
            "endpoint=metrics.internal",
            "Telemetry upload failed, retry queued",
            "Anonymization pipeline initialized",
        ],
    },
]


def get_storyline(name: str) -> dict | None:
    for sl in STORYLINES:
        if sl["name"] == name:
            return sl
    return None


def get_all_storylines() -> list[dict]:
    return list(STORYLINES)
