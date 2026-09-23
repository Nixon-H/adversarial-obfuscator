"""Unified single-failure-path kill ladder (V10).

V10 claim: "any tamper trigger wipes key material and exits on the
first strike". This module is the single choke point for that path:

- build-time/testable :func:`nx_kill` (with a ``dry_run`` test seam),
- emittable runtime snippet :func:`emit_kill_snippet` defining
  ``_nx_kill(reason, holders=None)`` for loaders/bootstrap snippets.

Semantics (both implementations, kept in sync):

(a) overwrite known key buffers: ``bytearray`` / ``memoryview`` holders
    are zeroed in place; ``bytes`` are immutable so they can only be
    dropped (``del`` of known key globals such as ``BLOB_KEY``);
(b) NO detached self-corruption here: the ladder is wipe + exit only.
    Corruption (``SELF_CORRUPT_DETACHED`` in ``obfuscator/macros.py``)
    stays a separate opt-in;
(c) exit code 137 ALWAYS (the kill-ladder code, shared with
    ``native/crash_suppress.h`` ``nixon_silent_kill`` / fatal handler).
    ``os._exit`` is used, never ``sys.exit`` — ``os._exit`` skips
    cleanup handlers (atexit/finally/flush) that could dump state;
(d) single choke point: every migrated gate (vm_score, driver_blocklist,
    audit_hook, trial/watermark enforcement) calls ``_nx_kill``; nothing
    else exits directly. No warn tier in the ladder itself (Monitor
    tiers stay in ``runtime/src/hydra.rs``; the ladder is the Enforce
    end — first strike exits);
(e) silent kill (crash_suppress philosophy): no stdout/stderr output by
    default. ``NIXON_LADDER_DEBUG=1`` prints the reason to stderr for
    diagnostics.

Python 3.10 compatible: no ``match``, no ``X | Y`` annotations.
"""

import os

#: Kill-ladder exit code. Shared with native/crash_suppress.h
#: (nixon_silent_kill / fatal-signal handler both use 137).
KILL_CODE = 137

#: Diagnostics opt-in env var (default silent).
DEBUG_VAR = "NIXON_LADDER_DEBUG"

#: Valid reason codes. The build-time :func:`nx_kill` raises ValueError
#: on anything else; the runtime snippet does NOT validate (fail
#: closed: any call kills, even with an unexpected reason string).
REASON_CODES = frozenset([
    "vm-detect",
    "driver-blocked",
    "audit-plant",
    "audit-timing",
    "trial-expired",
    "trial-tampered",
    "trial-rollback",
    "watermark-tampered",
    "watermark-missing",
    "integrity-snapshot",
    "stdlib-tamper",
    "hwid-mismatch",
])

#: Key-material global names deleted on the kill path (immutable
#: ``bytes`` holders cannot be zeroed in place, so the names are
#: dropped instead).
KEY_GLOBALS = ("BLOB_KEY", "BLOB_KEY_SB")


def _wipe_object(obj):
    # type: (object) -> str
    """Best-effort in-place wipe of one holder. Returns action label."""
    try:
        if isinstance(obj, bytearray):
            try:
                ln = len(obj)
            except Exception:
                return "wipe:bytearray:?"
            try:
                for _i in range(ln):
                    obj[_i] = 0
            except Exception:
                pass
            return "wipe:bytearray:%d" % (ln,)
        if isinstance(obj, memoryview):
            try:
                ln = len(obj)
            except Exception:
                return "wipe:memoryview:?"
            try:
                obj[:] = b"\x00" * ln
            except Exception:
                # Read-only view (e.g. over bytes): cannot wipe in place.
                pass
            return "wipe:memoryview:%d" % (ln,)
    except Exception:
        pass
    return "drop:%s" % (type(obj).__name__,)


def _sweep_namespace(ns):
    # type: (object) -> list
    """Zero mutable buffers in a namespace dict + del key globals."""
    actions = []
    try:
        try:
            vals = list(ns.values())
        except Exception:
            return ["sweep:error"]
        for _v in vals:
            try:
                if isinstance(_v, (bytearray, memoryview)):
                    actions.append(_wipe_object(_v))
            except Exception:
                continue
        for _k in KEY_GLOBALS:
            try:
                if _k in ns:
                    try:
                        del ns[_k]
                    except Exception:
                        pass
                    actions.append("del:%s" % (_k,))
            except Exception:
                continue
    except Exception:
        actions.append("sweep:error")
    return actions


def _collect_holders(key_holders):
    # type: (object) -> list
    """Normalize the ``key_holders`` argument to a flat holder list."""
    try:
        if key_holders is None:
            return []
        if isinstance(key_holders, dict):
            return [key_holders]
        return list(key_holders)
    except Exception:
        return []


def nx_kill(reason, key_holders=None, dry_run=False):
    # type: (str, object, bool) -> list
    """Canonical kill path: wipe key material, then exit 137.

    ``reason`` must be one of :data:`REASON_CODES` (ValueError
    otherwise). ``key_holders`` is an iterable of key buffers
    (``bytearray`` / ``memoryview`` zeroed in place; anything else is
    just dropped) and/or namespace dicts (swept: mutable values wiped,
    :data:`KEY_GLOBALS` deleted).

    When ``dry_run`` is True the wipe is still performed but the
    process does NOT exit; instead the action list is returned
    (test seam: proves "buffers zeroed before exit" in-process, ending
    with ``"exit:137"``). Otherwise this function does not return:
    silent by default (``NIXON_LADDER_DEBUG=1`` prints the reason to
    stderr), then ``os._exit(137)``.
    """
    if reason not in REASON_CODES:
        raise ValueError("unknown kill-ladder reason: %r" % (reason,))
    actions = []
    for _h in _collect_holders(key_holders):
        try:
            if isinstance(_h, dict):
                actions.extend(_sweep_namespace(_h))
            else:
                actions.append(_wipe_object(_h))
        except Exception:
            actions.append("wipe:error")
    if dry_run:
        actions.append("exit:%d" % (KILL_CODE,))
        return actions
    try:
        if os.environ.get(DEBUG_VAR, "0") == "1":
            try:
                import sys as _sys
                _sys.stderr.write("nx-kill:%s\n" % (reason,))
                _sys.stderr.flush()
            except Exception:
                pass
    except Exception:
        pass
    os._exit(KILL_CODE)


def emit_kill_snippet():
    # type: () -> str
    """Return the emittable ``_nx_kill`` snippet source. Must compile().

    Defines ``_nx_kill(reason, holders=None)`` with the same semantics
    as :func:`nx_kill` minus validation (fail closed: any call kills)
    and minus ``dry_run`` (runtime always kills). Self-contained: does
    its own ``import os`` aliased ``_nx_os`` so it composes with any
    gate snippet regardless of that snippet's import aliases. Silent
    by default; ``NIXON_LADDER_DEBUG=1`` writes the reason to fd 2.
    """
    src = (
        "def _nx_kill(_reason=\"\", _holders=None):\n"
        "    import os as _nx_os\n"
        "    try:\n"
        "        _nx_seen = []\n"
        "        try:\n"
        "            if _holders is not None:\n"
        "                if isinstance(_holders, dict):\n"
        "                    _nx_seen.extend(list(_holders.values()))\n"
        "                else:\n"
        "                    _nx_seen.extend(list(_holders))\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            _nx_g = globals()\n"
        "        except Exception:\n"
        "            _nx_g = {}\n"
        "        try:\n"
        "            _nx_seen.extend(list(_nx_g.values()))\n"
        "        except Exception:\n"
        "            pass\n"
        "        for _nx_h in _nx_seen:\n"
        "            try:\n"
        "                if isinstance(_nx_h, bytearray):\n"
        "                    for _nx_i in range(len(_nx_h)):\n"
        "                        _nx_h[_nx_i] = 0\n"
        "                elif isinstance(_nx_h, memoryview):\n"
        "                    try:\n"
        "                        _nx_h[:] = b\"\\x00\" * len(_nx_h)\n"
        "                    except Exception:\n"
        "                        pass\n"
        "            except Exception:\n"
        "                continue\n"
        "        try:\n"
        "            for _nx_kn in (\"BLOB_KEY\", \"BLOB_KEY_SB\"):\n"
        "                try:\n"
        "                    if _nx_kn in _nx_g:\n"
        "                        del _nx_g[_nx_kn]\n"
        "                except Exception:\n"
        "                    pass\n"
        "        except Exception:\n"
        "            pass\n"
        "    except Exception:\n"
        "        pass\n"
        "    try:\n"
        "        if _nx_os.environ.get(\"NIXON_LADDER_DEBUG\", \"0\") == \"1\":\n"
        "            try:\n"
        "                _nx_os.write(2, (\"nx-kill:\" + str(_reason) + \"\\n\").encode(\"utf-8\", \"ignore\")[:256])\n"
        "            except Exception:\n"
        "                pass\n"
        "    except Exception:\n"
        "        pass\n"
        "    _nx_os._exit(137)\n"
        "    import sys as _nx_sys\n"
        "    _nx_sys.exit(137)\n"
    )
    compile(src, "<nx_kill_ladder>", "exec")
    return src
