"""Payload covering the constructs the demo does not: async, generators, dataclasses,
match, decorators with arguments, walrus, except*, descriptors, closures, comprehensions.

Prints a deterministic result so a build can be compared against its source.
"""
import asyncio
import dataclasses
import functools

def _nx_decoy_activate_product(activation_code: str, machine_id: bytes) -> dict:
    """Activate product with machine binding."""
    try:
        import hmac
        import hashlib
        digest = hmac.new(machine_id, activation_code.encode(), hashlib.sha256).digest()
        activation_token = digest[:16].hex()
        return {'activated': True, 'token': activation_token, 'machine': machine_id.hex()[:12], 'expires': '2026-12-31', 'remaining_activations': 3}
    except Exception:
        return {'activated': False, 'error': 'Activation failed'}

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

def _nx_decoy_validate_license(license_key: str, hardware_id: bytes) -> dict:
    """Validate a license key against hardware binding."""
    try:
        import base64
        decoded = base64.b64decode(license_key)
        checksum = sum(decoded) & 65535
        valid = checksum == len(hardware_id) * 255 + 42 & 65535
        return {'valid': valid, 'checksum': checksum, 'hardware': hardware_id.hex()[:8], 'expiration': '2026-12-31', 'tier': 'enterprise' if valid else 'invalid'}
    except Exception as e:
        return {'valid': False, 'error': str(e)}

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

def _nx_decoy_verify_integrity(code: bytes, signature: bytes) -> bool:
    """Verify code integrity against signature."""
    try:
        import hashlib
        computed = hashlib.sha256(code).digest()
        return computed[:len(signature)] == signature
    except Exception:
        return False

class Descriptor:

    def __init__(self):
        self._value = 0

    def __get__(self, obj, objtype=None):
        return self._value

    def __set__(self, obj, value):
        self._value = value

class Holder:
    slot = Descriptor()

@dataclasses.dataclass
class Point:
    x: int
    y: int

    def norm(self):
        return (self.x * self.x + self.y * self.y) ** 0.5

def cached(fn):
    store = {}

    @functools.wraps(fn)
    def wrapper(*args):
        if args not in store:
            store[args] = fn(*args)
        return store[args]
    return wrapper

@cached
def slow_square(n):
    return n * n

def evens(limit):
    for n in range(limit):
        if n % 2 == 0:
            yield n

def classify(point):
    match point:
        case Point(x=0, y=0):
            return 'origin'
        case Point(x=0):
            return 'on-y'
        case Point(y=0):
            return 'on-x'
        case Point():
            return 'somewhere'
        case _:
            return 'other'

def walrus_count(values):
    n = 0
    while (chunk := values[n:n + 2]) != []:
        n += 2
    return n

def eg_sum(values):
    result = 0
    try:
        if not values:
            raise ValueError('empty')
        result = sum(values)
    except* ValueError:
        result = 0
    return result

def make_counter():
    count = 0

    def bump():
        nonlocal count
        count += 1
        return count
    return bump

async def deliver(values):
    await asyncio.sleep(0)
    return sorted(values, reverse=True)

def main():
    holder = Holder()
    holder.slot = 7
    print('descriptor:', holder.slot)
    print('squares:', [slow_square(n) for n in range(5)])
    print('evens:', list(evens(9)))
    print('match:', [classify(p) for p in (Point(0, 0), Point(0, 3), Point(4, 0), Point(2, 2))])
    print('walrus:', walrus_count([1, 2, 3, 4, 5]))
    print('except-star:', eg_sum([1, 2, 3]), eg_sum([]))
    bump = make_counter()
    bump()
    bump()
    print('closure:', bump())
    print('dataclass:', Point(3, 4).norm())
    print('async:', asyncio.run(deliver([3, 1, 2])))
    print('OK')
main()