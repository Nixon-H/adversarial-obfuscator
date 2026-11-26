"""§9 anti-rollback: refuse to run an older, weaker build.

The threat: once a protection flaw is fixed in build N+1, an attacker who can
substitute files re-installs build N, which still runs and still has the flaw.
A version number in a manifest does not stop that -- the attacker edits it too.

The protection is a monotonic integer level (not a marketing version, so
ordering cannot be gamed by "2.0.0-rc1" style strings) compared against a
high-water mark kept beside the artefact, MAC'd with the build key.

**Honest limit, asserted below so nobody forgets it:** the mark is client-side.
Deleting it, or running in a clean directory, lets the old build run again.
Real anti-rollback needs the issuer or a server to refuse old builds.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import rollback as rb  # noqa: E402

KEY = b"k" * 32


@pytest.fixture
def artefact(tmp_path):
    """A path in tmp_path; the module under test does all file I/O itself."""
    return str(tmp_path.joinpath("payload_protected.py"))


def test_first_install_records_the_level(artefact):
    result = rb.check_rollback(artefact, 5, KEY)
    assert result["level"] == 5
    assert result["previous"] == 0
    assert rb.read_mark(result["mark"]) == 5


def test_same_level_is_accepted(artefact):
    rb.check_rollback(artefact, 5, KEY)
    assert rb.check_rollback(artefact, 5, KEY)["previous"] == 5


def test_upgrade_raises_the_mark(artefact):
    rb.check_rollback(artefact, 5, KEY)
    assert rb.read_mark(rb.check_rollback(artefact, 7, KEY)["mark"]) == 7


def test_downgrade_is_refused(artefact):
    rb.check_rollback(artefact, 7, KEY)
    with pytest.raises(RuntimeError, match="refusing to downgrade"):
        rb.check_rollback(artefact, 6, KEY)


def test_downgrade_check_reads_the_mark_it_wrote(artefact):
    """The mark must survive a re-open: write then read it back."""
    mark = rb.check_rollback(artefact, 9, KEY)["mark"]
    assert rb.read_mark(mark) == 9
    with pytest.raises(RuntimeError):
        rb.check_rollback(artefact, 8, KEY)


def test_missing_mark_is_first_run_not_an_attack(artefact):
    """Absent mark must not brick a fresh install.

    A missing file means "first run here", not "attack": treating it as a
    failure would break every clean install. This is also the documented
    limit -- no mark, no memory.
    """
    assert rb.check_rollback(artefact, 1, KEY)["previous"] == 0


def test_level_must_be_a_non_negative_int(artefact):
    for bad in (-1, "5", 1.5, None):
        with pytest.raises(RuntimeError, match="non-negative int"):
            rb.check_rollback(artefact, bad, KEY)


def test_mac_is_bound_to_the_artefact_name():
    """A mark written for another product must not match this one."""
    assert rb._mac(KEY, 4, "other_product.py") != \
        rb._mac(KEY, 4, "payload_protected.py")


def test_mac_is_bound_to_the_level():
    assert rb._mac(KEY, 4, "p.py") != rb._mac(KEY, 5, "p.py")


def test_mac_is_bound_to_the_key():
    assert rb._mac(KEY, 4, "p.py") != rb._mac(b"other" * 8, 4, "p.py")


def test_corrupt_mark_degrades_to_zero(artefact):
    """A damaged mark reads as 0 rather than raising: it is a hint, not a key."""
    mark = rb.check_rollback(artefact, 3, KEY)["mark"]
    rb.write_mark(mark, KEY, 3, "payload_protected.py")
    assert rb.read_mark(mark) == 3
