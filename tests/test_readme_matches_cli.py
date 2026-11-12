"""The CLI reference must describe the CLI the code actually has.

The reference used to live in the README, hand-written, listing 42 of 271
options under a heading that claimed to come from `build.py --help`. A reference
that is 15% complete is worse than none: a reader concludes the rest of the
surface does not exist, and a flag nobody documents is a flag nobody uses or
tests.

These tests regenerate the block from the live parsers and fail if `docs/CLI.md`
is stale, so adding a flag without documenting it breaks CI.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_DOC = os.path.join(ROOT, "docs", "CLI.md")
GEN = os.path.join(ROOT, "scripts", "gen_cli_reference.py")


def _gen(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, GEN, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, timeout=120,
    )


def test_cli_reference_is_not_stale():
    """`gen_cli_reference.py --check` compares CLI.md against the live parser."""
    proc = _gen("--check")
    assert proc.returncode == 0, (
        "docs/CLI.md's CLI reference is out of date. Regenerate with:\n"
        "  python3 scripts/gen_cli_reference.py --write\n"
        f"{proc.stdout}\n{proc.stderr}"
    )


def test_cli_doc_has_the_generated_markers():
    document = open(CLI_DOC, encoding="utf-8").read()
    for marker in (
        "<!-- BEGIN GENERATED CLI REFERENCE -->",
        "<!-- END GENERATED CLI REFERENCE -->",
        "<!-- BEGIN GENERATED LOADER REFERENCE -->",
        "<!-- END GENERATED LOADER REFERENCE -->",
    ):
        assert marker in document, marker


def test_loader_reference_is_not_stale():
    """The loader CLI has its own 69-flag surface, documented the same way."""
    proc = _gen("--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "loader" in proc.stdout, proc.stdout


def test_every_parser_option_appears_in_the_cli_doc():
    """No flag may be documented in the parser but absent from CLI.md."""
    proc = _gen()
    assert proc.returncode == 0, proc.stderr
    generated = proc.stdout
    document = open(CLI_DOC, encoding="utf-8").read()
    missing = [
        line for line in generated.splitlines()
        if line.startswith("| `--") and line.split("`")[1] not in document
    ]
    assert not missing, f"options generated but not in docs/CLI.md: {missing[:5]}"


@pytest.mark.parametrize("name", [
    # flags whose real behaviour contradicts their name; each must carry a note
    "seed", "build-id", "pin-structure",
])
def test_inert_flags_carry_a_warning(name):
    """A reader must not discover an inert flag by reading its implementation."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import gen_cli_reference as gen

    assert name in gen.NOTES, f"{name} is inert and needs an entry in NOTES"

    proc = _gen()
    row = next(
        (l for l in proc.stdout.splitlines()
         if l.startswith(f"| `--{name}")), None)
    assert row is not None, f"--{name} missing from the generated reference"
    markers = ("Inert", "Archived", "Build-time only", "Partial seeding only",
               "Reproducibility seed", "Lowering-kernel seed only",
               "Structure only")
    assert any(m in row for m in markers), row
