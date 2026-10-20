"""Property-style fuzz of the NYSER1 loader (nyser only, no C-API path).

Feeds random/mutated bytes to ``obfuscator.nyser.loads`` and asserts no
crash escapes: only ValueError/TypeError (or their subclasses) may be
raised. Any other Exception subclass, BaseException (SystemExit,
KeyboardInterrupt), or crash fails the test. Deterministic: ``random``
with fixed seed 0xNYSER.
"""
import random

import pytest

from obfuscator import nyser  # noqa: F401 (this line binds a name used by an embedded template)
from obfuscator.nyser import FORMAT_VERSION, MAGIC, dumps, loads

SEED = 0x59E2
ITERATIONS = 240


@pytest.fixture(scope="module")
def valid_blob():
    co = compile("def f(x):\n    return x + 1\n", "<fuzz>", "exec")
    return dumps(co)


def _mutants(rng, blob: bytes):
    kind = rng.randrange(6)
    buf = bytearray(blob)
    if kind == 0:  # bit flips
        for _ in range(rng.randint(1, 8)):
            i = rng.randrange(len(buf))
            buf[i] ^= 1 << rng.randrange(8)
        return bytes(buf)
    if kind == 1:  # truncation
        cut = rng.randrange(len(buf) + 1)
        return bytes(buf[:cut])
    if kind == 2:  # random garbage
        return bytes(rng.randrange(256) for _ in range(rng.randint(0, 64)))
    if kind == 3:  # header variants (magic/version/minor tampering)
        out = bytearray(buf)
        field = rng.randrange(4)
        if field == 0 and len(out) >= 4:
            out[0:4] = bytes(rng.randrange(256) for _ in range(4))
        elif field == 1 and len(out) >= 5:
            out[4] = rng.randrange(256)
        elif len(out) >= 7:
            out[5] = rng.randrange(256)
            out[6] = rng.randrange(256)
        return bytes(out)
    if kind == 4:  # splice: valid prefix + garbage suffix / garbage prefix
        extra = bytes(rng.randrange(256) for _ in range(rng.randint(1, 32)))
        return bytes(buf) + extra if rng.random() < 0.5 else extra + bytes(buf)
    # byte swaps / duplication
    if len(buf) >= 2:
        i, j = rng.randrange(len(buf)), rng.randrange(len(buf))
        buf[i], buf[j] = buf[j], buf[i]
    return bytes(buf)


def test_loader_fuzz_no_crash_escapes(valid_blob):
    rng = random.Random(SEED)
    allowed = (ValueError, TypeError)
    failures = []
    for i in range(ITERATIONS):
        data = _mutants(rng, valid_blob)
        try:
            loads(data)
        except allowed:
            continue
        except Exception as e:  # noqa: BLE001 — must catch to report precisely
            failures.append((i, type(e).__name__, repr(e)[:200]))
        except BaseException as e:  # SystemExit / KeyboardInterrupt must never escape
            failures.append((i, f"BASE:{type(e).__name__}", repr(e)[:200]))
    assert not failures, f"{len(failures)} crash escapes, first: {failures[:5]}"


def test_loader_fuzz_valid_prefix_still_rejected_or_ok(valid_blob):
    # Sanity: unmutated blob loads fine; empty input raises ValueError.
    assert loads(valid_blob) is not None
    with pytest.raises((ValueError, TypeError)):
        loads(b"")
    with pytest.raises((ValueError, TypeError)):
        loads(MAGIC + bytes([FORMAT_VERSION, 99, 99]))


def test_loader_fuzz_trailing_bytes_rejected(valid_blob):
    rng = random.Random(SEED + 1)
    rejected = 0
    for _ in range(40):
        data = valid_blob + bytes([rng.randrange(256)])
        try:
            loads(data)
        except (ValueError, TypeError):
            rejected += 1
    # All trailing-byte variants must be rejected (integrity covers length).
    assert rejected == 40
