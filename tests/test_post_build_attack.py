"""Post-build mini-attack: the artefact scores itself.

The loop is only useful if the probe actually detects a leak and actually
clears a protected artefact.  Both directions are pinned here -- a probe that
always says "safe" would be worse than no probe.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.post_build_attack import (  # noqa: E402
    AttackCell, DEFAULT_NAMES, score_artifact, static_probe,
)
from obfuscator.bench_layers import recommend  # noqa: E402


PLAIN = '''\
def make_counter():
    count = 0
    return count


def main():
    print("hello")
'''

PROTECTED = '''\
_nixon_ǹড়ɗاयїŭňץ = 1
def _nx_9f2a1b(_nx_arg):
    return _nx_arg
'''


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_probe_detects_names_in_a_plain_payload(tmp_path):
    cell = static_probe(_write(tmp_path, "plain.py", PLAIN), DEFAULT_NAMES)
    assert cell.cracked is True
    assert "main" in cell.names_recovered
    assert "make_counter" in cell.names_recovered
    assert cell.recall > 0


def test_probe_clears_a_protected_artifact(tmp_path):
    cell = static_probe(_write(tmp_path, "prot.py", PROTECTED), DEFAULT_NAMES)
    assert cell.cracked is False
    assert cell.names_recovered == []
    assert cell.recall == 0.0


def test_probe_detects_plaintext_markers(tmp_path):
    text = PROTECTED + '\nMARKER = "ORBITAL-NATIVE-7f3a91d2"\n'
    cell = static_probe(_write(tmp_path, "m.py", text), DEFAULT_NAMES,
                        markers=["ORBITAL-NATIVE-7f3a91d2"])
    assert cell.cracked is True
    assert "ORBITAL-NATIVE-7f3a91d2" in cell.secrets_reported


def test_missing_artifact_is_an_error_not_a_crash(tmp_path):
    cell = static_probe(str(tmp_path / "nope.py"), DEFAULT_NAMES)
    assert cell.surface_chars == 0
    assert cell.cracked is False


def test_score_artifact_appends_to_the_campaign(tmp_path):
    art = _write(tmp_path, "a.py", PLAIN)
    out = str(tmp_path / "campaign.json")
    report = score_artifact(art, out=out)
    assert report["sha256"]
    assert report["cells"][0]["cracked"] is True
    doc = json.loads(open(out).read())
    assert len(doc["cells"]) == 1
    # A second run appends rather than replacing.
    score_artifact(art, out=out)
    doc2 = json.loads(open(out).read())
    assert len(doc2["cells"]) == 2


def test_campaign_cells_feed_the_layer_selector(tmp_path):
    """The loop closes: a scored build changes the recommendation input."""
    art = _write(tmp_path, "a.py", PLAIN)
    out = str(tmp_path / "campaign.json")
    score_artifact(art, out=out)
    rec = recommend([out])
    assert rec.cells_used >= 1
    # The static probe arm is not a build-toggleable layer, so it is reported
    # but not recommended for keep/drop.
    assert rec.keep == [] and rec.drop == []


def test_cell_shape_matches_the_campaign_schema():
    cell = AttackCell(arm="a", model="m", recall=0.5, cracked=True)
    doc = cell.as_dict()
    for key in ("arm", "model", "recall", "cracked", "names_recovered",
                "surface_chars", "secrets_reported", "status"):
        assert key in doc
