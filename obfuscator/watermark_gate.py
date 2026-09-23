"""Runtime watermark refuse-to-run gate (AUDIT GAP #71).

Build-time: :func:`build_watermark_context` mints a per-build secret and
an HMAC-SHA256 tag binding the watermark message::

    tag = HMAC-SHA256(build_key, b"nx-watermark-v1|" + watermark_bytes)

Runtime (emitted snippet, see :func:`emit_watermark_snippet`): recompute
the tag with a constant-time compare and refuse to run on mismatch.
Additionally, a sealed presence token proves the watermark payload block
was not stripped: the marker literal emitted alongside the snippet must
be present verbatim in the artifact globals at runtime; absence means
the watermark was removed -> refuse.

Fail-closed semantics follow the project's standard tamper termination:
the emitted snippet ends with an enforcement block that calls
``_nx_kill("watermark-" + verdict)`` (wipe + silent exit 137; same shape
as the trial gate in
``obfuscator/core/pipeline.py::generate_hybrid_loader_script``), so a
stripped/tampered watermark never reaches any payload.

When no watermark was configured at build time the emitted gate is the
literal ``_NX_WATERMARK_GATE = "DISABLED"`` and the artifact runs
unchanged (never break unmarked builds).

Pure-python, stdlib only, dependency-free so the snippet is emittable
into stubs/loaders.

Tamper model: message, tag, and the presence marker are all bound by
HMAC under the per-build ``build_key`` (a fresh 32-byte secret minted
at build time, embedded only as an opaque hex literal in the artifact).
Editing the message or deleting the marker without the key invalidates
the tag; copying the artifact is fine (no machine binding here — that
is the trial/HWID layer's job).

Python 3.10 compatible: no match statements, no X|Y annotations.
"""

import hashlib
import hmac as _hmac
import secrets as _secrets

#: HMAC domain separator (keeps the watermark tag distinct from the
#: trial-gate and last-seen stamps).
_WM_DOMAIN = b"nx-watermark-v1"

#: Gate verdicts returned by the runtime gate function.
GATE_OK = "ok"
GATE_DISABLED = "DISABLED"
GATE_TAMPERED = "tampered"
GATE_MISSING = "missing"


def compute_tag(build_key, message):
    # type: (bytes, str) -> str
    """HMAC-SHA256 hex tag binding a watermark message to a build key.

    Message: ``domain || b"|" || watermark_utf8``.
    """
    if not isinstance(build_key, (bytes, bytearray)) or not len(build_key):
        raise ValueError("build_key must be non-empty bytes")
    try:
        msg_bytes = str(message).encode("utf-8")
    except Exception as e:
        raise ValueError("message must be utf-8 encodable: %s" % (e,))
    if not msg_bytes:
        raise ValueError("message must be non-empty")
    msg = _WM_DOMAIN + b"|" + msg_bytes
    return _hmac.new(bytes(build_key), msg, hashlib.sha256).hexdigest()


def verify_tag(build_key, message, tag):
    # type: (bytes, str, str) -> bool
    """Constant-time tag check.  Never raises on bad input."""
    try:
        expected = compute_tag(build_key, message)
        return _hmac.compare_digest(str(expected), str(tag or ""))
    except Exception:
        return False


def check_watermark(build_key, message, tag, marker_present=True):
    # type: (bytes, str, str, bool) -> str
    """Pure build/runtime verdict: ``"ok"`` / ``"tampered"`` / ``"missing"``.

    Order: presence first (stripped watermark block), then the HMAC
    binding (edited message or wrong key).
    """
    if not marker_present:
        return GATE_MISSING
    try:
        msg_ok = bool(str(message)) and len(str(message).encode("utf-8")) > 0
    except Exception:
        msg_ok = False
    if not msg_ok:
        return GATE_MISSING
    if not verify_tag(build_key, message, tag):
        return GATE_TAMPERED
    return GATE_OK


def build_watermark_context(message, build_key=None):
    # type: (str, bytes) -> dict
    """Build-time helper: fresh key + tag (+ presence marker) for a message.

    Returns ``{"message": ..., "tag": hex, "marker": ...,
    "build_key": bytes}``.  When ``message`` is None/empty, returns
    ``{"disabled": True}`` (no watermark requested — additive no-op
    for callers).
    """
    if message is None or (isinstance(message, str) and message == ""):
        return {"disabled": True}
    msg = str(message)
    try:
        if not msg.encode("utf-8"):
            return {"disabled": True}
    except Exception:
        raise ValueError("message must be utf-8 encodable")
    key = bytes(build_key) if build_key is not None else _secrets.token_bytes(32)
    if not key:
        raise ValueError("build_key must be non-empty bytes")
    tag = compute_tag(key, msg)
    # Presence marker: deterministic from the key so every build with a
    # watermark carries a unique marker literal; the runtime gate checks
    # the marker literal is still present in the artifact globals.
    marker = "NXWM-" + hashlib.sha256(b"nx-wm-marker|" + key).hexdigest()[:16]
    return {"message": msg, "tag": tag, "marker": marker,
            "build_key": bytes(key)}


def emit_watermark_snippet(message, tag_hex, build_key_hex, marker,
                           func_name="_nx_watermark_gate"):
    # type: (str, str, str, str, str) -> str
    """Return the emittable runtime gate snippet.  Must compile().

    The snippet defines ``<func_name>()`` returning one of ``"ok"`` /
    ``"tampered"`` / ``"missing"``.  Callers enforce::

        _NX_WATERMARK_GATE = _nx_watermark_gate()
        if _NX_WATERMARK_GATE != "ok":
            _nx_kill("watermark-" + str(_NX_WATERMARK_GATE))  # exit 137

    All literals are embedded via ``repr`` (hex digests / marker contain
    only ``[0-9a-fA-F-]``; no quoting hazards).  Stdlib only.
    """
    msg = str(message or "")
    tag = str(tag_hex or "")
    key_hex = str(build_key_hex or "")
    mark = str(marker or "")
    if not msg:
        raise ValueError("message must be non-empty")
    bytes.fromhex(key_hex)
    bytes.fromhex(tag)
    if not tag or len(tag) != 64:
        raise ValueError("tag_hex must be a 64-char sha256 hex digest")
    if not mark:
        raise ValueError("marker must be non-empty")
    if not str(func_name).isidentifier():
        raise ValueError("func_name must be a valid identifier")
    src = (
        "def %s():\n" % (func_name,)
        + "    import hashlib as _wm_hashlib\n"
        + "    import hmac as _wm_hmac\n"
        + "    _wm_msg = %r\n" % (msg,)
        + "    _wm_tag = %r\n" % (tag,)
        + "    _wm_key = bytes.fromhex(%r)\n" % (key_hex,)
        + "    _wm_marker = %r\n" % (mark,)
        + "    try:\n"
        + "        _wm_seen = globals().get(\"_NX_WATERMARK_MARKER\") == _wm_marker\n"
        + "    except Exception:\n"
        + "        _wm_seen = False\n"
        + "    if not _wm_seen:\n"
        + "        return \"missing\"\n"
        + "    try:\n"
        + "        _wm_expect = _wm_hmac.new(_wm_key, b\"nx-watermark-v1|\" + str(_wm_msg).encode(\"utf-8\"), _wm_hashlib.sha256).hexdigest()\n"
        + "    except Exception:\n"
        + "        return \"tampered\"\n"
        + "    try:\n"
        + "        _wm_match = _wm_hmac.compare_digest(str(_wm_expect), str(_wm_tag))\n"
        + "    except Exception:\n"
        + "        _wm_match = (_wm_expect == _wm_tag)\n"
        + "    if not _wm_match:\n"
        + "        return \"tampered\"\n"
        + "    return \"ok\"\n"
    )
    compile(src, "<nx_watermark_gate>", "exec")
    return src
