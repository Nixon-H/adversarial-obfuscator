"""AI-BIN-002: a stamped artefact must fail closed when its anchor is zeroed.

The defect: the late self-checks were gated on the ANCHOR'S VALUE
(`_NX_SELF_CK not in (None, "", "0"*64)`), and the SAME predicate gated the
failure report. So zeroing `_NX_SELF_CK` skipped the check AND the report — and
the attacker who can edit the anchor is exactly the attacker the check exists to
catch. The mitigation said nothing.

The fix introduces a discriminator that is a fact about the BUILD rather than a
value an attacker can edit:

    _NX_SELF_STAMPED = True     # emitted only when the generator stamps

A stamped artefact whose anchor has been zeroed now fails closed. A
generator-emitted loader driven directly by tests or embedders never carries the
marker, so it keeps its legitimate no-op behaviour — which is why this fix broke
no existing test.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _loader(self_check=True):
    """Emit a loader. self_check=True is REQUIRED for the stamping branch.

    The first version of this file omitted it, so the marker was absent and
    three assertions failed against correct code -- a test bug, not a code bug.
    `generate_hybrid_loader_script` defaults `self_check=None`, and only the
    stamping branch emits `_NX_SELF_STAMPED`.
    """
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    src, _b, _f = generate_hybrid_loader_script(
        {"linux": b""}, b"print('P')\n" * 20, bytes(range(32)).hex(),
        native_only=False, section_split=True, section_count=4,
        self_check=self_check)
    return src


def _unstamped_loader():
    return _loader(self_check=False)


# ── the discriminator exists and is build-time, not value-time ────────────

def test_the_stamped_marker_is_emitted():
    src = _loader()
    assert "_NX_SELF_STAMPED = True" in src, (
        "no build-time stamped marker; the gate can only look at the anchor "
        "value, which is the value an attacker edits")


def test_the_marker_is_not_derived_from_the_anchor():
    """The marker must be a literal, not a function of _NX_SELF_CK."""
    src = _loader()
    idx = src.find("_NX_SELF_STAMPED = True")
    assert idx != -1
    line = src[idx:src.find("\n", idx)]
    assert "_NX_SELF_CK" not in line, (
        "the marker is derived from the anchor, so zeroing the anchor would "
        "also clear the marker and re-open the hole")


# ── the gate fires on the dangerous combination ───────────────────────────

def test_both_self_check_paths_fail_closed_on_a_zeroed_anchor():
    src = _loader()
    occurrences = src.count("anchor was removed or zeroed")
    assert occurrences == 2, (
        "expected the fail-closed diagnostic on BOTH the exec path and the "
        "native path; found %d" % occurrences)


def test_the_gate_distinguishes_stamped_from_unstamped():
    src = _loader()
    idx = src.find("anchor was removed or zeroed")
    window = src[max(0, idx - 700):idx + 200]
    assert "_NX_SELF_STAMPED" in window, (
        "the fail-closed branch does not consult the stamped marker")
    assert "_nx_anchor_ok" in window or "_NX_SELF_CK" in window, (
        "the fail-closed branch does not check the anchor value")


def test_an_unstamped_loader_stays_a_no_op():
    """The legitimate test/embedder case must not become fatal."""
    stamped = _loader(self_check=True)
    unstamped = _unstamped_loader()
    assert "_NX_SELF_STAMPED = True" in stamped, (
        "a stamped build must emit the marker")
    assert "_NX_SELF_STAMPED = True" not in unstamped, (
        "an UNstamped build emitted the marker, so an embedder's all-zero "
        "anchors would now be treated as tampering and the load would fail")
    # And the guard tolerates a missing marker rather than treating it as fatal:
    assert 'bool(globals().get("_NX_SELF_STAMPED"))' in stamped


# ── the rest of the artefact still works ──────────────────────────────────

def test_the_emitted_loader_still_compiles():
    compile(_loader(), "<loader>", "exec")
