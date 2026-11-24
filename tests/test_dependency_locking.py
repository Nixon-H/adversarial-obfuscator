"""AI-SC-003: dependency installs in artefact-producing jobs must be hash-locked.

The finding: the jobs that BUILD artefact installed dependencies without
`--require-hashes`, and two of the packages in that command (`setuptools`,
`wheel`) had no version pin either. A substituted or compromised wheel would not
have been detected at install time, in the jobs whose output is then signed.

What was wrong, concretely:

    release.yml, ci.yml:   pip install cython==3.0.12 setuptools wheel
                           -> setuptools and wheel unversioned, no hashes
    security-artifact.yml: pip install -r requirements.txt
    shadow-build.yml:      pip install -r requirements.txt
                           -> versions pinned, artefacts not verified
    three jobs:            pip install -r requirements-dev.txt
                           -> ruff/pyyaml version-pinned, not hash-verified

The fix routes every one of those through a generated lock with SHA-256 hashes,
and pins the two packages that were missing from requirements.txt at all.

These tests pin the POLICY, not the file contents: a new workflow that installs a
build dependency unhashed will fail here rather than shipping quietly.
"""
import glob
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")

#: Install commands that are legitimately not hash-locked, each with a reason.
#: Adding to this list should be a deliberate act with a stated justification.
ALLOWED_UNHASHED = (
    "pip-audit==",      # verification tool, never a build input
    "ruff",             # lint tool, pinned by version in the lock now anyway
)


def _install_lines():
    """Yield (workflow_file, line_no, line) for every real pip install."""
    for path in sorted(glob.glob(os.path.join(WORKFLOWS, "*.yml"))):
        with open(path, encoding="utf-8") as fh:
            for no, line in enumerate(fh, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "pip install" not in line:
                    continue
                # Skip prose in comments that merely mentions pip install.
                if line.lstrip().startswith("#"):
                    continue
                yield os.path.basename(path), no, line.rstrip()


def test_every_build_install_is_hash_locked():
    offenders = []
    for name, no, line in _install_lines():
        if "--require-hashes" in line:
            continue
        if any(allow in line for allow in ALLOWED_UNHASHED):
            continue
        offenders.append("%s:%d: %s" % (name, no, line.strip()))
    assert not offenders, (
        "these workflow installs are not hash-locked and are not on the "
        "documented exception list:\n  " + "\n  ".join(offenders))


def test_the_main_lock_covers_the_build_tools():
    """setuptools and wheel must be IN the lock, not installed by name."""
    text = open(os.path.join(ROOT, "requirements.lock"), encoding="utf-8").read()
    for pkg in ("setuptools", "wheel", "cython"):
        assert re.search(r"^%s==" % pkg, text, re.M | re.I), (
            "%s is not pinned in requirements.lock, so `pip install %s` in a "
            "workflow could not be hash-locked" % (pkg, pkg))


def test_the_lock_carries_hashes_for_every_package():
    text = open(os.path.join(ROOT, "requirements.lock"), encoding="utf-8").read()
    packages = re.findall(r"^([A-Za-z0-9_.-]+)==", text, re.M)
    assert packages, "no pinned packages found in the lock"
    hashes = len(re.findall(r"^ *--hash=sha256:", text, re.M))
    assert hashes >= len(packages) * 4, (
        "only %d hashes for %d packages; a universal lock should carry several "
        "wheels per package" % (hashes, len(packages)))


def test_the_dev_lock_exists_and_is_hashed():
    path = os.path.join(ROOT, "requirements-dev.lock")
    assert os.path.exists(path), (
        "requirements-dev.lock is missing; the dev tooling installs were "
        "switched to it, so its absence breaks three CI jobs")
    text = open(path, encoding="utf-8").read()
    assert "--hash=sha256:" in text
    assert re.search(r"^ruff==", text, re.M), "ruff is not pinned in the dev lock"


def test_setuptools_is_exactly_pinned_in_the_source_list():
    """A floating floor cannot be hash-locked."""
    text = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read()
    assert re.search(r"^setuptools==", text, re.M), (
        "setuptools still uses a floating floor; --generate-hashes needs an "
        "exact version, and the artefact-producing jobs install this package")
