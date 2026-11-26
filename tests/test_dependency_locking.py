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


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")

#: Install commands that are legitimately not hash-locked, each with a reason.
#: Adding to this list should be a deliberate act with a stated justification.
ALLOWED_UNHASHED = (
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


def test_the_pip_audit_lock_exists_and_is_hashed():
    """The auditor itself must not be an unverified supply-chain exception."""
    path = os.path.join(ROOT, "requirements-pip-audit.lock")
    assert os.path.exists(path), (
        "requirements-pip-audit.lock is missing; pip-audit must install "
        "through --require-hashes rather than as a trusted exception")
    text = open(path, encoding="utf-8").read()
    assert re.search(r"^pip-audit==2\.10\.1", text, re.M), (
        "pip-audit 2.10.1 is not pinned in requirements-pip-audit.lock")
    assert "--hash=sha256:" in text, (
        "requirements-pip-audit.lock carries no artifact hashes")


def test_no_unhashed_pip_audit_install_exception_remains():
    offenders = []
    for name, no, line in _install_lines():
        if "pip-audit" in line and "--require-hashes" not in line:
            offenders.append("%s:%d: %s" % (name, no, line.strip()))
    assert not offenders, (
        "pip-audit installs must use requirements-pip-audit.lock with "
        "--require-hashes:\n  " + "\n  ".join(offenders))


def test_the_farm_lock_exists_and_carries_hashes_for_all_build_tools():
    path = os.path.join(ROOT, "requirements-farm.lock")
    assert os.path.exists(path), (
        "requirements-farm.lock is missing; the generated native-build farm "
        "would have no hash-locked dependency file to install")
    text = open(path, encoding="utf-8").read()
    packages = re.findall(r"^([A-Za-z0-9_.-]+)==", text, re.M)
    assert sorted(p.lower() for p in packages) == ["cython", "packaging", "setuptools", "wheel"]
    for pkg in packages:
        block = re.search(r"^%s==[^\n]*(?:\n    .*)*" % re.escape(pkg),
                          text, re.M)
        assert block and "--hash=sha256:" in block.group(0), (
            "%s is present in requirements-farm.lock without artifact hashes" % pkg)


def test_the_farm_lock_hashes_are_copied_from_the_main_lock():
    main = open(os.path.join(ROOT, "requirements.lock"), encoding="utf-8").read()
    farm = open(os.path.join(ROOT, "requirements-farm.lock"), encoding="utf-8").read()
    main_hashes = set(re.findall(r"--hash=sha256:([0-9a-f]{64})", main))
    farm_hashes = set(re.findall(r"--hash=sha256:([0-9a-f]{64})", farm))
    assert farm_hashes and farm_hashes <= main_hashes


def test_generated_farm_workflow_uses_only_the_hash_locked_install():
    from obfuscator.core.utils import farm_driver_dependencies, render_farm_yaml

    yaml_text = render_farm_yaml("payload.py")
    assert yaml_text.count("pip install --require-hashes -r requirements-farm.lock") == 3
    assert "pip install cython" not in yaml_text
    assert "install upx" not in yaml_text
    assert any(remote == "requirements-farm.lock" and os.path.exists(local)
               for remote, local in farm_driver_dependencies())


def test_artifact_workflows_do_not_install_unused_upx():
    """UPX is not used by the acceptance/release jobs and must not be an
    unverified package-manager supply-chain exception there."""
    offenders = []
    for path in sorted(glob.glob(os.path.join(WORKFLOWS, "*.yml"))):
        with open(path, encoding="utf-8") as fh:
            for no, line in enumerate(fh, 1):
                if line.lstrip().startswith("#"):
                    continue
                if "install upx" in line or "install -y upx" in line:
                    offenders.append("%s:%d: %s" % (os.path.basename(path), no, line.strip()))
    assert not offenders, (
        "UPX is not invoked by these artifact workflows; installing it is an "
        "unnecessary unhashed supply-chain exception:\n  " + "\n  ".join(offenders))
