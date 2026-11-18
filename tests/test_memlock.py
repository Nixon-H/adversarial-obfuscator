"""§4 sensitive-memory handling: mlock the key and plaintext against swap.

The gap this closes: PR_SET_DUMPABLE=0 and RLIMIT_CORE=0 stop a core dump and
an external /proc/<pid>/mem read, but neither stops the kernel writing a secret
page to swap, where it outlives the process on disk.

Verified behaviour, measured before the code was written (2026-11-18):

    VmLck before          0 kB
    mlock 64 KB buffer    68 kB   (67 kB span, page-rounded)
    munlock               0 kB

and on a real protected artefact afterwards: VmLck peak **200 kB** with 75
nonzero samples during a run, while the artefact still produced its output.

Scope, which is deliberately narrow and stated in the module docstring:
  * only buffers the loader owns are locked;
  * the CPython heap is not locked and cannot be (RLIMIT_MEMLOCK is 8 MB here,
    the heap is far larger);
  * mlock pins PHYSICAL pages, so every copy the interpreter makes is a fresh
    page and is not covered. That is the CPython-erasure limit the review
    states, and locking does not change it.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.memlock import emit_snippet  # noqa: E402


def _module():
    """Import the emitted snippet as a real module."""
    import importlib.util
    import tempfile

    fd, path = tempfile.mkstemp(prefix="mlock-", suffix=".py")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(emit_snippet())
    try:
        spec = importlib.util.spec_from_file_location("mlock_mod", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load the emitted memlock snippet")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _vmlck_kb():
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmLck"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


def test_snippet_compiles_and_exposes_the_api():
    src = emit_snippet()
    compile(src, "<memlock>", "exec")
    mod = _module()
    for name in ("_nx_mlock", "_nx_munlock_all", "_nx_mlock_report"):
        assert hasattr(mod, name), "%s missing" % name


@pytest.mark.skipif(_vmlck_kb() is None, reason="no VmLck on this platform")
def test_mlock_actually_pins_pages():
    """The control must move VmLck, not silently no-op."""
    mod = _module()
    before = _vmlck_kb()
    buf = bytearray(b"KEY-MATERIAL" * 400)
    assert mod._nx_mlock(buf) is True
    during = _vmlck_kb()
    mod._nx_munlock_all()
    after = _vmlck_kb()
    assert during > before, "VmLck did not rise (before=%r during=%r)" % (
        before, during)
    assert after <= during, "VmLck did not fall after munlock"


def test_immutable_and_empty_buffers_are_refused_not_crashed():
    """bytes cannot be locked in place; the call must fail soft."""
    mod = _module()
    assert mod._nx_mlock(b"immutable") is False
    assert mod._nx_mlock(bytearray()) is False
    assert mod._nx_mlock("not a buffer") is False


def test_report_counts_successes_and_failures():
    mod = _module()
    buf = bytearray(4096)
    locked = mod._nx_mlock(buf)
    mod._nx_mlock(b"nope")
    report = mod._nx_mlock_report()
    mod._nx_munlock_all()
    assert report["locked"] >= (1 if locked else 0)
    assert report["failed"] >= 1


def test_unlock_is_safe_when_nothing_was_locked():
    mod = _module()
    mod._nx_munlock_all()  # must not raise
    assert mod._nx_mlock_report()["locked"] == 0


def test_loader_emits_the_mlock_helpers_unconditionally():
    """Both gates-on and gates-off loaders must define what they call.

    Measured 2026-11-18 on CFI: emitting helpers inside one branch left the
    other calling an undefined name. The same rule is asserted here.
    """
    import obfuscator.core.pipeline as pipeline

    blanks = {"windows": "", "linux": "", "darwin": "", "android": ""}
    original = getattr(pipeline, "_NX_TEST_LOADER_GATES_OFF", False)
    try:
        for gates_off in (True, False):
            pipeline._NX_TEST_LOADER_GATES_OFF = gates_off
            src, _blobs, _fb = pipeline.generate_hybrid_loader_script(
                dict(blanks), b"", "11" * 32, section_split=True)
            assert "def _nx_mlock" in src, (
                "gates_off=%s: mlock called but not defined" % gates_off)
            assert "_nx_mlock(" in src, "gates_off=%s: mlock never called" % gates_off
            compile(src, "<loader>", "exec")
    finally:
        pipeline._NX_TEST_LOADER_GATES_OFF = original
