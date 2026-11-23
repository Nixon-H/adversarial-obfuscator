"""The signed manifest must record the pack format version (§7).

The review register's §7 asks the manifest to bind nine things, and the
manifest already carried most of them: compiler/linker identity, toolchain
versions, transforms, target OS/architecture, dependency-lock digest, final
artefact digest and — once signed — the signing-key fingerprint. Two were
genuinely missing, and one of them was the *pack format version*: "does this
artefact carry a v2 or v3 section pack?" could not be answered from the signed
record at all.

Adding the field took three attempts, and both failures are worth keeping:

  1. reading `_section_armed` through globals() — that name is a LOCAL of
     `generate_hybrid_loader_script`, so it is absent from `main`'s globals and
     the field read `False` for EVERY build.
  2. reading `args.no_section_split` — argparse stores that flag as
     `section_split` with `action='store_false'`, so the lookup always fell
     back to its default and reported `requested: True` even when the operator
     passed `--no-section-split`.

Both looked correct in review and were wrong in production. That is the same
lesson the three filed findings taught: a field that is PRESENT is not a field
that is RIGHT, and only building something and reading the output tells you
which.

These tests check the field definition rather than running a full build — the
build takes ten minutes and the gate already exercises it. They pin the two
mistakes so neither can return.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

PIPELINE = os.path.join(REPO, "obfuscator", "core", "pipeline.py")


def _source():
    with open(PIPELINE, encoding="utf-8") as fh:
        return fh.read()


def _manifest_block():
    """The text of the pack record inside the write_manifest call."""
    src = _source()
    start = src.index('"pack": {')
    return src[start:start + 1400]


# ── the two mistakes must not come back ───────────────────────────────

def test_the_pack_field_does_not_read_a_local_through_globals():
    """Mistake 1: `_section_armed` is a local of another function.

    Reading it via globals() from `main` always yields None, so the field
    would silently report False for every build.
    """
    assert '_section_armed' not in _manifest_block(), (
        "the pack field reads _section_armed again; that name is a LOCAL of "
        "generate_hybrid_loader_script and is invisible from main(), so the "
        "field would always report False")


def test_the_pack_field_uses_the_real_argparse_attribute():
    """Mistake 2: the flag is `section_split`, not `no_section_split`."""
    block = _manifest_block()
    assert 'getattr(args, "section_split"' in block, (
        "the pack field must read args.section_split -- argparse stores "
        "--no-section-split as section_split with action='store_false'")
    assert 'args, "no_section_split"' not in block, (
        "the pack field reads args.no_section_split, which does not exist; "
        "the lookup would always fall back to its default")


def test_the_parser_really_uses_that_dest():
    """The assertion above is only right if the parser says so."""
    src = _source()
    assert ('--no-section-split", dest="section_split"' in src
            or "--no-section-split', dest='section_split'" in src), (
        "the CLI flag's dest changed; update the manifest field to match")


# ── the field's shape and honesty ─────────────────────────────────────

def test_the_pack_field_states_its_basis():
    """A reader must be able to tell what the value is derived from.

    `basis` records that this is the REQUESTED configuration plus a module
    constant — not the loader's post-build state, which main() cannot see.
    """
    block = _manifest_block()
    assert "basis" in block, (
        "the pack record must say what it is derived from; claiming a "
        "post-build fact it cannot observe would repeat the error class of "
        "the three filed findings")
    assert "cli-args" in block


def test_the_pack_field_records_version_count_and_request():
    block = _manifest_block()
    for key in ('"requested"', '"format_version"', '"section_count"'):
        assert key in block, "the pack record is missing the %s key" % (key,)


def test_the_version_comes_from_the_module_that_defines_it():
    """Not a literal: a hardcoded 3 goes stale when the format moves.

    That is exactly the defect this project hit three times in its own docs.
    """
    assert "_SECTION_PACK_FORMAT" in _manifest_block()
    src = _source()
    assert "SECTION_PACK_VERSION as _SECTION_PACK_FORMAT" in src, (
        "the version must be imported from section_split, not restated as a "
        "literal")


# ── the other §7 fields, as far as a static check can see ─────────────

@pytest.mark.parametrize("field_name", [
    "python", "python_impl", "platform", "machine", "gcc", "ld", "cython",
])
def test_the_toolchain_block_records_the_named_identity(field_name,
                                                        tmp_path):
    """§7 asks for compiler/linker identity, toolchain versions and target
    OS/architecture. These are the manifest's own keys for them."""
    from obfuscator.build_manifest import build_manifest

    art = tmp_path / "payload.py"
    art.write_text("X = 1\n", encoding="utf-8")
    manifest = build_manifest(str(art), transforms=["data"])
    assert field_name in (manifest.get("toolchain") or {}), (
        "the manifest toolchain block no longer records %r" % (field_name,))


def test_the_manifest_records_the_digests_the_register_asks_for(tmp_path):
    """Final artefact digest, dependency-lock digest, protection level."""
    from obfuscator.build_manifest import build_manifest

    art = tmp_path / "payload.py"
    art.write_text("X = 1\n", encoding="utf-8")
    manifest = build_manifest(str(art), transforms=["data"])
    assert manifest["artefact"]["sha256"], "final artefact digest missing"
    assert "dependency_lock_digest" in (manifest.get("build") or {}), (
        "dependency-lock digest missing from build{}")
    assert manifest.get("protection_level") is not None, (
        "protection_level missing; anti-rollback would have nothing to compare")
