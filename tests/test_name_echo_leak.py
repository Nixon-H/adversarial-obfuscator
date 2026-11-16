"""A payload must not print the identifier names the rename layer hides.

Regression for the 2026-11-14 bench finding. The token-holding analyst
recovered 4 of the 12 original top-level names without touching the rename
layer at all: it ran the artefact and read the labels the payload prints.

    print("evens:", list(evens(9)))     ->  evens: [0, 2, 4, 6, 8]

The literal is sealed at rest like every other string, so a static read of the
artefact shows nothing. It decrypts to the original name at run time, which
puts the name on stdout. `"evens:"` is an exact disclosure; `"walrus:"` against
`walrus_count` and `"descriptor:"` against `Descriptor` are stem hints that
narrow the guess to one candidate.

The obfuscator cannot rewrite these safely -- a printed label and a protocol
field are the same AST node -- so the build reports them instead. These tests
pin the detector and the warning it drives.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.sources import find_name_echoing_strings


def _hits(source):
    return find_name_echoing_strings(ast.parse(source))


def _kinds(source):
    return {(name, kind) for name, _, kind in _hits(source)}


def test_exact_name_in_a_printed_label_is_reported():
    src = (
        "def evens(limit):\n"
        "    return [n for n in range(limit) if n % 2 == 0]\n"
        "\n"
        "def main():\n"
        "    print('evens:', evens(9))\n"
    )
    assert ("evens", "exact") in _kinds(src)


def test_stem_hint_is_reported_as_a_hint_not_a_disclosure():
    src = (
        "def walrus_count(values):\n"
        "    return len(values)\n"
        "\n"
        "def main():\n"
        "    print('walrus:', walrus_count([1, 2]))\n"
    )
    kinds = _kinds(src)
    assert ("walrus_count", "stem") in kinds
    # The literal does not spell the whole name, so it must not be called exact.
    assert ("walrus_count", "exact") not in kinds


def test_a_payload_that_does_not_echo_its_names_reports_nothing():
    src = (
        "def evens(limit):\n"
        "    return [n for n in range(limit) if n % 2 == 0]\n"
        "\n"
        "def main():\n"
        "    print('result:', evens(9))\n"
    )
    assert _hits(src) == []


def test_short_words_do_not_produce_stem_hits():
    # "run" is under the four-character floor, so a label like "run:" must not
    # be reported against a definition called `runner`.
    src = (
        "def runner():\n"
        "    return 1\n"
        "\n"
        "def main():\n"
        "    print('run:', runner())\n"
    )
    assert _hits(src) == []


def test_a_name_inside_a_longer_word_is_not_an_exact_hit():
    # `evens` must not match inside `sevens`.
    src = (
        "def evens(limit):\n"
        "    return limit\n"
        "\n"
        "def main():\n"
        "    print('sevens:', evens(9))\n"
    )
    assert ("evens", "exact") not in _kinds(src)


def test_the_bench_payload_is_flagged():
    """The payload this finding came from must trip the detector."""
    payload = "/tmp/rea-run-rea/payload.py"
    if not os.path.exists(payload):
        import pytest
        pytest.skip("bench payload not present on this host")
    with open(payload, encoding="utf-8") as fh:
        kinds = _kinds(fh.read())
    assert ("evens", "exact") in kinds
    assert ("Descriptor", "stem") in kinds
    assert ("walrus_count", "stem") in kinds


def test_build_warns_when_the_payload_echoes_names():
    """The detector is wired into the build, not just importable."""
    from obfuscator.core import sources

    warnings = []
    original_warn = sources.UI.warn
    sources.UI.warn = lambda msg, *a, **k: warnings.append(str(msg))
    try:
        sources.apply_ast_mutation(
            "def evens(limit):\n"
            "    return [n for n in range(limit) if n % 2 == 0]\n"
            "\n"
            "def main():\n"
            "    print('evens:', evens(9))\n",
            {"rename": False},
        )
    finally:
        sources.UI.warn = original_warn
    assert any("identifier names" in w and "evens" in w for w in warnings), warnings
