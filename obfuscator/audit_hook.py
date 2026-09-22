"""Site-packages audit-hook plant detection (#27 audit gap, Batch B).

An attacker who can write into ``site-packages`` (or ``dist-packages``)
can plant a ``.pth`` file, a sitecustomize/usercustomize module, or any
third-party package whose import-time code calls ``sys.addaudithook``.
Once installed, that hook observes every audit event of the protected
process (imports, ``open``, socket connects, subprocess spawns).

This module provides a small runtime snippet (:func:`emit_snippet`)
installed at loader bootstrap. At bootstrap the snippet:

1. Wraps ``sys.addaudithook`` so every FUTURE hook addition is
   attributed: the caller's stack frames are walked and any frame whose
   ``__file__`` resolves inside ``site-packages`` / ``dist-packages``
   (while the protected entry module itself is NOT in site-packages)
   is treated as a plant.
2. Refuses the plant via the project's standard tamper path
   (the kill ladder ``_nx_kill("audit-plant")``, exit 137), unless
   opted out via ``NIXON_AUDITHOOK_PLANT_OFF`` (any of
   ``1/true/yes``; default ON).

Design notes (additive, fail-safe):

- Legit in-tree hooks (frames all outside site-packages, entry module
  in-tree) are passed through untouched.
- Frozen/builtin frames (no ``__file__``) are skipped, never flagged.
- The wrapper is installed once (``_NX_AUDIT_WRAPPED`` guard) and calls
  through to the ORIGINAL ``sys.addaudithook`` so semantics are
  preserved for legit callers.
- The snippet is registry-free: no new runtime dependency, compiles on
  3.10+ (no ``match``, no ``X | Y`` annotations).

V10 audit sub-claim "hook-addition detection + TIMING" (additive):

- Every passthrough registration through the wrapper bumps
  ``_NX_AUDIT_ADDED`` (addition counting at the registration gate).
- ``_NX_AUDIT_WRAPPER_ID`` records ``id()`` of the installed wrapper;
  ``_nx_audit_verify()`` re-checks ``sys.addaudithook is
  _nx_addaudithook`` (replacement detected -> fail closed via
  ``_nx_kill("audit-plant")``).
- A bootstrap canary observer (registered DIRECTLY via the original
  ``addaudithook``, bypassing the wrapper so bootstrap never
  self-flags) counts ``nixon.canary`` events in ``_NX_AUDIT_SEEN``.
  Honest limitation: CPython exposes NO public API to enumerate
  installed audit hooks, so full enumeration is impossible from
  Python. The canary instead proves (i) our observer is still live in
  the hook chain and (ii) no foreign hook ahead of it raises/blocks
  delivery (audit delivery stops at the first raising hook, so a
  blocking hook either raises out of ``sys.audit`` or stalls our
  counter — both fail closed). A purely PASSIVE pre-existing hook is
  invisible to the canary by design (it does not perturb execution);
  later additions are gated by the wrapper above.
- TIMING: install records ``time.perf_counter_ns()`` (``_NX_AUDIT_T0``)
  plus a baseline mean latency over 50 canary audits
  (``_NX_AUDIT_BASE_MEAN``). Verify re-measures 50 canaries; a mean
  above ``max(10x baseline, 500us floor)`` returns the ``"timing"``
  verdict (tracers/debuggers inflate per-event latency massively).
  Timing is report-only by DEFAULT (Monitor semantics, mirroring the
  vm_score ``NIXON_KOD`` gate); ``NIXON_AUDIT_TIMING`` set to a
  non-``"0"`` value arms the kill path (``_nx_kill("audit-timing")``).
  Plant/addition verdicts always kill regardless of that flag.
- ``_nx_audit_verify()`` runs once at bootstrap (post-baseline) and
  stays defined for periodic re-checks by hydra/background threads
  (no threads are started inside the snippet).
"""

from __future__ import annotations

import os

OPT_OUT_VAR = "NIXON_AUDITHOOK_PLANT_OFF"

#: Arm flag for timing enforcement. Mirrors the vm_score ``NIXON_KOD``
#: gate (default report-only): any value other than ``"0"`` (and unset
#: treated as disarmed) routes the ``"timing"`` verdict through the
#: kill ladder. Plant/addition verdicts always kill regardless.
TIMING_VAR = "NIXON_AUDIT_TIMING"

#: Canary audit event name observed by the bootstrap canary hook.
CANARY_EVENT = "nixon.canary"

#: Number of canary audits used for the timing baseline / re-measure.
TIMING_SAMPLES = 50

#: Absolute floor for the timing verdict (ns). Avoids false positives
#: on heavily loaded hosts where the install baseline itself is slow.
TIMING_FLOOR_NS = 500000

#: Multiplicative factor over the install baseline that flags timing.
TIMING_FACTOR = 10

_OPT_OUT_TRUE = ("1", "true", "True", "TRUE", "yes", "Yes", "YES")


def is_opted_out(env=None) -> bool:
    """Return True when the plant detector is disabled via env."""
    if env is None:
        env = os.environ
    try:
        val = env.get(OPT_OUT_VAR, "")
    except Exception:
        return False
    return str(val) in _OPT_OUT_TRUE


def is_timing_armed(env=None) -> bool:
    """Return True when timing-kill is armed via ``NIXON_AUDIT_TIMING``.

    Mirrors the vm_score ``NIXON_KOD`` gate: default (unset/``"0"``)
    is report-only; any other value arms the kill path.
    """
    if env is None:
        env = os.environ
    try:
        val = env.get(TIMING_VAR, "0")
    except Exception:
        return False
    return str(val) != "0"


def _is_site_path(path):
    # type: (object) -> bool
    try:
        low = str(path).lower().replace("\\", "/")
    except Exception:
        return False
    return "site-packages" in low or "dist-packages" in low


def hook_frame_is_plant(filenames, entry_file=None):
    """Decide plant vs legit from a list of caller filenames.

    ``filenames``: outermost..innermost caller ``__file__`` values (or
    None for frames without one). ``entry_file``: ``__file__`` of the
    protected entry module. Returns True (plant) when ANY caller frame
    resolves inside site-packages/dist-packages while the entry module
    is NOT itself in site-packages. All other cases -> False.
    """
    try:
        entry_in_site = _is_site_path(entry_file) if entry_file else False
    except Exception:
        entry_in_site = False
    if entry_in_site:
        return False
    try:
        for name in filenames or []:
            if name and _is_site_path(name):
                return True
    except Exception:
        return False
    return False


def emit_snippet() -> str:
    """Return the bootstrap snippet source. Must compile on 3.10+."""
    from obfuscator.kill_ladder import emit_kill_snippet as _kl_emit
    _kl_src = _kl_emit()
    src = (
        "import os as _os\n"
        "import sys as _sys\n"
        "\n"
        + _kl_src +
        "\n"
        "_NX_AUDIT_OPT_OUT = _os.environ.get(%r, '') in %r\n"
        % (OPT_OUT_VAR, tuple(_OPT_OUT_TRUE))
        + "if not _NX_AUDIT_OPT_OUT and not globals().get('_NX_AUDIT_WRAPPED', False):\n"
        "    globals()['_NX_AUDIT_WRAPPED'] = True\n"
        "    # NOTE: CPython exposes no public API to enumerate installed\n"
        "    # audit hooks, so full enumeration from Python is impossible.\n"
        "    # The canary below instead proves our observer is still live\n"
        "    # and no foreign hook ahead of it raises/blocks delivery.\n"
        "    try:\n"
        "        _nx_entry_file = globals().get('__file__', None)\n"
        "    except Exception:\n"
        "        _nx_entry_file = None\n"
        "    try:\n"
        "        _nx_orig_addaudithook = _sys.addaudithook\n"
        "    except Exception:\n"
        "        _nx_orig_addaudithook = None\n"
        "    if _nx_orig_addaudithook is not None:\n"
        "        def _nx_is_site_path(_p):\n"
        "            try:\n"
        "                _low = str(_p).lower().replace(chr(92), '/')\n"
        "            except Exception:\n"
        "                return False\n"
        "            return ('site-packages' in _low) or ('dist-packages' in _low)\n"
        "        def _nx_addaudithook(_hook, *args, **kwargs):\n"
        "            try:\n"
        "                _entry_in_site = bool(_nx_entry_file) and _nx_is_site_path(_nx_entry_file)\n"
        "            except Exception:\n"
        "                _entry_in_site = False\n"
        "            _plant = False\n"
        "            if not _entry_in_site:\n"
        "                try:\n"
        "                    _frm = _sys._getframe(1)\n"
        "                    while _frm is not None:\n"
        "                        try:\n"
        "                            _fn = _frm.f_code.co_filename\n"
        "                        except Exception:\n"
        "                            _fn = None\n"
        "                        if _fn and _nx_is_site_path(_fn):\n"
        "                            _plant = True\n"
        "                            break\n"
        "                        _frm = _frm.f_back\n"
        "                except Exception:\n"
        "                    _plant = False\n"
        "            if _plant:\n"
        "                _nx_kill(\"audit-plant\")\n"
        "            try:\n"
        "                _r = _nx_orig_addaudithook(_hook, *args, **kwargs)\n"
        "            except Exception:\n"
        "                raise\n"
        "            try:\n"
        "                globals()['_NX_AUDIT_ADDED'] = int(globals().get('_NX_AUDIT_ADDED', 0)) + 1\n"
        "            except Exception:\n"
        "                pass\n"
        "            return _r\n"
        "        try:\n"
        "            _sys.addaudithook = _nx_addaudithook\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            globals()['_NX_AUDIT_WRAPPER_ID'] = id(_nx_addaudithook)\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            globals().setdefault('_NX_AUDIT_ADDED', 0)\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            globals().setdefault('_NX_AUDIT_SEEN', 0)\n"
        "        except Exception:\n"
        "            pass\n"
        "        def _nx_audit_canary(_ev, _args):\n"
        "            try:\n"        "                if _ev == \"nixon.canary\":\n"
        "                    try:\n"
        "                        globals()['_NX_AUDIT_SEEN'] = int(globals().get('_NX_AUDIT_SEEN', 0)) + 1\n"
        "                    except Exception:\n"
        "                        pass\n"
        "            except Exception:\n"
        "                pass\n"
        "        try:\n"
        "            _nx_orig_addaudithook(_nx_audit_canary)\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            import time as _nx_time\n"
        "        except Exception:\n"
        "            _nx_time = None\n"
        "        try:\n"
        "            globals()['_NX_AUDIT_T0'] = _nx_time.perf_counter_ns() if _nx_time is not None else 0\n"
        "        except Exception:\n"
        "            try:\n"
        "                globals()['_NX_AUDIT_T0'] = 0\n"
        "            except Exception:\n"
        "                pass\n"
        "        def _nx_audit_baseline():\n"
        "            try:\n"
        "                _t = _nx_time\n"
        "            except Exception:\n"
        "                _t = None\n"
        "            if _t is None:\n"
        "                return 0\n"
        "            try:\n"
        "                _before = int(globals().get('_NX_AUDIT_SEEN', 0))\n"
        "            except Exception:\n"
        "                _before = 0\n"
        "            try:\n"
        "                _s = _sys.audit\n"
        "            except Exception:\n"
        "                return 0\n"
        "            try:\n"
        "                _t0 = _t.perf_counter_ns()\n"
        "            except Exception:\n"
        "                return 0\n"
        "            for _i in range(50):\n"
        "                try:\n"
        "                    _s(\"nixon.canary\")\n"
        "                except Exception:\n"
        "                    return -1\n"
        "            try:\n"
        "                _t1 = _t.perf_counter_ns()\n"
        "            except Exception:\n"
        "                return -1\n"
        "            try:\n"
        "                _after = int(globals().get('_NX_AUDIT_SEEN', 0))\n"
        "            except Exception:\n"
        "                _after = _before\n"
        "            if (_after - _before) < 50:\n"
        "                return -1\n"
        "            try:\n"
        "                _mean = (_t1 - _t0) // 50\n"
        "            except Exception:\n"
        "                return 0\n"
        "            if _mean <= 0:\n"
        "                return 1\n"
        "            return _mean\n"
        "        try:\n"
        "            globals()['_NX_AUDIT_BASE_MEAN'] = _nx_audit_baseline()\n"
        "        except Exception:\n"
        "            try:\n"
        "                globals()['_NX_AUDIT_BASE_MEAN'] = 0\n"
        "            except Exception:\n"
        "                pass\n"
        "        def _nx_audit_verify():\n"
        "            try:\n"
        "                _cur = _sys.addaudithook\n"
        "            except Exception:\n"
        "                _cur = None\n"
        "            try:\n"
        "                _mine = globals().get('_nx_addaudithook', None)\n"
        "            except Exception:\n"
        "                _mine = None\n"
        "            if _mine is not None and _cur is not _mine:\n"
        "                _nx_kill(\"audit-plant\")\n"
        "                return \"replaced\"\n"
        "            if _mine is None:\n"
        "                try:\n"
        "                    _wid = int(globals().get('_NX_AUDIT_WRAPPER_ID', 0))\n"
        "                except Exception:\n"
        "                    _wid = 0\n"
        "                if _wid and _cur is not None:\n"
        "                    try:\n"
        "                        _same = (id(_cur) == _wid)\n"
        "                    except Exception:\n"
        "                        _same = False\n"
        "                    if not _same:\n"
        "                        _nx_kill(\"audit-plant\")\n"
        "                        return \"replaced\"\n"
        "            try:\n"
        "                _m = _nx_audit_baseline()\n"
        "            except Exception:\n"
        "                _m = 0\n"
        "            if _m == -1:\n"
        "                _nx_kill(\"audit-plant\")\n"
        "                return \"canary-blocked\"\n"
        "            if _m > 0:\n"
        "                try:\n"
        "                    _base = int(globals().get('_NX_AUDIT_BASE_MEAN', 0))\n"
        "                except Exception:\n"
        "                    _base = 0\n"
        "                _thresh = 500000\n"
        "                try:\n"
        "                    _cand = int(_base) * 10\n"
        "                    if _cand > _thresh:\n"
        "                        _thresh = _cand\n"
        "                except Exception:\n"
        "                    pass\n"
        "                if _m > _thresh:\n"
        "                    try:\n"
        "                        _armed = (_os.environ.get(\"NIXON_AUDIT_TIMING\", \"0\") != \"0\")\n"
        "                    except Exception:\n"
        "                        _armed = False\n"
        "                    if _armed:\n"
        "                        _nx_kill(\"audit-timing\")\n"
        "                    return \"timing\"\n"
        "            return \"ok\"\n"
        "        try:\n"
        "            _nx_audit_verify()\n"
        "        except SystemExit:\n"
        "            raise\n"
        "        except BaseException:\n"
        "            pass\n"
        "        # Periodic re-check hook: hydra/background threads may call\n"
        "        # _nx_audit_verify() at any time (report-only unless armed).\n"
    )
    compile(src, "<nx_audit_hook>", "exec")
    return src
