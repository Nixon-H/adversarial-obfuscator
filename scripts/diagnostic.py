"""Diagnostic build mode helpers (V10 adopt).

When ``--diagnostic`` is passed, the build records per-stage wall timings,
counts applied transforms, checks key-material freshness, marks the
artifact visibly non-release, and logs a banner. All helpers are pure and
testable without running a full build.
"""

from __future__ import annotations

import time

DIAG_MARKER = "# NIXON-DIAGNOSTIC-BUILD: NOT FOR RELEASE"

# Canonical stage landmarks (subset of scripts/build.py Stage comments).
STAGES = (
    "parse",
    "obfuscate",
    "irgen",
    "llvmgen",
    "encrypt",
    "relay",
    "package",
    "done",
)


class DiagClock:
    """Record wall-clock stamps at stage landmarks."""

    def __init__(self) -> None:
        self.stamps: dict[str, float] = {}
        self.mark("parse")

    def mark(self, stage: str) -> None:
        self.stamps[stage] = time.perf_counter()

    def report(self) -> dict[str, float]:
        """Per-stage durations in seconds (done - parse chain)."""
        out: dict[str, float] = {}
        prev: str | None = None
        for stage in STAGES:
            if stage not in self.stamps:
                continue
            if prev is not None:
                out[stage] = max(0.0, self.stamps[stage] - self.stamps[prev])
            prev = stage
        return out


def summarize_transforms(opt_level: int, *, breaker: bool = True,
                         mba_level: int = 2, name_gate: bool = False,
                         lowering: str = "") -> dict:
    """Count applied transform families from resolved options.

    No pipeline import: mirrors the flag surface (opt_levels 17 flags +
    extras) so the diagnostic report stays decoupled from build internals.
    """
    from obfuscator.opt_levels import resolve
    flags = resolve(opt_level)
    enabled = sorted(k for k, v in flags.items() if v)
    return {
        "opt_level": opt_level,
        "enabled_flags": enabled,
        "enabled_count": len(enabled),
        "breaker": bool(breaker),
        "mba_level": int(mba_level),
        "name_gate": bool(name_gate),
        "lowering": str(lowering or ""),
    }


def key_freshness(blob_key_hex: str) -> dict:
    """Check key material freshness: non-empty, hex, >= 16 bytes."""
    try:
        raw = bytes.fromhex(blob_key_hex)
    except (ValueError, TypeError):
        return {"fresh": False, "reason": "not-hex"}
    if len(raw) < 16:
        return {"fresh": False, "reason": f"too-short:{len(raw)}"}
    if set(raw) == {0}:
        return {"fresh": False, "reason": "all-zero"}
    return {"fresh": True, "bytes": len(raw)}


def mark_diagnostic(path: str) -> None:
    """Append the visible non-release marker to an artifact file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + DIAG_MARKER + "\n")


def banner() -> str:
    return (
        "!!! NIXON DIAGNOSTIC BUILD — NOT FOR RELEASE !!!\n"
        "Timings, transform counts and key freshness follow; "
        "the artifact is visibly marked."
    )
