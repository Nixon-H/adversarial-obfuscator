"""§7.9 farm-runner integrity: the runner attests, and control must check.

The review's argument: *"A compromised build runner can potentially bypass
every protection you carefully implemented in the compiler."* Nothing compared
what a runner said it built against what it was sent, so a runner that swapped
the payload or edited the transform layer produced a blob indistinguishable
from a genuine one.

Two halves are tested here, both LOCALLY (no farm, no credentials):

  * the DRIVER the workflow embeds must compile and emit the attestation
    fields -- read through ``render_farm_driver``, which returns the same text
    ``create_workflow`` assembles;
  * the CONTROLLER's ``verify`` must reject a different payload hash, a missing
    C hash, a missing Python version, an unattested blob, mismatched bytes, and
    an ABSENT attestation.

That last one is the design decision worth stating: a missing attestation is a
failure, not "no objection". A control that passes when the evidence is absent
is decoration.
"""
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.runner_attest import (  # noqa: E402
    SCHEMA, payload_digest, summary, verify,
)

PAYLOAD = b"print('hello')\n"
DIGEST = payload_digest(PAYLOAD)


def _attestation(**overrides):
    base = {
        "schema": SCHEMA,
        "runner": {"os": "Linux", "machine": "x86_64", "python": "3.13.5",
                   "cython": "3.0.12", "gcc": "gcc (Debian 14.2.0)"},
        "payload_sha256": DIGEST,
        "c_sha256": "a" * 64,
        "seed": {"reproducible": "00", "diversified": "11"},
        "transforms": ["opaque-predicates"],
        "artifacts": {"payload.so": "b" * 64},
    }
    base.update(overrides)
    return base


# ── the controller must accept a genuine attestation ────────────────────

def test_genuine_attestation_passes():
    result = verify(_attestation(), DIGEST,
                    downloaded=[("payload.so", "b" * 64)])
    assert result["ok"] is True, result["problems"]


# ── and reject every way a runner can lie ───────────────────────────────

def test_a_different_payload_hash_is_rejected():
    """The runner must have built the bytes the controller sent."""
    result = verify(_attestation(payload_sha256="c" * 64), DIGEST,
                    downloaded=[("payload.so", "b" * 64)])
    assert result["ok"] is False
    assert any("payload hash mismatch" in p for p in result["problems"])


def test_a_missing_c_hash_is_rejected():
    result = verify(_attestation(c_sha256=""), DIGEST,
                    downloaded=[("payload.so", "b" * 64)])
    assert result["ok"] is False
    assert any("transformed C hash" in p for p in result["problems"])


def test_a_missing_python_version_is_rejected():
    """Without a toolchain record there is no provenance at all."""
    bad = _attestation()
    bad["runner"] = {"os": "Linux"}
    result = verify(bad, DIGEST, downloaded=[("payload.so", "b" * 64)])
    assert result["ok"] is False
    assert any("Python version" in p for p in result["problems"])


def test_a_required_toolchain_field_must_be_present():
    result = verify(_attestation(), DIGEST,
                    downloaded=[("payload.so", "b" * 64)],
                    require_toolchain=("cython", "msvc"))
    assert result["ok"] is False
    assert any("msvc" in p for p in result["problems"])


def test_an_unattested_download_is_rejected():
    """A blob the runner never mentioned could have come from anywhere."""
    result = verify(_attestation(), DIGEST,
                    downloaded=[("payload.pyd", "d" * 64)])
    assert result["ok"] is False
    assert any("never attested" in p for p in result["problems"])


def test_bytes_that_differ_from_the_attestation_are_rejected():
    """The runner attested one hash and handed back another."""
    result = verify(_attestation(), DIGEST,
                    downloaded=[("payload.so", "e" * 64)])
    assert result["ok"] is False
    assert any("does not match" in p for p in result["problems"])


@pytest.mark.parametrize("absent", [None, {}, "not a dict", 0])
def test_a_missing_attestation_is_a_failure_not_a_pass(absent):
    result = verify(absent, DIGEST)
    assert result["ok"] is False, (
        "an absent attestation was accepted: %r" % (absent,))


def test_a_wrong_schema_is_rejected():
    result = verify(_attestation(schema="something-else"), DIGEST,
                    downloaded=[("payload.so", "b" * 64)])
    assert result["ok"] is False


def test_no_artifacts_recorded_is_rejected_by_default():
    result = verify(_attestation(artifacts={}), DIGEST, downloaded=[])
    assert result["ok"] is False
    assert any("no artifact hashes" in p for p in result["problems"])


# ── the driver the workflow actually embeds ─────────────────────────────

def test_the_embedded_driver_compiles():
    """The runner text must be syntactically valid before a farm run.

    The f-string context has already produced two syntax bugs, where a literal
    braces dict was read as a format specifier, so compiling this text is the
    only cheap way to know the attestation code survives packaging.
    """
    from obfuscator.core.utils import render_farm_driver

    driver = render_farm_driver("payload.py")
    assert driver, "the driver rendered empty"
    compile(driver, "<farm-driver>", "exec")


def test_the_driver_and_yaml_carry_no_control_characters():
    """A backslash escape inside the f-string template becomes a control char.

    Measured run 44868914170: the template text 'Installer\\vswhere.exe' (a
    backslash-vee sequence) was consumed by the OUTER f-string as a vertical
    tab escape before the inner raw-string prefix applied. The rendered YAML
    carried a 0x0B, GitHub rejected the workflow, and the farm run died in
    zero seconds at parse time. This is the same trap as the braces dict
    (three strikes now), so the guard is mechanical: neither the driver nor
    the YAML may contain ANY C0 control character except tab and newline.
    """
    from obfuscator.core.utils import render_farm_driver, render_farm_yaml

    driver = render_farm_driver("payload.py")
    yaml_text = render_farm_yaml("payload.py")
    assert driver and yaml_text
    bad_driver = [pos for pos, ch in enumerate(driver)
                  if ord(ch) < 32 and ch not in "\t\n"]
    bad_yaml = [pos for pos, ch in enumerate(yaml_text)
                if ord(ch) < 32 and ch not in "\t\n"]
    assert not bad_driver, (
        "the rendered driver contains control char(s) at %r -- a backslash "
        "escape inside the f-string template was consumed at render time; "
        "context: %r" % (bad_driver[:3],
                         driver[bad_driver[0] - 60:bad_driver[0] + 60]
                         if bad_driver else ""))
    assert not bad_yaml, (
        "the rendered YAML contains control char(s) at %r -- GitHub will "
        "reject the workflow at parse time" % (bad_yaml[:3],))


def test_the_embedded_driver_emits_the_attestation_fields():
    from obfuscator.core.utils import render_farm_driver

    driver = render_farm_driver("payload.py")
    for field in ("nx-runner-attestation/v1", "payload_sha256", "c_sha256",
                  "artifacts", "runner-attestation.json", "cython", "gcc",
                  "clang"):
        assert field in driver, "driver does not record %r" % (field,)


def test_the_embedded_driver_records_both_seeds():
    """Seed provenance travels with the attestation, per §5."""
    from obfuscator.core.utils import render_farm_driver

    driver = render_farm_driver("payload.py")
    assert "_repro_seed" in driver and "_divers_seed" in driver
    assert "reproducible" in driver and "diversified" in driver


def test_summary_is_human_readable():
    line = summary(_attestation())
    assert "Linux" in line and "3.13.5" in line and "payload=" in line
    assert summary(None) == "no attestation"


def test_payload_digest_matches_hashlib():
    assert payload_digest(PAYLOAD) == hashlib.sha256(PAYLOAD).hexdigest()
