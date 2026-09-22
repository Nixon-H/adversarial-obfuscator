"""Batch C GAP 2 (#28): randomized fixed-literal residue (8 token families).

Two builds with different seeds must differ in residue tokens; each
artifact must still execute; the build-side map must resolve randomized
tokens back to (family, original).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.residue_random import (
    RESIDUE_FAMILIES,
    apply_residue,
    build_residue_map,
    resolve_token,
    residue_literals_in,
)
from obfuscator.core.pipeline import build_pipeline

_SRC = "print(6 * 7)\n"


def test_eight_families_defined():
    assert len(RESIDUE_FAMILIES) == 8
    for fam in ("markers", "versions", "separators", "padding",
                "magic", "sections", "errors", "nonces"):
        assert fam in RESIDUE_FAMILIES
        assert len(RESIDUE_FAMILIES[fam]) >= 1


def test_map_deterministic_under_seed():
    assert build_residue_map(11) == build_residue_map(11)
    assert build_residue_map(11) != build_residue_map(22)


def test_two_builds_differ_in_residue_tokens():
    ma, mb = build_residue_map(11), build_residue_map(22)
    flat_a = set(v for f in ma.values() for v in f.values())
    flat_b = set(v for f in mb.values() for v in f.values())
    assert flat_a and flat_b
    assert not (flat_a & flat_b)


def test_apply_residue_rewrites_and_resolves():
    src = "_NX_BUILD_ID = 'NXH1::NX::tail'\nprint(_NX_BUILD_ID)\n"
    out, mapping = apply_residue(src, 11)
    assert out != src
    compile(out, "<residue>", "exec")
    tok = mapping["markers"]["_NX_BUILD_ID"]
    assert tok in out
    assert resolve_token(tok, mapping) == ("markers", "_NX_BUILD_ID")
    # Whole-token only: 'NXH1X' must not be touched by the 'NXH1' literal.
    out2, _ = apply_residue("x = 'NXH1X'\n", 11)
    assert "NXH1X" in out2


def test_apply_residue_noop_when_disabled():
    src = "_NX_BUILD_ID = 1\n"
    out, mapping = apply_residue(src, 11, enabled=False)
    assert out == src
    assert mapping == {}


def test_pipeline_builds_execute_and_carry_map():
    for seed in (11, 22):
        opts = {}
        out = build_pipeline(_SRC, seed=seed, extra_options=opts)
        compile(out, "<residue_pipe>", "exec")
        assert opts.get("residue_map"), "pipeline must stash residue_map"
        # Every randomized token in the map resolves back.
        for family, fam_map in opts["residue_map"].items():
            for orig, tok in fam_map.items():
                assert resolve_token(tok, opts["residue_map"]) == (family, orig)


def test_pipeline_artifacts_execute(tmp_path):
    outs = []
    for seed in (11, 22):
        out = build_pipeline(_SRC, seed=seed)
        outs.append(out)
        p = tmp_path / ("residue_%d.py" % seed)
        p.write_text(out, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(p)], capture_output=True, text=True,
            timeout=60,
        )
        assert r.returncode == 0, r.stderr[-2000:]
        assert "42" in r.stdout
    assert outs[0] != outs[1]


def test_pipeline_opt_out_preserves_literals():
    src = "_NX_BUILD_ID = 1\nprint(6 * 7)\n"
    out = build_pipeline(src, seed=11,
                         extra_options={"residue_random": False})
    assert "_NX_BUILD_ID" in out
