"""Config schema validation proofs (fail-closed semantics).

Covers scripts/config_schema.py wired into
scripts/phases/phase02_config.py::load_advanced_protection_config.

Python 3.10 compatible: no match statements, no X | Y annotations.
"""
import argparse
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.config_schema import (  # noqa: E402
    ConfigError,
    check_conflicts,
    config_leaf_keys,
    load_config_file,
    schema_keys,
    validate_config,
)
import scripts.phases.phase02_config as p2  # noqa: E402

DEFAULT_JSON = os.path.join(ROOT, "config", "default.json")
SC = "shadow_compiler"


def _base():
    with open(DEFAULT_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def _mut(path, value):
    d = _base()
    node = d
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = value
    return d


def _del(path):
    d = _base()
    node = d
    for part in path[:-1]:
        node = node[part]
    del node[path[-1]]
    return d


def _opts(**kw):
    base = dict(
        advanced_protection=False, phase2=False,
        advanced_protection_only=None, phase2_only=None,
        phase2_extras=False, adversarial_injection=False,
        ephemeral_isa=False, microjit=False, oram=False, rop=False,
    )
    base.update(kw)
    return argparse.Namespace(**base)


# --- schema completeness ----------------------------------------------------

def test_schema_covers_every_default_json_key():
    """Every leaf in config/default.json has a schema rule.

    New keys cannot slip in unvalidated: add the key to SCHEMA first or
    this test fails.
    """
    with open(DEFAULT_JSON, encoding="utf-8") as fh:
        data = json.load(fh)
    leaves = config_leaf_keys(data)
    assert leaves, "default.json has no leaves?"
    missing = sorted(leaves - schema_keys())
    assert missing == [], "schema gaps: %r" % (missing,)


def test_valid_shipped_config_passes_clean():
    """The shipped default.json validates with zero warnings and round-trips."""
    clean, warnings = load_config_file(DEFAULT_JSON)
    assert warnings == []
    with open(DEFAULT_JSON, encoding="utf-8") as fh:
        assert clean == json.load(fh)


# --- malformed / missing file ------------------------------------------------

def test_malformed_json_raises_config_error(tmp_path):
    """Torn JSON -> ConfigError (clean error, not a raw traceback type)."""
    bad = tmp_path / "default.json"
    bad.write_text("{not valid json,,,", encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_config_file(str(bad))
    assert "malformed JSON" in str(excinfo.value)
    assert type(excinfo.value) is ConfigError


def test_missing_file_is_not_a_violation(tmp_path):
    """Absence raises FileNotFoundError (caller degrades); only poison fails."""
    with pytest.raises(FileNotFoundError):
        load_config_file(str(tmp_path / "nonexistent.json"))


def test_top_level_non_dict_rejected():
    with pytest.raises(ConfigError):
        validate_config([1, 2, 3])


def test_missing_shadow_compiler_section_rejected():
    with pytest.raises(ConfigError):
        validate_config({})


# --- unknown keys --------------------------------------------------------------

def test_unknown_keys_warn_and_are_dropped():
    clean, warnings = validate_config(_mut([SC, "evil_feature"], True))
    assert any("evil_feature" in w for w in warnings)
    assert "evil_feature" not in clean[SC]


def test_unknown_nested_keys_warn():
    d = _mut([SC, "runtime", "backdoor"], 1)
    clean, warnings = validate_config(d)
    assert any("backdoor" in w for w in warnings)
    assert "backdoor" not in clean[SC]["runtime"]


def test_unknown_keys_strict_error():
    with pytest.raises(ConfigError):
        validate_config(_mut([SC, "evil_feature"], True), strict=True)


# --- wrong types ----------------------------------------------------------------

@pytest.mark.parametrize("path,value", [
    ([SC, "encrypt", "cipher"], ["aes-256-ctr"]),       # crypto choice: list
    ([SC, "runtime", "exec_guard"], "yes"),             # gate: str
    ([SC, "runtime", "exec_guard"], ["true"]),          # gate: list
    ([SC, "adversarial_loop", "deobfuscation_threshold"], "all"),  # thr: str
    ([SC, "encrypt", "block_size"], "64"),              # int: str
    ([SC, "encrypt", "block_size"], True),              # int: bool
    ([SC, "adversarial_loop", "evolution_iterations"], 2.5),  # int: float
    ([SC, "stages", "encrypt"], 1),                     # gate: int
    ([SC, "vm", "ephemeral_isa"], "true"),              # gate: str
    ([SC, "adversarial_loop", "history_file"], ["x"]),  # path: list
    ([SC, "seed"], "random"),                           # seed: str
])
def test_wrong_type_security_field_raises(path, value):
    """Security-critical wrong type -> ConfigError, never a silent default."""
    with pytest.raises(ConfigError):
        validate_config(_mut(path, value))


def test_wrong_type_cosmetic_field_defaults_with_warning():
    """Cosmetic wrong type -> repo default + warning (build continues)."""
    clean, warnings = validate_config(_mut([SC, "version"], 123))
    assert clean[SC]["version"] == "2.0.0"
    assert any("version" in w for w in warnings)

    clean, warnings = validate_config(
        _mut([SC, "irgen", "optimization_level"], "high"))
    assert clean[SC]["irgen"]["optimization_level"] == 2
    assert any("optimization_level" in w for w in warnings)


def test_cosmetic_bool_for_int_rejected_as_type_error():
    """True is not 1: bool for an int knob warns + defaults (no silent arm)."""
    clean, warnings = validate_config(
        _mut([SC, "vm", "mutation_level"], True))
    assert clean[SC]["vm"]["mutation_level"] == 3
    assert any("mutation_level" in w for w in warnings)


# --- ranges / enums ---------------------------------------------------------------

@pytest.mark.parametrize("path,value", [
    ([SC, "encrypt", "entropy_flatten", "tolerance"], 5.0),
    ([SC, "encrypt", "entropy_flatten", "tolerance"], -0.5),
    ([SC, "adversarial_loop", "deobfuscation_threshold"], 1.5),
    ([SC, "adversarial_loop", "deobfuscation_threshold"], -0.1),
    ([SC, "encrypt", "block_size"], 0),
    ([SC, "encrypt", "block_size"], -64),
    ([SC, "encrypt", "cipher"], "xor"),          # weaker-than-shipped cipher
    ([SC, "encrypt", "cipher"], "aes-128-cbc"),
    ([SC, "runtime", "tee", "tee_type"], "rot13"),
    ([SC, "irgen", "bitslicing", "word_size"], 12),
    ([SC, "llvmgen", "ollvm_passes"], ["bcf", "evil"]),
    ([SC, "irgen", "chaff_circuits", "num_chaff"], 10 ** 9),
    ([SC, "adversarial_loop", "evolution_iterations"], -3),  # silent skip
    ([SC, "adversarial_loop", "history_file"], ""),          # empty sink
])
def test_out_of_range_security_field_raises(path, value):
    with pytest.raises(ConfigError):
        validate_config(_mut(path, value))


def test_out_of_range_cosmetic_clamps_with_warning():
    clean, warnings = validate_config(
        _mut([SC, "irgen", "optimization_level"], 99))
    assert clean[SC]["irgen"]["optimization_level"] == 3
    assert any("optimization_level" in w for w in warnings)

    clean, warnings = validate_config(
        _mut([SC, "runtime", "scratch_buffer_size"], -1))
    assert clean[SC]["runtime"]["scratch_buffer_size"] == 1
    assert any("scratch_buffer_size" in w for w in warnings)


def test_non_finite_threshold_rejected():
    """NaN threshold would make (score < NaN) always False -> silent no-evolve."""
    with pytest.raises(ConfigError):
        validate_config(_mut([SC, "adversarial_loop",
                              "deobfuscation_threshold"], float("nan")))
    with pytest.raises(ConfigError):
        validate_config(_mut([SC, "adversarial_loop",
                              "deobfuscation_threshold"], float("inf")))


# --- missing fields ---------------------------------------------------------------

@pytest.mark.parametrize("path", [
    [SC, "encrypt", "cipher"],
    [SC, "runtime", "exec_guard"],
    [SC, "adversarial_loop", "deobfuscation_threshold"],
])
def test_missing_required_security_field_raises(path):
    with pytest.raises(ConfigError):
        validate_config(_del(path))


def test_missing_optional_applies_default_silently():
    """Missing optional -> repo default, NO warning (debug-level at most)."""
    clean, warnings = validate_config(
        _del([SC, "irgen", "optimization_level"]))
    assert clean[SC]["irgen"]["optimization_level"] == 2
    assert warnings == []

    clean, warnings = validate_config(
        _del([SC, "runtime", "scratch_buffer_size"]))
    assert clean[SC]["runtime"]["scratch_buffer_size"] == 4096
    assert warnings == []


# --- poisoned configs (adversarial conditions) --------------------------------------

def test_poisoned_config_combination():
    """Threshold-as-string + gate-as-list in one file -> ConfigError."""
    d = _base()
    d[SC]["adversarial_loop"]["deobfuscation_threshold"] = "all"
    d[SC]["runtime"]["exec_guard"] = ["true"]
    with pytest.raises(ConfigError):
        validate_config(d)


def test_nested_bomb_under_unknown_key_neutralized():
    """100-deep nesting under an UNKNOWN key is dropped without recursing.

    The walker never descends into unknown subtrees (O(1) depth), so a
    nested bomb there costs one warning, not a RecursionError.
    """
    node = cur = {}
    for _ in range(100):
        cur["a"] = {}
        cur = cur["a"]
    clean, warnings = validate_config({"shadow_compiler": node})
    assert any("unknown config key" in w for w in warnings)
    assert "a" not in clean["shadow_compiler"]


def test_parser_depth_bomb_rejected(tmp_path):
    """20k-deep JSON defeats the C parser -> clean ConfigError, no crash."""
    depth = 20000
    bomb = tmp_path / "bomb.json"
    bomb.write_text('{"a":' * depth + "1" + "}" * depth, encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_config_file(str(bomb))
    assert "malformed JSON" in str(excinfo.value)
    assert type(excinfo.value) is ConfigError


def test_giant_list_rejected():
    """5000-entry target list -> ConfigError (bomb guard), not a hang."""
    d = _mut([SC, "irgen", "chaff_circuits", "target_functions"],
             ["f%d" % i for i in range(5000)])
    with pytest.raises(ConfigError) as excinfo:
        validate_config(d)
    assert "too long" in str(excinfo.value)


def test_section_as_scalar_rejected():
    """Whole protection section replaced by a scalar -> ConfigError."""
    with pytest.raises(ConfigError):
        validate_config(_mut([SC, "stages"], [1, 2, 3]))
    with pytest.raises(ConfigError):
        validate_config(_mut([SC, "runtime"], None))


def test_non_str_list_entries_rejected_for_security_lists():
    d = _mut([SC, "llvmgen", "rop", "target_functions"], ["ok", 123])
    with pytest.raises(ConfigError):
        validate_config(d)


def test_oversized_string_rejected():
    d = _mut([SC, "version"], "v" * 5000)
    # version is cosmetic, but oversized strings are a bomb vector:
    # refused fail-closed regardless of security flag.
    with pytest.raises(ConfigError):
        validate_config(d)


# --- conflicts / dangerous defaults -------------------------------------------------

def test_both_master_gates_off_with_features_warns():
    d = _base()
    d[SC]["advanced_protection"]["enabled"] = False
    d[SC]["phase2"]["enabled"] = False
    clean, warnings = validate_config(d)
    assert any("master gates" in w for w in warnings)


def test_vm_disabled_with_vm_features_warns():
    d = _base()
    d[SC]["vm"]["enabled"] = False
    assert d[SC]["phase2"]["features"]["vm"] is True
    clean, warnings = validate_config(d)
    assert any("vm.enabled is off" in w for w in warnings)


def test_encrypt_stage_off_with_flatten_on_warns():
    d = _base()
    d[SC]["stages"]["encrypt"] = False
    assert d[SC]["encrypt"]["entropy_flatten"]["enabled"] is True
    clean, warnings = validate_config(d)
    assert any("unencrypted" in w for w in warnings)


def test_zero_threshold_with_loop_enabled_warns():
    d = _base()
    d[SC]["adversarial_loop"]["deobfuscation_threshold"] = 0.0
    clean, warnings = validate_config(d)
    assert any("never" in w and "evolution" in w for w in warnings)


def test_zero_tolerance_with_flatten_enabled_warns():
    d = _base()
    d[SC]["encrypt"]["entropy_flatten"]["tolerance"] = 0.0
    clean, warnings = validate_config(d)
    assert any("chaff" in w for w in warnings)


def test_absolute_history_file_warns():
    d = _base()
    d[SC]["adversarial_loop"]["history_file"] = "/tmp/evil_history.json"
    clean, warnings = validate_config(d)
    assert any("absolute" in w for w in warnings)


def test_dangling_adversarial_tuning_warns():
    d = _base()
    d[SC]["adversarial_loop"]["enabled"] = False
    d[SC]["adversarial_loop"]["evolution_iterations"] = 10
    clean, warnings = validate_config(d)
    assert any("inert" in w for w in warnings)


def test_check_conflicts_pure_function():
    clean, warnings = validate_config(_base())
    assert check_conflicts(clean) == []
    assert warnings == []


# --- loader wiring ---------------------------------------------------------------------

def test_loader_rejects_poisoned_config_fail_closed(tmp_path, monkeypatch):
    """Poisoned default.json -> ConfigError from the loader (aborts build)."""
    poison = _base()
    poison[SC]["adversarial_loop"]["deobfuscation_threshold"] = "all"
    bad = tmp_path / "default.json"
    bad.write_text(json.dumps(poison), encoding="utf-8")
    monkeypatch.setattr(p2, "DEFAULT_CONFIG", str(bad))
    with pytest.raises(ConfigError):
        p2.load_advanced_protection_config(_opts())


def test_loader_rejects_malformed_json_fail_closed(tmp_path, monkeypatch):
    bad = tmp_path / "default.json"
    bad.write_text("{not valid json,,,", encoding="utf-8")
    monkeypatch.setattr(p2, "DEFAULT_CONFIG", str(bad))
    with pytest.raises(ConfigError):
        p2.load_advanced_protection_config(_opts())


def test_loader_missing_file_still_degrades(tmp_path, monkeypatch):
    """Absence is not tampering: missing file keeps the old degrade shape."""
    monkeypatch.setattr(p2, "DEFAULT_CONFIG",
                        str(tmp_path / "nonexistent.json"))
    assert p2.load_advanced_protection_config(_opts()) == {"features": {}}


def test_loader_valid_config_unchanged():
    """Shipped config through the loader: enabled + full feature matrix.

    15 shipped flags plus ephemeral_isa/microjit auto-enabled from the
    vm/runtime sections (phase02_config merge logic).
    """
    cfg = p2.load_advanced_protection_config(_opts())
    assert cfg.get("enabled") is True
    feats = cfg.get("features", {})
    with open(DEFAULT_JSON, encoding="utf-8") as fh:
        shipped = json.load(fh)[SC]["advanced_protection"]["features"]
    for name in shipped:
        assert feats.get(name) is True, name
    assert feats.get("ephemeral_isa") is True
    assert feats.get("microjit") is True
