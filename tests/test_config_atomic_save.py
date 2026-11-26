"""Secret-bearing config writes must be atomic, mode-0600, and symlink-safe."""
import json
import os
import stat

import pytest

from obfuscator.core.utils import ConfigManager


def _manager(path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "CONFIG_FILE", str(path))
    manager = object.__new__(ConfigManager)
    manager.config = {}
    return manager


def test_save_replaces_existing_file_atomically_with_0600(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("old")
    path.chmod(0o644)
    manager = _manager(path, monkeypatch)
    manager.set("token", "secret")
    manager.save()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {"token": "secret"}


def test_save_replaces_symlink_without_touching_target(tmp_path, monkeypatch):
    target = tmp_path / "target.json"
    target.write_text("sentinel")
    link = tmp_path / "config.json"
    link.symlink_to(target)
    manager = _manager(link, monkeypatch)
    manager.set("token", "secret")
    manager.save()
    assert target.read_text() == "sentinel"
    assert not link.is_symlink()
    assert json.loads(link.read_text()) == {"token": "secret"}


def test_fchmod_failure_preserves_original(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("original")
    manager = _manager(path, monkeypatch)

    def fail(*args, **kwargs):
        raise OSError("chmod failed")

    monkeypatch.setattr(os, "fchmod", fail)
    with pytest.raises(OSError, match="chmod failed"):
        manager.save()
    assert path.read_text() == "original"
