"""H0-H5 arm specifications (frozen experiment config companion).

Each arm maps to exact generate_variant options. H0 is byte-identical in
effect to the G2 seed_only control (same pass set, vm name retained as a
documented no-op). New families (rep, vm_dispatch) are isolated: all
other transforms explicitly OFF so effects attribute cleanly.
"""

# Base: everything the generator + pipeline would otherwise enable,
# forced OFF for isolation. (generate_variant hardcodes strip_meta,
# unfold_constants and obf_calls True and the pipeline defaults the
# rest True — all overridden here via extra_options merge.)
ISOLATION_OFF = {
    "cfg_flatten": False,
    "opaque_predicates": False,
    "bogus_exceptions": False,
    "mba_subs": False,
    "fragment_strings": False,
    "unicode_ids": False,
    "split_vars": False,
    "unfold_constants": False,
    "enhanced_junk": False,
    "break_decompiler": False,
    "code_checksums": False,
    "dynamic_code": False,
    "obf_calls": False,
    "exception_flow": False,
    "strip_meta": False,
}

ARMS = {
    "H0": {
        "purpose": "Negative control: seed-only variation.",
        "pass_sets": [["rename", "dead_code", "mba", "cfg_flatten", "vm"]],
        "extra_options": {},
    },
    "H1": {
        "purpose": "Existing heterogeneous baseline (CFG/data/expression).",
        "pass_sets": [
            ["rename", "dead_code", "mba", "cfg_flatten", "vm"],
            ["rename", "dead_code", "opaque_pred", "string_encode", "vm"],
            ["rename", "mba", "cfg_flatten", "opaque_pred", "string_encode", "vm"],
        ],
        "extra_options": {},
    },
    "H2": {
        "purpose": "Representation diversification hypothesis.",
        "pass_sets": [["rename"]],
        "extra_options": dict(ISOLATION_OFF, symbol_rename=True,
                              rep_diversify=True),
    },
    "H3": {
        "purpose": "Switch-dispatch execution model.",
        "pass_sets": [["rename"]],
        "extra_options": dict(ISOLATION_OFF, symbol_rename=True,
                              vm_dispatch="a"),
    },
    "H4": {
        "purpose": "Threaded-handler execution model.",
        "pass_sets": [["rename"]],
        "extra_options": dict(ISOLATION_OFF, symbol_rename=True,
                              vm_dispatch="b"),
    },
    "H5": {
        "purpose": "Main heterogeneous arm: existing + rep + VM (alternating).",
        "pass_sets": [
            ["rename", "dead_code", "mba", "cfg_flatten", "vm"],
            ["rename", "dead_code", "opaque_pred", "string_encode", "vm"],
            ["rename", "mba", "cfg_flatten", "opaque_pred", "string_encode", "vm"],
        ],
        "extra_options": {"rep_diversify": True, "vm_dispatch": "alternate"},
    },
}

ARM_ORDER = ["H0", "H1", "H2", "H3", "H4", "H5"]

# H5 alternates VM family per build index (recorded per build).
H5_FAMILIES = ("a", "b")


def resolve_options(arm, build_index, base_extra=None):
    """Concrete (pass_sets, extra_options) for one build. Deterministic."""
    spec = ARMS[arm]
    extra = dict(base_extra or {})
    extra.update(spec["extra_options"])
    if arm == "H5" and extra.get("vm_dispatch") == "alternate":
        extra = dict(extra)
        extra["vm_dispatch"] = H5_FAMILIES[build_index % len(H5_FAMILIES)]
    return spec["pass_sets"], extra


def config_freeze_hash():
    import hashlib
    import json
    canonical = json.dumps({"arms": ARMS, "order": ARM_ORDER,
                            "H5_FAMILIES": H5_FAMILIES}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
