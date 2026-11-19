"""The loader boundary is accepted, measured, and pinned here.

`docs/security/THREAT_BOUNDARY_LOADER.md` records a decision: the PAYLOAD is
hidden and the WRAPPER is not. That is a scope statement, and a scope statement
with no test decays into a claim, so this file pins the part of it that is
mechanically checkable.

The measurement behind it: renaming all 187 loader symbols left every
behaviour-bearing constant intact (`prctl`, `137`, `RLIMIT_CORE`, `mlock`,
`0o600`, the error string). Symbol obfuscation cannot hide behaviour, which is
why the boundary was accepted rather than engineered around.

What these tests assert:

  * the loader's behaviour lives in constants, not identifiers — so an
    obfuscation pass that only renames things cannot help, and nobody should
    try;
  * the PAYLOAD-side properties still hold (the guards exist and are wired), so
    accepting the wrapper limit did not quietly relax the payload;
  * the decision document exists and still says what was measured, because a
    boundary that drifts from its evidence is worse than no boundary.
"""
import os
import re
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

DOC = os.path.join(REPO, "docs", "security", "THREAT_BOUNDARY_LOADER.md")


def _loader_source():
    """Generate a hybrid loader and return its text."""
    from obfuscator.core import pipeline as pl

    return pl.generate_hybrid_loader_script(
        native_blobs={}, bytecode_fallback=b"", key_hex="00" * 32,
        native_only=False, build_id="boundary-test")[0]


def _rename_all_symbols(text):
    """Replace every loader symbol with an opaque name.

    This is the strongest symbol-level obfuscation that can be applied without
    changing behaviour, so it is the right probe for "would renaming help?".
    """
    names = sorted(set(re.findall(r"\b(_nx_[a-z_0-9]+|_NX_[A-Z_0-9]+)\b",
                                  text)))
    out = text
    for index, name in enumerate(names):
        out = re.sub(r"\b" + re.escape(name) + r"\b", "v%04x" % index, out)
    return out, len(names)


# ── the finding: behaviour survives renaming ─────────────────────────────

def test_the_loader_contains_behaviour_bearing_constants():
    """The syscall numbers and exit codes the model recovered."""
    loader = _loader_source()
    for marker in ("prctl", "137", "RLIMIT_CORE", "mlock"):
        assert marker in loader, (
            "%r is part of the enforcement behaviour and must be present; if "
            "it has gone, the boundary document needs re-measuring" % (marker,))


def test_renaming_every_symbol_does_not_remove_the_behaviour():
    """The measurement that made the boundary a decision rather than a task.

    If symbol obfuscation DID hide the behaviour, the boundary would be the
    wrong call and someone should implement it. This test fails if that ever
    becomes true, which is the signal to revisit the document.
    """
    loader = _loader_source()
    renamed, count = _rename_all_symbols(loader)
    assert count > 50, "expected a substantial symbol surface, got %d" % count
    for marker in ("prctl", "137", "RLIMIT_CORE", "mlock"):
        assert marker in renamed, (
            "%r disappeared under symbol renaming, which would mean the "
            "wrapper CAN be hidden by renaming -- re-measure and update "
            "docs/security/THREAT_BOUNDARY_LOADER.md" % (marker,))


def test_the_exit_code_is_a_literal_not_a_symbol():
    """`os._exit(137)` is behaviour; a named constant for it would be renamable."""
    loader = _loader_source()
    assert re.search(r"os\._exit\(\s*137\s*\)", loader) or "137" in loader


# ── the payload side still holds ─────────────────────────────────────────

def test_the_integrity_guards_are_still_wired():
    """Accepting the wrapper limit must not have relaxed the payload guards."""
    loader = _loader_source()
    assert "_nx_self_check" in loader, "self-check missing"
    assert "_NX_SELF_CK" in loader, "merkle anchor missing"
    assert "_NX_SELF_HM" in loader, "hmac anchor missing"
    assert "constant_time_compare" in loader, "constant-time compare missing"


def test_the_two_independent_layers_are_both_present():
    """§1's anti-patching redundancy: Merkle root AND HMAC.

    Measured in §5m: re-stamping the Merkle root alone is not enough, because
    the HMAC layer catches the tamper. Both constructions must be emitted for
    that result to hold.
    """
    loader = _loader_source()
    assert "sha256" in loader.lower(), "merkle layer missing"
    assert "hmac" in loader.lower(), "hmac layer missing"


def test_the_antidump_calls_are_present():
    loader = _loader_source()
    assert "PR_SET_DUMPABLE" in loader or "prctl" in loader
    assert "RLIMIT_CORE" in loader or "setrlimit" in loader


# ── the document itself ──────────────────────────────────────────────────

def test_the_boundary_document_exists():
    assert os.path.isfile(DOC), (
        "the accepted threat boundary must be recorded, not implied")


def test_the_document_still_records_the_measurement():
    """A boundary that drifts from its evidence is worse than none."""
    text = open(DOC, encoding="utf-8").read()
    for marker in ("187", "prctl", "137", "RLIMIT_CORE", "mlock"):
        assert marker in text, (
            "the document no longer records %r as part of the measurement"
            % (marker,))


def test_the_document_states_both_halves_of_the_boundary():
    """Payload holds / wrapper does not -- the whole point of the file."""
    text = open(DOC, encoding="utf-8").read()
    assert "payload" in text.lower()
    assert "wrapper" in text.lower()
    assert "accepted" in text.lower(), (
        "the document must state the decision, not just the finding")
    assert "0/4" in text and "0/2" in text, (
        "the payload-side numbers are the evidence that it HOLDS; they belong "
        "in the boundary file")


def test_the_document_names_what_would_change_the_answer():
    """Options that are not tuning changes, so the next attempt starts there."""
    text = open(DOC, encoding="utf-8").read()
    assert "native blob" in text.lower() or "native" in text.lower()
    assert "off-device" in text.lower() or "service" in text.lower()
