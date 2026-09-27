"""ChaCha20 string encryption with allowlist (AUDIT GAP #55).

Additive companion to the legacy XOR string transform in
``obfuscator/core/transforms.py`` (``StringLiteralObfuscator``): nothing in
the legacy path is removed or altered; this module adds a stronger,
authenticated mode selectable via the ``string_crypto`` option.

Public API:
    - is_allowlisted(value, allowlist) -> bool
    - encrypt_string(plaintext, key, allowlist=None) -> Optional[str]
      (hex seal, or None when allowlisted)
    - decrypt_string(seal_hex, key) -> str
    - make_session(key=None) -> dict with ``key``/``encrypt``/``decrypt``
    - emit_decoder_source(decoder_name, key) -> str (runtime stub)

Options understood (passed through ``apply_ast_mutation`` options):
    - ``string_crypto``: ``"chacha20"`` (default) or ``"xor"`` (legacy).
    - ``string_allowlist``: list of exact strings and/or ``"re:<pattern>"``
      regex entries. Matching strings stay plaintext in the payload.

Allowlist semantics (checked in this order per string):
    1. Exact match against a plain (non ``re:``) entry.
    2. ``re.search`` against each entry starting with ``"re:"``.
    3. Built-in safety nets (module docstring sentinels the pipeline must
       never encrypt): ``"_NX_PART_"`` prefix, ``"PLACEHOLDER"`` substring,
       and ``"__NX_STR_"`` marker. These mirror the legacy guards.

Python 3.10 compatible (stdlib only).
"""

import re

try:
    from obfuscator.chacha20 import (
        KEY_SIZE,
        aead_decrypt,
        aead_encrypt,
        build_stub_decoder,
        generate_key,
    )
except ImportError:  # pragma: no cover - direct-path fallback for tests
    from chacha20 import (  # type: ignore
        KEY_SIZE,
        aead_decrypt,
        aead_encrypt,
        build_stub_decoder,
        generate_key,
    )


LEGACY_MODE = "xor"
CHACHA_MODE = "chacha20"

DEFAULT_MODE = CHACHA_MODE

# Sentinel guards mirrored from StringLiteralObfuscator.visit_Constant.
_SENTINEL_PREFIXES = ("_NX_PART_", "__NX_STR_")
_SENTINEL_SUBSTRINGS = ("PLACEHOLDER", "__SIG_ANCHOR__", "__HMAC_ANCHOR__",
                        "__KEY_ANCHOR__")


def _regex_entries(allowlist):
    # type: (object) -> list
    patterns = []
    if not allowlist:
        return patterns
    items = allowlist if isinstance(allowlist, (list, tuple)) else [allowlist]
    for item in items:
        if isinstance(item, str) and item.startswith("re:"):
            try:
                patterns.append(re.compile(item[3:]))
            except re.error:
                continue
    return patterns


def _exact_entries(allowlist):
    # type: (object) -> set
    exact = set()
    if not allowlist:
        return exact
    items = allowlist if isinstance(allowlist, (list, tuple)) else [allowlist]
    for item in items:
        if isinstance(item, str) and not item.startswith("re:"):
            exact.add(item)
    return exact


def is_allowlisted(value, allowlist=None):
    # type: (str, object) -> bool
    """True when *value* must stay plaintext (allowlist or safety sentinel)."""
    if not isinstance(value, str):
        return True
    for prefix in _SENTINEL_PREFIXES:
        if value.startswith(prefix):
            return True
    for marker in _SENTINEL_SUBSTRINGS:
        if marker in value:
            return True
    if value in _exact_entries(allowlist):
        return True
    for pattern in _regex_entries(allowlist):
        try:
            if pattern.search(value):
                return True
        except Exception:
            continue
    return False


def normalize_mode(mode):
    # type: (object) -> str
    """Map the ``string_crypto`` option to a known mode.

    Raises ValueError on unknown modes (fail loud at build time rather
    than silently sealing with a different cipher than requested).
    """
    if mode in (None, "", "default", CHACHA_MODE):
        return CHACHA_MODE
    if mode == LEGACY_MODE:
        return LEGACY_MODE
    text = str(mode).strip().lower()
    if text in ("chacha", "chacha20", "aead"):
        return CHACHA_MODE
    if text in ("xor", "legacy"):
        return LEGACY_MODE
    raise ValueError("unknown string_crypto mode: %r" % (mode,))


def _check_key(key):
    # type: (bytes,) -> bytes
    if not isinstance(key, (bytes, bytearray)) or len(key) != KEY_SIZE:
        raise ValueError("ChaCha20 string key must be exactly 32 bytes")
    return bytes(key)


def encrypt_string(plaintext, key, allowlist=None):
    # type: (str, bytes, object) -> object
    """Seal *plaintext*; returns hex seal, or None when allowlisted.

    Raises TypeError for non-str input (fail loud at build time rather than
    emitting a stub that would crash at runtime).
    """
    if not isinstance(plaintext, str):
        raise TypeError("encrypt_string expects str, got %r" % type(plaintext))
    if is_allowlisted(plaintext, allowlist):
        return None
    _check_key(key)
    return aead_encrypt(bytes(key), plaintext.encode("utf-8")).hex()


def decrypt_string(seal_hex, key):
    # type: (str, bytes) -> str
    """Verify + decrypt a hex seal. Raises ValueError on tamper."""
    _check_key(key)
    return aead_decrypt(bytes(key), bytes.fromhex(seal_hex)).decode("utf-8")


def make_session(key=None):
    # type: (object) -> dict
    """One per-build session: fresh random key + bound helpers."""
    session_key = bytes(key) if key is not None else generate_key()
    _check_key(session_key)

    def _encrypt(plaintext, allowlist=None):
        return encrypt_string(plaintext, session_key, allowlist)

    def _decrypt(seal_hex):
        return decrypt_string(seal_hex, session_key)

    return {"key": session_key, "encrypt": _encrypt, "decrypt": _decrypt}


def emit_decoder_source(decoder_name, key):
    # type: (str, bytes) -> str
    """Runtime stub source for one build (self-contained pure Python)."""
    _check_key(key)
    return build_stub_decoder(decoder_name, bytes(key).hex())
