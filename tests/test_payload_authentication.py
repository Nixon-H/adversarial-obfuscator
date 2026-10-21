"""The payload must be authenticated, not just encrypted.

The outer loader XOR-encrypts the payload zip and had **no MAC over
it**.  A byte flipped in the payload region therefore corrupted the
payload *silently*: the loader ran, the payload was garbage, and the
artifact exited 0.  The build now computes an HMAC over the payload
( keyed with the inner key, which the loader already has) and the
loader verifies it before it extracts anything.

This test flips bytes at several points in the artifact and requires
that EVERY one of them fails: a tamper must never look like a clean
run.
"""
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BUILD_TIMEOUT = 600
_MARKER = "PAYLOAD-RAN"


def _build(tmp_path):
    source = os.path.join(str(tmp_path), "hello.py")
    with open(source, "w", encoding="utf-8") as fh:
        fh.write('print("%s")\n' % _MARKER)
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build", source,
         "--net-url", "https://127.0.0.1:9443/"],
        cwd=str(tmp_path), env=env, capture_output=True, text=True,
        timeout=_BUILD_TIMEOUT)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    artifact = os.path.join(str(tmp_path), "dist", "hello_protected.py")
    assert os.path.exists(artifact), (
        "no artifact produced; stdout tail: %s" % proc.stdout[-2000:])
    return artifact


def _run(path):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, path], capture_output=True,
                          text=True, timeout=300, env=env)


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    work = tmp_path_factory.mktemp("payload_mac")
    return _build(str(work))


def test_the_untampered_artifact_runs(artifact):
    run = _run(artifact)
    assert run.returncode == 0, run.stderr[-2000:]
    assert _MARKER in run.stdout


def test_every_tampered_artifact_fails(artifact, tmp_path):
    """A flipped byte anywhere must not look like a clean run."""
    with open(artifact, "rb") as fh:
        data = fh.read()
    failures = []
    for frac in (0.35, 0.5, 0.6, 0.7, 0.85):
        off = int(len(data) * frac)
        tampered = bytearray(data)
        tampered[off] = (tampered[off] + 1) % 256
        path = os.path.join(str(tmp_path), "tampered_%s.py" % frac)
        with open(path, "wb") as fh:
            fh.write(bytes(tampered))
        run = _run(path)
        if run.returncode == 0 or _MARKER in run.stdout:
            failures.append("offset %d (%.0f%%): exit %d, payload ran: %s"
                            % (off, frac * 100, run.returncode,
                               _MARKER in run.stdout))
    assert not failures, (
        "a tampered artifact looked like a clean run: %r" % (failures,))


def test_tampering_with_the_self_check_is_detected(artifact, tmp_path):
    """Editing the self-check's own code must not disable it.

    Two holes are closed here.  The check used to exclude the hashed
    lines by a MARKER string -- and the marker's own line was excluded
    from the hash too, so editing the marker was invisible to the
    check.  And an exception inside the check was logged and ignored,
    so breaking the check's code (a NameError, a bad Merkle helper)
    disabled it: the artifact carried on and exited 0.
    """
    with open(artifact, "rb") as fh:
        data = fh.read()
    failures = []
    for needle in (b"filtered_lines", b"constant_time_compare",
                   b"Self-check error"):
        base = data.find(needle)
        assert base > 0, "the self-check is not in the artifact: %r" % needle
        for delta in (0, 4, len(needle) // 2):
            off = base + delta
            tampered = bytearray(data)
            tampered[off] = (tampered[off] + 1) % 256
            path = os.path.join(str(tmp_path),
                                "selfcheck_%s_%d.py" % (needle.decode(), off))
            with open(path, "wb") as fh:
                fh.write(bytes(tampered))
            run = _run(path)
            if run.returncode == 0 or _MARKER in run.stdout:
                failures.append("%r at %d: exit %d, payload ran: %s"
                                % (needle, off, run.returncode,
                                   _MARKER in run.stdout))
    assert not failures, (
        "editing the self-check disabled it: %r" % (failures,))
