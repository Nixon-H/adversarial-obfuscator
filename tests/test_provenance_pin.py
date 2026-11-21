"""Release-mode pin enforcement (review register, second pass, item 3).

Measured on a release-candidate build (docs/research §6c, build NX-RC-004):
the non-token-derived provenance check verified the signature against the
EMBEDDED key and never consulted `NIXON_PROVENANCE_PUBKEY` — so a missing
run-time pin AND a wrong pin were both ACCEPTED (rc 0). The RC acceptance
run executed the refusal matrix against the rebuilt artefact and every row
now refuses (missing pin rc 137, wrong pin rc 137, attacker re-sign rc 137
with "run-time pin does not match").

These tests pin the EMITTED LOADER SOURCE at the emit level so the fail-open
regression cannot return quietly; the runtime behaviour is measured by the
acceptance run and recorded in §6c.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.attestation import emit_snippet, stamp_artefact  # noqa: E402
import hashlib  # noqa: E402


def test_the_non_token_check_consults_the_out_of_band_pin():
    """THE FAIL-OPEN REGRESSION, pinned at the emit level.

    The emitted check must reference the out-of-band pin variable; before
    the fix it never did, which is why a missing pin AND a wrong pin were
    both accepted on the RC build.
    """
    snippet = emit_snippet(pin_required=True)
    compile(snippet, "<check>", "exec")
    assert "NIXON_PROVENANCE_PUBKEY" in snippet, (
        "the non-token-derived check does not consult the out-of-band pin; "
        "the fail-open regression is back")
    assert "_nx_prov_pin_required = True" in snippet


def test_the_pin_gate_is_off_by_default():
    """Without the release policy the snippet keeps the old contract.

    `emit_snippet()` (no pin_required) serves every existing caller: tests
    that build loaders directly and embeddings that do not run under the
    release policy. Those keep "unsigned runs, wrong pin still checked".
    """
    snippet = emit_snippet()
    compile(snippet, "<check>", "exec")
    assert "_nx_prov_pin_required = False" in snippet


def test_the_release_policy_flags_flow_into_the_loader():
    """The build wires the SAME policy flag into the emitted check.

    NIXON_REQUIRE_PROVENANCE=1 at build time now does two things: it refuses
    an unsigned build (the pipeline gate, tested in test_failure_modes), and
    it bakes the run-time pin requirement into the loader — the acceptance
    run measured the missing-pin refusal firing at RUN time on the rebuilt
    artefact (rc 137, "release policy requires the out-of-band trust
    anchor").
    """
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "obfuscator", "core", "pipeline.py"),
        encoding="utf-8").read()
    # The pin threading reads the SAME flag the build gate reads.
    assert src.count('os.environ.get("NIXON_REQUIRE_PROVENANCE") == "1"') >= 2, (
        "the build policy flag must drive BOTH the unsigned-build refusal "
        "and the run-time pin requirement")
    assert "pin_required=_prov_pin_required" in src, (
        "the emitted check is no longer built with the pin requirement")


def test_the_pin_match_logic_is_in_the_emitted_check():
    """A present pin must MATCH the embedded key — the untrusted-publisher
    refusal, measured rc 137 ("run-time pin does not match the artefact's
    signing key")."""
    snippet = emit_snippet(pin_required=True)
    compile(snippet, "<check>", "exec")
    assert "run-time pin does not match" in snippet
    assert "bytes.fromhex" in snippet, (
        "the pin arrives as raw hex and must be decoded before the key "
        "comparison")
    # and the comparison is against the EMBEDDED key bytes, not a re-derive
    assert "_nx_prov_pin_b != _nx_prov_pk_b" in snippet


def test_stamp_artefact_still_round_trips_through_the_verify_path():
    """The signing side is unchanged: stamp -> signed_content -> verify.

    `stamp_artefact` takes the artefact as TEXT (measured: bytes raise
    TypeError — the same call shape the acceptance script hit first).
    """
    import base64 as b64
    import hashlib
    import re as _re
    from obfuscator.attestation import signed_content
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey)

    sk = Ed25519PrivateKey.generate()
    artefact = ("line one\n"
                '_NX_PROV_SIG = ""\n'
                '_NX_PROV_PK = ""\n'
                "line four\n")
    stamped = stamp_artefact(artefact, sk)
    stamped_text = stamped if isinstance(stamped, str) else \
        stamped.decode("utf-8")
    assert '_NX_PROV_SIG = ""' not in stamped_text, (
        "the signature slot was not filled")
    # The signed content excludes the slot lines; the verifier recomputes it.
    msg = signed_content(stamped_text.encode("utf-8"))
    sig = stamped_text.split('_NX_PROV_SIG = "')[1].split('"')[0]
    m = _re.search(r'_NX_PROV_PK = "(?:[0-9a-f]{16}: )?([A-Za-z0-9+/=]+)"',
                   stamped_text)
    pk_b = b64.b64decode(m.group(1))
    sig_b = b64.b64decode(sig)
    pub = Ed25519PublicKey.from_public_bytes(pk_b)
    pub.verify(sig_b, msg)  # raises on mismatch
    # The PK slot carries THIS key. The fingerprint PREFIX is added by the
    # pipeline's stamping step (measured: stamp_artefact writes the plain
    # base64; the prefix comes from the build), and the acceptance run
    # verified prefix-consistency on the real artefact.
