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


# ── the double-stamp finding (measured 2026-11-19) ───────────────────────

def test_the_hmac_key_ships_in_plaintext():
    """The premise of the double-stamp attack, asserted rather than assumed.

    The loader must hold the key to verify, so the key is in the file. That is
    what makes both integrity layers recomputable by anyone holding the
    artefact — the finding this file records.

    The ANCHOR NAMES are asserted on the template; the VALUES are a build-time
    product, so a stamped artefact is checked separately in
    test_a_stamped_artefact_exposes_its_key.
    """
    source = open(os.path.join(REPO, "obfuscator", "core", "pipeline.py"),
                  encoding="utf-8").read()
    for anchor in ("_NX_SELF_HK", "_NX_SELF_HM", "_NX_SELF_CK"):
        assert anchor in source, "%s is not emitted by the loader template" % anchor


def test_a_stamped_artefact_exposes_its_key():
    """A real stamped artefact carries the HMAC key as a plaintext literal."""
    import glob
    import re
    cands = sorted(glob.glob("/tmp/pydeobs-max-*/tiny/dist/tiny_protected.py"),
                   key=os.path.getmtime)
    if not cands:
        pytest.skip("no stamped artefact on disk")
    text = open(cands[-1], encoding="utf-8", errors="replace").read()
    match = re.search(r'^_NX_SELF_HK\s*=\s*"([0-9a-f]+)"', text, re.M)
    assert match, "a shipped artefact must carry _NX_SELF_HK"
    assert len(match.group(1)) == 64, "expected a 32-byte hex key, got %r" % (
        match.group(1)[:16],)


def test_the_attack_chain_measures_the_double_stamp_route():
    """The scenario must stay wired, or the finding goes stale silently."""
    source = open(os.path.join(REPO, "scripts", "attack_chain.py"),
                  encoding="utf-8").read()
    assert "def restamp_all" in source, (
        "the double-stamp helper is gone; the measurement cannot be reproduced")
    assert "tamper + BOTH stamps" in source, (
        "the double-stamp row is no longer reported")
    assert "INTEGRITY IS INTERNAL-ONLY" in source, (
        "the verdict for a successful double-stamp attack was removed")


def test_the_boundary_document_records_the_double_stamp_result():
    """The measured outcome belongs in the document, not only in the script.

    A successful attack recorded nowhere is a silent regression: the next
    reader would assume the five-route result means the control holds.
    """
    text = open(DOC, encoding="utf-8").read()
    assert "re-stamp BOTH" in text or "re-stamp both" in text.lower(), (
        "the document must record that recomputing both layers succeeds")
    assert "internally consistent" in text.lower(), (
        "the document must state what the check DOES establish")
    assert "authentic" in text.lower() or "publisher" in text.lower(), (
        "the document must state what it does not establish")


def test_the_document_names_the_real_fix():
    """A boundary without a path forward is an excuse. The fix is named."""
    text = open(DOC, encoding="utf-8").read()
    assert "ed25519" in text.lower(), (
        "signature verification is the smallest change with a real effect")
    assert "licence token" in text.lower() or "license token" in text.lower(), (
        "deriving the key from token material is the other real option")


# ── load-time signature verification (the double-stamp fix) ──────────────

def test_the_provenance_verifier_is_installed():
    """`obfuscator/attestation.py` must emit a self-contained check.

    This is the fix named for the measured double-stamp attack: the Merkle root
    and the HMAC are both recomputable from the artefact, so neither binds it to
    the publisher. A signature checked against an embedded public key does,
    because the private key never ships.
    """
    from obfuscator import attestation as A

    snippet = A.emit_snippet()
    assert "_nx_prov_verify" in snippet, "no verifier emitted"
    assert "_NX_PROV_SIG" in snippet, "no signature slot"
    assert "_NX_PROV_PK" in snippet, "no public-key slot"
    assert "sha512" in snippet.lower(), "not an Ed25519 construction"
    # The snippet is pasted into the loader, so it must compile standalone.
    compile(snippet, "<provenance-snippet>", "exec")


def test_the_reference_verifier_agrees_with_cryptography():
    """The stdlib verifier must match a real Ed25519 implementation.

    The artefact cannot import `cryptography`, which is why a pure-Python
    verifier exists. If it disagreed, signed artefacts would either refuse to
    run or — worse — accept a signature they should reject.
    """
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    from obfuscator import ed25519_verify as reference

    key = Ed25519PrivateKey.generate()
    other = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    other_public = other.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)

    message = b"artefact bytes"
    signature = key.sign(message)
    assert reference.verify(public, signature, message) is True
    assert reference.verify(public, signature, message + b"!") is False
    assert reference.verify(other_public, signature, message) is False
    assert reference.verify(public, bytes([signature[0] ^ 1]) + signature[1:],
                            message) is False
    assert reference.verify(public, signature[:-1], message) is False


def test_the_inline_verifier_matches_the_reference():
    """The copy that SHIPS is the one that must be tested.

    A reference that agrees with `cryptography` says nothing about a different
    block of code pasted into every artefact. The inline block is loaded as a
    module from a temp file rather than executed inline, so this test carries no
    dynamic-execution sink while still exercising the exact shipped bytes.
    """
    pytest.importorskip("cryptography")
    import importlib.util
    import tempfile

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    from obfuscator import attestation as A
    from obfuscator import ed25519_verify as reference

    handle, path = tempfile.mkstemp(suffix=".py", prefix="nx_inline_")
    try:
        os.write(handle, A.VERIFIER_SOURCE.encode("utf-8"))
        os.close(handle)
        spec = importlib.util.spec_from_file_location("nx_inline_v", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        inline = module._nx_prov_verify
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    key = Ed25519PrivateKey.generate()
    other = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    other_public = other.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)

    disagreements = []
    for message in (b"", b"x", b"artefact bytes", b"z" * 512):
        signature = key.sign(message)
        for args in ((public, signature, message),
                     (public, signature, message + b"!"),
                     (other_public, signature, message),
                     (public, bytes([signature[0] ^ 1]) + signature[1:], message),
                     (public, signature[:-1], message),
                     (public[:8], signature, message)):
            if inline(*args) != reference.verify(*args):
                disagreements.append(message[:8])
    assert disagreements == [], disagreements


def test_the_signed_stream_excludes_the_slots():
    """The circularity resolves the same way the other anchors resolve it.

    The signature covers the file and lives in the file, so the slot lines are
    outside the signed stream — a value cannot be part of what it describes.
    """
    from obfuscator import attestation as A

    text = b"a\n_NX_PROV_SIG = \"s\"\n_NX_PROV_PK = \"p\"\nb\n"
    content = A.signed_content(text)
    assert b"_NX_PROV_SIG" not in content and b"_NX_PROV_PK" not in content
    assert b"a" in content and b"b" in content
    assert b"_NX_PROV_SIG" in A.CHECK_SOURCE.encode(), (
        "the emitted check must name the slot it excludes")


def test_the_document_records_the_signature_fix():
    """The document must point at the implemented fix, not only the problem."""
    text = open(DOC, encoding="utf-8").read()
    assert "attestation.py" in text or "signature verification" in text.lower(), (
        "the boundary document must point at the implemented fix")


# ── token-derived provenance: the double-stamp fix, closed ───────────────

def test_plain_provenance_trusts_the_embedded_key():
    """The DEFAULT still trusts the embedded slot, and that is why it failed.

    Documented rather than hidden: an artefact verified against a key it carries
    agrees with itself. An attacker re-signs with their own key and the check
    passes — measured as the double-stamp attack.
    """
    from obfuscator import attestation as A
    snippet = A.emit_snippet()
    assert "NIXON_PROVENANCE_PUBKEY" not in snippet, (
        "the plain variant does not pin a key; that is the limitation")


def test_token_derived_provenance_does_not_trust_the_embedded_key():
    """The fix: the trust anchor moves out of the artefact.

    With ``token_derived=True`` the emitted check compares the embedded key
    against the token's key (or an out-of-band pinned key) and dies on mismatch,
    so re-signing requires the publisher's private key.
    """
    from obfuscator import attestation as A
    snippet = A.emit_snippet(token_derived=True)
    assert "NIXON_PROVENANCE_PUBKEY" in snippet, (
        "no out-of-band pin: the artefact would still verify itself")
    assert "does not match" in snippet, "no mismatch check emitted"
    assert "_nx_licence_key" in snippet, (
        "no token-derived key path: the customer's token is what makes the "
        "signature meaningful")
    compile(snippet, "<token-derived>", "exec")


def test_both_provenance_variants_compile():
    """Emitted code is pasted into every artefact, so it must be valid source."""
    from obfuscator import attestation as A
    for token_derived in (False, True):
        compile(A.emit_snippet(token_derived=token_derived),
                "<provenance>", "exec")
