"""The runtime manifest generator must not drift from the build input.

`relay/build.rs` embeds `runtime/manifest.json`; `runtime/gen_manifest.py`
regenerates the same document when an operator wants a new baseline.  Those
two drifted once (the generator still described `sha256(seed + block_index)`
while the manifest and `runtime/src/decrypt.rs` used the AES block derivation),
so the manifest is pinned here field-by-field.
"""
import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_GENERATOR = os.path.join(ROOT, "runtime", "gen_manifest.py")
_spec = spec_from_file_location("nixon_gen_manifest", _GENERATOR)
assert _spec and _spec.loader
_mod = module_from_spec(_spec)
_spec.loader.exec_module(_mod)
generate_manifest = _mod.generate_manifest

MANIFEST = os.path.join(ROOT, "runtime", "manifest.json")
FIXED_SEED = "11" * 32


def _checked_in():
    with open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def test_generated_manifest_matches_the_build_input():
    generated = generate_manifest(build_seed=FIXED_SEED)
    checked_in = _checked_in()
    # build_seed is injected by build.rs, so the placeholder differs by design.
    generated.pop("build_seed")
    checked_in.pop("build_seed")
    assert generated == checked_in


def test_checked_in_build_seed_is_an_injected_placeholder():
    seed = _checked_in()["build_seed"]
    assert seed == "" or (
        len(seed) == 64 and all(c in "0123456789abcdef" for c in seed)
    ), seed


def test_encryption_description_names_the_real_derivation():
    description = generate_manifest(build_seed=FIXED_SEED)["encryption"][
        "key_derivation"]
    assert "runtime/src/decrypt.rs" in description
    assert "sha256(seed + block_index)" not in description
