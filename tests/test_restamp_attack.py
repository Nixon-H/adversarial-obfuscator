"""§1 anti-patching: recomputing the Merkle stamp is NOT enough.

`scripts/attack_chain.py` measures this on a real artefact end to end. This file
pins the part that can be checked without building one: the re-stamp helper
must actually reproduce the loader's Merkle construction, or the attack-chain
row that says "tamper + restamp is blocked" would be reporting a failure of the
ATTACK rather than a defence.

That distinction is the whole point. An attack script whose restamp logic is
wrong will report "defended" for a loader that is not defended at all — a
false-negative in the attacker, indistinguishable in the output from a
true-positive in the defender. So the helper is tested against the exact
construction the loader uses, on synthetic input with a known-correct root.

Measured 2026-11-19 on a real artefact: all five tamper routes ended at rc 137,
including tamper+restamp, which the HMAC layer caught.
"""
import hashlib
import os
import sys


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import attack_chain  # noqa: E402


def _artefact(body_extra="", ck="0" * 64, hm="1" * 64, tok=""):
    """A synthetic loader-shaped file with the three anchor lines."""
    return (
        "import os\n"
        "_NX_SELF_CK = \"%s\"\n"
        "_NX_SELF_HM = \"%s\"\n"
        "_NX_SELF_TOK = \"%s\"\n"
        "_NX_CFI_SEQ = \"deadbeef\"\n"
        "def main():\n"
        "%s"
        "    return 0\n" % (ck, hm, tok, body_extra)
    )


def _reference_root(text, ck, hm, tok):
    """The loader's construction, reimplemented independently of the helper."""
    lines = text.encode().splitlines(keepends=True)
    filtered = [ln for ln in lines
                if ck.encode() not in ln
                and hm.encode() not in ln
                and b"_NX_CFI_SEQ = " not in ln
                and (not tok or tok.encode() not in ln)]
    content = b"".join(filtered)
    chunks = [content[i:i + 1024] for i in range(0, len(content), 1024)]
    hashes = [hashlib.sha256(b).hexdigest() for b in chunks]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [hashlib.sha256((hashes[i] + hashes[i + 1]).encode()).hexdigest()
                  for i in range(0, len(hashes), 2)]
    return hashes[0] if hashes else ""


def test_the_anchors_are_found_with_double_quotes():
    """The loader emits double quotes; a single-quote-only regex found nothing.

    That failure was silent: the attack script printed "no _NX_SELF_CK anchor"
    and skipped the most important scenario, so the run looked clean.
    """
    text = _artefact()
    assert attack_chain.CK.search(text), "CK anchor not matched"
    assert attack_chain.HM.search(text), "HM anchor not matched"
    assert attack_chain.TOK.search(text), "TOK anchor not matched"


def test_the_anchors_are_found_with_single_quotes():
    text = ("_NX_SELF_CK = '%s'\n_NX_SELF_HM = '%s'\n"
            % ("0" * 64, "1" * 64))
    assert attack_chain.CK.search(text)
    assert attack_chain.HM.search(text)


def test_the_restamp_reproduces_the_reference_construction():
    """If these disagree, an "attack blocked" row means the ATTACK was broken."""
    text = _artefact(ck="a" * 64)
    restamped, ok = attack_chain.recompute_self_ck(text)
    assert ok is True
    stamped = attack_chain.CK.search(restamped).group("val")
    assert stamped == _reference_root(text, "a" * 64, "1" * 64, "")


def test_the_restamp_changes_when_the_body_changes():
    """The property the attack relies on: a body edit moves the root."""
    first, _ = attack_chain.recompute_self_ck(_artefact(ck="a" * 64))
    second, _ = attack_chain.recompute_self_ck(
        _artefact(body_extra="    x = 1\n", ck="a" * 64))
    root_a = attack_chain.CK.search(first).group("val")
    root_b = attack_chain.CK.search(second).group("val")
    assert root_a != root_b


def test_the_restamp_leaves_the_body_untouched():
    """A restamp must not perturb anything except the CK value."""
    text = _artefact(ck="a" * 64)
    restamped, _ = attack_chain.recompute_self_ck(text)
    assert restamped.count("\n") == text.count("\n")
    assert "    return 0" in restamped
    assert _artefact(ck="a" * 64).split("_NX_SELF_CK")[0] in restamped


def test_a_file_without_an_anchor_is_reported_not_guessed():
    """No anchor means no restamp attempt — never a silent 'defended'."""
    text = "def main():\n    return 0\n"
    restamped, ok = attack_chain.recompute_self_ck(text)
    assert ok is False
    assert restamped == text


def test_an_empty_body_still_produces_a_stable_root():
    """Degenerate input must not crash or return a random value."""
    text = _artefact(ck="a" * 64)
    first, _ = attack_chain.recompute_self_ck(text)
    second, _ = attack_chain.recompute_self_ck(text)
    assert attack_chain.CK.search(first).group("val") == \
        attack_chain.CK.search(second).group("val")


def test_the_merkle_pairing_handles_an_odd_chunk_count():
    """The loader duplicates the last hash on an odd count; so must this."""
    # >1024 bytes forces more than one chunk.
    big = _artefact(body_extra="    pad = %r\n" % ("x" * 2000), ck="a" * 64)
    restamped, ok = attack_chain.recompute_self_ck(big)
    assert ok is True
    stamped = attack_chain.CK.search(restamped).group("val")
    assert stamped == _reference_root(big, "a" * 64, "1" * 64, "")


def test_the_chain_reports_the_restamp_outcome_separately():
    """The script must distinguish "attack failed" from "defence held".

    A single boolean cannot: if the restamp helper is wrong, the tampered
    artefact fails for the wrong reason and the run looks like a pass. The
    helper returning ok=True is what makes the row meaningful, so this asserts
    the two are reported as separate facts in the source.
    """
    source = open(os.path.join(REPO, "scripts", "attack_chain.py"),
                  encoding="utf-8").read()
    assert "restamp (no edit)" in source
    assert "tamper + restamp" in source
    assert "SELF-CHECK IS NOT BINDING" in source


# ── the harness's exclusion set must match the loader's ──────────────────

def test_restamp_excludes_the_provenance_slots():
    """The attacker's hash filter must exclude what the LOADER excludes.

    Measured 2026-11-20: restamp_all hashed the provenance slot lines while
    the loader excludes them, so every later attack row was stopped by
    MERKLE before reaching the layer under test -- a false pass, for the
    wrong reason, in the row that is supposed to prove the signature works.
    """
    source = open(os.path.join(REPO, "scripts", "attack_chain.py"),
                  encoding="utf-8").read()
    restamp_start = source.find("def restamp_all")
    assert restamp_start != -1
    body = source[restamp_start:source.find("\ndef ", restamp_start + 10)]
    for marker in ('b"_NX_PROV_SIG"', 'b"_NX_PROV_PK"',
                   'b"_NX_CFI_SEQ = "', "tok_v"):
        assert marker in body, (
            "restamp_all does not exclude %s from the hashed content; the "
            "loader does, so a restamped artefact would fail merkle before "
            "the layer under test is reached" % marker)


def test_the_chain_names_the_layer_that_fires():
    """Each verdict names a mechanism, not just a return code.

    A harness that reports "blocked" without saying by WHAT cannot
    distinguish "the signature held" from "my edit was a syntax error" --
    the defect that made the first re-sign row look defended when nothing had
    been tested.
    """
    source = open(os.path.join(REPO, "scripts", "attack_chain.py"),
                  encoding="utf-8").read()
    for named in ("SIGNATURE NOT BINDING", "CFI IS A TAMPER DETECTOR",
                  "re-sign, attacker key", "CFI removed + rechain"):
        assert named in source, (
            "the chain does not name %r; a row that only prints rc does not "
            "say which layer did the work" % named)
