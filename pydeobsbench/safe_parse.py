"""String extraction from adversarial artefacts, with no deserialiser.

PyDeObsBench exists to analyse artefacts it did NOT build, so every parser it
uses is an attack surface. The deep scan (2026-11-18) flagged the two
`marshal.loads` calls in `static_probes.py` as unsafe deserialisation
(CWE-502) -- correctly: CPython's unmarshaller can allocate attacker-chosen
sizes and is not a hostile-input parser.

The probes never needed a code object. They needed the STRINGS, because the
question they answer is "does the decoded payload still carry identifiers and
secrets as readable text". Those strings sit in the marshal stream as
length-prefixed byte runs, so a byte-level scan finds them without invoking
any deserialiser at all.

This module therefore contains no marshal, no pickle, no eval, no exec, no
subprocess and no importlib. Everything here is `bytes.find` over a buffer.
An attacker-supplied artefact can only influence the OUTPUT (which strings are
reported), never control flow in the probe process.

Encodings handled: UTF-8 (Python str constants are stored as UTF-8 bytes in
marshal) and latin-1 fallback for non-UTF-8 runs. Both are decoded with
errors="replace" so a deliberately malformed stream cannot raise.
"""
from __future__ import annotations

import re

# A run of printable characters. Python's marshal stores str constants as
# their UTF-8 bytes, so readable identifiers appear as contiguous runs.
_RUN = re.compile(rb"[\x20-\x7e\xc2-\xf4][\x20-\x7e\x80-\xbf\xc2-\xf4]{7,}")

# Bound the work: artefacts are attacker-sized, so cap both the buffer we walk
# and the number of strings we collect.
_MAX_SCAN_BYTES = 64 << 20
_MAX_STRINGS = 4000


def extract_strings(blob, min_len=8, limit=_MAX_STRINGS, max_bytes=_MAX_SCAN_BYTES):
    """Return printable string runs found in ``blob`` (no parsing, no imports).

    Deliberately over-inclusive: this is a leakage probe, so a false positive
    costs a manual look while a false negative would understate the leak.
    Callers filter against known ground truth, so extra strings are harmless.
    """
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        return []
    data = bytes(blob[:max_bytes])
    out = []
    for m in _RUN.finditer(data):
        if len(out) >= limit:
            break
        run = m.group(0)
        if len(run) < min_len:
            continue
        try:
            s = run.decode("utf-8")
        except UnicodeDecodeError:
            s = run.decode("latin-1")
        out.append(s)
    return out


def find_needles(blob, needles):
    """Which of ``needles`` (str or bytes) appear literally in ``blob``?

    The fast path for the benchmark: no string extraction, just containment,
    so the answer is exactly "is this ground-truth identifier in these bytes".
    """
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        return set()
    data = bytes(blob[: _MAX_SCAN_BYTES])
    hits = set()
    for n in needles:
        if not n:
            continue
        nb = n.encode() if isinstance(n, str) else bytes(n)
        if nb and nb in data:
            hits.add(n)
    return hits
