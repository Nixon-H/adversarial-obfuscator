"""RFC 6238 helpers used by the Cloudflare remote-execution gate."""
import base64
import json
import os
import stat
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.cloudflare_remote import write_totp_provisioning  # noqa: E402
from obfuscator.totp import (  # noqa: E402
    TOTPError, new_base32_secret, normalize_base32_secret,
    normalize_totp_code, otpauth_uri, totp_code, verify_totp,
)


def test_rfc6238_sha1_vector():
    # RFC 6238 Appendix B uses the ASCII seed "12345678901234567890" and
    # expects 94287082 at T=59 for the eight-digit SHA-1 profile.
    secret = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
    assert totp_code(secret, at=59, digits=8) == "94287082"
    assert totp_code(secret, at=59) == "287082"
    assert verify_totp(secret, "94287082", at=59, digits=8, window=0)


def test_authenticator_profile_is_base32_sha1_six_digits_thirty_seconds():
    secret = new_base32_secret()
    code = totp_code(secret, at=1200)
    assert len(secret) >= 32
    assert len(code) == 6 and code.isdigit()
    assert verify_totp(secret, code, at=1200, window=0)
    assert not verify_totp(secret, "000000" if code != "000000" else "999999",
                           at=1200, window=0)


def test_window_accepts_one_step_but_not_old_codes():
    secret = new_base32_secret()
    previous = totp_code(secret, at=1170)
    old = totp_code(secret, at=1110)
    assert verify_totp(secret, previous, at=1200, window=1)
    assert not verify_totp(secret, old, at=1200, window=1)


def test_spaces_in_user_entered_code_are_accepted():
    secret = new_base32_secret()
    code = totp_code(secret, at=1200)
    spaced = code[:3] + " " + code[3:]
    assert normalize_totp_code(spaced) == code
    assert verify_totp(secret, spaced, at=1200, window=0)


def test_malformed_secret_and_code_are_rejected():
    try:
        normalize_base32_secret("not valid !")
    except TOTPError:
        pass
    else:
        raise AssertionError("malformed base32 secret accepted")
    assert not verify_totp("not valid !", "123456", at=1200)
    assert not verify_totp(new_base32_secret(), "12345", at=1200)


def test_otpauth_uri_contains_interoperable_parameters():
    secret = new_base32_secret()
    uri = otpauth_uri(secret, label="test-label")
    assert uri.startswith("otpauth://totp/test-label?")
    assert "algorithm=SHA1" in uri
    assert "digits=6" in uri
    assert "period=30" in uri
    assert "secret=" in uri


def test_dual_totp_provisioning_is_independent_and_owner_only(tmp_path):
    path = tmp_path / "totp-provisioning.json"
    doc = write_totp_provisioning(str(path))
    assert doc["primary"]["secret"] != doc["secondary"]["secret"]
    assert doc["primary"]["otpauth_uri"] != doc["secondary"]["otpauth_uri"]
    loaded = json.loads(path.read_text())
    assert loaded["primary"]["secret"] == doc["primary"]["secret"]
    assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def test_dual_totp_provisioning_refuses_to_overwrite(tmp_path):
    path = tmp_path / "totp-provisioning.json"
    write_totp_provisioning(str(path))
    try:
        write_totp_provisioning(str(path))
    except FileExistsError:
        pass
    else:
        raise AssertionError("provisioning overwrite was accepted")
