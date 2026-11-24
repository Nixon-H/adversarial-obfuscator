"""AI-BIN-001: the RO-after-load sealing API must actually be called.

Found by the binary-security audit: `section_split.py` documents and tests a
read-only-after-load capability (`protect_after_load`, `seal_joined`,
`stream_join_sealed`) that re-mprotects the joined plaintext PROT_READ — and
**nothing in the shipped loader called it**. Grep across `obfuscator/` found zero
production callers: the mitigation was implemented, described as present, and
unreachable.

A documented control nobody invokes is worse than an undocumented gap, because
it stops the next person looking.

The fix wires the protection into the one place the whole cleartext payload is
contiguous before exec — the loader's join branch — best-effort, with a flag that
records whether it actually took effect so "not applied" is distinguishable from
"applied".
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _loader_source():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _blobs, _fb = generate_hybrid_loader_script(
        {"linux": b""}, b"print('P')\n" * 20, bytes(range(32)).hex(),
        native_only=False, section_split=True, section_count=4)
    return src


def test_the_loader_attempts_read_only_protection():
    """The emitted loader must call mprotect on the joined payload."""
    src = _loader_source()
    assert "mprotect" in src, (
        "the emitted loader never mprotects the joined payload; the documented "
        "read-only-after-load mitigation is unreachable, which is AI-BIN-001")
    assert "_NX_PAYLOAD_RO" in src, (
        "the loader does not record whether RO protection took effect, so "
        "'not applied' cannot be distinguished from 'applied'")


def test_ro_protection_is_best_effort_not_fatal():
    """Hardening must never break a legitimate artefact."""
    src = _loader_source()
    idx = src.find("_NX_PAYLOAD_RO")
    window = src[max(0, idx - 2600):idx + 400]
    assert "except Exception" in window, (
        "the RO block has no exception guard; a platform without mprotect "
        "would fail the load")
    assert "False" in window, (
        "there is no failure branch recording that RO was not applied")


def test_ro_uses_prot_read_not_exec():
    """The protection is read-only; it must not request an executable page.

    The first occurrence of "mprotect" in the emitted source is in the
    explanatory comment, so this searches for the CALL form
    (`_nx_ro_libc.mprotect(`) rather than the bare word.
    """
    src = _loader_source()
    idx = src.find("_nx_ro_libc.mprotect(")
    assert idx != -1, (
        "no mprotect call site found in the emitted loader")
    # The full call including its argument list.
    tail = src[idx:idx + 400]
    assert "_nx_ro_ct.c_size_t(_nx_ro_len), 1)" in tail, (
        "the mprotect call does not pass PROT_READ (1) as its third argument; "
        "found: %r" % tail[:200])
    assert "PROT_EXEC" not in tail, (
        "the mprotect call region mentions PROT_EXEC; the joined payload must "
        "never be made executable in place")
    assert "PROT_WRITE" not in tail, (
        "the mprotect call region mentions PROT_WRITE; the point is to REMOVE "
        "write access")


def test_a_production_caller_exists_in_the_loader_path():
    """Pin the actual regression: the API had zero production callers."""
    import subprocess
    out = subprocess.run(
        ["grep", "-rn", "mprotect", "--include=*.py",
         os.path.join(ROOT, "obfuscator", "core", "pipeline.py")],
        capture_output=True, text=True, timeout=60).stdout
    assert out.strip(), (
        "pipeline.py contains no mprotect reference, so no shipped artefact "
        "can apply read-only protection to its payload")
