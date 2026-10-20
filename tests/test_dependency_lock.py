"""The hash-pinned lock must match requirements.txt.

``requirements.txt`` states which versions the project wants;
``requirements.lock`` states exactly which artefacts CI is allowed to
install, with their SHA-256.  A dependency bump that does not
regenerate the lock leaves CI installing something the project did not
ask for -- which is the whole failure the lock exists to prevent.

This test checks the two files agree on the direct requirements, and
that every locked artefact carries a hash.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")
LOCK = os.path.join(ROOT, "requirements.lock")


def _requirements():
    """The direct requirements, as (name, specifier) pairs."""
    out = []
    with open(REQUIREMENTS, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#")[0].strip()
            if not line or line.startswith("-"):
                continue
            name, _, spec = line.partition("==")
            if not spec:
                name, _, spec = line.partition(">=")
            out.append((name.strip().lower(), spec.strip()))
    return out


def _locked():
    """The locked (name, version) pairs."""
    out = {}
    with open(LOCK, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#")[0].strip()
            m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;\\]+)", line)
            if m:
                out[m.group(1).lower().replace("_", "-")] = m.group(2)
    return out


def test_the_lock_exists():
    assert os.path.exists(LOCK), (
        "requirements.lock is missing: CI installs from it with "
        "--require-hashes")


def test_every_direct_requirement_is_in_the_lock():
    locked = _locked()
    missing = []
    for name, spec in _requirements():
        key = name.replace("_", "-")
        if key not in locked:
            missing.append("%s==%s" % (name, spec))
            continue
        if spec.startswith("==") and locked[key] != spec:
            missing.append("%s: requirements.txt says %s, the lock says %s"
                           % (name, spec, locked[key]))
    assert not missing, (
        "requirements.txt and requirements.lock disagree -- regenerate the "
        "lock with `make lock`: %r" % (missing,))


def test_every_locked_artefact_has_a_hash():
    """--require-hashes refuses an artefact without one."""
    with open(LOCK, encoding="utf-8") as fh:
        text = fh.read()
    entries = re.findall(r"^([A-Za-z0-9_.\-]+)==([^\s;\\]+)(.*?)(?=^[A-Za-z0-9_.\-]+==|\Z)",
                          text, re.M | re.S)
    assert entries, "the lock parsed as empty"
    unhashed = [name for name, _ver, body in entries
                if "--hash=sha256:" not in body]
    assert not unhashed, (
        "these locked artefacts have no hash, so --require-hashes would "
        "refuse them: %r" % (unhashed,))


def test_the_lock_covers_the_transitive_dependencies():
    """A lock with only the direct requirements is not a lock.

    The point of pinning the transitive closure is that nothing can be
    substituted underneath.  The direct requirements pull in a known set
    of transitives; if the lock does not contain them, pip is free to
    resolve them itself.
    """
    locked = set(_locked())
    expected_transitive = {"certifi", "charset-normalizer", "idna",
                           "pycparser", "cffi", "pluggy", "iniconfig",
                           "packaging", "exceptiongroup", "tomli",
                           "typing-extensions"}
    missing = sorted(t for t in expected_transitive if t not in locked)
    assert not missing, (
        "the lock does not pin these transitive dependencies: %r" % (missing,))
