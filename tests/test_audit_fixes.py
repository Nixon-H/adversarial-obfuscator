"""Regression tests for the 2026-11-13 audit fixes (docs/AUDIT-2026-11-13.md).

M1: requested/default-on integrity gates fail the build on emission errors
    instead of silently shipping "DISABLED".
M2: a requested AES seal fails closed when no backend exists; the XOR
    stream is only available as a deliberate choice.
Lows: licence payload typing, credential file mode, stealth-level poison,
    token save mode.
"""
import argparse
import os
import stat
import sys

import pytest

from obfuscator import licensing
from obfuscator.core.pipeline import encrypt_payload, generate_hybrid_loader_script

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

_BLANKS = {"windows": "", "linux": "", "darwin": ""}


def _gate_ns(**kw):
    base = dict(anti_rea_level="maximum", anti_rea_off=False,
                audit=None, research=None, skip=None, exclude=None,
                package=None, transforms=None, validate=None, access=None)
    base.update(kw)
    n = argparse.Namespace(**base)
    from scripts.build import _apply_rea_shields
    _apply_rea_shields(n)
    return n


# ── M1: gate emission failures fail closed ──────────────────────────────

def test_requested_watermark_gate_fails_closed(tmp_path, monkeypatch):
    """A requested --watermark must not silently ship DISABLED."""
    import obfuscator.watermark_gate as wg

    def boom(*a, **k):
        raise RuntimeError("emitter broken")

    monkeypatch.setattr(wg, "build_watermark_context", boom)
    with pytest.raises(SystemExit, match="watermark gate emission failed"):
        generate_hybrid_loader_script(
            _BLANKS, b"", "ab" * 32, build_id="bid-audit",
            watermark="MAX-001")


def test_default_on_snapshot_gate_fails_closed(monkeypatch):
    """The default-on snapshot gate must not silently ship DISABLED."""
    import obfuscator.frozen_snapshot as fs

    def boom(*a, **k):
        raise RuntimeError("emitter broken")

    monkeypatch.setattr(fs, "build_snapshot_context", boom)
    with pytest.raises(SystemExit, match="snapshot gate emission failed"):
        generate_hybrid_loader_script(
            _BLANKS, b"", "ab" * 32, build_id="bid-audit")


def test_kill_ladder_failure_fails_closed(monkeypatch):
    """Gates call _nx_kill; a missing ladder would be a runtime NameError."""
    import obfuscator.kill_ladder as kl

    def boom():
        raise RuntimeError("ladder broken")

    monkeypatch.setattr(kl, "emit_kill_snippet", boom)
    with pytest.raises(SystemExit, match="kill-ladder emission failed"):
        generate_hybrid_loader_script(
            _BLANKS, b"", "ab" * 32, build_id="bid-audit")


def test_requested_trial_gate_fails_closed(monkeypatch):
    import obfuscator.trial_bind as tb

    def boom(*a, **k):
        raise RuntimeError("emitter broken")

    monkeypatch.setattr(tb, "build_trial_context", boom)
    with pytest.raises(SystemExit, match="trial gate emission failed"):
        generate_hybrid_loader_script(
            _BLANKS, b"", "ab" * 32, build_id="bid-audit", trial_seconds=3600)


def test_no_trial_still_emits_disabled(tmp_path):
    """No trial configured: DISABLED remains the correct output."""
    src, _, _ = generate_hybrid_loader_script(
        _BLANKS, b"", "ab" * 32, build_id="bid-audit")
    assert '_NX_TRIAL_GATE = "DISABLED"' in src


# ── M2: requested AES fails closed ──────────────────────────────────────

def test_requested_aes_without_backend_fails_closed(monkeypatch):
    import obfuscator.core.pipeline as pl
    monkeypatch.setattr(pl, "_AES_CTR_AVAILABLE", False)
    with pytest.raises(SystemExit, match="no AES backend"):
        encrypt_payload(b"hello", b"k" * 32, b"n" * 16, use_aes_ctr=True)


def test_deliberate_xor_stream_still_works():
    out = encrypt_payload(b"hello", b"k" * 32, b"n" * 16, use_aes_ctr=False)
    assert len(out) == 5


# ── lows ────────────────────────────────────────────────────────────────

def test_non_dict_licence_payload_is_licence_error():
    seed = "22" * 32
    pub = licensing.public_key_from_hex(licensing.public_key_hex(
        licensing.private_key_from_hex(seed)))
    with pytest.raises(licensing.LicenceError, match="expected an object"):
        licensing.verify('{"payload": [1, 2, 3], "sig": "00"}', pub)


def test_save_token_writes_0600(tmp_path):
    path = tmp_path / "t.licence"
    # A pre-created predictable sibling must not control the final mode.
    (tmp_path / "t.licence.tmp").write_text("old")
    os.chmod(str(tmp_path / "t.licence.tmp"), 0o644)
    licensing.save_token("SECRET-TOKEN", str(path))
    mode = stat.S_IMODE(os.stat(str(path)).st_mode)
    assert mode == 0o600, oct(mode)
    assert path.read_text(encoding="utf-8").strip() == "SECRET-TOKEN"


def test_stealth_level_disables_the_whole_poison_family():
    n = _gate_ns(anti_rea_level="stealth")
    assert n.poison_level == 0
    assert n.provenance_poison is False
    assert n.poison_apis is False and n.poison_call_graph is False
    assert n.poison_paths is False and n.poison_protocols is False
    assert n.poison_imports is False and n.provenance_replace is False
