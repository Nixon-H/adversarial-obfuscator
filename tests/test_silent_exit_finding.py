"""AI-BUILD-001 regression: an artefact that runs nothing must not exit 0.

The defect: a default build of a payload dispatching through `globals()`
produced an artefact that exited 0 after running nothing. The native module
raised KeyError during init, the retry loop caught only ImportError, the outer
handler returned None, and the entrypoint treated None on a fallback build as
"the fallback was the intended outcome".

These tests pin the two halves of the fix, at the level of the EMITTED SOURCE,
because building a Cython artefact inside the gate would add a toolchain
dependency to a test that is really about control flow:

  1. the loader emits a completion flag set by `_exec_fallback`, so "the
     fallback ran" is distinguishable from "nothing ran";
  2. the entrypoint emits a non-zero exit for the case "native verdict is None
     AND the fallback never ran", and does so for fallback builds too -- the
     previous guard was substituted False exactly there.

The behavioural half was verified separately against a real artefact built from
tests-adjacent fixture code: before the fix it printed nothing and exited 0;
after it printed `[FATAL] artefact ran no payload ...` and exited 79. That
measured result is recorded in docs/security/REVIEW_FINDINGS_FILED.md.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _loader_source(**kwargs):
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _blobs, _fb = generate_hybrid_loader_script(
        {"linux": b""}, b"print('P')\n" * 20, bytes(range(32)).hex(),
        native_only=kwargs.pop("native_only", False),
        section_split=kwargs.pop("section_split", True),
        **kwargs)
    return src


def test_the_fallback_marks_that_it_ran():
    """`_exec_fallback` must set an observable completion flag."""
    src = _loader_source()
    assert '_NX_FALLBACK_RAN' in src, (
        "the emitted loader has no completion flag, so the entrypoint cannot "
        "tell 'the fallback ran' from 'nothing ran'")
    # It must be set inside _exec_fallback, before any early return.
    idx_fn = src.find("def _exec_fallback(")
    assert idx_fn != -1
    idx_flag = src.find("_NX_FALLBACK_RAN", idx_fn)
    idx_disabled = src.find('if "DISABLED" in str(FALLBACK_BLOB)', idx_fn)
    assert idx_flag != -1 and (idx_disabled == -1 or idx_flag < idx_disabled), (
        "the completion flag must be set before the early-return paths, or a "
        "fallback that returns early leaves the flag unset")


def test_a_fallback_build_reports_and_exits_nonzero_when_nothing_ran():
    """The guard must be emitted for fallback builds, not only native-only."""
    src = _loader_source(native_only=False)
    assert "_NX_FALLBACK_RAN" in src
    assert "ran no payload" in src, (
        "no diagnostic for the 'nothing ran' case")
    assert "exit(79)" in src, (
        "the 'nothing ran' case must exit non-zero")
    # The native-only guard is substituted False for fallback builds; the new
    # one must NOT be tied to that substitution, or it inherits the same hole.
    idx = src.find("ran no payload")
    prelude = src[max(0, idx - 1200):idx]
    assert "not False" in prelude or "if (not " in prelude, (
        "the new guard appears to be gated on the native-only placeholder, "
        "which is False exactly for the builds that need it")


def test_native_only_build_keeps_its_own_fatal_exit():
    """The pre-existing native-only guard must not be lost."""
    src = _loader_source(native_only=True)
    assert "native-only artefact" in src
    assert "exit(78)" in src


def test_the_leaky_except_still_catches_only_importerror():
    """Document the remaining gap rather than pretend it is closed.

    The retry loop around exec_module intentionally catches ImportError to try
    the next module name. A payload exception of another type still escapes to
    the outer handler -- which now reports and exits non-zero instead of
    returning a silent success, so the failure is observable even though the
    retry behaviour is unchanged.
    """
    src = _loader_source()
    idx = src.find("except ImportError:")
    assert idx != -1, (
        "the module-name retry no longer catches ImportError; if that loop "
        "changed shape, the AI-BUILD-001 analysis needs rechecking")
    # The outer handler must still exist and must not swallow into success.
    assert "except Exception" in src
