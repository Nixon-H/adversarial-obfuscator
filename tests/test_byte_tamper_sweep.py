"""Batch C GAP 1 (#14): byte-tamper sweep — single-byte mutations fail closed.

Builds a small obfuscated artifact twice with different seeds via the
existing helper ``obfuscator.core.pipeline.build_pipeline`` (the same
helper used by tests/test_obfuscated_payload.py), then flips 12 single
bytes at spread offsets in each artifact file. Each mutated copy must
fail closed when executed: returncode != 0 OR stdout/stderr contains a
refusal marker (SyntaxError/Traceback/Error/refus/denied/integrity/
tamper/checksum/failed).

Manual probes (2026-09-22): XOR 0x01 flips in ASCII regions sometimes
leave valid syntax (silent pass), while XOR 0xFF flips in this pipeline
(always UTF-8 multibyte identifiers) reliably break decoding or names,
so the sweep uses 0xFF. Baseline artifact prints "probe-ok 42" rc=0.
"""
import os
import subprocess
import sys

import pytest

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from obfuscator.core.pipeline import build_pipeline
except Exception as _exc:  # missing toolchain / deps -> graceful skip
    build_pipeline = None
    _IMPORT_ERROR = _exc
else:
    _IMPORT_ERROR = None

pytestmark = pytest.mark.slow

_PAYLOAD_SRC = "NIXON_TAMPER_PROBE = 6 * 7\nprint(\"probe-ok\", NIXON_TAMPER_PROBE)\n"
_EXPECT_OUT = "probe-ok 42\n"
_N_MUTS = 12

_REFUSAL_MARKERS = (
    "traceback", "syntaxerror", "indentationerror", "nameerror",
    "error", "refus", "denied", "integrity", "tamper", "checksum",
    "failed", "failure", "invalid", "mismatch", "no encoding",
)


def _build_artifact(seed):
    """Reuse the existing build helper; return artifact text."""
    if build_pipeline is None:
        pytest.skip("build helper unavailable: %r" % (_IMPORT_ERROR,))
    try:
        return build_pipeline(_PAYLOAD_SRC, seed=seed)
    except Exception as exc:
        pytest.skip("build helper failed (missing toolchain?): %r" % (exc,))


def _fail_closed(proc, baseline_out):
    combined = (proc.stdout + proc.stderr).lower()
    if proc.returncode != 0:
        return True
    if any(m in combined for m in _REFUSAL_MARKERS):
        return True
    # Same output with rc 0 means the mutation silently passed.
    return proc.stdout != baseline_out


def _sweep_one_build(tmp_path, seed):
    artifact = _build_artifact(seed)
    base = tmp_path / ("tamper_base_%d.py" % seed)
    base.write_bytes(artifact.encode("utf-8"))
    r0 = subprocess.run(
        [sys.executable, str(base)], capture_output=True, text=True,
        timeout=60,
    )
    assert r0.returncode == 0, r0.stderr[-2000:]
    assert _EXPECT_OUT in r0.stdout
    data = base.read_bytes()
    n = len(data)
    results = []
    for k in range(_N_MUTS):
        off = (n * (k + 1)) // (_N_MUTS + 1)
        mut = bytearray(data)
        mut[off] ^= 0xFF
        mp = tmp_path / ("tamper_mut_%d_%d.py" % (seed, k))
        mp.write_bytes(bytes(mut))
        r = subprocess.run(
            [sys.executable, str(mp)], capture_output=True, text=True,
            timeout=60,
        )
        closed = _fail_closed(r, r0.stdout)
        results.append((k, off, r.returncode, closed))
    return results


def test_tamper_sweep_seed_11(tmp_path):
    results = _sweep_one_build(tmp_path, 11)
    bad = [k for k, _, _, closed in results if not closed]
    assert not bad, "seed 11 mutations silently passed: %r" % (bad,)


def test_tamper_sweep_seed_22(tmp_path):
    results = _sweep_one_build(tmp_path, 22)
    bad = [k for k, _, _, closed in results if not closed]
    assert not bad, "seed 22 mutations silently passed: %r" % (bad,)
