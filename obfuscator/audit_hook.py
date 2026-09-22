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
   (``os._exit(1)`` — the same fail-closed primitive the emitted
   vm_score loader snippet uses), unless opted out via
   ``NIXON_AUDITHOOK_PLANT_OFF`` (any of ``1/true/yes``; default ON).

Design notes (additive, fail-safe):

- Legit in-tree hooks (frames all outside site-packages, entry module
  in-tree) are passed through untouched.
- Frozen/builtin frames (no ``__file__``) are skipped, never flagged.
- The wrapper is installed once (``_NX_AUDIT_WRAPPED`` guard) and calls
  through to the ORIGINAL ``sys.addaudithook`` so semantics are
  preserved for legit callers.
- The snippet is registry-free: no new runtime dependency, compiles on
  3.10+ (no ``match``, no ``X | Y`` annotations).
"""

from __future__ import annotations

import os

OPT_OUT_VAR = "NIXON_AUDITHOOK_PLANT_OFF"

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
    src = (
        "import os as _os\n"
        "import sys as _sys\n"
        "\n"
        "_NX_AUDIT_OPT_OUT = _os.environ.get(%r, '') in %r\n"
        % (OPT_OUT_VAR, tuple(_OPT_OUT_TRUE))
        + "if not _NX_AUDIT_OPT_OUT and not globals().get('_NX_AUDIT_WRAPPED', False):\n"
        "    globals()['_NX_AUDIT_WRAPPED'] = True\n"
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
        "                try:\n"
        "                    _os._exit(1)\n"
        "                except Exception:\n"
        "                    pass\n"
        "                _sys.exit(1)\n"
        "            return _nx_orig_addaudithook(_hook, *args, **kwargs)\n"
        "        try:\n"
        "            _sys.addaudithook = _nx_addaudithook\n"
        "        except Exception:\n"
        "            pass\n"
    )
    compile(src, "<nx_audit_hook>", "exec")
    return src
