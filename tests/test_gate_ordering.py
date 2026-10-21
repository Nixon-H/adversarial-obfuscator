"""A gate that fires must kill the artifact BEFORE the payload runs.

The hybrid loader's template ended with

    if __name__ == "__main__":
        _load_native()

and the phase-4 suffix -- which holds every gate -- was appended
AFTER it.  So the payload was decrypted and executed first, and the
gates ran afterwards.  A trial-expired artifact ran its payload and
only then died: the gates were advisory, not gating.

This test is behavioural.  It emits a hybrid loader whose VM score
always trips, runs it, and requires that the payload never executes.
"""
import marshal
import os
import subprocess
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.core.pipeline import generate_hybrid_loader_script  # noqa: E402
from obfuscator.core.utils import fast_xor_bytes  # noqa: E402

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))
_MARKER = "GATE-ORDER-OK"


def _emit(tmp_path, **kwargs):
    """A hybrid loader carrying a payload that prints a marker."""
    payload = "print(%r)\n" % _MARKER
    blob = zlib.compress(marshal.dumps(compile(payload, "<p>", "exec")))
    enc = fast_xor_bytes(blob, _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        _BLANKS, bytes(enc), _RAW_KEY.hex(), **kwargs)
    # The probe call stands in for the payload entry point: it comes
    # AFTER the gates, so a gate that fires stops it.
    src += "\n_ci_probe_out = _exec_fallback()\n"
    path = os.path.join(str(tmp_path), "loader.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    return path


def _run(path):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    return subprocess.run([sys.executable, path], capture_output=True, text=True,
                          timeout=300, env=env)


def test_an_armed_gate_kills_before_the_payload_runs(tmp_path):
    path = _emit(tmp_path, vm_threshold=0.0, kod=True)
    run = _run(path)
    assert _MARKER not in run.stdout + run.stderr, (
        "the payload ran even though the VM gate fired -- the gates are "
        "advisory, not gating:\n%s" % (run.stdout[-2000:],))
    assert run.returncode != 0, (
        "the loader exited 0 even though a gate fired:\n%s"
        % (run.stdout[-2000:],))


def test_a_disarmed_gate_lets_the_payload_run(tmp_path):
    """The control: with the gate disarmed, the loader works.

    Without this, the test above could pass for the wrong reason -- a
    loader that never worked at all.
    """
    path = _emit(tmp_path, vm_threshold=0.0, kod=False)
    run = _run(path)
    assert _MARKER in run.stdout + run.stderr, (
        "the payload did not run with the gate disarmed:\n%s"
        % (run.stdout[-2000:] + run.stderr[-2000:]))
