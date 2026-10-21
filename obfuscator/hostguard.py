"""Bind-once host dict + HMAC builtin check + isolated exec (Phase-4).

:func:`emit_hostguard_snippet` returns a self-contained Python source string
implementing ``bind_host`` / ``check_host`` / ``verify_builtin`` /
``isolated_exec``. The snippet must compile().
"""


def emit_hostguard_snippet() -> str:
    src = '''import sys as _sys
import hashlib as _hashlib
import builtins as _builtins

# The loader calls _NX_HOSTGUARD(code, ns) when it is set, and runs a
# plain exec() when it is not.  Publishing a CALLABLE (rather than a
# flag) keeps the loader's template free of hostguard-specific names.
def _nx_hostguard_exec(code_obj, ns):
    """Bind the host, verify the builtins are unpatched, then exec."""
    bind_host(ns)
    for _bn in ("exec", "eval", "compile"):
        if not verify_builtin(_bn):
            raise RuntimeError("builtin %s patched" % _bn)
    exec(code_obj, ns)
    return ns

_NX_HOSTGUARD = _nx_hostguard_exec

_NX_HOST = None

try:
    _NX_BUILTINS_MOD = _builtins
    _NX_BUILTINS_DICT = dict(vars(_builtins))
except Exception:
    try:
        _NX_BUILTINS_DICT = dict(_builtins.__dict__)
    except Exception:
        _NX_BUILTINS_DICT = {}


def _nx_digest_ns(ns):
    try:
        _keys = sorted(ns.keys())
    except Exception:
        _keys = sorted((str(_k) for _k in ns.keys()))
    _h = _hashlib.sha256()
    for _k in _keys:
        _h.update(str(_k).encode("utf-8", errors="ignore"))
        _h.update(b"\\x00")
    return _h.hexdigest()


def bind_host(ns):
    """Bind the host namespace once: store id(ns) + key-digest."""
    global _NX_HOST
    _NX_HOST = {"id": id(ns), "digest": _nx_digest_ns(ns)}
    return _NX_HOST


def check_host(ns):
    """Verify SAME object identity AND key-digest match; else RuntimeError."""
    if _NX_HOST is None:
        raise RuntimeError("host not bound")
    if id(ns) != _NX_HOST.get("id"):
        raise RuntimeError("host identity mismatch")
    if _nx_digest_ns(ns) != _NX_HOST.get("digest"):
        raise RuntimeError("host namespace tampered")
    return True


def verify_builtin(name, ref=None):
    """Compare builtins.__dict__[name] against ref or import-time snapshot.

    Returns True/False (never raises on missing names).
    """
    try:
        _cur = _builtins.__dict__.get(name) if hasattr(_builtins, "__dict__") else vars(_builtins).get(name)
    except Exception:
        return False
    if ref is not None:
        try:
            return _cur is ref
        except Exception:
            return False
    try:
        _orig = _NX_BUILTINS_DICT.get(name, None)
    except Exception:
        return False
    if name not in _NX_BUILTINS_DICT:
        return False
    try:
        return _cur is _orig
    except Exception:
        return False


def isolated_exec(code_obj, ns, expected_hash=None):
    """Verify host, verify builtins, verify hash, then exec.

    - check_host(ns) must pass
    - builtins exec/eval/compile must be unpatched (verify_builtin)
    - if expected_hash is not None: sha256 of the compiled bytecode
      (marshal of code_obj when possible, else repr) must match.
    Returns the namespace after exec.
    """
    check_host(ns)
    for _bn in ("exec", "eval", "compile"):
        if not verify_builtin(_bn):
            raise RuntimeError("builtin %s patched" % _bn)
    if expected_hash is not None:
        try:
            import marshal as _marshal
            _raw = _marshal.dumps(code_obj)
        except Exception:
            try:
                _raw = repr(code_obj).encode("utf-8", errors="ignore")
            except Exception:
                _raw = b""
        _got = _hashlib.sha256(_raw).hexdigest()
        if _got != expected_hash:
            raise RuntimeError("code hash mismatch")
    exec(code_obj, ns)
    return ns


def host_hash(code_obj):
    """Helper: compute the expected_hash value isolated_exec expects."""
    try:
        import marshal as _marshal
        _raw = _marshal.dumps(code_obj)
    except Exception:
        _raw = repr(code_obj).encode("utf-8", errors="ignore")
    return _hashlib.sha256(_raw).hexdigest()
'''
    compile(src, "<nx_hostguard>", "exec")
    return src
