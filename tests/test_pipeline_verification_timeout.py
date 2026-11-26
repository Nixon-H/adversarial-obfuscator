"""Artifact verification must fail closed when either execution times out."""
import subprocess

from obfuscator.core import pipeline


def test_original_timeout_is_not_a_pass(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 120)

    monkeypatch.setattr(pipeline.subprocess, "run", timeout)
    results = pipeline.test_protected_file("artifact.py", "source.py")
    original = results["original"]
    assert original["status"] in {"FAIL", "ERROR"}
    assert original.get("returncode", 0) != 0
    assert "comparison" not in results


def test_obfuscated_timeout_is_not_a_pass(monkeypatch):
    monkeypatch.setattr(
        pipeline.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ok\n", ""),
    )

    class HungProcess:
        returncode = -6

        def __init__(self):
            self.calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("artifact.py", timeout, stderr=b"stack")
            return "", "stack"

        def send_signal(self, signum):
            pass

    monkeypatch.setattr(pipeline.subprocess, "Popen", lambda *a, **k: HungProcess())
    results = pipeline.test_protected_file("artifact.py", "source.py")
    obfuscated = results["obfuscated"]
    assert obfuscated["status"] in {"FAIL", "ERROR"}
    assert obfuscated.get("returncode", 0) != 0
    assert "comparison" not in results
