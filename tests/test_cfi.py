"""§1 control-flow integrity: execution must pass checkpoints in order.

The loader verifies content (Merkle + HMAC) and pack structure. Neither
notices a change in WHICH code runs: replacing a check with `pass`, or jumping
past it, leaves every hash intact.

CFI is a checkpoint chain: each mark folds a fixed tag into a running digest
seeded from the per-build key, and the final digest is compared against a value
stamped at build time, immediately before the payload runs. A skipped,
duplicated or reordered checkpoint changes the chain.

Honest limit, asserted here so it cannot be forgotten: an attacker who reads
the file can see the tags and the expected digest and forge a matching chain.
This raises the number of coordinated edits; it is not a wall.
"""
import importlib.util
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.cfi import (  # noqa: E402
    CFI_SCHEMA, CFI_TAGS, emit_snippet, expected_chain, mark_call,
)


def _module(chain_value, hmac_key="ab" * 32):
    """Load the emitted CFI snippet as a real module at a given chain value."""
    fd, path = tempfile.mkstemp(prefix="cfi-", suffix=".py")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("_NX_SELF_HK = %r\n" % hmac_key)
        fh.write("_NX_CFI_SEQ = %r\n" % chain_value)
        fh.write("_NX_CFI_SEED = None\n_NX_CFI_STATE = None\n"
                 "_NX_CFI_MARKS = 0\n")
        fh.write("def _nx_self_fail(m):\n    raise SystemExit(m)\n")
        fh.write(emit_snippet())
    try:
        spec = importlib.util.spec_from_file_location("cfi_mod", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load the emitted CFI snippet")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _verify(marks, chain_value=None, key="ab" * 32):
    mod = _module(chain_value if chain_value is not None
                  else expected_chain(key), key)
    for tag in marks:
        mod._nx_cfi_mark(tag)
    mod._nx_cfi_verify()


def test_in_order_chain_is_accepted():
    _verify(CFI_TAGS)


@pytest.mark.parametrize("marks,label", [
    (("id", "use"), "skipped"),
    (("enter", "id", "use"), "reordered"),
    (("id", "enter", "use", "use"), "duplicated"),
    ((), "none"),
])
def test_any_deviation_is_rejected(marks, label):
    with pytest.raises(SystemExit):
        _verify(marks)


def test_chain_is_order_count_and_key_sensitive():
    base = expected_chain("ab" * 32, ("id", "enter", "use"))
    assert base != expected_chain("ab" * 32, ("enter", "id", "use"))
    assert base != expected_chain("ab" * 32, ("id", "enter"))
    assert base != expected_chain("cd" * 32, ("id", "enter", "use"))


def test_wrong_expected_value_is_rejected():
    with pytest.raises(SystemExit):
        _verify(CFI_TAGS, chain_value="0" * 64)


def test_zeroed_slot_fails_closed():
    """An unstamped artefact must refuse to start, not run unverified."""
    with pytest.raises(SystemExit):
        _verify(CFI_TAGS, chain_value="0" * 64)


def test_mark_call_matches_the_expected_sequence():
    """The emitted call text must correspond to the tags the build hashes."""
    for tag in CFI_TAGS:
        call = mark_call(tag).strip()
        assert call.startswith("_nx_cfi_mark("), call
        assert tag in call, "%r does not name its tag" % call
    assert CFI_SCHEMA in emit_snippet()


def test_build_stamper_rekeys_the_generator_cfi_chain():
    """Regression: production stamping must replace the zero-key chain.

    The generator fills _NX_CFI_SEQ with a self-consistent chain derived from
    the zeroed self-check key so direct callers can execute it. The production
    stamper later replaces _NX_SELF_HK with the real build secret. If it only
    replaces an all-zero CFI slot, the generator-filled value survives and every
    stamped artefact dies with ``control-flow: chain mismatch``.
    """
    import re

    from obfuscator.core import pipeline

    src, _, _ = pipeline.generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": "", "android": ""},
        b"", "11" * 32, build_id="cfi-stamp-regression", self_check=True)
    real_hk = "cd" * 32
    stamped = pipeline._stamp_hybrid_selfcheck(src, real_hk)

    hk = re.search(r'_NX_SELF_HK = "([0-9a-f]{64})"', stamped)
    cfi = re.search(r'_NX_CFI_SEQ = "([0-9a-f]{64})"', stamped)
    assert hk and hk.group(1) == real_hk
    assert cfi and cfi.group(1) == expected_chain(real_hk)
    assert cfi.group(1) != expected_chain("00" * 32)


def test_loader_template_marks_common_enter_and_native_use():
    """Native and fallback execution must traverse the same three checkpoints."""
    from obfuscator.core import pipeline

    src, _, _ = pipeline.generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": "", "android": ""},
        b"", "11" * 32, build_id="cfi-template-paths")

    load_native = src[src.index("def _load_native():"):]
    fallback = src[src.index("def _exec_fallback():"):src.index("def _load_native():")]
    assert "_nx_cfi_mark('enter')" in load_native
    assert "_nx_cfi_mark('enter')" not in fallback
    native_exec = load_native.index("spec.loader.exec_module(module)")
    native_use = load_native.rindex("_nx_cfi_mark('use')", 0, native_exec)
    native_verify = load_native.rindex("_nx_cfi_verify()", 0, native_exec)
    assert native_use < native_verify < native_exec
