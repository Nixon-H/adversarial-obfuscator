"""A tampered artifact must not look like a successful run.

The outer loader's state machine broke out of its loop on ANY failure
(``break``), and the function then returned normally.  A tampered
artifact therefore ran nothing at all and **exited 0**: to an operator,
and to any script checking the exit code, the tampered artifact looked
exactly like a clean success.

The self-hash feeds the key derivation, so tampering corrupts the
payload -- the failure was always there, it was just being reported as
success.  A crashed loader now dies instead, the same shape as the
kill ladder in the inner loader.
"""
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BUILD_TIMEOUT = 600


def _build(tmp_path):
    source = os.path.join(str(tmp_path), "hello.py")
    with open(source, "w", encoding="utf-8") as fh:
        fh.write('print("PAYLOAD-RAN")\n')
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
    # Shared helper: dumps the child's stack if the run hangs instead of
    # just raising TimeoutExpired (3.14 runners do this intermittently).
    from tests._artifact_run import run_artifact
    return run_artifact(path, timeout=300, env=env)


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    work = tmp_path_factory.mktemp("tamper")
    return _build(str(work))


def test_the_untampered_artifact_runs(artifact):
    run = _run(artifact)
    assert run.returncode == 0, run.stderr[-2000:]
    assert "PAYLOAD-RAN" in run.stdout


def test_a_tampered_artifact_does_not_look_successful(tmp_path, artifact):
    """A flipped byte must not look like a clean run.

    The flip position is chosen OUTSIDE the integrity anchors: those
    lines are excluded from the loader's self-hash by design (the build
    fills them in after hashing the rest), so a flip inside them is
    the one place the loader cannot detect a change.
    """
    with open(artifact, "rb") as fh:
        data = fh.read()
    anchor_spans = []
    offset = 0
    for line in data.splitlines(keepends=True):
        if b"__SIG_ANCHOR__" in line or b"__HMAC_ANCHOR__" in line:
            anchor_spans.append((offset, offset + len(line)))
        offset += len(line)

    def _in_anchor(pos):
        return any(a <= pos < b for a, b in anchor_spans)

    mid = len(data) // 2
    off = None
    for delta in range(len(data)):
        for cand in (mid + delta, mid - delta):
            if 0 <= cand < len(data) and not _in_anchor(cand):
                off = cand
                break
        if off is not None:
            break
    assert off is not None, "no flippable byte outside the anchors"

    tampered = bytearray(data)
    tampered[off] = (tampered[off] + 1) % 256
    path = os.path.join(str(tmp_path), "tampered.py")
    with open(path, "wb") as fh:
        fh.write(bytes(tampered))

    run = _run(path)
    assert "PAYLOAD-RAN" not in run.stdout + run.stderr, (
        "the tampered artifact ran its payload")
    assert run.returncode != 0, (
        "the tampered artifact exited 0 -- a tamperer sees a clean success:\n%s"
        % (run.stdout[-2000:]))
