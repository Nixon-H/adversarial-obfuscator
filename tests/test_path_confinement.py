"""Generated-file containment, and the two real defects found while adding it.

The Mimosa gate reported 900+ whole-project findings, and rather than suppress
them the scan was read. Two of them were genuine and are fixed here:

  1. ``polymorph_cpp_stub`` seeded a build-varying mutation from the GLOBAL
     ``random`` stream. That is not per-build diversification (§5) -- the
     pattern depended on what else had drawn from the shared generator.

  2. ``ObfuscationTransformer.transform`` patched the process-global ``secrets``
     module to make builds reproducible, but restored it WITHOUT ``try/finally``.
     One failed transform left ``secrets.token_bytes`` pointing at a Mersenne
     Twister for the rest of the process, so every later nonce, key and
     challenge drawn anywhere became predictable. That is why the scanner flags
     it, and the fix is to bound the patch lifetime, not to silence the rule.

The rest of this file covers ``confined_path``: generated filenames are not
trusted to be safe just because today's caller passes a uuid.
"""
import os
import random
import secrets
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import (  # noqa: E402
    ObfuscationTransformer, confined_path)


# ── confined_path: containment, not a cosmetic check ──────────────────────

def test_a_plain_name_resolves_inside_the_root(tmp_path):
    assert confined_path(tmp_path, "generated.pyx") == \
        os.path.join(os.path.realpath(tmp_path), "generated.pyx")


def test_a_subdirectory_is_preserved_when_allowed(tmp_path):
    """Native-mode keys are relative paths; flattening them would merge files."""
    resolved = confined_path(tmp_path, "pkg/mod.pyx", allow_subdirs=True)
    assert resolved.endswith(os.path.join("pkg", "mod.pyx"))


def test_a_subdirectory_is_refused_when_not_allowed(tmp_path):
    with pytest.raises(ValueError):
        confined_path(tmp_path, "pkg/mod.pyx")


@pytest.mark.parametrize("name", [
    "../escape.pyx",
    "../../etc/passwd",
    "/etc/passwd",
    "..",
    "",
    "a/../../escape.pyx",
    "with space.pyx",
    "nul\x00byte.pyx",
])
def test_escaping_names_are_refused(tmp_path, name):
    with pytest.raises(ValueError):
        confined_path(tmp_path, name, allow_subdirs=True)


def test_a_sibling_prefix_is_not_mistaken_for_a_child(tmp_path):
    """The old realpath().startswith() idiom had this bug.

    ``/tmp/build`` is a string prefix of ``/tmp/build-evil``, so the previous
    containment check would have accepted a path resolving into the sibling
    directory. The reachable form is a ``..`` component that walks out and back
    into the sibling; the fix is the ``base + os.sep`` boundary plus refusing
    ``..`` outright.
    """
    sibling = str(tmp_path) + "-evil"
    with pytest.raises(ValueError):
        confined_path(tmp_path, "../" + os.path.basename(sibling) + "/x.pyx",
                      allow_subdirs=True)
    # And the legitimate case still works, so the fix is not "refuse everything".
    assert confined_path(tmp_path, "x.pyx").startswith(os.path.realpath(tmp_path))


# ── defect 1: the global RNG is not per-build diversification ─────────────

def test_polymorph_cpp_stub_uses_a_local_rng(tmp_path, monkeypatch):
    """The mutation must not be drawn from the shared `random` stream.

    The injection only fires on a line ending in ``{`` that is not a
    struct/class/switch, i.e. a function body. Two calls with the global
    generator reset to the same state must still differ, because the junk is
    seeded from ``os.urandom`` rather than from the shared stream.
    """
    stub = tmp_path / "nixon_stub.cpp"
    # `int f() {` is a function body: it is the line class that gets junk.
    stub.write_text("int f() {\n    return 1;\n}\n" * 40)
    monkeypatch.chdir(tmp_path)
    random.seed(1234)                      # freeze the global stream
    before = random.getstate()

    from obfuscator.core import pipeline as pl
    pl.polymorph_cpp_stub()
    after_first = stub.read_text()
    assert "_jnk_" in after_first, "the fixture never triggered an injection"

    random.setstate(before)                # same starting state again
    stub.write_text("int f() {\n    return 1;\n}\n" * 40)
    pl.polymorph_cpp_stub()
    after_second = stub.read_text()
    assert after_first != after_second, (
        "injected junk repeated after resetting the global RNG: the stub is "
        "seeded from the shared stream, not per build")


# ── defect 2: the secrets patch must be undone on the exception path ───────

def test_the_secrets_patch_is_restored_after_a_failed_transform(monkeypatch):
    """A failed transform must not leave `secrets` deterministic.

    This is the defect the static scanner reported as "weak randomness in a
    cryptographic context": the patch was process-global and only undone on
    success, so one exception degraded every later nonce in the process.
    """
    original_token_bytes = secrets.token_bytes
    transformer = ObfuscationTransformer(seed=7)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated transform failure")

    monkeypatch.setattr("obfuscator.core.pipeline.apply_ast_mutation", _boom)
    with pytest.raises(RuntimeError):
        transformer.transform("x = 1\n", {})

    assert secrets.token_bytes is original_token_bytes, (
        "secrets.token_bytes was left patched after a failed transform")


def test_the_secrets_patch_is_restored_after_a_successful_transform():
    original_token_bytes = secrets.token_bytes
    ObfuscationTransformer(seed=11).transform("x = 1\ny = 2\n", {})
    assert secrets.token_bytes is original_token_bytes


def test_the_global_random_state_is_restored_after_a_failed_transform(monkeypatch):
    random.seed(99)
    expected = random.getstate()
    transformer = ObfuscationTransformer(seed=5)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("obfuscator.core.pipeline.apply_ast_mutation", _boom)
    with pytest.raises(RuntimeError):
        transformer.transform("x = 1\n", {})
    assert random.getstate() == expected, (
        "the global random stream was left reseeded by a failed build")
