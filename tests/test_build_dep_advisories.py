"""Pinned build dependencies must stay at or above their patched versions.

Pinning `setuptools` and `wheel` (finding AI-SC-003) had an unexpected benefit:
Dependabot could finally SEE them, and immediately reported three advisories --
one high. Both were installed by name and unpinned before, so they were absent
from the dependency graph and the advisories were never surfaced.

    wheel       >= 0.40.0, <= 0.46.1   HIGH   arbitrary file-permission
                                              modification via path traversal
                                              in `wheel unpack`
    setuptools  < 83.0.0               MEDIUM MANIFEST.in exclusion bypass via
                                              Unicode NFC/NFD collision on
                                              APFS/HFS+
    setuptools  >= 38.2.2, < 84.1.0    LOW    Windows path escape via
                                              namespace_packages.txt during
                                              legacy wheel installation

This is a real cost of pinning that is worth stating: a pinned dependency
carries a CVE surface that an unpinned one hides. The mitigation is to stay at
or above the patched versions, which is what these tests enforce.

A downgrade below a patched version fails here with the advisory named, so a
future "pin it back to what worked" change cannot silently reintroduce a HIGH.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: package -> (minimum safe version tuple, advisory description)
PATCHED_MINIMUMS = {
    "wheel": ((0, 46, 2),
              "GHSA high: path traversal in `wheel unpack` allows arbitrary "
              "file-permission modification"),
    "setuptools": ((84, 1, 0),
                   "GHSA medium (MANIFEST.in bypass, patched 83.0.0) and low "
                   "(Windows path escape, patched 84.1.0)"),
}


def _version_tuple(text):
    return tuple(int(p) for p in re.findall(r"\d+", text)[:3])


def _pins(path):
    """Return {package: version_string} for exact `name==version` pins."""
    out = {}
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^([A-Za-z0-9_.-]+)==([0-9][0-9A-Za-z.\-]*)", line)
            if m:
                out[m.group(1).lower()] = m.group(2)
    return out


@pytest.mark.parametrize("pkg", sorted(PATCHED_MINIMUMS))
def test_requirements_pin_is_at_or_above_the_patched_version(pkg):
    minimum, why = PATCHED_MINIMUMS[pkg]
    pins = _pins("requirements.txt")
    assert pkg in pins, (
        "%s is not exactly pinned in requirements.txt; an unpinned build "
        "dependency cannot be hash-locked and is invisible to Dependabot" % pkg)
    got = _version_tuple(pins[pkg])
    assert got >= minimum, (
        "%s is pinned at %s but the patched version is %s (%s). Staying below "
        "a patched version reintroduces the advisory."
        % (pkg, pins[pkg], ".".join(map(str, minimum)), why))


@pytest.mark.parametrize("pkg", sorted(PATCHED_MINIMUMS))
def test_the_lock_agrees_with_the_pin(pkg):
    """The lock must not lag behind requirements.txt."""
    req = _pins("requirements.txt").get(pkg)
    lock = _pins("requirements.lock").get(pkg)
    assert lock is not None, "%s missing from requirements.lock" % pkg
    assert req == lock, (
        "requirements.txt pins %s==%s but requirements.lock has %s==%s; the "
        "lock was not regenerated after the bump" % (pkg, req, pkg, lock))


@pytest.mark.parametrize("pkg", sorted(PATCHED_MINIMUMS))
def test_the_lock_carries_hashes_for_the_bumped_package(pkg):
    text = open(os.path.join(ROOT, "requirements.lock"), encoding="utf-8").read()
    block = re.search(r"^%s==[^\n]*\n((?: *--hash=[^\n]*\n)+)" % re.escape(pkg),
                      text, re.M)
    assert block, (
        "%s has no hash block in requirements.lock, so --require-hashes "
        "cannot verify it" % pkg)
    assert "sha256:" in block.group(1)
