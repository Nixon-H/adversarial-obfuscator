"""The review packages' reproduction instructions must not be fiction.

Three commissioning packages hand an independent reviewer commands to run:
`CRYPTO_REVIEW_PACKAGE.md` §8, `RE_EVALUATION_PROTOCOL.md` §2.1 and §8, and
`MIMOSA_REVIEW_PACKAGE.md` §8. Those commands were RUN while preparing the
packages, and the first drafts were wrong in ways that would have cost a
reviewer an hour:

  * the RE protocol omitted `PYTHONPATH`, so `python3 -m obfuscator.core.
    pipeline` failed with ModuleNotFoundError from any directory that was not
    the checkout root;
  * the RE protocol's command wrote its artefact into the REPOSITORY
    (`tests/fixtures/dist`) rather than scratch, dirtying the tree the reviewer
    is meant to be evaluating — measured, then corrected by copying the subject
    to scratch first;
  * the protocol said the control arm was "obfuscation disabled" without naming
    a flag; `--opt-level 0` is the mechanism that exists.

This module pins the corrected instructions. It checks the build flags against
the parser's own source rather than by invoking the CLI, so it stays fast and
does not need a subprocess: the question is "does the tool accept this flag",
and the parser definition answers that directly.
"""
import ast
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

CRYPTO = os.path.join(REPO, "docs", "security", "CRYPTO_REVIEW_PACKAGE.md")
RE_PROTOCOL = os.path.join(REPO, "docs", "security", "RE_EVALUATION_PROTOCOL.md")
MIMOSA = os.path.join(REPO, "docs", "security", "MIMOSA_REVIEW_PACKAGE.md")
PIPELINE = os.path.join(REPO, "obfuscator", "core", "pipeline.py")


def _text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _build_flags():
    """Every `add_argument` flag string in the pipeline module's source.

    Read from the parser definition rather than the CLI, so this test neither
    spawns a process nor depends on import side effects.
    """
    tree = ast.parse(_text(PIPELINE))
    flags = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "add_argument"):
            for arg in node.args:
                if (isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                        and arg.value.startswith("-")):
                    flags.add(arg.value)
    return flags


# ── RE protocol: the flags its two build commands use ─────────────────

@pytest.mark.parametrize("flag", [
    "--opt-level", "--skip-cloud", "--package", "--section-count",
    "--watermark", "--in-place", "--no-anti-rea",
])
def test_the_protocols_build_flags_exist(flag):
    """Every flag the protocol tells a reviewer to pass must be accepted.

    `--opt-level` is the control arm; if it stopped existing the reviewer
    could not build the baseline this protocol depends on.
    """
    assert flag in _build_flags(), (
        "%s is not a build flag; the protocol tells a reviewer to pass it"
        % (flag,))


def test_the_protocol_documents_pythonpath():
    """The corrected §2.1 must state PYTHONPATH, which the first draft omitted."""
    text = _text(RE_PROTOCOL)
    assert "PYTHONPATH" in text, (
        "the protocol must state PYTHONPATH or the documented command fails "
        "with ModuleNotFoundError from any non-checkout directory")
    assert "ModuleNotFoundError" in text, (
        "the protocol should say what goes wrong without it, so a reviewer "
        "recognises the failure instead of debugging the tool")


def test_the_protocol_warns_that_the_build_writes_beside_the_payload():
    """The correction that keeps a reviewer's checkout clean."""
    text = _text(RE_PROTOCOL)
    assert "writes beside the payload" in text, (
        "the protocol must warn that the build targets the payload's own "
        "directory, not the current directory")
    assert "dirty" in text, (
        "the warning must say why it matters: it dirties the tree under review")
    assert "git" in text and "status --porcelain" in text, (
        "the protocol must give the reviewer a way to confirm the checkout "
        "stayed clean")


def test_the_protocol_states_the_measured_equivalence_result():
    """§5's gate is claimed to have been exercised, not assumed."""
    text = _text(RE_PROTOCOL)
    assert "Measured" in text and "identical" in text, (
        "the protocol should record that both arms were built and produced "
        "identical output, so the reviewer starts from a working pair")
    for marker in ("RE-SUBJECT-OUTCOME 38664 rejected", "audit:rejected"):
        assert marker in text, (
            "the protocol must state the expected observable output (%r)"
            % (marker,))


# ── crypto package: the REPL inspection step ──────────────────────────

def test_the_crypto_package_reproduction_step_works():
    """§8 tells the reviewer to call split_sealed and read the pack dict."""
    from obfuscator.section_split import split_sealed

    pack = split_sealed(b"payload for review" * 4, sections=4,
                        key=b"\x11" * 32)
    assert set(pack) >= {"sections", "count", "total", "v", "state",
                         "key_hint", "per_section"}
    assert pack["v"] == 2 and pack["count"] == 4
    section = pack["sections"][0]
    assert set(section) >= {"i", "salt", "nonce", "data"}
    assert len(bytes.fromhex(section["nonce"])) == 16, (
        "§3.5 documents a 16-byte nonce; the builder must emit one")
    assert "split_sealed" in _text(CRYPTO), (
        "the package must still tell the reviewer how to inspect a pack")


def test_no_package_contains_a_credential_shaped_literal():
    """The standing rule: no usable credential in docs, examples or tests."""
    for path in (CRYPTO, RE_PROTOCOL, MIMOSA):
        text = _text(path)
        assert not re.search(r"[0-9a-fA-F]{64}", text), (
            "%s contains a 64-hex string; that is the shape of a private key "
            "and must not be written into a document"
            % os.path.basename(path))


# ── every package keeps its NOT PERFORMED / NOT RUN banner ────────────

@pytest.mark.parametrize("path,banner", [
    (CRYPTO, "NOT PERFORMED"),
    (RE_PROTOCOL, "NOT RUN"),
    (MIMOSA, "NOT PERFORMED"),
])
def test_each_package_declares_it_has_not_been_reviewed(path, banner):
    """A package that reads as a completed review is worse than a gap."""
    text = _text(path)
    assert banner in text, (
        "%s must state %r up front, or it reads as a finished review"
        % (os.path.basename(path), banner))


def test_no_package_claims_an_independent_review_happened():
    """The specific phrasing that would be a false claim."""
    for path in (CRYPTO, RE_PROTOCOL, MIMOSA):
        lowered = _text(path).lower()
        assert "independently reviewed" not in lowered, (
            "%s claims independent review has occurred"
            % os.path.basename(path))
        assert "reviewer confirmed" not in lowered, (
            "%s claims a reviewer confirmed something"
            % os.path.basename(path))
