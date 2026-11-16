"""Bench-driven layer selection: the ranking must be honest.

The value of this module is that it refuses to guess.  Each test pins one of
those refusals, because a selector that silently ranks unmeasured layers (or
crowns a layer on a single cell) is worse than no selector at all.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.bench_layers import (  # noqa: E402
    KNOWN_LAYERS, LayerScore, campaign_files, recommend, score_layers,
)


def _cell(arm, recall, cracked, surface, model="m1"):
    return {"arm": arm, "recall": recall, "cracked": cracked,
            "surface_chars": surface, "model": model}


def test_resistance_is_one_minus_recall():
    s = LayerScore(layer="x", cells=1, mean_recall=0.25, mean_surface_chars=1024)
    assert abs(s.resistance - 0.75) < 1e-9


def test_value_penalises_size():
    """Same resistance, ten times the size -> ten times less value."""
    small = LayerScore(layer="a", cells=1, mean_recall=0.5,
                       mean_surface_chars=1024)
    big = LayerScore(layer="b", cells=1, mean_recall=0.5,
                     mean_surface_chars=10240)
    assert small.value > big.value * 9


def test_unmeasured_layer_is_not_ranked():
    rec = recommend([])
    assert rec.scores == []
    assert set(rec.unmeasured) >= {"mba", "opaque", "strings"}
    assert rec.keep == [] and rec.drop == []


def test_a_layer_that_stops_nothing_is_dropped():
    """Only layers the build can toggle are ranked -- use real names."""
    cells = [
        _cell("mba", recall=0.0, cracked=False, surface=4096),
        _cell("decoy", recall=1.0, cracked=True, surface=200000),
    ]
    rec = recommend_from_cells(cells)
    assert "mba" in rec.keep
    assert "decoy" in rec.drop


def recommend_from_cells(cells):
    """recommend() reads files; this exercises the same logic on cells."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"cells": cells}, fh)
        path = fh.name
    try:
        return recommend([path])
    finally:
        os.unlink(path)


def test_cracked_and_recall_are_both_used():
    scores = score_layers([
        _cell("a", 0.0, False, 1000),
        _cell("a", 0.5, False, 1000),
    ])
    s = next(x for x in scores if x.layer == "a")
    assert s.cells == 2
    assert s.cracked_rate == 0.0
    assert abs(s.mean_recall - 0.25) < 1e-9


def test_string_booleans_are_parsed():
    """Campaign JSON stores cracked as the string 'True' in places."""
    scores = score_layers([_cell("a", 0.0, "True", 1000),
                           _cell("a", 0.0, "False", 1000)])
    s = next(x for x in scores if x.layer == "a")
    assert s.cracked_rate == 0.5


def test_models_are_reported():
    scores = score_layers([_cell("a", 0.0, False, 1000, model="m1"),
                           _cell("a", 0.0, False, 1000, model="m2")])
    s = next(x for x in scores if x.layer == "a")
    assert set(s.models) == {"m1", "m2"}


def test_real_campaign_data_is_discovered():
    files = campaign_files(os.path.join(ROOT, "docs", "research"))
    assert files, "no campaign JSONs found under docs/research"
    rec = recommend(files)
    assert rec.cells_used > 0
    # Every kept/dropped layer must be one the build can actually toggle.
    assert all(name in KNOWN_LAYERS for name in rec.keep + rec.drop)


def test_summary_mentions_unmeasured_layers():
    rec = recommend([])
    text = rec.summary()
    assert "UNMEASURED" in text
