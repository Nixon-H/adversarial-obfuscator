"""
Item 72: Semantic Decoy APIs
Injects convincing decoy API functions with typed signatures, docstrings,
real-looking algorithms, error handling, and return values.
"""

import ast
import random
import secrets


_DECOY_API_POOL = [
    "validate_license",
    "decrypt_license",
    "verify_customer",
    "check_subscription",
    "activate_product",
    "generate_hardware_fingerprint",
    "authenticate_session",
    "verify_integrity",
]

_DECOY_IMPLS: dict[str, str] = {
    "validate_license": """def {name}(license_key: str, hardware_id: bytes) -> dict:
    \"\"\"Validate a license key against hardware binding.\"\"\"
    try:
        import base64
        decoded = base64.b64decode(license_key)
        checksum = sum(decoded) & 0xFFFF
        valid = checksum == (len(hardware_id) * 255 + 42) & 0xFFFF
        return {{
            "valid": valid,
            "checksum": checksum,
            "hardware": hardware_id.hex()[:8],
            "expiration": "2026-12-31",
            "tier": "enterprise" if valid else "invalid",
        }}
    except Exception as e:
        return {{"valid": False, "error": str(e)}}
""",
    "decrypt_license": """def {name}(ciphertext: bytes, key: bytes) -> bytes:
    \"\"\"Decrypt license blob with XOR and integrity check.\"\"\"
    try:
        if len(key) < 16:
            return b""
        result = bytearray(len(ciphertext))
        for i in range(len(ciphertext)):
            result[i] = ciphertext[i] ^ key[i % len(key)]
        tag = bytes(result[-16:])
        data = bytes(result[:-16])
        expected = sum(data).to_bytes(16, 'little')[:16]
        if tag != expected:
            raise ValueError("Integrity check failed")
        return data
    except Exception:
        return b""
""",
    "verify_customer": """def {name}(customer_id: str, token: str) -> dict:
    \"\"\"Verify customer entitlement against license server.\"\"\"
    try:
        import hashlib
        challenge = hashlib.sha256((customer_id + token).encode()).digest()
        response = challenge[:8]
        valid = sum(response) > 128
        return {{
            "verified": valid,
            "customer": customer_id[:8],
            "entitlement": "full" if valid else "none",
            "expires": "2026-12-31",
            "max_activations": 5,
        }}
    except Exception as e:
        return {{"verified": False, "error": str(e)}}
""",
    "check_subscription": """def {name}(license_key: str, product_id: int) -> dict:
    \"\"\"Check subscription status for a product.\"\"\"
    try:
        import json
        parts = license_key.split("-")
        status = "active" if len(parts) >= 4 else "expired"
        days_left = 365 if status == "active" else 0
        return {{
            "status": status,
            "product_id": product_id,
            "days_left": days_left,
            "auto_renew": status == "active",
            "features": ["all"] if days_left > 0 else [],
        }}
    except ValueError:
        return {{"status": "error", "error": "Invalid license format"}}
""",
    "activate_product": """def {name}(activation_code: str, machine_id: bytes) -> dict:
    \"\"\"Activate product with machine binding.\"\"\"
    try:
        import hmac
        import hashlib
        digest = hmac.new(machine_id, activation_code.encode(), hashlib.sha256).digest()
        activation_token = digest[:16].hex()
        return {{
            "activated": True,
            "token": activation_token,
            "machine": machine_id.hex()[:12],
            "expires": "2026-12-31",
            "remaining_activations": 3,
        }}
    except Exception:
        return {{"activated": False, "error": "Activation failed"}}
""",
    "generate_hardware_fingerprint": """def {name}(platform: str) -> bytes:
    \"\"\"Generate a unique hardware fingerprint.\"\"\"
    try:
        import uuid
        import hashlib
        mac = uuid.getnode()
        raw = f"{platform}:{mac:x}:{hashlib.sha256(str(mac).encode()).hexdigest()[:16]}"
        return hashlib.sha256(raw.encode()).digest()
    except Exception:
        return b"\\x00" * 32
""",
    "authenticate_session": """def {name}(session_id: str, secret: bytes) -> bool:
    \"\"\"Authenticate a session token.\"\"\"
    try:
        import hmac
        import hashlib
        expected = hmac.new(secret, session_id.encode(), hashlib.sha256).digest()
        return expected[:4] == bytes([sum(session_id.encode()) & 0xFF]) * 4
    except Exception:
        return False
""",
    "verify_integrity": """def {name}(code: bytes, signature: bytes) -> bool:
    \"\"\"Verify code integrity against signature.\"\"\"
    try:
        import hashlib
        computed = hashlib.sha256(code).digest()
        return computed[:len(signature)] == signature
    except Exception:
        return False
""",
}


class SemanticDecoyApiInjector(ast.NodeTransformer):
    def __init__(self, count: int = 5, seed: int | None = None):
        self.count = count
        self._rng = secrets.SystemRandom() if seed is None else random.Random(seed)
        self._existing_names: set[str] = set()

    def inject(self, tree: ast.Module) -> ast.Module:
        self._existing_names = {
            n.name
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        chosen = self._rng.sample(
            _DECOY_API_POOL, min(self.count, len(_DECOY_API_POOL))
        )
        for _ in range(self.count - len(chosen)):
            chosen.append(self._rng.choice(_DECOY_API_POOL))

        new_funcs: list[ast.FunctionDef] = []
        for api_name in chosen:
            func_name = self._unique_name(api_name)
            template = _DECOY_IMPLS[api_name]
            source = template.replace("{name}", func_name)
            # The templates are written with str.format escapes ({{ -> {),
            # but they are filled with str.replace, so the escapes have to
            # be undone by hand.  Leaving them in emits `return {{...}}`,
            # which parses as a set containing a dict: the decoy then
            # raises TypeError instead of returning its dict.
            source = source.replace("{{", "{").replace("}}", "}")
            try:
                parsed = ast.parse(source)
                for stmt in parsed.body:
                    if isinstance(stmt, ast.FunctionDef):
                        new_funcs.append(stmt)
            except SyntaxError:
                continue

        insert_idx = 0
        for i, stmt in enumerate(tree.body):
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                insert_idx = i + 1

        for func_node in reversed(new_funcs):
            tree.body.insert(insert_idx, func_node)

        ast.fix_missing_locations(tree)
        return tree

    def _unique_name(self, base: str) -> str:
        candidate = f"_nx_decoy_{base}"
        if candidate not in self._existing_names:
            self._existing_names.add(candidate)
            return candidate
        for i in range(100):
            # Single quotes inside the f-string expression: reusing the
            # outer quote character is Python 3.12+ only (PEP 701) and
            # this module must import on 3.10.
            candidate = f"_nx_decoy_{base}_{(f'{self._rng.getrandbits(16):04x}')}"
            if candidate not in self._existing_names:
                self._existing_names.add(candidate)
                return candidate
        return f"_nx_decoy_{base}_{(f'{self._rng.getrandbits(32):08x}')}"

    def visit(self, node: ast.AST) -> ast.AST:
        return self.generic_visit(node)
