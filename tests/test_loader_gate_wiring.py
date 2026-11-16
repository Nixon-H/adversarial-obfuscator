"""The loader's environment gates must reference names that exist.

Regression for the 2026-11-15 bench finding. The state machine in
``LOADER_BODY`` gates on nine classes -- sandbox, emulator, frame debugger,
opaque predicate, hardware fingerprint, blockchain licence, key shard,
geofence, integrity monitor. Every one of those ``_source`` blocks was built
into ``build_context`` but never placed in the template, so each gate
referenced a name that was never defined and died in its bare ``except``.
The gates were dead in every build, and nothing said so: the artifact still
ran, it just ran with nine fewer checks than the recipe claimed.

Two smaller wiring bugs surfaced with them:

* ``VAR_ANTI_SANDBOX_CLS`` was a second, independently randomised name for
  ``ANTI_SANDBOX_CLS``. ``build_context.update(VARS)`` then overwrote the
  correct alias, so even the one gate whose source *was* placed pointed at
  the wrong name.
* ``DECOY_FUNC`` was its own random name, never defined; the state machine
  calls it with no arguments.

These tests pin the wiring, not the behaviour of the gates themselves.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core import sources


#: ``_source`` keys the state machine gates on. Each must be placed in the
#: loader template, or the gate that uses it is dead code.
_GATE_SOURCES = [
    "anti_sandbox_source",
    "anti_emulator_source",
    "frame_anti_debug_source",
    "opaque_const_source",
    "hw_perf_fingerprint_source",
    "blockchain_license_source",
    "tor_client_source",
    "key_shard_source",
    "geofence_source",
    "integrity_monitor_source",
]


def _loader_template():
    """The template the build actually formats: HEAD + BODY."""
    return sources.LOADER_HEAD + "\n" + sources.LOADER_BODY


def test_every_gate_source_is_placed_in_the_loader_template():
    template = _loader_template()
    missing = [name for name in _GATE_SOURCES
               if "{%s}" % name not in template]
    assert not missing, (
        "these gate sources are built but never placed in LOADER_BODY, so "
        "the gates that use them are dead code: %s" % (missing,))


def test_no_alias_entry_shadows_the_name_it_aliases():
    """A ``VAR_X`` entry must not be a second random name for ``X``.

    ``build_context`` sets ``VAR_X`` to ``VARS["X"]`` and then
    ``build_context.update(VARS)`` runs. If ``VAR_X`` is also in ``_VARS_MAP``
    the update wins and the reference points at a name nothing defines.
    """
    shadowed = [key for key in sources._VARS_MAP
                if key.startswith("VAR_") and key[4:] in sources._VARS_MAP]
    assert not shadowed, (
        "these VAR_ aliases are independently randomised and will be "
        "overwritten by build_context.update(VARS): %s" % (shadowed,))


def test_decoy_func_is_one_of_the_generated_decoys():
    sources.generate_decoy_code()
    decoys = sources.VARS["DECOY_FUNCS"]
    assert sources.VARS["DECOY_FUNC"] in decoys, (
        "the state machine calls {DECOY_FUNC}() but it is not one of the "
        "emitted decoys %s" % (decoys,))


def test_tls_ca_placeholder_is_substituted_before_emission():
    """``TLS_CTX_SOURCE`` carries its own placeholder; ``apply_vars`` does not
    know it, so the pipeline has to substitute it. Left raw it emitted
    ``_nx_ca = {tls_ca_b64}`` -- a set display that raised NameError the
    moment the key fetch built its TLS context, and that Cython rejected."""
    assert "{tls_ca_b64}" in sources.TLS_CTX_SOURCE
    rendered = sources.TLS_CTX_SOURCE.replace("{tls_ca_b64}", "''")
    assert "{tls_ca_b64}" not in rendered


def test_no_corrupted_stdlib_aliases_in_the_templates():
    """Two aliases were spelled with the wrong CJK character, so the emitted
    payload referenced a name that was never bound."""
    source = open(sources.__file__, encoding="utf-8").read()
    for bad in ("_nixon_時間時間", "_nixon_ハッシュ解시"):
        assert bad not in source, "%s is not a bound alias" % bad


def test_runtime_key_is_read_through_globals():
    """``_RUNTIME_KEY`` only exists after the network key fetch. A bare read
    is a NameError in CPython's eyes only because of short-circuiting, and
    Cython rejects it outright."""
    pipeline = open(
        os.path.join(os.path.dirname(sources.__file__), "pipeline.py"),
        encoding="utf-8").read()
    assert "globals().get('_RUNTIME_KEY')" in pipeline
    assert "'_RUNTIME_KEY' not in globals() or _RUNTIME_KEY" not in pipeline


def test_gate_sources_use_only_known_placeholders():
    """Every ``{PLACEHOLDER}`` a gate source uses must be a VARS key, or
    ``apply_vars`` leaves it raw and the emitted payload carries a literal
    brace expression."""
    unknown = {}
    for name in _GATE_SOURCES:
        const = getattr(sources, name.upper().replace("_SOURCE", "_SOURCE"))
        body = getattr(sources, const, None)
        if body is None:
            continue
        for placeholder in set(re.findall(r"\{([A-Z][A-Z0-9_]*)\}", body)):
            if placeholder not in sources.VARS:
                unknown.setdefault(name, []).append(placeholder)
    assert not unknown, "unresolved placeholders: %s" % (unknown,)
