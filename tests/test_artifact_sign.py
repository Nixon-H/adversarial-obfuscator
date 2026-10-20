"""Tests for scripts/artifact_sign.py."""
import os
import subprocess
import sys


from scripts.artifact_sign import sign_file, verify_file

KEY = b"test-key-0123456789abcdef"
WRONG_KEY = b"wrong-key-9876543210fedcba"


def test_roundtrip(tmp_path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"hello artifact")
    sig = sign_file(str(target), KEY)
    assert sig["algo"] == "hmac-sha256"
    assert len(sig["hex"]) == 64
    assert verify_file(str(target), KEY, sig) is True


def test_tamper_fails(tmp_path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"original bytes")
    sig = sign_file(str(target), KEY)
    target.write_bytes(b"tampered bytes")
    assert verify_file(str(target), KEY, sig) is False


def test_wrong_key_fails(tmp_path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"secret payload")
    sig = sign_file(str(target), KEY)
    assert verify_file(str(target), WRONG_KEY, sig) is False


def test_bad_sig_shape_rejected(tmp_path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"data")
    assert verify_file(str(target), KEY, {"algo": "md5", "hex": "00"}) is False
    assert verify_file(str(target), KEY, {"algo": "hmac-sha256"}) is False
    assert verify_file(str(target), KEY, "not-a-dict") is False  # type: ignore[arg-type]


def test_cli_smoke(tmp_path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"cli smoke bytes")
    key_hex = KEY.hex()
    env = dict(os.environ)
    env.pop("NIXON_SIGN_KEY", None)
    sign = subprocess.run(
        [sys.executable, "-m", "scripts.artifact_sign", str(target),
         "--key-hex", key_hex],
        capture_output=True, text=True, timeout=30,
    )
    assert sign.returncode == 0, sign.stderr
    hex_digest = sign.stdout.strip()
    assert len(hex_digest) == 64
    verify = subprocess.run(
        [sys.executable, "-m", "scripts.artifact_sign", str(target),
         "--key-hex", key_hex, "--verify", hex_digest],
        capture_output=True, text=True, timeout=30,
    )
    assert verify.returncode == 0
    assert verify.stdout.strip() == "OK"
    bad = subprocess.run(
        [sys.executable, "-m", "scripts.artifact_sign", str(target),
         "--key-hex", key_hex, "--verify", "00" * 32],
        capture_output=True, text=True, timeout=30,
    )
    assert bad.returncode != 0
    assert bad.stdout.strip() == "FAIL"
