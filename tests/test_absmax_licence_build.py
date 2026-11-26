"""Regression for ABSOLUTE MAXIMUM machine-bound licence builds.

A licence token carrying ``payload.hwid`` must be verified against the same
host identity supplied to the build.  The pre-fix build called the verifier
without an HWID, so every correctly machine-bound token was refused before
the artefact could be built.
"""
import argparse
import time

import pytest

from obfuscator import licensing as lic
from obfuscator.core.pipeline import _verify_build_licence_document
from tests.test_licensing import _keypair


def _bound_document(hwid="HWID:" + "a" * 64):
    private, _public = _keypair()
    now = time.time()
    licence = lic.Licence(
        licence_id="L-bound-build",
        customer="acme",
        issued_at=now,
        expires_at=now + 3600,
        features=("pro",),
        hwid=hwid,
    )
    return lic.issue(licence, private), private, hwid


def test_machine_bound_licence_accepts_matching_build_hwid():
    import json
    token, private, hwid = _bound_document()
    args = argparse.Namespace(hwid=hwid)
    verified = _verify_build_licence_document(
        json.loads(token), lic.public_key_hex(private), args)
    assert verified.hwid == hwid


def test_machine_bound_licence_rejects_mismatched_build_hwid():
    import json
    token, private, _hwid = _bound_document()
    args = argparse.Namespace(hwid="HWID:" + "b" * 64)
    with pytest.raises(lic.LicenceError, match="different machine"):
        _verify_build_licence_document(
            json.loads(token), lic.public_key_hex(private), args)


def test_machine_bound_licence_still_fails_closed_without_build_hwid():
    import json
    token, private, _hwid = _bound_document()
    args = argparse.Namespace(hwid="")
    with pytest.raises(lic.LicenceError, match="no hwid"):
        _verify_build_licence_document(
            json.loads(token), lic.public_key_hex(private), args)
