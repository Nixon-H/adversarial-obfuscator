"""Tests for ADR-0005 artifact authenticity (bound signatures + gates).

Covers ``scripts/artifact_sign.py`` bound sign/verify
(``hmac-sha256-binding-v1``), legacy bytes-only compatibility, the
verify-before-extract zip gate, the no-key warning policy, and the
package-step sidecar. The ``obfuscator.core.utils`` download/upload glue
is intentionally NOT imported here (module import has log-redirect/UI
side effects); policy logic is tested at the helper level and the glue
is ``py_compile`` + review covered (see ADR-0005 residual risk 7).
"""
import json
import logging
import os
import zipfile
from types import SimpleNamespace

import pytest

from scripts import artifact_sign as A
from scripts.artifact_sign import (
    BINDING_ALGO,
    SignatureMismatchError,
    default_metadata,
    enforce_dir_sidecars,
    read_sidecar,
    resolve_key,
    sign_artifact,
    sign_file,
    verify_artifact,
    verify_file,
    verify_zip_sidecars,
    write_sidecar,
    zip_sidecar_names,
)

KEY = bytes.fromhex("ab" * 32)
WRONG_KEY = bytes.fromhex("cd" * 32)
META = {"repo": "acme/farm", "commit": "deadbeef" * 5,
        "build_id": "b-123", "platform": "linux"}


def _write(path, data: bytes):
    with open(str(path), "wb") as f:
        f.write(data)
    return str(path)


# --- bound sign/verify ----------------------------------------------------

def test_bound_roundtrip(tmp_path):
    target = _write(tmp_path / "artifact.bin", b"hello bound artifact")
    sig = sign_artifact(target, KEY, dict(META))
    assert sig["algo"] == BINDING_ALGO
    assert len(sig["hex"]) == 64
    assert sig["metadata"] == META
    assert verify_artifact(target, KEY, sig) is True


def test_bound_expected_subset_pin(tmp_path):
    target = _write(tmp_path / "artifact.bin", b"pinned bytes")
    sig = sign_artifact(target, KEY, dict(META))
    assert verify_artifact(target, KEY, sig, {"build_id": "b-123"}) is True
    assert verify_artifact(target, KEY, sig, {"build_id": "other"}) is False


def test_tampered_bytes_fail_closed(tmp_path):
    target = _write(tmp_path / "artifact.bin", b"original bytes")
    sig = sign_artifact(target, KEY, dict(META))
    _write(tmp_path / "artifact.bin", b"tampered bytes")
    assert verify_artifact(target, KEY, sig) is False


def test_tampered_metadata_fail_closed(tmp_path):
    target = _write(tmp_path / "artifact.bin", b"original bytes")
    sig = sign_artifact(target, KEY, dict(META))
    sig["metadata"]["build_id"] = "attacker-build"
    assert verify_artifact(target, KEY, sig) is False
    del sig["metadata"]
    assert verify_artifact(target, KEY, sig) is False


def test_wrong_key_fails(tmp_path):
    target = _write(tmp_path / "artifact.bin", b"secret payload")
    sig = sign_artifact(target, KEY, dict(META))
    assert verify_artifact(target, WRONG_KEY, sig) is False


def test_legacy_bytes_only_still_verifies(tmp_path):
    target = _write(tmp_path / "artifact.bin", b"legacy bytes")
    legacy = sign_file(target, KEY)
    assert verify_artifact(target, KEY, legacy) is True
    # ... but a legacy sig can never satisfy a metadata pin (no downgrade).
    assert verify_artifact(target, KEY, legacy, {"build_id": "b-123"}) is False
    assert verify_file(target, KEY, legacy) is True  # old API untouched


def test_default_metadata_keys(tmp_path):
    meta = default_metadata()
    for k in ("repo", "commit", "build_id", "platform", "python"):
        assert k in meta
    extra = default_metadata({"build_id": "x", "custom": 1})
    assert extra["build_id"] == "x"


# --- key resolution -------------------------------------------------------

def test_resolve_key_precedence(monkeypatch):
    monkeypatch.setenv("NIXON_SIGN_KEY", KEY.hex())
    monkeypatch.setenv("NIXON_ARTIFACT_KEY_HEX", WRONG_KEY.hex())
    assert resolve_key() == WRONG_KEY  # explicit name wins
    monkeypatch.delenv("NIXON_ARTIFACT_KEY_HEX")
    assert resolve_key() == KEY  # legacy fallback


def test_resolve_key_absent_or_malformed(monkeypatch):
    monkeypatch.delenv("NIXON_ARTIFACT_KEY_HEX", raising=False)
    monkeypatch.delenv("NIXON_SIGN_KEY", raising=False)
    assert resolve_key() is None
    monkeypatch.setenv("NIXON_SIGN_KEY", "not-hex!!")
    assert resolve_key() is None
    monkeypatch.setenv("NIXON_SIGN_KEY", "")
    assert resolve_key() is None


# --- verify-before-extract zip gate ----------------------------------------

def _signed_zip(tmp_path, payload: bytes, meta=None):
    member = tmp_path / "payload.linux.bin"
    _write(member, payload)
    sig = sign_artifact(str(member), KEY, dict(meta or META))
    sidecar = write_sidecar(str(member), sig)
    zpath = str(tmp_path / "payload.zip")
    with zipfile.ZipFile(zpath, "w") as z:
        z.write(str(member), "payload.linux.bin")
        z.write(sidecar, "payload.linux.bin.sig.json")
    return zpath


def test_zip_gate_ok(tmp_path):
    zpath = _signed_zip(tmp_path, b"farm bytes v1")
    assert zip_sidecar_names(zpath) == ["payload.linux.bin.sig.json"]
    assert verify_zip_sidecars(zpath, KEY) == 1


def test_zip_gate_tamper_fail_closed(tmp_path):
    zpath = _signed_zip(tmp_path, b"farm bytes v1")
    # Rebuild the zip with the same sidecar but modified member bytes.
    with zipfile.ZipFile(zpath, "r") as z:
        sidecar_raw = z.read("payload.linux.bin.sig.json")
    bad = str(tmp_path / "payload_bad.zip")
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("payload.linux.bin", b"PATCHED bytes")
        z.writestr("payload.linux.bin.sig.json", sidecar_raw)
    with pytest.raises(SignatureMismatchError):
        verify_zip_sidecars(bad, KEY)


def test_zip_gate_wrong_key_fail_closed(tmp_path):
    zpath = _signed_zip(tmp_path, b"farm bytes v1")
    with pytest.raises(SignatureMismatchError):
        verify_zip_sidecars(zpath, WRONG_KEY)


def test_zip_gate_no_sidecars_zero(tmp_path):
    zpath = str(tmp_path / "plain.zip")
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("payload.linux.bin", b"unsigned farm bytes")
    assert zip_sidecar_names(zpath) == []
    assert verify_zip_sidecars(zpath, KEY) == 0


def test_zip_gate_missing_sibling_or_bad_algo(tmp_path):
    orphan = str(tmp_path / "orphan.zip")
    with zipfile.ZipFile(orphan, "w") as z:
        z.writestr("ghost.sig.json", json.dumps(
            {"algo": BINDING_ALGO, "hex": "00" * 32, "metadata": {}}))
    with pytest.raises(SignatureMismatchError):
        verify_zip_sidecars(orphan, KEY)
    weird = str(tmp_path / "weird.zip")
    with zipfile.ZipFile(weird, "w") as z:
        z.writestr("f.bin", b"data")
        z.writestr("f.bin.sig.json", json.dumps(
            {"algo": "rot13", "hex": "00" * 32}))
    with pytest.raises(SignatureMismatchError):
        verify_zip_sidecars(weird, KEY)


# --- on-disk sidecar policy (no silent downgrade) ---------------------------

def _staged_dir(tmp_path, payload: bytes, meta=None):
    member = tmp_path / "payload.linux.bin"
    _write(member, payload)
    sig = sign_artifact(str(member), KEY, dict(meta or META))
    write_sidecar(str(member), sig)
    return str(tmp_path)


def test_enforce_dir_with_key_verified(tmp_path):
    d = _staged_dir(tmp_path, b"good bytes")
    assert enforce_dir_sidecars(d, KEY) == {"status": "verified", "count": 1}


def test_enforce_dir_with_key_mismatch_raises(tmp_path):
    d = _staged_dir(tmp_path, b"good bytes")
    _write(os.path.join(d, "payload.linux.bin"), b"swapped bytes")
    with pytest.raises(SignatureMismatchError):
        enforce_dir_sidecars(d, KEY)


def test_enforce_dir_no_key_warns_loudly(tmp_path, caplog):
    d = _staged_dir(tmp_path, b"good bytes")
    with caplog.at_level(logging.WARNING, logger="scripts.artifact_sign"):
        result = enforce_dir_sidecars(d, None)
    assert result["status"] == "unverified-no-key"
    assert any(r.levelno == logging.WARNING and "ARTIFACT-AUTH" in r.message
               for r in caplog.records)


def test_enforce_dir_no_key_no_sigs_warns(tmp_path, caplog):
    _write(tmp_path / "payload.linux.bin", b"unsigned bytes")
    with caplog.at_level(logging.WARNING, logger="scripts.artifact_sign"):
        result = enforce_dir_sidecars(str(tmp_path), None)
    assert result["status"] == "no-key-no-signatures"
    assert any(r.levelno == logging.WARNING and "ARTIFACT-AUTH" in r.message
               for r in caplog.records)


def test_enforce_dir_key_no_sigs_info(tmp_path):
    _write(tmp_path / "payload.linux.bin", b"unsigned bytes")
    assert enforce_dir_sidecars(str(tmp_path), KEY) == {
        "status": "no-signatures", "count": 0}


# --- package step writes bound sidecars -------------------------------------

def test_package_step_writes_bound_sidecar(tmp_path, monkeypatch):
    import scripts.phases.phase06_package as pkg

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    monkeypatch.setattr(pkg, "BUILD_DIR", str(build_dir))
    monkeypatch.setenv("NIXON_TEST_PKG_KEY", KEY.hex())

    payload = _write(tmp_path / "src.py", b"print('hi')")
    staged = _write(tmp_path / "obf_tmp.py", b"obfuscated bytes")
    opts = SimpleNamespace(sign_key_env="NIXON_TEST_PKG_KEY",
                           include_original=False, build_id="pkg-b1")
    pkg.phase_package(payload, staged, "app_obfuscated.py", opts)

    sidecar = build_dir / "app_obfuscated.py.sig.json"
    assert sidecar.exists()
    sig = read_sidecar(str(sidecar))
    assert sig["algo"] == BINDING_ALGO
    assert sig["metadata"]["build_id"] == "pkg-b1"
    assert "platform" in sig["metadata"]
    assert verify_artifact(
        str(build_dir / "app_obfuscated.py"), KEY, sig) is True
    # Tamper the packaged file: bound verification fails closed.
    _write(build_dir / "app_obfuscated.py", b"patched bytes")
    assert verify_artifact(
        str(build_dir / "app_obfuscated.py"), KEY, sig) is False


def test_package_step_without_key_skips_cleanly(tmp_path, monkeypatch,
                                                capsys):
    import scripts.phases.phase06_package as pkg

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    monkeypatch.setattr(pkg, "BUILD_DIR", str(build_dir))
    monkeypatch.delenv("NIXON_TEST_PKG_MISSING", raising=False)

    payload = _write(tmp_path / "src.py", b"print('hi')")
    staged = _write(tmp_path / "obf_tmp.py", b"obfuscated bytes")
    opts = SimpleNamespace(sign_key_env="NIXON_TEST_PKG_MISSING",
                           include_original=False, build_id="")
    pkg.phase_package(payload, staged, "app_obfuscated.py", opts)  # no raise
    assert not (build_dir / "app_obfuscated.py.sig.json").exists()
    assert (build_dir / "app_obfuscated.py").exists()
    assert A.BINDING_ALGO == "hmac-sha256-binding-v1"
