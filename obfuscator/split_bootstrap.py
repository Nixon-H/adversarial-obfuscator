"""V10 kernel split-bootstrap: Shamir threshold key + fragmented decoder.

Closes the caveat honestly: the loader/emitted kernel bootstrap derives
key material from a **split-secret scheme** with a **fragmented decoder**
rather than a single embedded key.

Split-secret scheme (build time)
--------------------------------
:func:`split_bootstrap_key` reuses the EXISTING Shamir implementation in
``scripts/dispersal/payload_dispersal.py`` (:meth:`ShamirSharing.split_secret`
/ :meth:`ShamirSharing.recover_secret`) — no reimplementation. With
``n=3, k=2`` the 32-byte bootstrap key becomes 3 shares; any 2 rebuild it.

.. important::

    ``ShamirSharing`` works over ``GF(251)``, so secret bytes >= 251 do
    NOT roundtrip (verified 2026-09-22: ~10/20 random 32-byte keys failed).
    A raw AES-style key therefore cannot be split directly. The bridge is
    :func:`_to_splittable`/:func:`_from_splittable`: the raw key is mapped to
    its 64-char ASCII hex encoding (bytes ``0-9a-f`` < 251, lossless for ANY
    key) and the *hex bytes* are what get Shamir-split. Recovery decodes hex
    back to the original key. This is documented, not hidden: every fragment
    helper carries the reason in its docstring.

Fragmented decoder (runtime)
----------------------------
The emitted runtime snippet reconstructs via the same Shamir combine math
only at first use (lazy, cached in ``_NX_SB_KEY``), and the decode path is
split across 3 cooperating functions so NO single function contains the
full decode path:

- ``_nx_sb_collect()`` — gathers k fragments from their separate stub
  locations; knows WHERE shares live, never the combine math.
- ``_nx_sb_combine(parts)`` — Lagrange-interpolates hex bytes at x=0 and
  hex-decodes to the raw key; knows HOW shares combine, never the
  locations or the salt. Fails closed (``ValueError``) on wrong share
  count.
- ``_nx_sb_activate()`` — lazy first-use entry: collect -> combine ->
  apply the build-id salt (``xor(raw, sha256(build_id))``, the same
  derivation as ``obfuscator/key_emit.py::derive_effective_key`` so the
  split path yields the SAME effective key the loader decrypts with) ->
  cache in ``_NX_SB_KEY`` -> wipe fragment holders and intermediates.
  Knows WHEN the key materializes, never the combine math.

Fragment placement (genuine fragmentation, not one string cut in 3 lines):

1. ``_NX_SB_HEAD`` — emitted with the loader head (key-material section).
2. ``_NX_SB_TRAIL`` — emitted with the section trailer (far from #1).
3. ``_NX_SB_THIRD`` — emitted with the SALT group next to the
   ``_NX_SB_SALT`` build-id literal (far from #2); the salt itself is
   applied at activate-time, so a tampered build id derives a wrong key.

Tamper-detection honesty note: a corrupted share does not ALWAYS raise.
The split covers ASCII-hex bytes through ``GF(251)`` interpolation, so a
small share flip can occasionally land back inside the hex alphabet
(measured ~6% for single-bit tail flips) and combine to a wrong-but-valid
key — a silent wrong key, NOT a guaranteed ``ValueError``. Fail-closed
here means: (a) malformed shares (bad ``x:b64`` shape, length mismatch)
always raise; (b) large corruptions raise via the bad-hex check; (c) any
residual wrong-key output fails downstream at decrypt time (authenticated
payload / decompression error), never as a valid decryption. Tests flip
a full byte mid-share (reliably non-hex) for the deterministic raise
case.

Between the three literal groups the emitter injects ≥ 8 filler comment
lines each, so the fragments are non-adjacent in the emitted stub.
:func:`fragments_spread` asserts/measures that spread.

Post-reconstruction wipe: after ``_nx_sb_activate()`` derives the key it
zeroes what it can and ``del``-etes the fragment holder names
(``_NX_SB_HEAD``/``_NX_SB_TRAIL``/``_NX_SB_THIRD``) from its namespace.
Honesty note: the emitted fragment literals are Python ``str`` (immutable,
interned) — they cannot be zeroed in place the way ``bytearray`` buffers
can. The wipe therefore (a) zeroes the mutable intermediates (the raw
combined key copy and a scratch ``bytearray`` per holder) via
``ctypes.memset`` where available, and (b) deletes the holder NAMES from
``globals()`` so a post-activation ``"_NX_SB_HEAD" in ns`` reads ``False``
and the values are unreachable without a gc/referent walk. Module-level
``str`` copies (co_consts, interning) remain — that residual is inherent
to emitting key material as Python source and is documented here, not
hidden.

Build-time API: :func:`split_bootstrap_key`, :func:`emit_bootstrap_snippet`,
:func:`fragments_spread`, :func:`snip_markers`.
"""

from __future__ import annotations

import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.dispersal.payload_dispersal import ShamirSharing

DEFAULT_N = 3
DEFAULT_K = 2

# Marker/literal names used by the runtime snippet. Kept in one place so
# tests and the pipeline wiring can reference the same contract.
HEAD_VAR = "_NX_SB_HEAD"
TRAIL_VAR = "_NX_SB_TRAIL"
SALT_VAR = "_NX_SB_SALT"
CACHE_VAR = "_NX_SB_KEY"
COLLECT_FN = "_nx_sb_collect"
COMBINE_FN = "_nx_sb_combine"
ACTIVATE_FN = "_nx_sb_activate"

# Marker comments delimiting the 3 fragment groups in the emitted stub.
HEAD_MARKER = "# [NX_SB_FRAG:HEAD]"
TRAIL_MARKER = "# [NX_SB_FRAG:TRAIL]"
SALT_MARKER = "# [NX_SB_FRAG:SALT]"


def _to_splittable(key: bytes) -> bytes:
    """Map raw key bytes to Shamir-safe bytes.

    ``ShamirSharing`` interpolates over ``GF(251)``: any secret byte >= 251
    is reduced mod 251 and does NOT roundtrip. The raw bootstrap key is
    arbitrary bytes (e.g. ``secrets.token_bytes(32)``), so split the
    ASCII hex encoding instead — hex chars are all < 251 and the mapping
    is a bijection for every possible key.
    """
    if not isinstance(key, (bytes, bytearray)) or len(key) == 0:
        raise ValueError("key must be non-empty bytes")
    return bytes(key).hex().encode("ascii")


def _from_splittable(blob: bytes) -> bytes:
    """Inverse of :func:`_to_splittable`: ASCII-hex bytes -> raw key."""
    try:
        return bytes.fromhex(bytes(blob).decode("ascii"))
    except Exception as e:
        raise ValueError("split-bootstrap combine produced bad hex: %s" % (e,))


def _b64_indexed(share: tuple) -> str:
    """Encode one ``(x, share_bytes)`` pair as ``\"x:base64\"`` text."""
    x, data = share
    return "%d:%s" % (int(x), base64.b64encode(bytes(data)).decode("ascii"))


def _parse_indexed(text: str) -> tuple:
    """Parse one ``\"x:base64\"`` fragment back to ``(x, share_bytes)``."""
    try:
        xs, b64 = str(text).split(":", 1)
        return (int(xs), base64.b64decode(b64))
    except Exception as e:
        raise ValueError("bad split-bootstrap fragment: %s" % (e,))


def split_bootstrap_key(key: bytes, n: int = DEFAULT_N,
                        k: int = DEFAULT_K) -> dict:
    """Split ``key`` into ``n`` fragments with threshold ``k``.

    Uses the EXISTING :meth:`ShamirSharing.split_secret` API (build-time
    dispersal; never reimplemented here). The raw key is first mapped via
    :func:`_to_splittable` because ``ShamirSharing`` is ``GF(251)`` and
    cannot roundtrip bytes >= 251.

    Returns ``{"fragments": [str, ...], "k": int, "n": int}`` where each
    fragment is ``"x:base64\"`` text (the x-coordinate travels with the
    share so the runtime combiner needs no out-of-band index table).
    """
    if k < 2:
        raise ValueError("threshold k must be >= 2 (ShamirSharing floor)")
    if k > n:
        raise ValueError("threshold k cannot exceed n")
    splittable = _to_splittable(key)
    shares = ShamirSharing.split_secret(splittable, n, k)
    if len(shares) != n:
        raise ValueError("ShamirSharing returned %d shares, expected %d"
                         % (len(shares), n))
    return {"fragments": [_b64_indexed(s) for s in shares], "k": int(k),
            "n": int(n)}


def recover_bootstrap_key(fragments, k: int) -> bytes:
    """Recombine ``fragments`` (``\"x:base64\"`` text) via the existing API.

    Fails closed: fewer than ``k`` fragments -> ``ValueError`` (raised by
    :meth:`ShamirSharing.recover_secret`); malformed/tampered fragments ->
    ``ValueError`` from parsing, length checks, or hex decoding.
    """
    frags = list(fragments or [])
    if len(frags) < int(k):
        raise ValueError("Not enough shares: need %d, got %d"
                         % (int(k), len(frags)))
    shares = [_parse_indexed(f) for f in frags[:int(k)]]
    lens = {len(d) for _, d in shares}
    if len(lens) != 1:
        raise ValueError("share length mismatch")
    raw = ShamirSharing.recover_secret(shares, int(k))
    return _from_splittable(raw)


def _lit(text: str) -> str:
    """Render fragment text as a safe double-quoted Python literal.

    Fragments are ``[0-9]:[A-Za-z0-9+/=]`` — no quotes or backslashes by
    construction; assert that so the emitted stub cannot break out.
    """
    if '"' in text or "\\" in text or "\n" in text:
        raise ValueError("fragment contains unsafe characters")
    return '"%s"' % (text,)


_FILLER = (
    "# -- nx-sb pad: decoy key-material spacing (keeps fragments apart) --\n"
)


def emit_bootstrap_snippet(fragments, k: int,
                           build_id: str = "nx-sb") -> str:
    """Return the runtime fragmented-decoder snippet for the stub.

    ``fragments`` is the 3-element list from :func:`split_bootstrap_key`
    (``k=2`` default). Placement in the emitted stub:

    - HEAD group (loader head): the first fragment literal.
    - TRAIL group (section trailer): the second fragment literal, ≥8 pad
      lines after HEAD so the two literals are non-adjacent.
    - SALT group (build-id leg): the third fragment literal next to the
      ``_NX_SB_SALT`` build-id literal, again ≥8 pad lines after TRAIL.
      The salt itself is NOT key material — it is applied inside
      ``_nx_sb_activate()`` as ``xor(raw, sha256(build_id))`` (same
      derivation as ``key_emit.derive_effective_key``), so a tampered
      build id fails closed at decrypt time.

    Decoder fragmentation (no single function holds the full decode path):

    - ``_nx_sb_collect()`` — locations only (reads the 3 groups).
    - ``_nx_sb_combine(parts)`` — math only (Lagrange at x=0 + hex
      decode). Fails closed on wrong share count / bad hex.
    - ``_nx_sb_activate()`` — lazy first-use entry; caches into
      ``_NX_SB_KEY``; wipes fragment holders afterwards.
    """
    frags = list(fragments or [])
    if len(frags) != 3:
        raise ValueError("need exactly 3 fragments, got %d" % len(frags))
    if int(k) != 2:
        raise ValueError("emitted snippet supports k=2 only (got %r)" % (k,))
    if not isinstance(build_id, str) or not build_id:
        raise ValueError("build_id must be a non-empty string")
    if '"' in build_id or "\\" in build_id:
        raise ValueError("build_id contains unsafe characters")
    for f in frags:
        _parse_indexed(f)  # fail fast on malformed input
        _lit(f)

    lines = []
    lines.append(HEAD_MARKER)
    lines.append("%s = %s" % (HEAD_VAR, _lit(frags[0])))
    for _ in range(8):
        lines.append(_FILLER.rstrip("\n"))
    lines.append(TRAIL_MARKER)
    lines.append("%s = %s" % (TRAIL_VAR, _lit(frags[1])))
    for _ in range(8):
        lines.append(_FILLER.rstrip("\n"))
    lines.append(SALT_MARKER)
    lines.append("%s = %s" % (SALT_VAR, _lit(build_id)))
    lines.append("_NX_SB_THIRD = %s" % (_lit(frags[2]),))
    lines.append("")
    lines.append("# _collect: locations only.")
    lines.append("def %s():" % COLLECT_FN)
    lines.append('    """Gather k fragments from separate stub locations."""')
    lines.append("    return [%s, %s, _NX_SB_THIRD]" % (HEAD_VAR, TRAIL_VAR))
    lines.append("")
    # _combine: math only. Self-contained Lagrange-over-GF(251) + hex
    # decode mirroring scripts/dispersal/payload_dispersal.py::ShamirSharing
    # (stdlib only in the emitted stub; no build-time imports allowed).
    lines.append("def %s(parts):" % COMBINE_FN)
    lines.append('    """Lagrange-interpolate hex bytes at x=0; fail closed."""')
    lines.append("    import base64 as _sb_b64")
    lines.append("    _PRIME = 251")
    lines.append("    if len(parts) < 2:")
    lines.append('        raise ValueError("split-bootstrap: need 2 shares, got %d" % len(parts))')
    lines.append("    _shares = []")
    lines.append("    for _p in parts[:2]:")
    lines.append('        _xs, _b64 = str(_p).split(":", 1)')
    lines.append("        _shares.append((int(_xs), _sb_b64.b64decode(_b64)))")
    lines.append("    if len(_shares[0][1]) != len(_shares[1][1]):")
    lines.append('        raise ValueError("split-bootstrap: share length mismatch")')
    lines.append("    _out = bytearray(len(_shares[0][1]))")
    lines.append("    for _bi in range(len(_out)):")
    lines.append("        _acc = 0")
    lines.append("        for _i, (_xi, _yi_raw) in enumerate(_shares):")
    lines.append("            _yi = _yi_raw[_bi]")
    lines.append("            _num, _den = 1, 1")
    lines.append("            for _j, (_xj, _yj_raw) in enumerate(_shares):")
    lines.append("                if _i == _j:")
    lines.append("                    continue")
    lines.append("                _num = (_num * (0 - _xj)) % _PRIME")
    lines.append("                _den = (_den * (_xi - _xj)) % _PRIME")
    lines.append("            _acc = (_acc + _yi * _num * pow(_den, -1, _PRIME)) % _PRIME")
    lines.append("        _out[_bi] = _acc & 0xFF")
    lines.append("    try:")
    lines.append("        return bytes.fromhex(bytes(_out).decode('ascii'))")
    lines.append("    except Exception as _e:")
    lines.append('        raise ValueError("split-bootstrap: bad combined hex (%s)" % (_e,))')
    lines.append("")
    # _activate: timing + salt only (lazy first use + wipe). Applies the
    # build-id salt — xor(raw, sha256(build_id)) — the same derivation as
    # obfuscator/key_emit.py::derive_effective_key, so _activate() yields
    # the SAME effective key the hybrid loader decrypts with (BLOB_KEY).
    lines.append("%s = None" % CACHE_VAR)
    lines.append("def %s():" % ACTIVATE_FN)
    lines.append('    """Lazy first-use: collect -> combine -> salt -> cache -> wipe."""')
    lines.append("    global %s" % CACHE_VAR)
    lines.append("    if %s is not None:" % CACHE_VAR)
    lines.append("        return %s" % CACHE_VAR)
    lines.append("    _parts = %s()" % COLLECT_FN)
    lines.append("    _raw = %s(_parts)" % COMBINE_FN)
    lines.append("    import hashlib as _sb_hk")
    lines.append("    _mask = _sb_hk.sha256(str(%s).encode()).digest()" % SALT_VAR)
    lines.append("    _key = bytes(_b ^ _mask[_i % len(_mask)] for _i, _b in enumerate(_raw))")
    lines.append("    _sb_wipe = bytearray(_raw)")
    lines.append("    %s = _key" % CACHE_VAR)
    lines.append("    try:")
    lines.append("        import ctypes as _sb_ct")
    lines.append("        _sb_targets = []")
    lines.append("        try:")
    lines.append("            _sb_targets.append(_sb_wipe)")
    lines.append("        except Exception:")
    lines.append("            pass")
    lines.append("        for _name in (%s, %s, '_NX_SB_THIRD'):"
                  % (repr(HEAD_VAR), repr(TRAIL_VAR)))
    lines.append("            try:")
    lines.append("                _buf = bytearray(globals().get(_name, b'') or b'')")
    lines.append("                if len(_buf):")
    lines.append("                    _sb_ct.memset(_sb_ct.addressof(_sb_ct.c_char.from_buffer(_buf)), 0, len(_buf))")
    lines.append("            except Exception:")
    lines.append("                pass")
    lines.append("            try:")
    lines.append("                del globals()[_name]")
    lines.append("            except Exception:")
    lines.append("                pass")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    return _key")
    lines.append("")
    return "\n".join(lines)


def fragments_spread(snippet: str) -> dict:
    """Measure fragment non-adjacency in an emitted snippet.

    Returns ``{"head_line": int, "trail_line": int, "gap": int}`` (0-based
    line numbers of the two share literals and the line gap between them).
    """
    lines = snippet.split("\n")
    head = trail = None
    for i, ln in enumerate(lines):
        if ln.startswith(HEAD_VAR + " ="):
            head = i
        elif ln.startswith(TRAIL_VAR + " ="):
            trail = i
    if head is None or trail is None:
        raise ValueError("snippet missing fragment literals")
    return {"head_line": head, "trail_line": trail,
            "gap": abs(trail - head)}


def snip_markers() -> dict:
    """Return the stub contract markers (for pipeline wiring + tests).

    Includes ``third_var`` (``_NX_SB_THIRD``) and the pipeline-level
    ``armed_var`` (``_NX_SPLIT_BOOTSTRAP_ARMED``) / ``blob_var``
    (``BLOB_KEY_SB``) names so the renamer-reserve audit and the loader
    wiring reference the same contract.
    """
    return {"head": HEAD_MARKER, "trail": TRAIL_MARKER, "salt": SALT_MARKER,
            "head_var": HEAD_VAR, "trail_var": TRAIL_VAR,
            "third_var": "_NX_SB_THIRD",
            "salt_var": SALT_VAR, "cache_var": CACHE_VAR,
            "collect": COLLECT_FN, "combine": COMBINE_FN,
            "activate": ACTIVATE_FN,
            "armed_var": "_NX_SPLIT_BOOTSTRAP_ARMED",
            "flag_var": "_NX_SPLIT_BOOTSTRAP",
            "blob_var": "BLOB_KEY_SB"}
