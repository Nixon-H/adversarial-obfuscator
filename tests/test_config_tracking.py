"""The build configuration must be in the repository.

``config/default.json`` is the feature configuration: every Phase 2
protection is gated on it, and ``config/baseline_report.json`` is the
baseline the security-regression checker compares against.  Both used to
be gitignored along with the whole ``config/`` directory, because that
directory can hold machine-local settings.

The consequence was that a fresh clone had no ``config/default.json``:
every feature gate read an empty config, the build degraded to a
weaker artifact, and the schema tests failed with ``FileNotFoundError``.
The tokens do not live in these files -- they live in the setup wizard's
store -- so there is no reason to keep the build's own configuration
out of the repository.
"""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSON = os.path.join(ROOT, "config", "default.json")
BASELINE_JSON = os.path.join(ROOT, "config", "baseline_report.json")


def _git_ls_files(path):
    try:
        proc = subprocess.run(["git", "-C", ROOT, "ls-files", "--error-unmatch",
                               path], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None          # not a git checkout: nothing to assert
    return proc.returncode == 0


def test_default_config_exists():
    assert os.path.exists(DEFAULT_JSON), (
        "config/default.json is missing; every Phase 2 feature gate "
        "reads it and the build would silently degrade")


def test_default_config_is_tracked_by_git():
    tracked = _git_ls_files("config/default.json")
    if tracked is None:
        return
    assert tracked, (
        "config/default.json is not tracked: a fresh clone would build a "
        "different, weaker artifact")


def test_baseline_report_is_tracked_by_git():
    tracked = _git_ls_files("config/baseline_report.json")
    if tracked is None:
        return
    assert tracked, (
        "config/baseline_report.json is not tracked: the security-gate "
        "baseline would be missing on a fresh clone")


def test_relay_config_stays_untracked():
    """The machine-local relay config must NOT be committed."""
    tracked = _git_ls_files("config/relay.json")
    if tracked is None:
        return
    assert not tracked, "config/relay.json is machine-local and must stay untracked"


def test_tracked_config_contains_no_secrets():
    """The tracked config must be safe to publish."""
    with open(DEFAULT_JSON, encoding="utf-8") as fh:
        raw = fh.read().lower()
    for marker in ("password", "secret", "api_key", "apikey", "bearer ",
                   "private_key", "token"):
        assert marker not in raw, (
            "config/default.json contains %r; it is tracked, so it must "
            "not hold a credential" % marker)
    json.loads(open(DEFAULT_JSON, encoding="utf-8").read())
