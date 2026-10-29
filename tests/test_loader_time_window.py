"""The payload key must not depend on when the artefact is run.

The key derivation mixed a 30-day rotation window into the key:

    time_window = max(0, (now - BUILD_TIMESTAMP) // (30 days))
    time_salt   = sha256(str(time_window))
    k_dec       = xor(k_final, time_salt, prov_salt)

At pack time the window is always 0; at run time it was recomputed from
the wall clock, so it became 1 after thirty days and the key no longer
matched. Every artefact quietly stopped decrypting a month after it was
built.

Nothing caught it because no test ran an artefact "later" -- the harness
always runs them within the same minute they are built. These guards are
textual and cheap: they assert the template uses the pack-time constant
instead of the clock, which is what keeps pack and run in agreement
whenever the artefact executes.
"""

import re


def _template():
    src = open(
        __file__.replace("test_loader_time_window.py", "") + "../obfuscator/core/sources.py",
        encoding="utf-8",
    ).read()
    return src


def test_the_key_derivation_uses_the_pack_time_window():
    src = _template()
    assert "time_window = _NX_BUILD_WINDOW" in src, (
        "the payload key derivation recomputes its window from the wall "
        "clock again -- artefacts will stop decrypting after 30 days"
    )


def test_the_environment_key_uses_the_pack_time_window():
    src = _template()
    assert "    w = _NX_BUILD_WINDOW" in src


def test_the_window_is_not_recomputed_from_the_clock():
    src = _template()
    # The exact shape that caused the expiry: a window derived from time().
    bad = re.findall(r"time_window\s*=\s*max\(0,[^\n]*time\(\)", src)
    assert not bad, bad
    bad2 = re.findall(r"w\s*=\s*\(ct\s*-\s*BUILD_TIMESTAMP\)", src)
    assert not bad2, bad2


def test_the_constant_is_emitted_next_to_the_timestamp():
    src = _template()
    assert "_NX_BUILD_WINDOW = 0" in src
    assert "BUILD_TIMESTAMP = {build_timestamp}" in src
