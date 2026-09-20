"""Python version matrix for code-object feature gating (Phase 5 hygiene).

Centralizes CPython minor-version knowledge so pipeline stages can gate
features instead of probing ``sys.version_info`` ad hoc.

Bypass var (CI-only scope, batch 3):
    ``NIXON_VERIFY_SKIP_VERSION_CHECK`` — when set to a truthy value AND
    a CI gate var (``NIXON_CI`` or ``NIXON_ALLOW_SKIP``) is also truthy, the
    snippet produced by :func:`emit_version_gate` skips the version check.
    Both vars are required: SKIP alone holds the gate. This exists ONLY for
    CI jobs that exercise cross-version fixtures; it must never be set in
    production builds because loading a payload built for another minor
    version misbuilds code objects. Rule: new version-gate bypasses
    require the CI scope.
"""

from __future__ import annotations

import os
import sys
from typing import TypedDict


class _FeatureInfo(TypedDict):
    min: tuple
    added: str
    note: str

SUPPORTED = [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14)]

CURRENT = (sys.version_info[0], sys.version_info[1])

FEATURES: dict[str, _FeatureInfo] = {
    "nyser_exceptiontable": {
        "min": (3, 11),
        "added": "3.11",
        "note": "co_exceptiontable introduced (PEP 657 / zero-cost exceptions)",
    },
    "exceptiontable_rebuild": {
        "min": (3, 11),
        "added": "3.11",
        "note": "NYSER1 rebuild passes co_exceptiontable via Code.replace",
    },
    "linetable": {
        "min": (3, 10),
        "added": "3.10",
        "note": "co_linetable replaces co_lnotab (PEP 626)",
    },
    "per_opcode_cache": {
        "min": (3, 11),
        "added": "3.11",
        "note": "adaptive interpreter per-opcode caches (PEP 659)",
    },
    "co_positions": {
        "min": (3, 10),
        "added": "3.10",
        "note": "co_positions() column-offset API (PEP 626)",
    },
    "adaptive_specialization": {
        "min": (3, 11),
        "added": "3.11",
        "note": "specializing adaptive interpreter (PEP 659)",
    },
    "type_params": {
        "min": (3, 12),
        "added": "3.12",
        "note": "PEP 695 type-parameter syntax (co_typeparams)",
    },
    "fstring_tokens": {
        "min": (3, 12),
        "added": "3.12",
        "note": "PEP 701 tokenized f-strings (new FSTRING_MIDDLE opcodes)",
    },
    "marshal_version": {
        "min": (3, 10),
        "added": "3.10",
        "note": "marshal format baseline pinned at 3.10+ code objects",
    },
    "annotation_scope": {
        "min": (3, 12),
        "added": "3.12",
        "note": "PEP 695 annotation scopes on functions/classes",
    },
    "deferred_annotations": {
        "min": (3, 14),
        "added": "3.14",
        "note": "PEP 649/749 deferred annotation evaluation (co_annotations behavior change)",
    },
    "template_strings": {
        "min": (3, 14),
        "added": "3.14",
        "note": "PEP 750 template-string literals (new TEMPLATE_STR opcodes)",
    },
    "code_qualname": {
        "min": (3, 11),
        "added": "3.11",
        "note": "co_qualname present (3.11+); 3.14 keeps layout, NYSER1 rebuild unaffected",
    },
}

_BYPASS_VAR = "NIXON_VERIFY_SKIP_VERSION_CHECK"
_CI_GATE_VARS = ("NIXON_CI", "NIXON_ALLOW_SKIP")


def _is_truthy(value: str | None) -> bool:
    return value not in (None, "", "0", "false", "False", "no", "No")


def supports(feature: str) -> bool:
    """Return True if ``feature`` is supported on CURRENT."""
    info = FEATURES.get(feature)
    if info is None:
        raise KeyError(f"unknown feature: {feature!r}")
    min_ver = info["min"]
    assert isinstance(min_ver, tuple)
    return CURRENT >= min_ver


def gate(feature: str) -> None:
    """Raise RuntimeError if ``feature`` is unsupported on CURRENT."""
    info = FEATURES.get(feature)
    if info is None:
        raise KeyError(f"unknown feature: {feature!r}")
    if not supports(feature):
        min_ver = info["min"]
        raise RuntimeError(
            f"feature {feature!r} requires Python "
            f"{min_ver[0]}.{min_ver[1]}+ (added {info['added']}); "
            f"running on {CURRENT[0]}.{CURRENT[1]}. {info['note']}"
        )


def matrix_table() -> str:
    """ASCII table of feature x supported-on-CURRENT."""
    header_f = "feature"
    header_s = f"3.{CURRENT[1]}?"
    width_f = max(len(header_f), max(len(f) for f in FEATURES))
    width_s = max(len(header_s), len("yes"), len("no"))
    lines = [
        f"{header_f:<{width_f}}  {header_s:<{width_s}}  min",
        f"{'-' * width_f}  {'-' * width_s}  ---",
    ]
    for name in sorted(FEATURES):
        info = FEATURES[name]
        min_ver = info["min"]
        assert isinstance(min_ver, tuple)
        supported = "yes" if supports(name) else "no"
        lines.append(
            f"{name:<{width_f}}  {supported:<{width_s}}  "
            f"{min_ver[0]}.{min_ver[1]}"
        )
    return "\n".join(lines)


def emit_version_gate(required: tuple) -> str:
    """Return a Python source snippet enforcing ``required`` version.

    The snippet exits via ``sys.exit(1)`` with a clear message when
    ``sys.version_info[:2] != required`` unless BOTH the bypass env var
    ``NIXON_VERIFY_SKIP_VERSION_CHECK`` AND a CI gate var (``NIXON_CI``
    or ``NIXON_ALLOW_SKIP``) are truthy. SKIP alone holds the gate, so
    production artifacts cannot bypass with a single env var.
    """
    req_major, req_minor = required[0], required[1]
    gate_vars = ", ".join(repr(v) for v in _CI_GATE_VARS)
    return (
        "import os as _os\n"
        "import sys as _sys\n"
        f"_req = ({req_major!r}, {req_minor!r})\n"
        f"_bypass = _os.environ.get({_BYPASS_VAR!r})\n"
        "_bypass_on = _bypass not in (None, '', '0', 'false', 'False', 'no', 'No')\n"
        f"_ci_on = any(_os.environ.get(_v) not in (None, '', '0', 'false', 'False', 'no', 'No') for _v in ({gate_vars},))\n"
        "if tuple(_sys.version_info[:2]) != _req and not (_bypass_on and _ci_on):\n"
        "    _sys.stderr.write(\n"
        "        f'version mismatch: required {_req[0]}.{_req[1]} '\n"
        "        f'but running '\n"
        "        f'{_sys.version_info[0]}.{_sys.version_info[1]}; '\n"
        f"        f'set {_BYPASS_VAR} + CI gate to bypass (CI only)' + chr(10))\n"
        "    _sys.exit(1)\n"
    )
