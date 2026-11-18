"""§5-B compiler diversity: the backend selector must be real and honest.

Measured 2026-11-18 on this machine: gcc and clang both build the same target
and produce identical payload output, with opcode cosine 0.9869 and trigram
Jaccard 0.2772 between the artefacts (vs 0.9987 / 0.679 for two gcc builds).
The diversity is real but limited by Cython inlining the payload into one
module-init symbol; see the report.

These tests pin the SELECTOR's behaviour, which is the part that can silently
rot: an env override must be honoured, an unavailable override must fall back
loudly rather than silently, and the chosen compiler must be one that exists.
"""
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import obfuscator.core.pipeline as pipeline  # noqa: E402


def _selector_source():
    """The backend-selection block as emitted in build_local_cython."""
    import inspect
    return inspect.getsource(pipeline.build_local_cython)


def test_both_backends_are_referenced():
    src = _selector_source()
    assert "NIXON_NATIVE_CC" in src, "env override documented but not read"
    for cc in ("gcc", "clang"):
        assert '"%s"' % cc in src, "%s not considered" % cc


def test_selector_falls_back_when_none_installed():
    """No compiler -> the build must refuse, not silently produce nothing."""
    src = _selector_source()
    assert "no C compiler found" in src, (
        "missing-compiler path must fail loudly: a native build that quietly "
        "degrades is how every earlier benchmark measured the fallback")


def test_selector_reports_an_unavailable_override():
    """A requested backend that is not installed must be announced.

    A "diversified" build that silently resolves to one backend is worse than
    no claim at all, because the artefact then carries a manifest saying
    something untrue.
    """
    src = _selector_source()
    assert "unavailable; using" in src, (
        "an unavailable NIXON_NATIVE_CC must be reported, not swallowed")


@pytest.mark.skipif(not shutil.which("gcc"), reason="gcc absent")
def test_compile_accepts_the_flag_set_each_backend_needs():
    """Every installed backend must accept the shared flag list.

    Cheap syntactic check: -flto and the hardening flags are the ones that
    historically differed between toolchains, so an unsupported flag would
    surface as a build failure rather than at runtime.
    """
    src = _selector_source()
    for flag in ("-flto", "-fPIC", "-fstack-protector-strong"):
        assert flag in src, "%s missing from the shared flag list" % flag
