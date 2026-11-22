"""Reproducible-transform experiment (register P2 row, seventh pass).

MEASURED 2026-11-22 on this host, same tree:

    obfuscator.core.pipeline.build_pipeline(SRC, seed=424242)  twice
        run 1  sha256 <a>   <n1> B
        run 2  sha256 <b>   <n2> B
        identical: <see the print below>

The distinction this module exists to hold is the one the sixth-round
review asked for explicitly: **source identity** (the same tree produces a
build) is not the same claim as **reproducible builds** (the same tree and
the same seed produce identical bytes). Only the first is a property of the
pipeline's correctness; the second is what the P2 row asks about, and it is
measured here rather than asserted.

Two separate layers, and they behave differently:

  * the AST transform layer IS seeded: `build_pipeline(seed=...)` seeds
    `random` and patches `secrets` for the duration of the transform, and
    restores both in a `finally` (so a failed transform cannot leave the
    process drawing predictable nonces). Two transforms with the same seed
    produce the same source text.
  * the emitted LOADER is not: it mints its helper name with
    `secrets.token_hex(8)` and reads the clock for the trial gate at RUNTIME,
    which is deliberate -- a loader whose identifiers are predictable from a
    build seed would defeat the point. `NX_BUILD_SEED` seeds the transform,
    not the loader's runtime draws.

So the honest status is: the transform layer is reproducible under a pinned
seed, and the shipped artefact is not byte-identical across builds by
design. Both facts are pinned below so a future change to either is a
deliberate edit rather than a silent drift.
"""
import hashlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

SRC = '''\
def main():
    print("REPRO")
    total = 0
    for i in range(3):
        total += i * 2
    return total


if __name__ == "__main__":
    main()
'''


def _transform_once(seed):
    """One in-process transform at a pinned seed; returns (digest, size)."""
    from obfuscator.core.pipeline import build_pipeline
    out = build_pipeline(SRC, seed=seed, extra_options={})
    return hashlib.sha256(out.encode("utf-8")).hexdigest(), len(out)


def test_the_transform_layer_is_reproducible_at_a_pinned_seed():
    """Same source + same seed => same transformed text, twice in a row."""
    sha_a, len_a = _transform_once(424242)
    sha_b, len_b = _transform_once(424242)
    print("\ntransform reproducibility: a=%s (%d B) b=%s (%d B)"
          % (sha_a[:16], len_a, sha_b[:16], len_b))
    assert (sha_a, len_a) == (sha_b, len_b), (
        "the AST transform layer is not reproducible at a pinned seed; the "
        "seed lever (build_pipeline(seed=...)) no longer covers every draw")
    assert len_a > len(SRC), "the transform produced nothing"


def test_the_seed_actually_controls_the_output():
    """A different seed must produce a DIFFERENT artefact.

    Without this, "reproducible" could be satisfied by a transform that
    ignores its seed and emits a constant -- reproducible and useless.
    """
    sha_a, _ = _transform_once(424242)
    sha_c, _ = _transform_once(999999)
    assert sha_a != sha_c, (
        "two different seeds produced identical output; the seed is not "
        "reaching the transforms that vary")


def test_the_seeded_transform_restores_process_globals():
    """A seeded transform must not leave `secrets` patched behind it.

    `_patch_secrets` is a process-global monkeypatch. If it leaked, every
    later key/nonce/challenge drawn anywhere in the process would come from
    a Mersenne Twister -- a real defect, not a style point.
    """
    import secrets
    before = secrets.token_bytes
    _transform_once(424242)
    after = secrets.token_bytes
    assert before is after, (
        "the seeded transform left `secrets.token_bytes` patched; a later "
        "draw in this process would be predictable")


def test_the_reproducibility_status_is_documented_honestly():
    """The matrix must state the status the experiment measured."""
    path = os.path.join(REPO, "docs", "security", "COMPATIBILITY_MATRIX.md")
    with open(path, encoding="utf-8") as fh:
        matrix = fh.read()
    assert "Reproducibility" in matrix, (
        "the compatibility matrix must state the reproducibility status")
    assert ("not byte-identical" in matrix
            or "not demonstrated" in matrix), (
        "the matrix must not imply shipped builds are byte-reproducible")
    assert "NX_BUILD_SEED" in matrix, (
        "the matrix must name the seed lever and what it does not cover")
