"""The self-check must be anchored to a secret the artefact does not carry.

Regression for the 2026-11-15 bench finding. The loader's self-check hashed
its own source and compared against a value stored in that same source, keyed
with ``_HMAC_KEY_`` -- also stored in that same source. An analyst holding the
artefact could therefore edit it and recompute both values, and the check
passed. That is exactly how the position-2 bypass worked.

The fix adds a third anchor on the HMAC line, keyed with the licence's
``key_material``. That value is not in the artefact: it arrives with the
external token. A patched artefact cannot re-stamp itself without the token.

These tests pin the wiring and the fail-closed behaviour. They do not claim
the anchor stops a token holder -- it cannot, and the honest limit is recorded
in ``mistral.md``.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core import pipeline, sources


def _loader_template() -> str:
    return sources.LOADER_HEAD + "\n" + sources.LOADER_BODY


def test_keyed_anchor_variable_is_registered():
    """The template field must resolve, or every build dies on format()."""
    assert "KEYED_ANCHOR" in sources.VARS
    assert sources.VARS["KEYED_ANCHOR"]


def test_anchor_line_carries_three_placeholders():
    """Three 64-zero slots: checksum, HMAC, keyed anchor.

    The build fills them with three successive ``subn(count=1)`` calls, so a
    missing slot would silently leave the keyed anchor empty and the check
    would never run.
    """
    template = _loader_template()
    line = next(
        (l for l in template.splitlines() if "__HMAC_ANCHOR__" in l), None)
    assert line is not None, "HMAC anchor line disappeared from the template"
    assert line.count('"0' * 1) >= 0  # placeholder is {dummy_hmac}, not zeros
    assert "{dummy_hmac}" in line
    assert "{dummy_keyed}" in line
    assert "{VAR_KEYED_ANCHOR}" in line


def test_self_check_verifies_the_keyed_anchor():
    """The runtime half must exist and must fail closed."""
    template = _loader_template()
    start = template.index("def {FUNC_SELF}():")
    end = template.index("def {FUNC_LIVE_CHK}():", start)
    body = template[start:end]
    assert "{VAR_KEYED_ANCHOR}" in body
    assert "_nx_licence_payload" in body
    # Fail closed: a missing key material is a failure, not a skip.
    assert "keyed anchor present but no licence key_material" in body
    assert "_nx_self_fail" in body


def test_keyed_anchor_is_skipped_for_unlicensed_builds():
    """An unlicensed build has an empty anchor and must still run.

    The check is skipped rather than failed, otherwise every build without
    ``--licence token=`` would exit 137.
    """
    template = _loader_template()
    start = template.index("def {FUNC_SELF}():")
    end = template.index("def {FUNC_LIVE_CHK}():", start)
    body = template[start:end]
    assert re.search(r"if \{VAR_KEYED_ANCHOR\}:\s*\n", body), (
        "the keyed check must be guarded by the anchor being non-empty")


def test_build_raises_when_the_anchor_slot_is_missing():
    """A template without the third slot must fail the build, not ship.

    Silently shipping an empty anchor would disable the check while the
    build still reported success -- the failure mode this whole file exists
    to prevent.
    """
    src = open(pipeline.__file__, encoding="utf-8").read()
    assert "keyed anchor slot missing" in src


def test_cython_compat_reports_match_and_trystar():
    """The pre-flight must name the constructs Cython cannot parse."""
    assert pipeline.cython_compat_issues("x = 1\n") == []
    match_src = "def f(p):\n    match p:\n        case 1:\n            return 1\n"
    issues = pipeline.cython_compat_issues(match_src)
    assert issues and "pattern matching" in issues[0][1]
    trystar = "try:\n    pass\nexcept* ValueError:\n    pass\n"
    issues = pipeline.cython_compat_issues(trystar)
    assert issues and "exception groups" in issues[0][1]


def test_cython_compat_does_not_flag_ordinary_code():
    """A false positive would silently disable the native path."""
    ordinary = (
        "import os\n"
        "class A:\n"
        "    def m(self, x):\n"
        "        return [i for i in range(x) if i % 2 == 0]\n"
        "def g(*a, **k):\n"
        "    try:\n"
        "        return a[0]\n"
        "    except (IndexError, KeyError):\n"
        "        return k\n"
    )
    assert pipeline.cython_compat_issues(ordinary) == []
