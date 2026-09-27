"""Stdlib function auditing (runtime integrity, additive).

Build-time: :func:`build_audit_context` records ``{qualified_name:
sha256}`` for ~20 critical stdlib functions. Source-hash preferred
(``inspect.getsource``); bytecode fallback (``func.__code__.co_code``)
for builtins/C functions that have no retrievable source. Runtime
(emitted snippet, see :func:`emit_audit_snippet`): re-checks a cheap
SUBSET (bytecode-compare only, no source reads — fast, no filesystem
I/O beyond imports) and fails closed via the kill ladder
``_nx_kill("stdlib-tamper")`` on mismatch (monkeypatched stdlib).

False-positive discipline (documented, not hidden):

- Only FUNCTIONS are checked (exact ``co_code`` byte compare), never
  module file bytes (that's the frozen_snapshot layer).
- ``sys.addaudithook`` is DELIBERATELY EXCLUDED: our own audit-hook
  plant detector (``obfuscator/audit_hook.py``) legitimately wraps it
  at bootstrap, so auditing its identity would self-flag every
  protected artifact.
- Same version-binding as frozen snapshots: the build tag
  (``major.minor.micro-releaselevel``) is embedded, and the snippet
  enforces ONLY on tag match; otherwise ``"version-mismatch"``
  (report-only, never kills). Same-interpreter but sitecustomize-
  patched targets WILL trip the gate — that is the intended signal
  (the target stdlib genuinely differs from the build host's).

Opt-out (mirrors ``obfuscator/audit_hook.py`` conventions):

- Runtime env ``NIXON_STDLIB_AUDIT_OFF`` in ``("1","true","True",
  "TRUE","yes","Yes","YES")`` -> snippet returns ``"disabled"``.
- Build flag ``--no-stdlib-audit`` (``stdlib_audit_off=True`` in
  ``generate_hybrid_loader_script``) -> pipeline emits the DISABLED
  literal, no snippet, no hashes baked.

Python 3.10 compatible: no ``match``, no ``X | Y`` annotations.
"""

import hashlib
import importlib
import inspect
import os
import sys

#: Runtime opt-out env var (truthy disables; mirrors audit_hook OPT_OUT_VAR).
OPT_OUT_VAR = "NIXON_STDLIB_AUDIT_OFF"

_OPT_OUT_TRUE = ("1", "true", "True", "TRUE", "yes", "Yes", "YES")

#: Curated critical-function list: (dotted_path, resolve_hint).
#: classes (subprocess.Popen, socket.socket, threading.Thread) ARE audited
#: via their ``__init__`` bytecode (exact-method compare: a subclass swap
#: or method patch changes co_code -> mismatch). ``sys.addaudithook`` is
#: DELIBERATELY EXCLUDED: our own audit-hook plant detector
#: (``obfuscator/audit_hook.py``) legitimately wraps it at bootstrap, so
#: auditing its identity would self-flag every protected artifact.
#: C builtins WITHOUT bytecode (os.urandom, builtins.eval/exec/compile,
#: builtins.open/__import__, marshal.loads/dumps, hashlib.sha256,
#: struct.pack, io.open, os.open/execv) CANNOT be bytecode-compared — they
#: fingerprint as ``identity`` (build-time record only) and are SKIPPED
#: by the runtime snippet (documented, not hidden). The runtime subset
#: is exactly the ``bytecode``-kind entries (~11: importlib.import_module,
#: json.loads/dumps, base64.b64decode/encode, hmac.new/digest, the three
#: class __init__s, threading.current_thread) — all pure-python stdlib
#: with stable co_code on a matching interpreter tag.
CRITICAL_FUNCTIONS = (
    ("os.urandom", "func"),
    ("builtins.eval", "func"),
    ("builtins.exec", "func"),
    ("builtins.compile", "func"),
    ("builtins.__import__", "func"),
    ("builtins.open", "func"),
    ("importlib.import_module", "func"),
    ("marshal.loads", "func"),
    ("marshal.dumps", "func"),
    ("json.loads", "func"),
    ("json.dumps", "func"),
    ("base64.b64decode", "func"),
    ("base64.b64encode", "func"),
    ("hashlib.sha256", "func"),
    ("hmac.new", "func"),
    ("hmac.digest", "func"),
    ("struct.pack", "func"),
    ("io.open", "func"),
    ("os.open", "func"),
    ("os.execv", "func"),
    # Classes: audited via __init__ bytecode (exact-method compare).
    ("subprocess.Popen", "method:__init__"),
    ("socket.socket", "method:__init__"),
    ("threading.Thread", "method:__init__"),
    ("threading.current_thread", "func"),
)

#: Gate verdicts returned by the runtime gate function.
GATE_OK = "ok"
GATE_DISABLED = "DISABLED"
GATE_MISMATCH = "mismatch"
GATE_VERSION_MISMATCH = "version-mismatch"


def build_tag():
    # type: () -> str
    """Version tag binding the audit table to the BUILD interpreter."""
    try:
        from obfuscator.frozen_snapshot import build_tag as _tag
        return _tag()
    except Exception:
        try:
            vi = sys.version_info
            return "%d.%d.%d-%s" % (vi[0], vi[1], vi[2], vi[3])
        except Exception:
            return "unknown"


def is_opted_out(env=None):
    # type: (object) -> bool
    """Return True when the stdlib audit gate is disabled via env."""
    if env is None:
        env = os.environ
    try:
        val = env.get(OPT_OUT_VAR, "")
    except Exception:
        return False
    return str(val) in _OPT_OUT_TRUE


def _resolve(path):
    # type: (str) -> object
    """Import-resolve a dotted path to the target object (or None)."""
    try:
        parts = str(path).split(".")
        if len(parts) < 2:
            return None
        mod = importlib.import_module(parts[0])
        obj = mod
        for part in parts[1:]:
            obj = getattr(obj, part)
        return obj
    except Exception:
        return None


def _code_of(obj, hint):
    # type: (object, str) -> object
    """Return the code object to hash for a target (or None)."""
    try:
        if hint.startswith("method:"):
            meth = hint.split(":", 1)[1]
            if isinstance(obj, type):
                raw = vars(obj).get(meth)
                if raw is None:
                    return None
                fn = getattr(raw, "__func__", raw)
            else:
                fn = getattr(obj, meth, None)
            return getattr(fn, "__code__", None)
        co = getattr(obj, "__code__", None)
        if co is not None:
            return co
        # Builtin/C callables (os.urandom, marshal.loads): no __code__.
        return None
    except Exception:
        return None


def fingerprint_of(path, hint="func"):
    # type: (str, str) -> dict
    """Build-time fingerprint for one qualified name.

    Returns ``{"kind": ..., "sha256": source-hex, "co_sha256": ...}``
    where ``kind`` is ``"source+bytecode"`` (pure-python: both hashes
    recorded; the runtime subset uses ``co_sha256`` — exact co_code
    compare, no source reads at runtime), ``"source"`` (no code object
    but sourceable — build record only, skipped at runtime),
    ``"identity"`` (C/builtin callable with neither source nor
    ``__code__`` — build record only, skipped at runtime), or
    ``"unavailable"`` (unresolvable — never kills, skipped at runtime).
    """
    obj = _resolve(path)
    if obj is None:
        return {"kind": "unavailable", "sha256": "", "co_sha256": ""}
    src_hex = ""
    try:
        src = inspect.getsource(obj)
        if isinstance(src, str) and src:
            src_hex = hashlib.sha256(src.encode("utf-8")).hexdigest()
    except Exception:
        src_hex = ""
    co_hex = ""
    co = _code_of(obj, hint)
    if co is not None:
        try:
            co_hex = hashlib.sha256(bytes(co.co_code)).hexdigest()
        except Exception:
            co_hex = ""
    if src_hex and co_hex:
        return {"kind": "source+bytecode", "sha256": src_hex,
                "co_sha256": co_hex}
    if co_hex:
        return {"kind": "bytecode", "sha256": "", "co_sha256": co_hex}
    if src_hex:
        return {"kind": "source", "sha256": src_hex, "co_sha256": ""}
    # C/builtin callable: identity is the only stable signal.
    try:
        if isinstance(obj, type):
            return {"kind": "unavailable", "sha256": "", "co_sha256": ""}
        return {"kind": "identity", "sha256": "", "co_sha256": ""}
    except Exception:
        return {"kind": "unavailable", "sha256": "", "co_sha256": ""}


def build_audit_context(functions=None):
    # type: (object) -> dict
    """Build-time helper: fingerprint the critical function list.

    Returns ``{"tag": build_tag(), "funcs": {qname: fingerprint},
    "runtime": {qname: co_code-sha256}}`` where ``runtime`` is the cheap
    runtime subset (every entry WITH bytecode — exact co_code compare,
    no source reads at runtime).
    """
    specs = list(functions) if functions else list(CRITICAL_FUNCTIONS)
    funcs = {}
    runtime = {}
    for spec in specs:
        try:
            if isinstance(spec, (tuple, list)):
                path, hint = str(spec[0]), str(spec[1])
            else:
                path, hint = str(spec), "func"
        except Exception:
            continue
        try:
            fp = fingerprint_of(path, hint)
        except Exception:
            fp = {"kind": "unavailable", "sha256": "", "co_sha256": ""}
        funcs[path] = {"kind": fp.get("kind", "unavailable"),
                       "sha256": fp.get("sha256", ""),
                       "co_sha256": fp.get("co_sha256", "")}
        try:
            co_hex = fp.get("co_sha256", "")
        except Exception:
            co_hex = ""
        if co_hex:
            runtime[path] = co_hex
    return {"tag": build_tag(), "funcs": funcs, "runtime": runtime}


def verify_audit(runtime_table, expected_tag, runtime_tag=None):
    # type: (dict, str, str) -> str
    """Pure version-bound verdict over the runtime subset.

    ``runtime_table``: ``{qname: expected_co_code_sha256}``. Resolves
    each name per call via ``importlib.import_module`` + attribute walk
    (no stale local binding is kept — but note this is NOT a fresh
    import: ``sys.modules`` caching still applies, so a module replaced
    wholesale in ``sys.modules`` before the call resolves to the
    replacement; plain attribute walk is enough — a monkeypatch replaces
    the attribute, which is exactly what the compare detects). Returns
    ``"ok"`` / ``"mismatch"`` / ``"version-mismatch"``. Unresolvable or
    code-less targets are SKIPPED (never fail — a same-tag interpreter
    always exposes the same pure-python functions, so a skip means a
    genuinely odd runtime, not tamper).
    """
    try:
        rt = str(runtime_tag) if runtime_tag is not None else build_tag()
    except Exception:
        rt = ""
    if str(expected_tag) != rt:
        return GATE_VERSION_MISMATCH
    try:
        items = sorted((runtime_table or {}).items())
    except Exception:
        return GATE_OK
    hint_of = {}
    try:
        for spec in CRITICAL_FUNCTIONS:
            hint_of[str(spec[0])] = str(spec[1])
    except Exception:
        pass
    for path, want in items:
        try:
            obj = _resolve(str(path))
        except Exception:
            continue
        if obj is None:
            continue
        co = _code_of(obj, hint_of.get(str(path), "func"))
        if co is None:
            continue
        try:
            got = hashlib.sha256(bytes(co.co_code)).hexdigest()
        except Exception:
            continue
        if got != str(want):
            return GATE_MISMATCH
    return GATE_OK


def emit_audit_snippet(runtime_table, expected_tag, func_name="_nx_stdlib_gate"):
    # type: (dict, str, str) -> str
    """Return the emittable runtime gate snippet. Must compile().

    The snippet defines ``<func_name>()`` returning ``"ok"`` /
    ``"mismatch"`` / ``"version-mismatch"`` / ``"disabled"``. Callers
    enforce::

        _NX_STDLIB_GATE = _nx_stdlib_gate()
        if _NX_STDLIB_GATE == "mismatch":
            _nx_kill("stdlib-tamper")

    Bytecode-compare only (no source reads, no file I/O): each entry is
    resolved via ``__import__`` + attribute walk and its
    ``__code__.co_code`` sha256 compared. Unresolvable/code-less targets
    are skipped (frozen-layout safe). All literals embedded via
    ``repr`` (dotted paths + hex digests only). Stdlib only.
    """
    if not str(func_name).isidentifier():
        raise ValueError("func_name must be a valid identifier")
    try:
        tag = str(expected_tag)
    except Exception:
        raise ValueError("expected_tag must be a string")
    if not tag:
        raise ValueError("expected_tag must be non-empty")
    try:
        items = sorted((runtime_table or {}).items())
    except Exception:
        raise ValueError("runtime_table must be a mapping")
    clean = []
    for path, want in items:
        try:
            p = str(path)
            w = str(want)
        except Exception:
            continue
        if not p or not w or len(w) != 64:
            continue
        try:
            bytes.fromhex(w)
        except Exception:
            continue
        if "." not in p:
            continue
        clean.append((p, w))
    src = (
        "def %s():\n" % (func_name,)
        + "    import hashlib as _sa_hashlib\n"
        + "    import os as _sa_os\n"
        + "    import sys as _sa_sys\n"
        + "    _sa_tag = %r\n" % (tag,)
        + "    _sa_funcs = %r\n" % ([(p, w) for (p, w) in clean],)
        + "    try:\n"
        + "        _sa_off = str(_sa_os.environ.get(%r, '')) in %r\n" % (OPT_OUT_VAR, tuple(_OPT_OUT_TRUE))
        + "    except Exception:\n"
        + "        _sa_off = False\n"
        + "    if _sa_off:\n"
        + "        return \"disabled\"\n"
        + "    try:\n"
        + "        _sa_vi = _sa_sys.version_info\n"
        + "        _sa_rt = \"%d.%d.%d-\" % (_sa_vi[0], _sa_vi[1], _sa_vi[2]) + str(_sa_vi[3])\n"
        + "    except Exception:\n"
        + "        return \"version-mismatch\"\n"
        + "    if _sa_rt != _sa_tag:\n"
        + "        return \"version-mismatch\"\n"
        + "    for (_sa_path, _sa_want) in _sa_funcs:\n"
        + "        try:\n"
        + "            _sa_parts = str(_sa_path).split(\".\")\n"
        + "            _sa_obj = __import__(_sa_parts[0])\n"
        + "            for _sa_part in _sa_parts[1:]:\n"
        + "                _sa_obj = getattr(_sa_obj, _sa_part)\n"
        + "        except Exception:\n"
        + "            continue\n"
        + "        try:\n"
        + "            _sa_co = getattr(_sa_obj, \"__code__\", None)\n"
        + "            if _sa_co is None and isinstance(_sa_obj, type):\n"
        + "                try:\n"
        + "                    _sa_fn = vars(_sa_obj).get(\"__init__\", None)\n"
        + "                except Exception:\n"
        + "                    _sa_fn = None\n"
        + "                try:\n"
        + "                    _sa_fn = getattr(_sa_fn, \"__func__\", _sa_fn)\n"
        + "                except Exception:\n"
        + "                    pass\n"
        + "                _sa_co = getattr(_sa_fn, \"__code__\", None)\n"
        + "        except Exception:\n"
        + "            continue\n"
        + "        if _sa_co is None:\n"
        + "            continue\n"
        + "        try:\n"
        + "            _sa_got = _sa_hashlib.sha256(bytes(_sa_co.co_code)).hexdigest()\n"
        + "        except Exception:\n"
        + "            continue\n"
        + "        if _sa_got != _sa_want:\n"
        + "            return \"mismatch\"\n"
        + "    return \"ok\"\n"
    )
    compile(src, "<nx_stdlib_gate>", "exec")
    return src
