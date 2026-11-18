"""Generate the runtime state-validation snippet for section packs.

§1 "runtime state validation": detect inconsistent internal state, not just
tampered bytes. The per-section HMAC tags already prove the ciphertext is
authentic. What they do NOT prove is that the loader is interpreting the pack
under the same structural claims the builder sealed it with — count, total
length, index ordering, per-section salts. An attacker who edits those fields
is not changing any authenticated byte; they are changing what the authenticated
bytes are taken to mean, and that is the cheap attack this closes.

The check recomputes a digest over the pack's DECLARED structure and compares
it with the `state` field the builder wrote. Build and runtime run the same
function over the same inputs, so the two cannot drift.

Fails CLOSED on a pack without `state`: the pre-2026-11-18 format is rejected
rather than silently accepted, because "this is an old pack" is exactly what an
attacker would assert.

Emitted once and shared by all loader variants; hand-copying it into each was
how earlier divergences happened.
"""
from __future__ import annotations

#: Bumped only when the state digest's input set changes.
STATE_SCHEMA = "nx-pack-state/v1"


def state_digest(sections, count, total):
    """Digest the pack's structural claims (NOT the ciphertext).

    Pure function: `sections` is an iterable of dicts with "i" and "salt".
    Used by the builder to write the field and reproduced verbatim by the
    emitted runtime check, so a divergence would be a build-time failure to
    match rather than a silent acceptance.
    """
    import hashlib

    h = hashlib.sha256()
    h.update((STATE_SCHEMA + ":").encode("ascii"))
    h.update(int(count).to_bytes(4, "big"))
    h.update(int(total).to_bytes(8, "big"))
    for sec in sorted(sections, key=lambda s: int(s["i"])):
        h.update(int(sec["i"]).to_bytes(4, "big"))
        h.update(str(sec.get("salt", "")).encode("ascii", "ignore"))
    return h.hexdigest()[:32]


def emit_state_check_snippet() -> str:
    """Return a Python function that verifies a pack's structural consistency."""
    body = r'''
def _nx_pack_state_ok(pack):
    """Verify the pack's declared structure matches its own content.

    Fails closed on a missing `state` field: the pre-2026-11-18 format is
    rejected rather than accepted.
    """
    try:
        import hashlib as _nx_st_sh
        sections = pack["sections"]
        count = int(pack["count"])
        total = int(pack["total"])
        declared = pack.get("state")
        if not declared:
            return False
        if len(sections) != count:
            return False
        seen = []
        h = _nx_st_sh.sha256()
        h.update(b"__NX_STATE_SCHEMA__:")
        h.update(count.to_bytes(4, "big"))
        h.update(total.to_bytes(8, "big"))
        for sec in sorted(sections, key=lambda s: int(s["i"])):
            idx = int(sec["i"])
            if idx in seen:
                return False
            seen.append(idx)
            h.update(idx.to_bytes(4, "big"))
            h.update(str(sec.get("salt", "")).encode("ascii", "ignore"))
        if seen != list(range(count)):
            return False
        # The declared total must equal what the sections actually carry
        # (ciphertext minus the 32-byte tag), so a re-sliced pack cannot keep
        # a stale total.
        carried = 0
        for sec in sections:
            raw = bytes.fromhex(sec["data"])
            if len(raw) < 32:
                return False
            carried += len(raw) - 32
        if carried != total:
            return False
        return h.hexdigest()[:32] == str(declared)
    except Exception:
        return False
'''
    return body.replace("__NX_STATE_SCHEMA__", STATE_SCHEMA)
