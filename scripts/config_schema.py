"""
config_schema.py

Purpose:
Fail-closed schema validation for config/default.json. Every key in the
default config is covered by an explicit per-key rule; values that control
protection posture (gates, thresholds, crypto choices, stage switches) are
security-critical and any violation raises ConfigError instead of silently
degrading to weaker protections.

Architectural Role:
Validation gate for the central configuration hub
(scripts/phases/phase02_config.py). Called on every config load; warnings
flow through scripts/common.log, violations abort the build via ConfigError.

Execution Context:
Imported by scripts/phases/phase02_config.py and scripts/build.py.
Pure stdlib, no third-party imports.

Dependencies:
json, math, os (stdlib); scripts.common.log for warning emission.

Security Relevance:
Fail-closed direction throughout:
- unknown keys are dropped from the clean dict (warn; strict=True errors)
- wrong type on a security-critical key -> ConfigError (never defaulted)
- out-of-range/enum violation on security-critical key -> ConfigError
  (cosmetic keys clamp-to-range + warn instead)
- missing REQUIRED security field -> ConfigError
- missing optional field -> repo default applied silently (caller may log
  at debug; defaults are protections-ON biased, the fail-safe direction)
- structural violations (section given as list/scalar/null, nesting bombs,
  oversized containers) -> ConfigError, never silent truncation

Python 3.10 compatible: no match statements, no X | Y annotations,
no 3.11-only stdlib APIs.
"""

import copy
import json
import math
import os

try:
    from .common import log
except Exception:  # pragma: no cover - fallback for exotic import paths

    def log(phase, msg):
        print("[%s] %s" % (phase, msg))


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------

class ConfigError(ValueError):
    """Raised for any security-critical config violation.

    Subclasses ValueError so generic ``except ValueError`` call sites still
    catch it, but callers can distinguish "config refused fail-closed" from
    programming errors. Malformed JSON is wrapped into this type so callers
    never see a raw traceback-grade JSONDecodeError escape the loader.
    """


# ---------------------------------------------------------------------------
# Resource-exhaustion guards (nested-bomb / giant-list poisoning)
# ---------------------------------------------------------------------------

MAX_DEPTH = 32        # nesting deeper than this is a bomb, not a config
MAX_NODES = 20000     # total dicts+lists visited during one validation
MAX_LIST_LEN = 4096   # any single list longer than this is rejected
MAX_STR_LEN = 4096    # any single string value longer than this is rejected


# ---------------------------------------------------------------------------
# Field rules
# ---------------------------------------------------------------------------
# dtype: 'bool' | 'int' | 'float' | 'str' | 'list'
# For 'float', plain ints are accepted and converted (JSON has no float/int
# distinction at the syntax level for e.g. 1 vs 1.0; callers may pass either).
# For 'list', elem gives the required element dtype ('str') and choices
# optionally restricts element values (used for ollvm pass names).

def _F(dtype, default, sec, required=False, min=None, max=None,
       choices=None, elem=None, nonempty=False, allow_null=False):
    return {
        "dtype": dtype,
        "default": default,
        "security_critical": sec,
        "required": required,
        "min": min,
        "max": max,
        "choices": choices,
        "elem": elem,
        "nonempty": nonempty,
        "allow_null": allow_null,
    }


def _BOOL_SEC(default):
    return _F("bool", default, True)

# Valid OLLVM pass names, verified against llvmgen/codegen.py:20
# (argparse choices) and llvmgen/passes.py:717-721 (apply dispatch).
# Anything else is silently ignored by apply_all -> fail-open, hence
# security-critical: reject unknown entries fail-closed.
OLLVM_KNOWN_PASSES = ("bcf", "bogus", "fla", "flatten", "sub", "substitute")

# Valid TEE types, verified against scripts/build.py --tee-type choices.
TEE_KNOWN_TYPES = ("software", "sgx", "sev", "apple")

# The only cipher with a matching implementation (encrypt/encrypt.py,
# AES-256-CTR). Nothing in-tree reads this key today, so a wrong value is
# currently inert — but a future reader must never silently honor a weaker
# cipher, so unknown values are rejected fail-closed (conservative).
CIPHER_KNOWN = ("aes-256-ctr",)

SCHEMA = {
    # --- top-level metadata ---------------------------------------------
    "shadow_compiler.version": _F("str", "2.0.0", False),
    # seed feeds deterministic builds (llvmgen/passes.py:614 emits it into
    # generated IR as i64; a non-int would emit garbage). Nullable by design.
    "shadow_compiler.seed": _F("int", None, True, allow_null=True),
    # --- pipeline stage gates (False drops the whole stage -> posture) ---
    "shadow_compiler.stages.obfuscate": _BOOL_SEC(True),
    "shadow_compiler.stages.irgen": _BOOL_SEC(True),
    "shadow_compiler.stages.llvmgen": _BOOL_SEC(True),
    "shadow_compiler.stages.encrypt": _BOOL_SEC(True),
    "shadow_compiler.stages.relay": _BOOL_SEC(True),
    "shadow_compiler.stages.runtime": _BOOL_SEC(True),
    # --- AST obfuscator passes ------------------------------------------
    "shadow_compiler.obfuscator.cfg_flatten": _BOOL_SEC(True),
    "shadow_compiler.obfuscator.opaque_predicates": _BOOL_SEC(True),
    "shadow_compiler.obfuscator.bogus_exceptions": _BOOL_SEC(True),
    "shadow_compiler.obfuscator.mba_subs": _BOOL_SEC(True),
    "shadow_compiler.obfuscator.fragment_strings": _BOOL_SEC(True),
    "shadow_compiler.obfuscator.unicode_ids": _BOOL_SEC(True),
    "shadow_compiler.obfuscator.provenance_removal": _BOOL_SEC(True),
    "shadow_compiler.obfuscator.dataflow_obfuscation": _BOOL_SEC(True),
    # --- IR generation ---------------------------------------------------
    # optimization_level has no verified in-tree consumer (grep finds no
    # reader): cosmetic. Range 0-3 follows clang -O convention.
    "shadow_compiler.irgen.optimization_level": _F("int", 2, False,
                                                   min=0, max=3),
    "shadow_compiler.irgen.variant_pool": _BOOL_SEC(True),
    "shadow_compiler.irgen.semantic_fragmentation": _BOOL_SEC(True),
    "shadow_compiler.irgen.jit_templates": _BOOL_SEC(True),
    "shadow_compiler.irgen.watermarking": _BOOL_SEC(True),
    "shadow_compiler.irgen.bitslicing.enabled": _BOOL_SEC(True),
    "shadow_compiler.irgen.bitslicing.word_size": _F("int", 64, True,
                                                     choices=(32, 64)),
    "shadow_compiler.irgen.chaff_circuits.enabled": _BOOL_SEC(True),
    "shadow_compiler.irgen.chaff_circuits.num_chaff": _F("int", 10, True,
                                                         min=0, max=1024),
    "shadow_compiler.irgen.chaff_circuits.target_functions": _F(
        "list", [], True, elem="str"),
    # --- LLVM codegen ----------------------------------------------------
    "shadow_compiler.llvmgen.ollvm_passes": _F(
        "list", ["bcf", "fla", "sub"], True, elem="str",
        choices=OLLVM_KNOWN_PASSES),
    "shadow_compiler.llvmgen.enable_integrity": _BOOL_SEC(True),
    "shadow_compiler.llvmgen.rop.enabled": _BOOL_SEC(True),
    "shadow_compiler.llvmgen.rop.target_functions": _F(
        "list", [], True, elem="str"),
    # --- encryption ------------------------------------------------------
    "shadow_compiler.encrypt.cipher": _F("str", "aes-256-ctr", True,
                                         required=True,
                                         choices=CIPHER_KNOWN),
    # block_size feeds _split_blocks (encrypt/encrypt.py:135): 0 crashes
    # (range step 0), negative yields zero blocks. Must be a real int.
    "shadow_compiler.encrypt.block_size": _F("int", 64, True,
                                             min=1, max=65536),
    "shadow_compiler.encrypt.entropy_flatten.enabled": _BOOL_SEC(True),
    # tolerance feeds scripts/entropy_flatten.py:130,147
    # (chaff iff entropy > target + tolerance); 0.0 chaffs everything.
    "shadow_compiler.encrypt.entropy_flatten.tolerance": _F(
        "float", 0.3, True, min=0.0, max=1.0),
    "shadow_compiler.encrypt.entropy_flatten.chaff_per_page": _F(
        "int", 64, True, min=0, max=4096),
    # --- VM ---------------------------------------------------------------
    "shadow_compiler.vm.enabled": _BOOL_SEC(True),
    # Numeric VM knobs have no verified failure bound in-tree; cosmetic
    # (clamp + warn) so an out-of-range knob can never abort a build, while
    # the bool gates above stay fail-closed on type violations.
    "shadow_compiler.vm.mutation_level": _F("int", 3, False, min=0, max=10),
    "shadow_compiler.vm.num_registers": _F("int", 16, False,
                                           min=1, max=256),
    # "8-16 bits" per vm/vm_isa.py:248.
    "shadow_compiler.vm.opcode_width": _F("int", 8, True, choices=(8, 16)),
    "shadow_compiler.vm.ephemeral_isa": _BOOL_SEC(True),
    # --- master protection gates ------------------------------------------
    "shadow_compiler.advanced_protection.enabled": _BOOL_SEC(True),
    "shadow_compiler.phase2.enabled": _BOOL_SEC(True),
    # --- adversarial loop --------------------------------------------------
    "shadow_compiler.adversarial_loop.enabled": _BOOL_SEC(True),
    # threshold feeds scripts/phases/phase09_adversarial.py:73
    # (evolve iff score < threshold); 0.0 can never fire.
    "shadow_compiler.adversarial_loop.deobfuscation_threshold": _F(
        "float", 0.7, True, required=True, min=0.0, max=1.0),
    # iterations feeds range(evolution_iterations) (phase09:84);
    # negative silently skips evolution -> security-relevant bound.
    "shadow_compiler.adversarial_loop.evolution_iterations": _F(
        "int", 1, True, min=0, max=100),
    # history_file is a write sink (phase09:88-108, makedirs + atomic_write);
    # a poisoned absolute path writes outside build/. Non-str/empty rejected
    # fail-closed; absolute paths warn (legit power-user override exists).
    "shadow_compiler.adversarial_loop.history_file": _F(
        "str", "build/evolution_history.json", True, nonempty=True),
    # --- runtime gates ------------------------------------------------------
    "shadow_compiler.runtime.minimal": _BOOL_SEC(True),
    "shadow_compiler.runtime.static_python": _BOOL_SEC(True),
    "shadow_compiler.runtime.jit_memory": _BOOL_SEC(True),
    # exec_guard is embedded into the .shadorenc metadata word
    # (encrypt/encrypt.py:147-161): silently flipping it drops the guard.
    "shadow_compiler.runtime.exec_guard": _BOOL_SEC(True),
    "shadow_compiler.runtime.microjit": _BOOL_SEC(True),
    "shadow_compiler.runtime.tee.enabled": _BOOL_SEC(True),
    "shadow_compiler.runtime.tee.tee_type": _F("str", "sgx", True,
                                               choices=TEE_KNOWN_TYPES),
    "shadow_compiler.runtime.tee.target_functions": _F(
        "list", [], True, elem="str"),
    "shadow_compiler.runtime.oram.enabled": _BOOL_SEC(True),
    # ORAM geometry has no verified failure bound in-tree; cosmetic.
    "shadow_compiler.runtime.oram.tree_height": _F("int", 8, False,
                                                  min=1, max=32),
    "shadow_compiler.runtime.oram.block_size": _F("int", 64, False,
                                                  min=1, max=65536),
    "shadow_compiler.runtime.scratch_buffer_size": _F("int", 4096, False,
                                                      min=1, max=1048576),
    "shadow_compiler.phase2_extras.enabled": _BOOL_SEC(True),
}

# Feature-flag leaves, generated to avoid transcription drift. All default
# True in the shipped config; every flag silently disables one protection
# when False, so wrong types are security-critical (but False itself is a
# legitimate posture choice and never errors).
_ADV_FEATURES = (
    "provenance_removal", "dataflow_obfuscation", "variant_pool",
    "semantic_fragmentation", "jit_templates", "mutation", "watermark",
    "adversarial", "microjit", "entropy_flatten", "bitslice",
    "chaff_circuits", "classification", "vm_isa", "ephemeral_isa",
)
_PHASE2_FEATURES = (
    "provenance_removal", "dataflow_obfuscation", "variant_pool",
    "semantic_fragmentation", "jit_templates", "watermarking", "vm",
    "mutating_isa", "adversarial", "replay_poison", "timing_traps",
    "oram", "microjit", "ephemeral_isa", "ledger_proof",
)
_EXTRAS_FEATURES = (
    "bitslicing", "chaff_circuits", "entropy_flatten", "tee",
    "speculative_traps", "transient_exec", "crypto_cfg", "port_entangle",
)
for _name in _ADV_FEATURES:
    SCHEMA["shadow_compiler.advanced_protection.features." + _name] = \
        _BOOL_SEC(True)
for _name in _PHASE2_FEATURES:
    SCHEMA["shadow_compiler.phase2.features." + _name] = _BOOL_SEC(True)
for _name in _EXTRAS_FEATURES:
    SCHEMA["shadow_compiler.phase2_extras.features." + _name] = \
        _BOOL_SEC(True)
del _name

# required=True is only meaningful on leaves whose absence must abort the
# build. advanced_protection.enabled has a legitimate fallback (phase2), so
# it stays optional-with-default; cipher / exec_guard / threshold have no
# safe fallback and are required. shadow_compiler itself is always required.
REQUIRED_PATHS = frozenset((
    "shadow_compiler.encrypt.cipher",
    "shadow_compiler.runtime.exec_guard",
    "shadow_compiler.adversarial_loop.deobfuscation_threshold",
))

# Parent path -> direct child names, derived from SCHEMA so the walker and
# the completeness test share one source of truth. Intermediate section
# nodes (which have no SCHEMA entry of their own) are included: for every
# schema path a.b.c, "b" is a child of "a" and "c" a child of "a.b".
_CHILDREN = {"": {"shadow_compiler"}}
for _path in SCHEMA:
    _parts = _path.split(".")
    for _i in range(1, len(_parts)):
        _parent = ".".join(_parts[:_i])
        _CHILDREN.setdefault(_parent, set()).add(_parts[_i])
del _path, _parts, _i, _parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def schema_keys():
    """Return the set of dotted paths covered by SCHEMA."""
    return set(SCHEMA)


def config_leaf_keys(data, _prefix=""):
    """Enumerate dotted leaf paths of a nested config dict.

    Dicts recurse; every other value (bool/int/str/list/None) is a leaf.
    """
    keys = set()
    if isinstance(data, dict):
        for name, value in data.items():
            path = _prefix + name if not _prefix else _prefix + "." + name
            if isinstance(value, dict):
                keys.update(config_leaf_keys(value, path))
            else:
                keys.add(path)
    return keys


def _fail(path, msg):
    raise ConfigError("config %s: %s" % (path, msg))


def _check_str_len(path, value, warnings):
    if len(value) > MAX_STR_LEN:
        _fail(path, "string value too long (%d chars, max %d) "
                    "-- refusing oversized input" % (len(value), MAX_STR_LEN))


def _validate_leaf(path, value, spec, strict, warnings, depth):
    """Validate one leaf value. Returns the clean value.

    Raises ConfigError on security-critical violations; on cosmetic
    violations appends a warning and returns the spec default (or a
    clamped value for numeric range breaches).
    """
    dtype = spec["dtype"]
    sec = spec["security_critical"]

    def _violation(msg, default):
        if sec:
            _fail(path, msg)
        warnings.append("%s: %s; using default %r" % (path, msg, default))
        return copy.deepcopy(default)

    # --- null handling ---------------------------------------------------
    if value is None:
        if spec["allow_null"]:
            return None
        return _violation("null value not allowed", spec["default"])

    # --- bool (must precede int: bool is a subclass of int) -------------
    if dtype == "bool":
        if isinstance(value, bool):
            return value
        return _violation("expected bool, got %s" % type(value).__name__,
                          spec["default"])

    # --- int (reject bool explicitly: True == 1 would silently arm/disarm)
    if dtype == "int":
        if isinstance(value, bool):
            return _violation("expected int, got bool", spec["default"])
        if not isinstance(value, int):
            return _violation("expected int, got %s" % type(value).__name__,
                              spec["default"])
        if spec.get("choices") is not None and value not in spec["choices"]:
            return _violation(
                "value %r not in allowed set %r" % (value, spec["choices"]),
                spec["default"])
        if spec.get("min") is not None and value < spec["min"]:
            if sec:
                _fail(path, "value %r below minimum %r" % (value, spec["min"]))
            warnings.append("%s: value %r below minimum %r; clamped"
                            % (path, value, spec["min"]))
            return spec["min"]
        if spec.get("max") is not None and value > spec["max"]:
            if sec:
                _fail(path, "value %r above maximum %r" % (value, spec["max"]))
            warnings.append("%s: value %r above maximum %r; clamped"
                            % (path, value, spec["max"]))
            return spec["max"]
        return value

    # --- float (accept ints, reject bool/NaN/inf) ------------------------
    if dtype == "float":
        if isinstance(value, bool):
            return _violation("expected float, got bool", spec["default"])
        if isinstance(value, int):
            value = float(value)
        if not isinstance(value, float):
            return _violation("expected float, got %s" % type(value).__name__,
                              spec["default"])
        if not math.isfinite(value):
            # NaN poisons every comparison (score < NaN is always False ->
            # evolution silently never runs). Always fail closed, even for
            # cosmetic floats: a NaN default would be worse than an abort.
            _fail(path, "non-finite float %r not allowed" % (value,))
        if spec.get("min") is not None and value < spec["min"]:
            if sec:
                _fail(path, "value %r below minimum %r" % (value, spec["min"]))
            warnings.append("%s: value %r below minimum %r; clamped"
                            % (path, value, spec["min"]))
            return float(spec["min"])
        if spec.get("max") is not None and value > spec["max"]:
            if sec:
                _fail(path, "value %r above maximum %r" % (value, spec["max"]))
            warnings.append("%s: value %r above maximum %r; clamped"
                            % (path, value, spec["max"]))
            return float(spec["max"])
        return value

    # --- str ---------------------------------------------------------------
    if dtype == "str":
        if not isinstance(value, str):
            return _violation("expected str, got %s" % type(value).__name__,
                              spec["default"])
        _check_str_len(path, value, warnings)
        if spec.get("nonempty") and value == "":
            return _violation("empty string not allowed", spec["default"])
        if spec.get("choices") is not None and value not in spec["choices"]:
            return _violation(
                "value %r not in allowed set %r" % (value, spec["choices"]),
                spec["default"])
        return value

    # --- list ---------------------------------------------------------------
    if dtype == "list":
        if isinstance(value, tuple):
            value = list(value)
        if not isinstance(value, list):
            return _violation("expected list, got %s" % type(value).__name__,
                              spec["default"])
        if len(value) > MAX_LIST_LEN:
            _fail(path, "list too long (%d entries, max %d) -- refusing "
                        "oversized input" % (len(value), MAX_LIST_LEN))
        clean_list = []
        for i, entry in enumerate(value):
            epath = "%s[%d]" % (path, i)
            if spec.get("elem") == "str":
                if not isinstance(entry, str):
                    if sec:
                        _fail(epath, "expected str entry, got %s"
                                     % type(entry).__name__)
                    warnings.append("%s: dropping non-str entry" % epath)
                    continue
                _check_str_len(epath, entry, warnings)
            if spec.get("choices") is not None and entry not in spec["choices"]:
                if sec:
                    _fail(epath, "unknown entry %r (allowed: %r) -- "
                                 "refusing to silently ignore" %
                          (entry, list(spec["choices"])))
                warnings.append("%s: dropping unknown entry %r" % (epath,
                                                                   entry))
                continue
            clean_list.append(entry)
        return clean_list

    _fail(path, "internal error: unknown dtype %r" % (dtype,))


def _validate_node(node, prefix, strict, warnings, depth, counter):
    """Recursively validate one dict node. Returns the clean dict."""
    counter[0] += 1
    if counter[0] > MAX_NODES:
        _fail(prefix or "<root>",
              "config too large (node budget exceeded) -- refusing")
    if depth > MAX_DEPTH:
        _fail(prefix or "<root>",
              "nesting too deep (max %d) -- refusing nested bomb" % MAX_DEPTH)
    if not isinstance(node, dict):
        # A section that should be a dict but arrived as list/scalar/null:
        # children cannot be validated, so fail closed (never default a
        # whole protection section — the default would mask tampering).
        _fail(prefix or "<root>",
              "expected a config section (dict), got %s"
              % type(node).__name__)
    known = _CHILDREN.get(prefix, set()) if prefix else {"shadow_compiler"}
    clean = {}
    for name, value in node.items():
        path = name if not prefix else prefix + "." + name
        if name not in known:
            # Unknown subtrees are dropped WITHOUT recursing into them:
            # a nested bomb under an unknown key is neutralized here, in
            # O(1) walker depth, instead of being traversed.
            if len(warnings) < 500:
                msg = "unknown config key %r ignored" % path
                if strict:
                    _fail(path, "unknown config key (strict mode)")
                warnings.append(msg)
            elif len(warnings) == 500:
                warnings.append("... further unknown-key warnings suppressed")
            continue
        if path in SCHEMA:
            # Depth/budget accounting for large leaf containers.
            if isinstance(value, (dict, list)):
                counter[0] += 1
                if counter[0] > MAX_NODES:
                    _fail(path, "config too large -- refusing")
            clean[name] = _validate_leaf(path, value, SCHEMA[path],
                                         strict, warnings, depth + 1)
        else:
            # Intermediate section node: must be a dict (checked inside).
            clean[name] = _validate_node(value, path, strict, warnings,
                                         depth + 1, counter)
    # Fill missing optional leaves with repo defaults (silent: the caller
    # may log these at debug; they are NOT warnings).
    for name in known:
        path = name if not prefix else prefix + "." + name
        if path in SCHEMA and name not in clean:
            if path in REQUIRED_PATHS:
                _fail(path, "missing required security field -- refusing "
                            "to build with an unknown protection posture")
            clean[name] = copy.deepcopy(SCHEMA[path]["default"])
    return clean


# ---------------------------------------------------------------------------
# Conflict / dangerous-default detection (all rules verified against code)
# ---------------------------------------------------------------------------

def _sc(clean):
    sc = clean.get("shadow_compiler", {})
    return sc if isinstance(sc, dict) else {}


def check_conflicts(clean):
    """Return a list of warning strings for conflicting/dangerous combos.

    Only encodes conflicts verified against in-tree consumers (cites in
    each message). Never raises: conflicts warn, violations raise.
    """
    out = []
    sc = _sc(clean)
    if not sc:
        return out

    def _feat(*names):
        for section in ("advanced_protection", "phase2", "phase2_extras"):
            feats = sc.get(section, {}).get("features", {})
            if not isinstance(feats, dict):
                continue
            for n in names:
                if feats.get(n) is True:
                    return True
        return False

    def _any_feat():
        for section in ("advanced_protection", "phase2", "phase2_extras"):
            feats = sc.get(section, {}).get("features", {})
            if isinstance(feats, dict) and any(v is True for v in
                                               feats.values()):
                return True
        return False

    ap_en = sc.get("advanced_protection", {}).get("enabled", False)
    p2_en = sc.get("phase2", {}).get("enabled", False)

    # 1. Both master gates off while features are on: every downstream
    #    _phase2_enabled() gate (irgen/*, obfuscator/*, vm/*) returns False,
    #    so all feature flags are silently inert.
    if not ap_en and not p2_en and _any_feat():
        out.append("conflict: feature flags are on but both master gates "
                   "(advanced_protection.enabled, phase2.enabled) are off -- "
                   "every downstream gate reads the master switch, so the "
                   "build will emit an unprotected artifact")

    # 2. VM subsystem off while VM features requested: build.py gates
    #    phase_vm_compile on phase2_cfg.features.vm, independent of
    #    vm.enabled -> inconsistent posture signal.
    if sc.get("vm", {}).get("enabled", True) is False and (
            _feat("vm", "vm_isa", "mutating_isa", "ephemeral_isa")):
        out.append("conflict: vm.enabled is off but VM features "
                   "(vm/vm_isa/mutating_isa/ephemeral_isa) are requested -- "
                   "build.py gates VM compile on the feature flag, not "
                   "vm.enabled")

    # 3. Entropy flatten on while the encrypt stage is off: flatten runs on
    #    the raw object and build.py logs ERROR when no ELF is available;
    #    an operator may believe "encrypt section on == encrypted".
    stages = sc.get("stages", {})
    ef_en = sc.get("encrypt", {}).get("entropy_flatten", {}).get(
        "enabled", False)
    if stages.get("encrypt", True) is False and ef_en:
        out.append("conflict: stages.encrypt is off but "
                   "encrypt.entropy_flatten.enabled is on -- artifact "
                   "leaves the pipeline unencrypted")

    # 4. Dangling adversarial tuning (mirrors build.py _warn_dangling):
    #    threshold/iterations set while the loop is disabled.
    adv = sc.get("adversarial_loop", {})
    if adv.get("enabled", True) is False and (
            adv.get("deobfuscation_threshold", 0.7) != 0.7
            or adv.get("evolution_iterations", 1) != 1):
        out.append("conflict: adversarial_loop.enabled is off but "
                   "deobfuscation_threshold/evolution_iterations are "
                   "non-default -- tuning is inert")

    # 5. Dangerous threshold defaults (verified: phase09_adversarial.py
    #    evolves iff score < threshold; scores lie in [0, 1]).
    if adv.get("enabled", False) is True:
        thr = adv.get("deobfuscation_threshold", 0.7)
        if thr == 0.0:
            out.append("dangerous default: deobfuscation_threshold is 0.0 "
                       "with the loop enabled -- score < 0.0 never holds, "
                       "so evolution silently never runs")
        elif thr == 1.0:
            out.append("dangerous default: deobfuscation_threshold is 1.0 "
                       "with the loop enabled -- evolution fires on every "
                       "build (slow builds, possible oscillation)")

    # 6. Zero tolerance chaffs every page (verified:
    #    scripts/entropy_flatten.py chaffs iff entropy > target+tolerance).
    ef = sc.get("encrypt", {}).get("entropy_flatten", {})
    if ef.get("enabled", False) is True and ef.get("tolerance", 0.3) == 0.0:
        out.append("dangerous default: entropy_flatten.tolerance is 0.0 "
                   "with flattening enabled -- every page gets chaff "
                   "(binary bloat)")

    # 7. History-file outside the build tree (verified write sink at
    #    phase09_adversarial.py:88-108). Absolute paths are a legitimate
    #    power-user override, hence warn (not error).
    hf = adv.get("history_file", "")
    if isinstance(hf, str) and hf != "" and os.path.isabs(hf):
        out.append("caution: adversarial_loop.history_file is absolute "
                   "(%r) -- evolution history writes outside the build "
                   "tree" % hf)

    # 8. Every stage off: degenerate empty build.
    if stages and all(v is False for v in stages.values()
                      if isinstance(v, bool)):
        out.append("conflict: all pipeline stages are disabled -- build "
                   "will emit an unprotected artifact")

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_config(data, *, strict=False):
    """Validate a parsed config dict.

    Args:
        data: parsed JSON object (must be a dict).
        strict: when True, unknown keys raise ConfigError instead of
            warning.

    Returns:
        (clean_dict, warnings): clean_dict has unknown keys removed,
        defaults filled, cosmetic values clamped; warnings lists
        human-readable strings (unknown keys, cosmetic fixes, conflicts).
        Missing optional fields are defaulted SILENTLY (not warnings) so
        callers can distinguish "default applied" from "value repaired".

    Raises:
        ConfigError: security-critical violation (wrong type, out of
            range/enum, missing required field, structural/bomb input,
            strict-mode unknown key). Never returns a defaulted
            security-critical value.
    """
    if not isinstance(data, dict):
        _fail("<root>", "top-level config must be an object, got %s"
                        % type(data).__name__)
    if "shadow_compiler" not in data:
        _fail("shadow_compiler", "missing required security section -- "
                                 "refusing to build with an unknown "
                                 "protection posture")
    warnings = []
    clean = _validate_node(data, "", strict, warnings, 0, [0])
    for c in check_conflicts(clean):
        warnings.append(c)
    return clean, warnings


def _too_deep(obj, limit=MAX_DEPTH):
    """True when the parsed document nests deeper than *limit*.

    Iterative: the point is to answer this without recursing, because
    3.14's JSON decoder happily parses a 20k-deep object that used to
    raise RecursionError on earlier interpreters.  Relying on the parser
    to fail made the depth-bomb guard version-dependent -- and a bomb
    hidden under an unknown key was never traversed by the schema walker,
    so it was not caught either.
    """
    stack = [(obj, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > limit:
            return True
        if isinstance(node, dict):
            stack.extend((value, depth + 1) for value in node.values())
        elif isinstance(node, (list, tuple)):
            stack.extend((value, depth + 1) for value in node)
    return False


def load_config_file(path, *, strict=False):
    """Load and validate a config file. Returns (clean_dict, warnings).

    Raises:
        FileNotFoundError: file absent (absence is NOT a violation; the
            caller decides whether to degrade, as today).
        ConfigError: malformed JSON or any security-critical violation.
            The message is self-contained (no traceback needed to act).
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    if len(raw) > 10 * 1024 * 1024:
        raise ConfigError("config %s: file too large (%d bytes) -- "
                          "refusing" % (path, len(raw)))
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        # ValueError covers JSONDecodeError (its superclass); RecursionError
        # covers deeply-nested inputs that blow the C parser's stack. Both
        # become a clean ConfigError, never a traceback-grade crash.
        raise ConfigError("config %s: malformed JSON (%s) -- refusing to "
                          "build with an unreadable protection posture"
                          % (path, exc))
    if _too_deep(data):
        raise ConfigError(
            "config %s: malformed JSON (nesting deeper than %d levels) -- "
            "refusing to build with a possible depth bomb"
            % (path, MAX_DEPTH))
    try:
        return validate_config(data, strict=strict)
    except ConfigError as exc:
        raise ConfigError("config %s: %s" % (path, exc))
