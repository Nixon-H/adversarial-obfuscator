"""The maximum-security document must list every flag and env var the code has.

The audit's central complaint about the document was that it described the
maximum profiles without listing the live configuration surface: 15 build flags
and 68-70 `NIXON_*` variables existed in the code and appeared nowhere in it.

That is the kind of gap that reopens silently. Every new flag or environment
variable added to the parser or the runtime is, by default, undocumented — and
nobody notices because the document still reads as complete.

These tests make the gap loud. They derive the lists from the LIVE source (the
argument parser and a grep of `NIXON_*` reads) rather than from a stored
snapshot, so adding a flag without documenting it fails here.
"""
import os
import re
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "MAXIMUM_SECURITY.md")
ADDENDUM = os.path.join(ROOT, "docs", "MAXIMUM_SECURITY_ADDENDUM_20261127.md")
PIPELINE = os.path.join(ROOT, "obfuscator", "core", "pipeline.py")


def _doc_text():
    with open(DOC, encoding="utf-8") as fh:
        text = fh.read()
    # The base document is operator-frozen. New parser surface may be
    # documented in the companion addendum without rewriting that file.
    if os.path.exists(ADDENDUM):
        with open(ADDENDUM, encoding="utf-8") as fh:
            text += "\n" + fh.read()
    return text


def _cli_flags():
    """Every add_argument flag in pipeline.py, across all subcommands."""
    with open(PIPELINE, encoding="utf-8") as fh:
        src = fh.read()
    return sorted(set(re.findall(r"add_argument\('(--[a-z0-9-]+)'", src)))


def _env_vars():
    """Every NIXON_* name read anywhere in obfuscator/ or scripts/."""
    out = subprocess.run(
        ["grep", "-rhoE", r"NIXON_[A-Z0-9_]+", "--include=*.py",
         os.path.join(ROOT, "obfuscator"), os.path.join(ROOT, "scripts")],
        capture_output=True, text=True, timeout=120).stdout
    return sorted(set(out.split()))


@pytest.mark.parametrize("flag", _cli_flags())
def test_every_cli_flag_is_documented(flag):
    """A flag the parser accepts must be named in the document."""
    doc = _doc_text()
    assert flag in doc, (
        "%s is accepted by the parser but appears nowhere in "
        "docs/MAXIMUM_SECURITY.md. Either document it, or state that it is "
        "deliberately undocumented and why." % flag)


@pytest.mark.parametrize("var", _env_vars())
def test_every_env_var_is_documented(var):
    """An environment variable the code reads must be named in the document."""
    doc = _doc_text()
    assert var in doc, (
        "%s is read by the code but appears nowhere in "
        "docs/MAXIMUM_SECURITY.md. The inventory groups variables by whether "
        "an operator should set them; add it to the right group." % var)


def test_the_inventory_section_exists():
    """The grouped inventory must be present, not just scattered mentions."""
    doc = _doc_text()
    assert "## Complete flag and environment inventory" in doc, (
        "the inventory section is missing; scattered mentions of individual "
        "names are not an inventory")
    for heading in ("Release-policy gates", "Key material and trust anchors",
                    "Internal / emitted-loader housekeeping"):
        assert heading in doc, (
            "the inventory lost its %r grouping, so a reader can no longer "
            "tell operator-facing variables from internal ones" % heading)


def test_the_undocumented_build_flags_are_present():
    """The five build-subcommand flags the earlier text omitted."""
    doc = _doc_text()
    for flag in ("--bind", "--private-key", "--no-split-bootstrap",
                 "--in-place", "--cf-account"):
        assert flag in doc, "%s is missing from the inventory" % flag


def test_the_weakening_flags_are_labelled_as_such():
    """A flag that REDUCES protection must not be listed neutrally."""
    doc = _doc_text()
    idx = doc.find("--no-split-bootstrap")
    assert idx != -1
    window = doc[max(0, idx - 400):idx + 400]
    assert "weakens" in window.lower() or "weaken" in window.lower(), (
        "--no-split-bootstrap is documented neutrally; it ships the bootstrap "
        "key unsplit instead of as a Shamir split and must be marked as "
        "reducing protection")
