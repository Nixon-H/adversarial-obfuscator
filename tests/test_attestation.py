"""Attestation ownership (post-C-sim-removal).

The legacy C sim (native/attestation.c) was DELETED: it was an unwired
experimental sim with known defects (always-false compare, srand/rand
self-attesting region). Canonical payload-integrity attestation is
``runtime/src/sw_attestation.rs`` (exercised by ``cargo test`` in runtime/).
The relay launcher keeps its own liveness module (relay/src/attestation.rs).
See docs/ATTESTATION.md.
"""
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_c_sim_removed():
    assert not os.path.exists(os.path.join(ROOT, "native", "attestation.c")), (
        "native/attestation.c must stay deleted; canonical is runtime/src/sw_attestation.rs"
    )


def test_rust_canonical_present():
    path = os.path.join(ROOT, "runtime", "src", "sw_attestation.rs")
    assert os.path.isfile(path)
    src = open(path).read()
    assert "AttestationEngine" in src


def test_relay_liveness_present():
    path = os.path.join(ROOT, "relay", "src", "attestation.rs")
    assert os.path.isfile(path)


@pytest.mark.skip(reason="C-sim suite retired with native/attestation.c; see cargo test for sw_attestation")
def test_c_sim_suite_retired():
    pass
