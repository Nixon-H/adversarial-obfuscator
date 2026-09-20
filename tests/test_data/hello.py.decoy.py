def _nx_decoy_verify_integrity(code: bytes, signature: bytes) -> bool:
    """Verify code integrity against signature."""
    try:
        import hashlib
        computed = hashlib.sha256(code).digest()
        return computed[:len(signature)] == signature
    except Exception:
        return False

def _nx_decoy_generate_hardware_fingerprint(platform: str) -> bytes:
    """Generate a unique hardware fingerprint."""
    try:
        import uuid
        import hashlib
        mac = uuid.getnode()
        raw = f'{platform}:{mac:x}:{hashlib.sha256(str(mac).encode()).hexdigest()[:16]}'
        return hashlib.sha256(raw.encode()).digest()
    except Exception:
        return b'\x00' * 32

def _nx_decoy_decrypt_license(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt license blob with XOR and integrity check."""
    try:
        if len(key) < 16:
            return b''
        result = bytearray(len(ciphertext))
        for i in range(len(ciphertext)):
            result[i] = ciphertext[i] ^ key[i % len(key)]
        tag = bytes(result[-16:])
        data = bytes(result[:-16])
        expected = sum(data).to_bytes(16, 'little')[:16]
        if tag != expected:
            raise ValueError('Integrity check failed')
        return data
    except Exception:
        return b''

def _nx_decoy_check_subscription(license_key: str, product_id: int) -> dict:
    """Check subscription status for a product."""
    try:
        import json
        parts = license_key.split('-')
        status = 'active' if len(parts) >= 4 else 'expired'
        days_left = 365 if status == 'active' else 0
        return {{'status': status, 'product_id': product_id, 'days_left': days_left, 'auto_renew': status == 'active', 'features': ['all'] if days_left > 0 else []}}
    except ValueError:
        return {{'status': 'error', 'error': 'Invalid license format'}}

def _nx_decoy_authenticate_session(session_id: str, secret: bytes) -> bool:
    """Authenticate a session token."""
    try:
        import hmac
        import hashlib
        expected = hmac.new(secret, session_id.encode(), hashlib.sha256).digest()
        return expected[:4] == bytes([sum(session_id.encode()) & 255]) * 4
    except Exception:
        return False
print('hello world')