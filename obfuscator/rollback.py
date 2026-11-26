"""§9 anti-rollback: refuse to run an older, weaker build.

The review's row: *"Anti-rollback protection — prevent downgrade to vulnerable
versions."* The threat is concrete: once a protection flaw is fixed in build
N+1, an attacker who can substitute files re-installs build N, which still runs
and still has the flaw. Version numbers in a manifest do not stop that on their
own, because the attacker edits them too.

Design.

  * A monotonic ``protection_level`` is recorded IN THE SIGNED BUILD MANIFEST
    (obfuscator/build_manifest.py). It is an integer, not a marketing version,
    so ordering is unambiguous and comparison cannot be gamed by string forms
    like "2.0.0-rc1".
  * At runtime the loader compares its own level against a high-water mark kept
    beside the artefact. If the artefact's level is BELOW the mark, it refuses
    to run -- that is the downgrade case.
  * If it is above, the mark is raised.
  * The mark is HMAC'd with a domain-separated runtime rollback key. Emitted
    loaders prefer a customer/licence lineage root when one is available, so a
    payload-key rotation does not invalidate the lineage; unbound builds fall
    back to their reconstructed payload key and therefore only recognise marks
    written with the same key material. The raw payload key is never embedded
    in the loader as a contiguous rollback secret.

**Honest limits, stated here and in the tests.** A high-water mark stored on
the client protects only against an attacker who does not delete it. Someone
who removes the file, or runs the artefact in a clean directory, gets the old
build to run again. Cross-build continuity additionally requires the customer
or licence binding material to remain stable; freshly re-keyed artefacts start
a new lineage. Real anti-rollback requires the issuer (or a server) to refuse
old builds. This implementation raises a downgrade from "copy a file" to
"delete a file AND know you had to" -- useful against casual rollback, useless
against a determined local attacker. Saying that is more valuable than
pretending the mark is authoritative.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile

SCHEMA = "nx-rollback/v1"

#: Filename of the high-water mark, stored beside the artefact by default.
MARK_NAME = ".nx-rollback-mark"


def mark_path(artefact_path, override=None):
    """Where the high-water mark lives for ``artefact_path``.

    Default: beside the artefact, so a move of the artefact moves its mark.
    The result is realpath-normalised and asserted to sit in the artefact's own
    directory, so a crafted ``artefact_path`` cannot redirect the mark outside
    it. ``override`` exists for tests and for callers keeping state elsewhere.
    """
    if override:
        return os.path.realpath(os.path.abspath(override))
    base = os.path.dirname(os.path.realpath(os.path.abspath(artefact_path)))
    candidate = os.path.join(base, MARK_NAME)
    if os.path.dirname(os.path.realpath(candidate)) != base:
        raise ValueError("rollback mark path escaped the artefact directory")
    return candidate


def _mac(key: bytes, level: int, artefact_name: str) -> str:
    """Bind the mark to the level and the artefact name.

    Without the name, a mark raised for one product would block a different
    one at a lower level; without the key, the mark is editable.
    """
    body = ("%s:%d:%s" % (SCHEMA, int(level), artefact_name)).encode()
    return hmac.new(bytes(key), body, hashlib.sha256).hexdigest()


def derive_mark_key(root_key):
    """Derive the emitted loader's rollback-mark key from its runtime key.

    The rollback gate must not embed the payload key as a contiguous literal.
    Deriving a domain-separated mark key from the already reconstructed runtime
    key keeps the raw payload key split/masked while avoiding key reuse across
    the payload-decryption and mark-authentication domains. Emitted loaders
    prefer the customer/licence lineage root when one is available because a
    random per-build payload key cannot validate marks written by other builds.
    """
    return hashlib.sha256(
        b"nx-rollback/v1/key:" + bytes(root_key)).digest()


def read_mark(path, key=None, artefact_name=None):
    """Return the recorded level, or 0 when absent/unreadable/corrupt.

    Absent means "first run here", not "attack": treating a missing mark as a
    failure would brick every fresh install.

    MAC VERIFIED ON READ (review register, seventh pass -- found while
    measuring the §3 restore-state rows). This function used to return the
    stored level WITHOUT checking the MAC, so the MAC bound the mark but
    nothing ever verified it: an attacker who edited the level downward was
    obeyed, and write_mark's documented purpose ("a hand-edited mark cannot
    lower it without also knowing the key") was not implemented on the read
    path. When ``key`` and ``artefact_name`` are supplied the MAC is
    verified and a mismatch reads as 0 (corrupt), which the caller treats as
    fresh-install semantics -- never as a trusted lower level.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("schema") != SCHEMA:
            return 0
        level = int(data.get("level", 0))
        if key is not None and artefact_name is not None:
            expected = _mac(key, level, artefact_name)
            if not hmac.compare_digest(str(data.get("mac", "")), expected):
                # A forged or corrupted MAC is NOT a trustworthy level.
                return 0
        return level
    except (OSError, ValueError, TypeError):
        return 0


def write_mark(path, key, level, artefact_name):
    """Atomically record a new level, MAC'd with the build key."""
    payload = {
        "schema": SCHEMA,
        "level": int(level),
        "mac": _mac(key, level, artefact_name),
    }
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".nx-rb-")
    except OSError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, sort_keys=True)
        os.replace(tmp, path)
        return True
    except OSError:
        # A failed replace must not leave a readable stray mark candidate in
        # the artefact directory; atomic-write cleanup is part of the contract.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False


def emit_rollback_snippet(level):
    """Return self-contained loader code for runtime rollback enforcement.

    The snippet deliberately duplicates the small mark format rather than
    importing this module because emitted artefacts must run without the
    repository on ``sys.path``. It does not embed the payload key: the gate
    derives a domain-separated mark key at runtime from the loader's already
    reconstructed ``_NX_EFF_KEY``/``BLOB_KEY``. Invalid input is a build-time
    error because an armed rollback gate must never degrade to a silent no-op.
    """
    if not isinstance(level, int) or level < 0:
        raise ValueError("rollback level must be a non-negative int")
    return """_NX_ROLLBACK_LEVEL = %d


def _nx_rollback_gate():
    import hashlib as _nx_rb_hashlib
    import hmac as _nx_rb_hmac
    import json as _nx_rb_json
    import os as _nx_rb_os
    import sys as _nx_rb_sys
    import tempfile as _nx_rb_tempfile
    try:
        _nx_rb_art = _nx_rb_os.path.realpath(_nx_rb_os.path.abspath(
            globals().get('__file__') or (_nx_rb_sys.argv[0] if _nx_rb_sys.argv else '')))
        _nx_rb_base = _nx_rb_os.path.dirname(_nx_rb_art)
        _nx_rb_name = _nx_rb_os.path.basename(_nx_rb_art)
        _nx_rb_path = _nx_rb_os.path.join(_nx_rb_base, '.nx-rollback-mark')
        _nx_rb_root = (globals().get('_NX_ROLLBACK_ROOT')
                       or globals().get('_NX_EFF_KEY')
                       or globals().get('BLOB_KEY'))
        if not _nx_rb_root:
            return 'mark-unwritable'
        _nx_rb_key = _nx_rb_hashlib.sha256(
            b'nx-rollback/v1/key:' + bytes(_nx_rb_root)).digest()

        def _nx_rb_mac(_level):
            _body = ('nx-rollback/v1:%%d:%%s' %% (int(_level), _nx_rb_name)).encode()
            return _nx_rb_hmac.new(_nx_rb_key, _body, _nx_rb_hashlib.sha256).hexdigest()

        _nx_rb_seen = 0
        _nx_rb_exists = _nx_rb_os.path.exists(_nx_rb_path)
        if _nx_rb_exists:
            try:
                with open(_nx_rb_path, encoding='utf-8') as _nx_rb_fh:
                    _nx_rb_data = _nx_rb_json.load(_nx_rb_fh)
                if _nx_rb_data.get('schema') == 'nx-rollback/v1':
                    _nx_rb_candidate = int(_nx_rb_data.get('level', 0))
                    if _nx_rb_hmac.compare_digest(
                            str(_nx_rb_data.get('mac', '')),
                            _nx_rb_mac(_nx_rb_candidate)):
                        _nx_rb_seen = _nx_rb_candidate
            except Exception:
                _nx_rb_seen = 0
        if _NX_ROLLBACK_LEVEL < _nx_rb_seen:
            return 'refused'
        if _NX_ROLLBACK_LEVEL > _nx_rb_seen or not _nx_rb_exists:
            _nx_rb_tmp = None
            try:
                _nx_rb_fd, _nx_rb_tmp = _nx_rb_tempfile.mkstemp(
                    dir=_nx_rb_base, prefix='.nx-rb-')
                with _nx_rb_os.fdopen(_nx_rb_fd, 'w', encoding='utf-8') as _nx_rb_fh:
                    _nx_rb_json.dump({
                        'schema': 'nx-rollback/v1',
                        'level': int(_NX_ROLLBACK_LEVEL),
                        'mac': _nx_rb_mac(_NX_ROLLBACK_LEVEL),
                    }, _nx_rb_fh, sort_keys=True)
                _nx_rb_os.replace(_nx_rb_tmp, _nx_rb_path)
            except Exception:
                try:
                    if _nx_rb_tmp:
                        _nx_rb_os.unlink(_nx_rb_tmp)
                except Exception:
                    pass
                return 'mark-unwritable'
        return 'ok'
    except Exception:
        return 'mark-unwritable'
""" % (level,)

def check_rollback(artefact_path, level, key, override_path=None):
    """Raise RuntimeError on a downgrade; otherwise raise the mark.

    Returns a small dict describing what happened, so a caller can log it
    without re-reading the mark.
    """
    if not isinstance(level, int) or level < 0:
        raise RuntimeError("anti-rollback: level must be a non-negative int, "
                           "got %r" % (level,))
    name = os.path.basename(os.path.abspath(artefact_path))
    path = mark_path(artefact_path, override_path)
    seen = read_mark(path, key=key, artefact_name=name)
    if level < seen:
        raise RuntimeError(
            "anti-rollback: this artefact is protection level %d but level %d "
            "was already installed here; refusing to downgrade"
            % (level, seen))
    if level > seen or not os.path.exists(path):
        if not write_mark(path, key, level, name):
            raise RuntimeError(
                "anti-rollback: protection mark could not be written; "
                "refusing to run with rollback enforcement disarmed")
    return {"level": level, "previous": seen, "mark": path}
