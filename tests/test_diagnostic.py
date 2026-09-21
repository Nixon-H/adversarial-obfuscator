"""Tests for scripts/diagnostic.py — diagnostic build mode helpers."""
import time

from scripts.diagnostic import (
    DIAG_MARKER,
    STAGES,
    DiagClock,
    banner,
    key_freshness,
    mark_diagnostic,
    summarize_transforms,
)


def test_clock_reports_expected_keys():
    clock = DiagClock()
    time.sleep(0.001)
    clock.mark("obfuscate")
    clock.mark("done")
    report = clock.report()
    assert set(report) == {"obfuscate", "done"}
    assert all(v >= 0.0 for v in report.values())


def test_summarize_counts_flags():
    summary = summarize_transforms(4)
    assert summary["opt_level"] == 4
    assert summary["enabled_count"] == len(summary["enabled_flags"])
    assert summary["enabled_count"] > 0
    l0 = summarize_transforms(0)
    assert l0["enabled_count"] == 0
    l5 = summarize_transforms(5)
    assert l5["enabled_count"] >= summary["enabled_count"]


def test_key_freshness():
    assert key_freshness("00" * 32)["fresh"] is False  # all-zero
    assert key_freshness("abcd")["fresh"] is False  # too short
    assert key_freshness("zz")["fresh"] is False  # not hex
    import os
    good = key_freshness(os.urandom(32).hex())
    assert good["fresh"] is True and good["bytes"] == 32


def test_mark_diagnostic(tmp_path):
    target = tmp_path / "out.py"
    target.write_text("x = 1\n")
    mark_diagnostic(str(target))
    assert DIAG_MARKER in target.read_text()


def test_banner_text():
    text = banner()
    assert "DIAGNOSTIC" in text and "NOT FOR RELEASE" in text


def test_flag_exists():
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, "scripts/build.py", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert "--diagnostic" in proc.stdout
    assert "--name-gate" in proc.stdout
    assert "--lowering" in proc.stdout
