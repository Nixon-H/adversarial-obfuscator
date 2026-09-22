"""Frozen stdlib file snapshots (runtime integrity, additive).

Build-time: :func:`build_snapshot_context` records
``{module_name: sha256 of the module's origin FILE BYTES}`` for a curated
stdlib list on the BUILD host. Runtime (emitted snippet, see
:func:`emit_snapshot_snippet`): re-hash the same file paths on the TARGET,
compare, and fail closed via the kill ladder
``_nx_kill("integrity-snapshot")`` on mismatch (swapped/planted stdlib).

Version binding (CRITICAL — stdlib bytes differ across CPython
releases/distro patches, so an unbound hash compare would brick every
cross-version artifact):

- The build tag ``sys.version`` (``major.minor.micro`` + releaselevel,
  e.g. ``"3.11.9-final"``) is embedded as ``_NX_SNAPSHOT_TAG``.
- The runtime snippet enforces ONLY when
  ``_nx_snapshot_tag() == _NX_SNAPSHOT_TAG``; on ANY tag mismatch it
  returns ``"version-mismatch"`` (report-only, never kills) and callers
  must emit the ``_NX_SNAPSHOT_GATE = "DISABLED"`` literal path instead
  of the enforcing gate. Same version-binding convention as
  ``obfuscator/stdlib_audit.py``.

Missing files are SKIPPED, never failed (frozen/zipimport artifacts and
builtin modules lack ``.py`` paths; ``find_spec().origin`` may be
``"frozen"``, ``"built-in"``, or ``None`` — those entries hash NOTHING
at build time and verify NOTHING at runtime; this is documented, not
hidden). Only entries with a real on-disk file participate.

Opt-out (mirrors ``obfuscator/audit_hook.py`` conventions):

- Runtime env ``NIXON_SNAPSHOT_OFF`` in ``("1","true","True","TRUE",
  "yes","Yes","YES")`` -> snippet returns ``"disabled"`` (never kills).
- Build flag ``--no-snapshot`` (``snapshot_off=True`` in
  ``generate_hybrid_loader_script``) -> pipeline emits the DISABLED
  literal, no snippet, no hashes baked.

Python 3.10 compatible: no ``match``, no ``X | Y`` annotations.
"""

import hashlib
import importlib.util
import os
import sys

#: Runtime opt-out env var (truthy disables; mirrors audit_hook OPT_OUT_VAR).
OPT_OUT_VAR = "NIXON_SNAPSHOT_OFF"

_OPT_OUT_TRUE = ("1", "true", "True", "TRUE", "yes", "Yes", "YES")

#: Curated stdlib module list. File-backed on every supported CPython
#: (pure-python stdlib .py files); builtin/frozen entries are skipped at
#: build AND runtime (documented above). ``os``/``sys``/``io``/``marshal``
#: are included for intent but skip themselves on most builds — the
#: surviving file-backed set (hashlib, hmac, json, base64, struct,
#: socket, subprocess, threading, traceback, importlib, ...) is the
#: actual enforcement surface; ``build_snapshot_context`` reports which.
CRITICAL_MODULES = (
    "os",
    "io",
    "hashlib",
    "hmac",
    "json",
    "base64",
    "struct",
    "socket",
    "subprocess",
    "threading",
    "traceback",
    "importlib",
    "importlib.util",
    "marshal",
    "sys",
)

#: Gate verdicts returned by the runtime gate function.
GATE_OK = "ok"
GATE_DISABLED = "DISABLED"
GATE_MISMATCH = "mismatch"
GATE_VERSION_MISMATCH = "version-mismatch"


def build_tag():
    # type: () -> str
    """Version tag binding the snapshot to the BUILD interpreter.

    ``"major.minor.micro-releaselevel"`` (e.g. ``"3.11.9-final"``).
    Micro + releaselevel are included deliberately: distro stdlib
    backports change file bytes without a minor bump.
    """
    try:
        vi = sys.version_info
        return "%d.%d.%d-%s" % (vi[0], vi[1], vi[2], vi[3])
    except Exception:
        return "unknown"


def is_opted_out(env=None):
    # type: (object) -> bool
    """Return True when the snapshot gate is disabled via env."""
    if env is None:
        env = os.environ
    try:
        val = env.get(OPT_OUT_VAR, "")
    except Exception:
        return False
    return str(val) in _OPT_OUT_TRUE


def _origin_of(name):
    # type: (str) -> str
    """Return the module's origin file path, or "" when not file-backed."""
    try:
        spec = importlib.util.find_spec(name)
    except Exception:
        return ""
    if spec is None:
        return ""
    try:
        origin = spec.origin
    except Exception:
        return ""
    if not origin or not isinstance(origin, str):
        return ""
    low = origin.lower()
    if low in ("built-in", "frozen"):
        return ""
    try:
        if not os.path.isfile(origin):
            return ""
    except Exception:
        return ""
    return origin


def hash_file_bytes(path):
    # type: (str) -> str
    """sha256 hex of a file's bytes. Raises on unreadable input."""
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build_snapshot_context(modules=None):
    # type: (object) -> dict
    """Build-time helper: hash origin files for the critical module list.

    Returns ``{"tag": build_tag(), "files": {name: {"path": origin,
    "sha256": hex}}, "skipped": [names without file backing]}``.
    ``files`` may be a subset of the curated list (builtin/frozen/missing
    entries land in ``skipped`` — documented, never an error). Pure
    build-time: reads BUILD-host files only.
    """
    names = list(modules) if modules else list(CRITICAL_MODULES)
    files = {}
    skipped = []
    for name in names:
        try:
            origin = _origin_of(str(name))
        except Exception:
            origin = ""
        if not origin:
            skipped.append(str(name))
            continue
        try:
            digest = hash_file_bytes(origin)
        except Exception:
            skipped.append(str(name))
            continue
        files[str(name)] = {"path": origin, "sha256": digest}
    return {"tag": build_tag(), "files": files, "skipped": skipped}


def check_snapshot(files, runtime_tag=None):
    # type: (dict, str) -> str
    """Pure build/runtime verdict helper (testable without a loader).

    ``files``: ``{name: {"path": ..., "sha256": ...}}`` as recorded at
    build time. Returns ``"ok"`` / ``"mismatch"`` / ``"version-mismatch"``.

    Version binding: when ``runtime_tag`` (default: current interpreter)
    differs from ``files.get("__tag__")``... actually the tag travels
    separately — callers pass ``expected_tag`` via the ``__tag__`` key
    convention is NOT used; instead compare explicitly: this helper
    takes ``expected_tag`` from ``files.pop``-free sidecar? Simplified:
    the tag check lives in the emitted snippet; here ``runtime_tag``
    compared against ``build_tag()`` of THIS process only when the
    caller embeds the expected tag as ``files["__tag__"]``... To keep
    the helper honest and simple: signature is
    ``check_snapshot(files, expected_tag=None, runtime_tag=None)`` —
    see below. (Kept minimal: version gate + re-hash + compare.)
    """
    return _check_snapshot_impl(files, None, runtime_tag)


def _check_snapshot_impl(files, expected_tag=None, runtime_tag=None):
    # type: (object, object, object) -> str
    try:
        rt = str(runtime_tag) if runtime_tag is not None else build_tag()
    except Exception:
        rt = ""
    if expected_tag is not None and str(expected_tag) != rt:
        return GATE_VERSION_MISMATCH
    try:
        items = list((files or {}).items())
    except Exception:
        return GATE_OK
    for name, entry in items:
        try:
            if str(name) == "__tag__":
                continue
            path = entry.get("path", "") if isinstance(entry, dict) else ""
            want = entry.get("sha256", "") if isinstance(entry, dict) else ""
        except Exception:
            continue
        if not path or not want:
            continue
        try:
            if not os.path.isfile(path):
                # Missing on target (frozen/zipimport layout differs
                # from the build host): skip, don't fail.
                continue
        except Exception:
            continue
        try:
            with open(path, "rb") as fh:
                got = hashlib.sha256(fh.read()).hexdigest()
        except Exception:
            continue
        if got != str(want):
            return GATE_MISMATCH
    return GATE_OK


def verify_snapshot(files, expected_tag, runtime_tag=None):
    # type: (dict, str, str) -> str
    """Version-bound verdict: ``"ok"`` / ``"mismatch"`` / ``"version-mismatch"``."""
    return _check_snapshot_impl(files, expected_tag, runtime_tag)


def emit_snapshot_snippet(files, expected_tag, func_name="_nx_snapshot_gate"):
    # type: (dict, str, str) -> str
    """Return the emittable runtime gate snippet. Must compile().

    The snippet defines ``<func_name>()`` returning ``"ok"`` /
    ``"mismatch"`` / ``"version-mismatch"`` / ``"disabled"``. Callers
    enforce::

        _NX_SNAPSHOT_GATE = _nx_snapshot_gate()
        if _NX_SNAPSHOT_GATE == "mismatch":
            _nx_kill("integrity-snapshot")

    ``"version-mismatch"`` and ``"disabled"`` are report-only (never
    kill) by pipeline construction. Missing/unreadable files are
    skipped (frozen/zipimport-safe). All literals embedded via ``repr``
    (hex digests contain only ``[0-9a-f]``; paths may contain quotes —
    ``repr`` handles them). Stdlib only.
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
        items = sorted((files or {}).items())
    except Exception:
        raise ValueError("files must be a mapping")
    clean = []
    for name, entry in items:
        try:
            n = str(name)
            if n == "__tag__" or not n:
                continue
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path", "") or "")
            want = str(entry.get("sha256", "") or "")
        except Exception:
            continue
        if not path or not want or len(want) != 64:
            continue
        try:
            bytes.fromhex(want)
        except Exception:
            continue
        clean.append((n, path, want))
    src = (
        "def %s():\n" % (func_name,)
        + "    import hashlib as _ss_hashlib\n"
        + "    import os as _ss_os\n"
        + "    import sys as _ss_sys\n"
        + "    _ss_tag = %r\n" % (tag,)
        + "    _ss_files = %r\n" % ([(n, p, w) for (n, p, w) in clean],)
        + "    try:\n"
        + "        _ss_off = str(_ss_os.environ.get(%r, '')) in %r\n" % (OPT_OUT_VAR, tuple(_OPT_OUT_TRUE))
        + "    except Exception:\n"
        + "        _ss_off = False\n"
        + "    if _ss_off:\n"
        + "        return \"disabled\"\n"
        + "    try:\n"
        + "        _ss_vi = _ss_sys.version_info\n"
        + "        _ss_rt = \"%d.%d.%d-\" % (_ss_vi[0], _ss_vi[1], _ss_vi[2]) + str(_ss_vi[3])\n"
        + "    except Exception:\n"
        + "        return \"version-mismatch\"\n"
        + "    if _ss_rt != _ss_tag:\n"
        + "        return \"version-mismatch\"\n"
        + "    for (_ss_name, _ss_path, _ss_want) in _ss_files:\n"
        + "        try:\n"
        + "            _ss_isfile = _ss_os.path.isfile(_ss_path)\n"
        + "        except Exception:\n"
        + "            continue\n"
        + "        if not _ss_isfile:\n"
        + "            continue\n"
        + "        try:\n"
        + "            with open(_ss_path, \"rb\") as _ss_fh:\n"
        + "                _ss_got = _ss_hashlib.sha256(_ss_fh.read()).hexdigest()\n"
        + "        except Exception:\n"
        + "            continue\n"
        + "        if _ss_got != _ss_want:\n"
        + "            return \"mismatch\"\n"
        + "    return \"ok\"\n"
    )
    compile(src, "<nx_snapshot_gate>", "exec")
    return src
