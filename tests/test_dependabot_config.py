"""Dependabot must be configured, and it must cover the ecosystems we pin.

Why this exists: pinning setuptools and wheel (AI-SC-003) let Dependabot see them
for the first time, and it reported three advisories -- one HIGH. After both were
bumped past their patched versions, GitHub's dependency graph still resolved the
OLD versions and the alerts stayed open. Timestamps showed a lag (alerts created
10:27Z, fix landed 12:45Z) and there is no REST endpoint to force a rescan.

The durable fix is a dependabot.yml that gives the graph a scheduled job to
reconcile against. These tests keep it present and keep its scope honest: a
config that silently stops covering an ecosystem is indistinguishable from no
config until an advisory goes unreported.
"""
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, ".github", "dependabot.yml")


def _config():
    assert os.path.exists(CONFIG), (
        ".github/dependabot.yml is missing; without it the dependency graph "
        "only updates on an incidental manifest change, which is how three "
        "advisories sat open after the fix that resolved them")
    with open(CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_config_parses_and_is_version_2():
    cfg = _config()
    assert cfg["version"] == 2
    assert isinstance(cfg["updates"], list) and cfg["updates"]


def test_pip_ecosystem_is_covered():
    cfg = _config()
    eco = {u["package-ecosystem"] for u in cfg["updates"]}
    assert "pip" in eco, (
        "the pip ecosystem is not covered, so pinned Python dependencies "
        "cannot receive advisory-driven updates")


def test_github_actions_ecosystem_is_covered():
    """AI-SC-002 (91 tag-pinned refs) needs this ecosystem to be managed."""
    cfg = _config()
    eco = {u["package-ecosystem"] for u in cfg["updates"]}
    assert "github-actions" in eco, (
        "the github-actions ecosystem is not covered; that is the mechanical "
        "path to immutable SHA pins for the 91 tag-pinned references")


def test_build_tooling_moves_as_one_group():
    """setuptools and wheel must bump together -- a lone bump broke the build."""
    cfg = _config()
    pip = next(u for u in cfg["updates"]
               if u["package-ecosystem"] == "pip")
    groups = pip.get("groups") or {}
    patterns = set()
    for g in groups.values():
        patterns.update(g.get("patterns") or [])
    for pkg in ("setuptools", "wheel"):
        assert pkg in patterns, (
            "%s is not in any Dependabot group; setuptools and wheel must move "
            "together because a lone bump of one produces a wheel/setuptools "
            "mismatch on the Cython path" % pkg)


def test_every_update_has_a_schedule():
    for u in _config()["updates"]:
        assert u.get("schedule", {}).get("interval"), (
            "%s has no schedule interval, so it never runs"
            % u.get("package-ecosystem"))
