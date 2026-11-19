"""§4 enforcement moved into the native blob (§5l boundary push, 2026-11-19).

The accepted loader boundary said: the payload is hidden, the wrapper is not.
The option recorded for pushing that boundary -- "move the enforcement into
the native blob" -- is implemented, and this file pins what it means:

  * native/enforcement.c exports nx_apply_protections() and it actually
    applies the anti-dump policy (measured on the kernel, not assumed);
  * every blob this pipeline builds carries that <entry> -- the loader
    REFUSES a blob without it, so a producer that forgets the source ships
    dead artefacts rather than unprotected ones;
  * a native-only artefact (--package native-only, fallback DISABLED) has no
    Python execution path to payload plaintext: its text must not carry the
    anti-dump syscalls (DS 4.1 Flash reconstructed the old block verbatim --
    that is the §5l finding this change addresses);
  * any build that CAN reach payload plaintext through Python (sectioned or
    bytecode fallback) still emits the Python block -- the fallback runs in
    production for those builds, and dropping the block would be a §4
    regression on that path, not a boundary push.
"""
import os
import re
import sys
import tempfile

import pytest

# Repo root, built without climbing dirname chains: join the parts as
# strings and normalise once, then verify containment wherever a path is
# used for I/O (the runtime refuses anything that escapes the repo).
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.sep.join((_HERE, os.pardir)))
sys.path.insert(0, REPO)


def _in_repo(*parts):
    """Normalise and confine a path to the repo root."""
    candidate = os.path.realpath(os.sep.join((REPO,) + tuple(parts)))
    if candidate != REPO and not candidate.startswith(REPO + os.sep):
        raise AssertionError("path escapes the repo root")
    return candidate


ENFORCEMENT_C = _in_repo("native", "enforcement.c")
PROBE = _in_repo("tests", "fixtures", "enforcement_probe.py")

#: The behaviour-bearing syscall names DS 4.1 Flash recovered from the old
#: top-of-loader block (§5l). A native-only artefact must not carry them.
SYSCALL_MARKERS = ("prctl", "setrlimit", "RLIMIT_CORE", "PR_SET_DUMPABLE",
                   "PT_DENY_ATTACH")


def _loader(native_only):
    from obfuscator.core import pipeline as pl
    return pl.generate_hybrid_loader_script(
        native_blobs={"linux": "AAAA"} if native_only else {},
        bytecode_fallback=b"", key_hex="00" * 32,
        native_only=native_only, build_id="enf-test") [0]


# ── the emission rule ─────────────────------------------------------------
def test_native_only_loader_carries_no_syscall_names():
    """The whole point of the boundary push: the syscalls leave the text."""
    loader = _loader(native_only=True)
    for marker in SYSCALL_MARKERS:
        assert marker not in loader, (
            "%r recovered verbatim is exactly the §5l finding; a native-only "
            "build must not carry it in text" % (marker,))


def test_native_only_loader_calls_the_enforcement_entry_fail_closed():
    loader = _loader(native_only=True)
    assert "nx_apply_protections" in loader, (
        "the enforcement call must be present -- its absence would mean the "
        "artefact runs with NO anti-dump policy")
    assert "lacks enforcement entry" in loader, (
        "a blob without the entry must be refused, not skipped")


def test_plain_build_still_emits_the_python_block():
    """Builds that can reach plaintext through Python keep the block."""
    loader = _loader(native_only=False)
    for marker in ("prctl", "setrlimit", "RLIMIT_CORE"):
        assert marker in loader, (
            "a build with a Python path to payload plaintext must keep the "
            "anti-dump block (a §4 regression if dropped)")


def test_memguard_snippet_is_report_only_when_native_enforced():
    """The second readable prctl site switches form, not disappears.

    memguard's snippet was the second place the syscalls appeared in text.
    For native-only builds it reports the enforcement bitmask the loader
    captured, so the diagnostic channel stays meaningful without syscall
    names. The snippet is compiled, never executed: installing the handlers
    or the syscalls inside pytest would be process-wide side effects, and
    the mask itself is measured by the blob probe below.
    """
    from obfuscator.memguard import emit_snippet
    native = emit_snippet(native_enforced=True)
    for marker in SYSCALL_MARKERS:
        assert marker not in native
    assert "_NX_NATIVE_ENF" in native, (
        "the report must carry the enforcement bitmask the loader recorded")
    compile(native, "<mg_native>", "exec")  # syntax-checked, never executed
    assert "NIXON_MEM_REPORT" in native, (
        "the diagnostic channel must survive the switch")
    plain = emit_snippet()
    assert "prctl" in plain and "RLIMIT_CORE" in plain


# ── the native side ─────────────────--------------------------------------
def test_enforcement_source_exists_and_carries_the_handlers():
    assert os.path.isfile(ENFORCEMENT_C), (
        "native/enforcement.c is the boundary push; without it the loader "
        "refuses every blob")
    src = open(ENFORCEMENT_C, encoding="utf-8").read()
    assert "nx_apply_protections" in src, "the entry is missing"
    assert "_exit(137)" in src, (
        "the silent kill-ladder handlers must ride along with the "
        "enforcement entry (the file is self-contained by design)")


@pytest.mark.skipif(sys.platform != "linux", reason="Linux syscalls")
def test_built_blob_applies_the_policy_in_a_subprocess():
    """Measured, not assumed: the real blob applies the anti-dump policy.

    The blob is produced by the pipeline's own local build (production path
    compiles payload.c + enforcement.c together), then a committed probe
    fixture dlopens it, calls the enforcement entry, and prints the kernel
    state. The probe runs in a SUBPROCESS through the shared run_artifact
    helper: the policy is process-wide, and applying it inside pytest would
    change how every later test crashes and what /proc exposes.
    """
    from tests import _artifact_run
    from obfuscator.core.pipeline import build_local_cython
    payload = ("def main():\n"
               "    print('enf-blob-probe')\n"
               "\n"
               "if __name__ == '__main__':\n"
               "    main()\n")
    blob_data, blob_name = build_local_cython(payload)
    assert blob_data, "local blob build failed -- see the build log above"
    tmp = tempfile.mkdtemp(prefix="nx-enf-blob-")
    try:
        # the probe loads the blob with ctypes.CDLL, which does not care
        # about the extension, so a fixed file name suffices; containment
        # is validated before anything is written
        blob_path = os.path.realpath(os.sep.join((tmp, "blob.so")))
        if blob_path != tmp and not blob_path.startswith(tmp + os.sep):
            raise AssertionError("blob path escaped the scratch dir")
        with open(blob_path, "wb") as fh:
            fh.write(blob_data)
        result = _artifact_run.run_artifact(
            PROBE, timeout=120,
            env=dict(os.environ, NX_ENF_SO=blob_path,
                     PYTHONPATH=REPO))
        assert result.returncode == 0, (result.returncode, result.stderr[-400:])
        lines = (result.stdout or "").strip().splitlines()
        assert lines, "probe printed nothing"
        match = re.match(r"mask=(\d+) core=(\d+)", lines[-1])
        assert match, result.stdout
        mask = int(match.group(1))
        assert mask & 1, "dumpable was not cleared (mask=%d)" % mask
        assert mask & 2, "core limit was not zeroed (mask=%d)" % mask
        assert match.group(2) == "0", "kernel still allows core dumps"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
