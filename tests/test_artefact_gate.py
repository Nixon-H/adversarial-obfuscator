"""The artefact-dependent tests must actually run.

Eighteen tests need a compiled artefact -- the C shared libraries and
the Rust relay binary -- and each of them SKIPS itself when the
artefact is absent.  That is the right behaviour for a developer
without a compiler, and the wrong behaviour for CI: with the build
scheduled *after* the tests, CI skipped all of them too, and a skipped
test proves nothing.

This gate runs in CI (NIXON_REQUIRE_ARTEFACTS=1) and fails the build
if an artefact is missing -- so a missing artefact is a failed build,
not a quiet skip.

`/tmp/libmicrojit.so` was on the list until 2026-10-26.  `make
microjit-so` was removed when native/microjit.c was archived
(archive/native/README.md: nothing ever loaded the .so), so the gate
demanded an artefact no build step produces and every CI run failed on
it.  The list tracks the artefacts `make all` actually builds.
"""

import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = (
    os.path.join(ROOT, "build", "nixon_core.so"),
    os.path.join(ROOT, "build", "wb.so"),
    os.path.join(ROOT, "build", "py_compile.so"),
    os.path.join(ROOT, "build", "orbital-relay"),
)


@pytest.mark.skipif(
    not os.environ.get("NIXON_REQUIRE_ARTEFACTS"),
    reason="the artefact gate is enforced in CI (NIXON_REQUIRE_ARTEFACTS=1)",
)
def test_the_artefact_dependent_tests_can_run():
    """Every artefact those tests need must be present."""
    missing = [p for p in REQUIRED if not os.path.exists(p)]
    assert not missing, (
        "these artefacts are missing, so the tests that need them would "
        "SKIP instead of running: %r" % (missing,))


def test_the_artefact_list_is_not_empty():
    """A guard against the list being emptied by accident."""
    assert len(REQUIRED) >= 4
    assert any("orbital-relay" in p for p in REQUIRED)
