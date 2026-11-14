"""The downloaded-farm zip gate must actually stop extraction.

`_verify_download_zip` used to return False on the "sidecars present but no
key" path, and both callers ignored the return value and extracted anyway.
It now raises, so the gate cannot be bypassed by ignoring a boolean.
"""
import pytest


def _patch(monkeypatch, names, keys=()):
    from scripts import artifact_sign
    monkeypatch.setattr(artifact_sign, "zip_sidecar_names", lambda path: names)
    monkeypatch.setattr(artifact_sign, "resolve_ed25519_public_keys",
                        lambda: list(keys))


def test_sidecars_without_a_key_refuse_extraction(monkeypatch):
    from obfuscator.core.utils import _verify_download_zip
    _patch(monkeypatch, ["artifact.sig"])
    with pytest.raises(ValueError, match="no verification key"):
        _verify_download_zip("artifact.zip", "artifact", None)


def test_unreadable_sidecars_refuse_extraction(monkeypatch):
    from scripts import artifact_sign
    from obfuscator.core.utils import _verify_download_zip

    def boom(path):
        raise OSError("not a zip")

    monkeypatch.setattr(artifact_sign, "zip_sidecar_names", boom)
    with pytest.raises(ValueError, match="could not read signature sidecars"):
        _verify_download_zip("artifact.zip", "artifact", None)


def test_no_sidecars_is_the_auditable_downgrade(monkeypatch):
    from obfuscator.core.utils import _verify_download_zip
    _patch(monkeypatch, [])
    assert _verify_download_zip("artifact.zip", "artifact", None) is True


def test_key_without_sidecars_is_an_unsigned_farm(monkeypatch):
    from obfuscator.core.utils import _verify_download_zip
    _patch(monkeypatch, [], keys=["00" * 32])
    assert _verify_download_zip("artifact.zip", "artifact", None) is True
