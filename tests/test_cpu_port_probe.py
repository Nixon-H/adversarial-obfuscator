"""The --cpu-port probe must never fail the build.

It runs `cargo test`, which compiles the runtime crate first. On a cold CI runner
that is minutes, and a 60-second timeout raised TimeoutExpired straight out of the
builder -- `--cpu-port` failed on Windows in two separate flag tiers with "builder
exited 1" while the same flag built in 3.4 seconds locally, where the crate was
already compiled.

The probe's verdict is only ever "passed" or "SKIP", so nothing it hits may become
an exception.
"""

import subprocess

from scripts.phases.phase27_cpu_port import phase_cpu_port


def test_a_cargo_timeout_becomes_a_skip_not_a_failure(monkeypatch):
    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="cargo", timeout=900)

    monkeypatch.setattr("scripts.phases.phase27_cpu_port.subprocess.run", boom)
    result = phase_cpu_port()
    assert result == {"status": "skip", "reason": "TimeoutExpired"}


def test_a_missing_cargo_becomes_a_skip_not_a_failure(monkeypatch):
    def missing(*_a, **_k):
        raise FileNotFoundError("cargo")

    monkeypatch.setattr("scripts.phases.phase27_cpu_port.subprocess.run", missing)
    result = phase_cpu_port()
    assert result["status"] == "skip"


def test_a_normal_result_is_still_recorded(monkeypatch):
    class Done:
        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr("scripts.phases.phase27_cpu_port.subprocess.run",
                        lambda *a, **k: Done())
    assert phase_cpu_port() is None
