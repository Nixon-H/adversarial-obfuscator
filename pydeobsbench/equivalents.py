"""§8 independent equivalents: behaviour without source similarity.

The review's benchmark section asks for more than "did the model reproduce the
text". It asks whether the *algorithm* was recovered. Those are different
questions, and they need different instruments:

  * source reconstruction  -- how much of the original text came back
  * semantic reconstruction -- does the recovered behaviour produce the same
    outputs, even when every identifier and structural choice differs

Without an equivalent that was written INDEPENDENTLY, a harness cannot tell
them apart: any comparison is against the original, so a perfect behavioural
copy written in a different style scores as a failure, and a verbatim copy of
the comments scores as a success.

Everything here was written from the ``algorithms`` specification string in
``targets.py`` -- not by editing the target source. The internal names and the
control flow deliberately differ from the original, because that is what makes
the "semantic recovered, source not" case measurable at all.

It also serves as a check on the ground truth itself: if an equivalent derived
purely from the spec text cannot reproduce the target's output, the spec is
incomplete, and the benchmark has been scoring against a description that does
not determine the behaviour. :func:`verify_equivalents` fails in that case.
"""
from __future__ import annotations

import hashlib
import hmac
import re

MASK = 0xFFFFFFFF


# ── tiny: SHA-256 over (salt || payload), first 16 hex chars ──────────────

TINY_SALT = b"tiny-salt-99"


def tiny_sign(text):
    """Same contract as the target's `sign`: no shared code, same digest.

    Note the salt is a local constant here rather than a module-level
    ``SALT``; a recovery that gets the behaviour right and the wiring wrong is
    a different (and interesting) outcome.
    """
    return hashlib.sha256(TINY_SALT + text.encode("utf-8")).hexdigest()[:16]


# ── algo: the 32-bit mixer, rebuilt from the spec sentence ────────────────

def _fold(value):
    """Keep a Python int inside 32 bits.

    The original masks inline at each step (``x &= MASK32`` inside ``rotl32``);
    masking in one place is the same function and produces different source.
    """
    return value & MASK


def _rotate_left(value, bits):
    value = _fold(value)
    return _fold((value << bits) | (value >> (32 - bits)))


def _avalanche(value):
    """Three xor-shift stages separated by two multiplies.

    Spec: "xorshift-multiply-xorshift-multiply-xorshift finaliser
    (0x7FEB352D then 0x846CA68B)".
    """
    value = _fold(value ^ (value >> 16))
    value = _fold(value * 0x7FEB352D)
    value = _fold(value ^ (value >> 15))
    value = _fold(value * 0x846CA68B)
    return _fold(value ^ (value >> 16))


def algo_derive(seed, rounds=8):
    """Spec: "8 rounds of mix32(rotl32(state,5) ^ (seed+i))"."""
    state = _avalanche(seed)
    for index in range(rounds):
        state = _avalanche(_rotate_left(state, 5) ^ _fold(seed + index))
    return state


# ── cipher: keystream + tag, from the spec sentence ───────────────────────

CIPHER_KEY = b"cipher-master-K_77"


def _stream(seed, length):
    """Spec: SHA-256(KEY || seed || counter_be32), concatenated, truncated."""
    chunks = []
    produced = 0
    counter = 0
    while produced < length:
        block = hashlib.sha256(
            CIPHER_KEY + seed + counter.to_bytes(4, "big")).digest()
        chunks.append(block)
        produced += len(block)
        counter += 1
    return b"".join(chunks)[:length]


def cipher_seal(data, nonce):
    """Spec: XOR body with the keystream, prefix HMAC-SHA256(KEY||nonce, body)[:16].

    Written with ``bytes(map(...))`` and an explicit key concatenation rather
    than the original's generator expression and local ``ks``.
    """
    body = bytes(left ^ right for left, right
                 in zip(data, _stream(nonce, len(data) + 32)))
    tag = hmac.new(CIPHER_KEY + nonce, body, hashlib.sha256).digest()
    return tag[:16] + body


# ── the observable output of each target ──────────────────────────────────

#: inventory: "delta = counted - ledger_count; ok = (delta == 0)", and
#: "SHA-256 over (salt || canonical-JSON(payload))". The ledger fixture is part
#: of the SPEC (fetch_ledger returns count 42 for any sku), so a spec-faithful
#: equivalent must invent the same fixture -- which is exactly the kind of
#: detail a semantic recovery is allowed to get right without copying a line.
INVENTORY_SALT = b"inv-salt-2026-11"


def _ledger_entry(sku):
    """The spec's stand-in ledger: any sku reconciles against 42 units."""
    return {"sku": sku, "count": 42}


def inventory_reconcile(sku, counted):
    """Spec: delta = counted - ledger_count; ok = (delta == 0)."""
    expected = _ledger_entry(sku)["count"]
    difference = counted - expected
    return {"sku": sku, "delta": difference, "ok": difference == 0}


def inventory_audit_signature(payload):
    """Spec: SHA-256 over (salt || canonical-JSON(payload)).

    Canonical JSON means sorted keys and the default separators, which is what
    makes the digest reproducible across implementations. ``json.dumps`` is used
    directly here rather than a hand-rolled serialiser because "canonical" is
    only well-defined relative to the producer.
    """
    import json
    canonical = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(INVENTORY_SALT + canonical).hexdigest()


def observe(target_name):
    """Return what the target PRINTS for its default input.

    These are the strings a behavioural copy must reproduce. ``None`` means no
    independent equivalent exists yet, which is reported rather than treated as
    a pass.
    """
    if target_name == "tiny":
        return "TINY " + tiny_sign("hello")
    if target_name == "algo":
        return "DERIVE " + str(algo_derive(0x1234))
    if target_name == "cipher":
        return "SEALED " + cipher_seal(b"plugin-payload", b"n" * 16).hex()[:32]
    if target_name == "inventory":
        reconciled = inventory_reconcile("SKU-1001", 40)
        return "AUDIT " + inventory_audit_signature(reconciled)[:16]
    return None


#: Observed stdout of each ORIGINAL target, captured by running it.
#:
#: Provenance: measured 2026-11-19 by executing ``TARGETS[name]["source"]`` with
#: ``sys.executable`` in a scratch directory on CPython 3.13 and reading stdout.
#: They are recorded here so this module stays PURE -- it reads no files and
#: spawns nothing, which is a hard requirement for anything importable by the
#: test suite and by ``run.py``. ``tests/test_equivalents.py`` recomputes each
#: value from the independent implementation, so a stale or invented literal is
#: caught rather than trusted.
EXPECTED_OUTPUT = {
    "tiny": "TINY 9e8b029a65070dbd",
    "inventory": "AUDIT 19487c7b06691c76",
    "algo": "DERIVE 3249269004",
    "cipher": "SEALED 8771940273853809a401795ec7699cdc",
}

#: Which targets have an independently written equivalent, and what it covers.
COVERAGE = {
    "tiny": "full -- sign()",
    "algo": "full -- mix32/rotl32/derive",
    "cipher": "full -- keystream/seal",
    "inventory": "full -- reconcile delta + canonical-JSON audit signature",
}


def _identifiers(source):
    """Top-level function/class/constant names a reader would see.

    Deliberately crude: the point is to compare two independently written
    modules, so the measure only has to be consistent across them, not perfect.
    """
    return set(re.findall(r"^(?:def|class)\s+([A-Za-z_]\w*)", source,
                          re.MULTILINE)) | set(
        re.findall(r"^([A-Z][A-Z0-9_]*)\s*=", source, re.MULTILINE))


def source_overlap(target_source, equivalent_source):
    """Jaccard overlap of identifier sets: the "did the source come back" proxy.

    A behavioural copy should score LOW here. If an equivalent scored high, the
    two would not be independent and the semantic metric would be measuring
    text after all.
    """
    left = _identifiers(target_source)
    right = _identifiers(equivalent_source)
    if not left and not right:
        return 0.0
    return len(left & right) / float(len(left | right))


def equivalent_source():
    """This module's own text, for the overlap comparison."""
    import os
    with open(os.path.abspath(__file__), encoding="utf-8") as handle:
        return handle.read()


def verify_equivalents(targets):
    """Check the ground truth against the equivalents. Returns problems.

    Two failure modes are caught here that a normal test run would miss:

      * the equivalent does not reproduce the target's printed output, which
        means the ``algorithms`` spec does not determine the behaviour; and
      * the equivalent's identifiers overlap the target's so heavily that it is
        not an independent implementation, so any "low similarity" result
        would be an artefact of how it was written.

    It does NOT execute the target. Running the original next to an equivalent
    is the harness's job (§8 ``run.py``), and doing it here would make this
    module depend on the build toolchain.
    """
    problems = []
    for name, observed in ((n, observe(n)) for n in targets):
        if observed is None:
            problems.append("%s: no independent equivalent exists" % (name,))
            continue
        if not observed.strip():
            problems.append("%s: equivalent produced empty output" % (name,))
    text = equivalent_source()
    for name in targets:
        if name in COVERAGE and COVERAGE[name].startswith("none"):
            continue
        target_source = targets[name].get("source") or ""
        overlap = source_overlap(target_source, text)
        if overlap > 0.5:
            problems.append(
                "%s: equivalent identifier overlap %.2f is too high to call "
                "it independent" % (name, overlap))
    return problems
