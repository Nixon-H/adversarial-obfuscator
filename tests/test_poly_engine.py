import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.poly.poly_engine import PolyEngine


def test_probe_python_version():
    engine = PolyEngine()
    ver = engine.probe_python_version()
    parts = ver.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_probe_os():
    engine = PolyEngine()
    os_name = engine.probe_os()
    assert isinstance(os_name, str)
    assert len(os_name) > 0


def test_probe_architecture():
    engine = PolyEngine()
    arch = engine.probe_architecture()
    assert isinstance(arch, str)
    assert len(arch) > 0


def test_probe_cpu_features():
    engine = PolyEngine()
    features = engine.probe_cpu_features()
    assert isinstance(features, list)
    assert len(features) > 0


def test_probe_environment_variables():
    engine = PolyEngine()
    env_vars = engine.probe_environment_variables()
    assert isinstance(env_vars, dict)
    assert "PATH" in env_vars or "HOME" in env_vars


def test_probe_filesystem_layout():
    engine = PolyEngine()
    layout = engine.probe_filesystem_layout()
    assert isinstance(layout, dict)
    assert "/etc" in layout
    assert "/tmp" in layout


def test_get_environment_profile():
    engine = PolyEngine(seed=12345)
    profile = engine.get_environment_profile()
    assert "python" in profile
    assert "os" in profile
    assert "arch" in profile
    assert "cpu_features" in profile
    assert "env_vars" in profile
    assert "fs_layout" in profile
    assert "fingerprint" in profile
    assert len(profile["fingerprint"]) == 32


def test_consistent_fingerprint():
    engine1 = PolyEngine(seed=42)
    engine2 = PolyEngine(seed=42)
    assert engine1._compute_fingerprint() == engine2._compute_fingerprint()


def test_encrypt_for_environment():
    engine = PolyEngine(seed=999)
    plaintext = b"hello world this is a secret message"
    result = engine.encrypt_for_environment(plaintext)
    assert "ciphertext" in result
    assert "iv" in result
    assert "fingerprint" in result
    assert "decrypt_code" in result
    assert len(result["decrypt_code"]) > 0


def test_generate_decrypt_code_has_guards():
    engine = PolyEngine(seed=123)
    code = engine.generate_decrypt_code(b"testdata", b"keymaterial")
    assert "platform.system()" in code
    assert "platform.machine()" in code
    assert "sys.version_info" in code
    assert "poly-engine" in code


def test_verify_environment():
    engine = PolyEngine(seed=777)
    assert engine.verify_environment() is True
