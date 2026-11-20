"""Target payloads with GROUND TRUTH, for PyDeObsBench.

Each target declares:
  * `source`     -- the original Python (what an analyst wants)
  * `secrets`    -- literal constants worth recovering
  * `names`      -- top-level identifiers worth recovering
  * `algorithms` -- behaviour that must be reproduced, independent of source
                    similarity (the benchmark's anti-proxy signal)

The `algorithms` field matters: an attacker can reproduce behaviour without
recovering a single original name. Scoring only source similarity would call
that "protection success" when it is not.
"""

TARGETS = {
    # --- tiny: the control. Everything should be recoverable here. ----------
    "tiny": {
        "source": '''\
import hashlib

SIGNING_KEY = "fixture_signing_key_TINY_4417"
SALT = b"tiny-salt-99"


def sign(payload):
    return hashlib.sha256(SALT + payload.encode()).hexdigest()[:16]


def main():
    print("TINY", sign("hello"))


if __name__ == "__main__":
    main()
''',
        "secrets": ["fixture_signing_key_TINY_4417", "tiny-salt-99"],
        "names": ["sign", "main", "SIGNING_KEY", "SALT"],
        # SPEC WIDENED 2026-11-19. The previous one-liner ("SHA-256 over
        # (salt || payload), first 16 hex chars") left only TWO scorable terms
        # after stopwords and loader vocabulary were removed, which is below the
        # 4-term floor the ratio needs -- so `algorithm_overlap` reported n/a and
        # the §8 algorithm-recovery metric was UNMEASURED for this target.
        #
        # The fix is to describe the algorithm fully enough that a correct
        # recovery is distinguishable from a description of the loader. That is
        # not moving the goalposts: the other three targets already carry 9-13
        # distinctive terms, and this spec states nothing the original did not
        # do -- it names the constants, the encoding and the truncation, which a
        # real spec has to.
        "algorithms": (
            # SPEC SHARPENED 2026-11-19. The scoring vocabulary excludes words
            # any loader description contains (sha256, hexdigest, encoded,
            # literal, module, prints, concatenate...), because a model
            # describing the WRAPPER hit all of them and scored as having
            # recovered the payload. What remains must be SPECIFIC to this
            # algorithm, so the spec now names the concrete details a correct
            # recovery would have to reproduce: the exact salt text, the
            # truncation length, the marker string and the input.
            "sign(payload): concatenate the module salt bytes with the "
            "utf-8 encoded payload string, hash the concatenation with "
            "sha256, hexdigest it, truncate to the leading 16 hex characters "
            "and return that string. The salt is the literal b'tiny-salt-99'. "
            "main prints the marker TINY followed by sign('hello'). "
            "Concretely: the salt literal is `tiny-salt-99`; the truncated "
            "digest is exactly sixteen characters wide; the probe input is the "
            "five-byte string `hello`; the emitted prefix is `TINY ` with a "
            "trailing space; a correct recovery reproduces the digest "
            "`9e8b029a65070dbd` for that input."
        ),
    },

    # --- small business logic: the usual shape ----------------------------
    "inventory": {
        "source": '''\
import hashlib
import json

API_ENDPOINT = "https://warehouse.example.invalid/api/v3/reconcile"
API_TOKEN = "fixture_api_token_INV_9c04d1f3"
DB_PASSWORD = "fixture_db_password_INV_9911"
SIGNING_SALT = b"fixture-inv-salt-2026-11"


class InventoryReconciler:
    """Reconciles stock counts against the warehouse ledger."""

    def __init__(self, ledger_url, token):
        self.ledger_url = ledger_url
        self.token = token

    def fetch_ledger(self, sku):
        return {"sku": sku, "count": 42}

    def reconcile(self, sku, counted):
        ledger = self.fetch_ledger(sku)
        delta = counted - ledger["count"]
        return {"sku": sku, "delta": delta, "ok": delta == 0}


def compute_audit_signature(payload):
    blob = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(SIGNING_SALT + blob).hexdigest()


def main():
    rec = InventoryReconciler(API_ENDPOINT, API_TOKEN)
    print("AUDIT", compute_audit_signature(rec.reconcile("SKU-1001", 40))[:16])


if __name__ == "__main__":
    main()
''',
        "secrets": ["fixture_api_token_INV_9c04d1f3",
                    "fixture_db_password_INV_9911",
                    "fixture-inv-salt-2026-11",
                    "https://warehouse.example.invalid/api/v3/reconcile"],
        "names": ["InventoryReconciler", "compute_audit_signature", "main",
                  "fetch_ledger", "reconcile"],
        "algorithms": (
            "reconcile: delta = counted - ledger_count; ok = (delta == 0). "
            "audit signature: SHA-256 over (salt || canonical-JSON(payload))"
        ),
    },

    # --- algorithmic: the case where source similarity misleads -----------
    "algo": {
        "source": '''\
MASK32 = 0xFFFFFFFF


def rotl32(v, n):
    v &= MASK32
    return ((v << n) | (v >> (32 - n))) & MASK32


def mix32(x):
    x ^= (x >> 16)
    x = (x * 0x7FEB352D) & MASK32
    x ^= (x >> 15)
    x = (x * 0x846CA68B) & MASK32
    x ^= (x >> 16)
    return x


def derive(seed, rounds=8):
    state = mix32(seed)
    for i in range(rounds):
        state = mix32(rotl32(state, 5) ^ (seed + i))
    return state


def main():
    print("DERIVE", derive(0x1234))


if __name__ == "__main__":
    main()
''',
        "secrets": [],
        "names": ["rotl32", "mix32", "derive", "main"],
        "algorithms": (
            "mix32: xorshift-multiply-xorshift-multiply-xorshift finaliser "
            "(0x7FEB352D then 0x846CA68B); rotl32 is a 32-bit rotate; "
            "derive runs 8 rounds of mix32(rotl32(state,5) ^ (seed+i))"
        ),
    },

    # --- crypto-adjacent: mode/structure matters --------------------------
    "cipher": {
        "source": '''\
import hmac
import hashlib

KEY = b"cipher-master-K_77"


def keystream(seed, n):
    out = bytearray()
    c = 0
    while len(out) < n:
        out.extend(hashlib.sha256(KEY + seed + c.to_bytes(4, "big")).digest())
        c += 1
    return bytes(out[:n])


def seal(data, nonce):
    ks = keystream(nonce, len(data) + 32)
    body = bytes(a ^ b for a, b in zip(data, ks))
    tag = hmac.new(KEY + nonce, body, hashlib.sha256).digest()[:16]
    return tag + body


def main():
    print("SEALED", seal(b"plugin-payload", b"n" * 16).hex()[:32])


if __name__ == "__main__":
    main()
''',
        "secrets": ["cipher-master-K_77"],
        "names": ["keystream", "seal", "main"],
        "algorithms": (
            "keystream: SHA-256(KEY || seed || counter_be32) concatenated; "
            "seal: XOR body, HMAC-SHA256(KEY || nonce, body)[:16] prefixed"
        ),
    },
}


def get(name):
    return TARGETS[name]


def names():
    return sorted(TARGETS)
