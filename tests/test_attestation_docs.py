"""Batch-3 attestation dedupe: lock the ownership decision in text.

No behavior change: asserts the canonical/deprecated/launcher-scope
labels exist where future contributors will look.
"""
import os

REPO = os.path.join(os.path.dirname(__file__), "..")


def _read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as f:
        return f.read()


def test_attestation_doc_exists_with_three_components():
    doc = _read("docs/ATTESTATION.md")
    lines = [l for l in doc.splitlines() if l.strip()]
    assert 15 <= len(lines) <= 60, f"doc should be 15-25 lines, got {len(lines)}"
    assert "runtime/src/sw_attestation.rs" in doc
    assert "native/attestation.c" in doc
    assert "relay/src/attestation.rs" in doc
    assert "runtime/src/sw_attestation.rs" in doc.split(
        "new attestation logic goes in")[1]


def test_c_sim_marked_deprecated():
    # C sim deleted 2026-09-20: assert absence (not deprecation text).
    # Canonical attestation is runtime/src/sw_attestation.rs.
    assert not os.path.exists(os.path.join(REPO, "native", "attestation.c")), (
        "native/attestation.c must stay deleted")
    assert not os.path.exists(os.path.join(REPO, "native", "attestation.h")), (
        "native/attestation.h must stay deleted")


def test_relay_marked_launcher_scope():
    src = _read("relay/src/attestation.rs")
    assert "launcher" in src.lower()
    assert "runtime/src/sw_attestation.rs" in src
