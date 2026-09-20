"""opt_levels.py — O0..O5 optimization/protection ladder.

Canonical flag set (17 flags): the 6 pipeline base flags plus 11 extras.
Levels are monotonic: each level is a superset of the previous one.
"""

from __future__ import annotations

BASE_FLAGS = [
    "cfg_flatten",
    "opaque_predicates",
    "bogus_exceptions",
    "mba_subs",
    "fragment_strings",
    "unicode_ids",
]

EXTRA_FLAGS = [
    "junk",
    "decoys",
    "minify",
    "const_unfold",
    "call_indirection",
    "reflection",
    "dataflow",
    "watermark",
    "variant_pool",
    "fragmentation",
    "provenance",
]

ALL_FLAGS = BASE_FLAGS + EXTRA_FLAGS

assert len(ALL_FLAGS) == 17, f"expected 17 canonical flags, got {len(ALL_FLAGS)}"


def _level(base_on=(), extra_on=()) -> dict:
    cfg = {f: False for f in ALL_FLAGS}
    for f in list(base_on) + list(extra_on):
        if f not in cfg:
            raise ValueError(f"unknown flag: {f}")
        cfg[f] = True
    return cfg


_L0 = _level()
_L1 = _level(base_on=BASE_FLAGS, extra_on=["minify"])
_L2 = _level(
    base_on=BASE_FLAGS,
    extra_on=["minify", "junk", "const_unfold", "call_indirection", "reflection"],
)
_L3 = _level(
    base_on=BASE_FLAGS,
    extra_on=[
        "minify",
        "junk",
        "const_unfold",
        "call_indirection",
        "reflection",
        "decoys",
    ],
)
_L4 = _level(
    base_on=BASE_FLAGS,
    extra_on=[
        "minify",
        "junk",
        "const_unfold",
        "call_indirection",
        "reflection",
        "decoys",
        "dataflow",
        "provenance",
    ],
)
_L5 = _level(base_on=BASE_FLAGS, extra_on=EXTRA_FLAGS)

LEVELS: dict[int, dict] = {
    0: _L0,
    1: _L1,
    2: _L2,
    3: _L3,
    4: _L4,
    5: _L5,
}

_LEVEL_NAMES = {
    0: "O0 (none)",
    1: "O1 (safe)",
    2: "O2 (balanced)",
    3: "O3 (strong)",
    4: "O4 (recommended)",
    5: "O5 (aggressive)",
}


def resolve(level: int) -> dict:
    """Return a copy of the flag dict for *level*. Rejects unknown levels."""
    if not isinstance(level, int) or isinstance(level, bool) or level not in LEVELS:
        raise ValueError(f"unknown opt level: {level!r} (valid: 0-5)")
    return dict(LEVELS[level])


def describe(level: int) -> str:
    """Return a one-line human-readable description of *level*."""
    cfg = resolve(level)  # validates
    on = sorted(f for f, v in cfg.items() if v)
    off = sorted(f for f, v in cfg.items() if not v)
    name = _LEVEL_NAMES.get(level, f"O{level}")
    return (
        f"--opt-level {level} {name}: "
        f"{len(on)}/{len(cfg)} enabled "
        f"[on: {', '.join(on) if on else 'none'}; "
        f"off: {', '.join(off) if off else 'none'}]"
    )


def apply_to_args(args, level: int):
    """Set flag attributes on an argparse Namespace from *level*."""
    cfg = resolve(level)  # validates
    for flag, value in cfg.items():
        setattr(args, flag, value)
    # Also expose the level itself for downstream logging.
    try:
        setattr(args, "opt_level", level)
    except Exception:
        pass
    return args
