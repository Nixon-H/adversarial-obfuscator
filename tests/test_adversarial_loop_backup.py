"""Regression tests for adversarial-loop rollback and change accounting."""
import json
import os
import stat

import pytest

import adversarial_loop as loop


def test_noop_replacement_does_not_count_or_write(tmp_path, monkeypatch):
    path = tmp_path / "source.py"
    path.write_text("value = 1\n")
    before = path.stat().st_mtime_ns
    assert loop._replace_in_file(path, "value = 1", "value = 1") == 0
    assert path.stat().st_mtime_ns == before


def test_reset_fails_closed_when_backup_missing(tmp_path, monkeypatch):
    source = tmp_path / "source.py"
    source.write_text("modified\n")
    monkeypatch.setattr(loop, "SOURCE_FILES", [source])
    monkeypatch.setattr(loop, "BACKUP_DIR", tmp_path / "missing")
    with pytest.raises(RuntimeError, match="missing source backups"):
        loop._reset_source_files()
    assert source.read_text() == "modified\n"


def test_backup_is_immutable_and_restores_source(tmp_path, monkeypatch):
    source = tmp_path / "source.py"
    source.write_text("original\n")
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(loop, "SOURCE_FILES", [source])
    monkeypatch.setattr(loop, "BACKUP_DIR", backup_dir)

    loop._ensure_source_backups()
    backup = backup_dir / source.name
    assert backup.read_text() == "original\n"
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        assert not (stat.S_IMODE(backup.stat().st_mode) & stat.S_IWUSR)

    source.write_text("modified\n")
    loop._reset_source_files()
    assert source.read_text() == "original\n"
    assert stat.S_IMODE(source.stat().st_mode) & stat.S_IWUSR


def test_loop_config_overrides_are_loaded_and_validated(tmp_path, monkeypatch):
    config = tmp_path / "default.json"
    config.write_text(json.dumps({"adversarial_loop": {
        "proof_threshold": 91,
        "consecutive_target": 2,
        "max_rounds": 7,
        "max_bench_failures": 3,
    }}))
    monkeypatch.setattr(loop, "CONFIG_PATH", config)
    assert loop._load_loop_config() == {
        "proof_threshold": 91,
        "consecutive_target": 2,
        "max_rounds": 7,
        "max_bench_failures": 3,
    }
    config.write_text(json.dumps({"adversarial_loop": {"max_rounds": 0}}))
    with pytest.raises(RuntimeError, match="positive integer"):
        loop._load_loop_config()
