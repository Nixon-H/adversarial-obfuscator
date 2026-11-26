"""§7 workflow/action identities — the last in-session-closable provenance gap.

The register's §7 asks the manifest to bind nine things. Eight were already
recorded; the ninth, "workflow and action identities", was absent because a
LOCAL build genuinely cannot know which CI run produced an artefact.

The distinction that makes this closable: a local build's honest answer is
`null` ("no CI ran"), which is a FACT -- not the same as a forgotten field.
GitHub Actions exports the workflow and run identity in the environment, so a
CI build can record it, and the manifest does.

These tests pin both cases, because a field that is only ever exercised in CI
would be untested on every developer machine, and a field that is only ever
tested locally would never be tested at all.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator.build_manifest import (  # noqa: E402
    _CI_IDENTITY_ENV, _ci_identity, build_manifest,
)

CI_VARS = [var for _key, var in _CI_IDENTITY_ENV]


@pytest.fixture
def clean_ci_env(monkeypatch):
    """Remove every CI variable so the absent case is genuinely absent."""
    for var in CI_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def _manifest(tmp_path):
    art = tmp_path / "payload.py"
    art.write_text("X = 1\n", encoding="utf-8")
    return build_manifest(str(art), transforms=["data"])


# ── absent case: a local build records null, not a missing field ──────

def test_a_local_build_records_null_not_an_absent_field(clean_ci_env,
                                                        tmp_path):
    """`ci: null` is a FACT ("no CI"), not a gap.

    If the key were omitted entirely, a reader could not tell "built locally"
    from "someone forgot to record it". That is the same distinction the pack
    record makes with `format_version: null`.
    """
    manifest = _manifest(tmp_path)
    assert "ci" in (manifest.get("build") or {}), (
        "the build block must always carry the ci key, even when null")
    assert manifest["build"]["ci"] is None


def test_the_helper_returns_none_when_nothing_is_set(clean_ci_env):
    assert _ci_identity() is None


# ── present case: the CI identity is recorded ─────────────────────────

def test_a_ci_build_records_the_workflow_identity(clean_ci_env, tmp_path):
    clean_ci_env.setenv("GITHUB_WORKFLOW", "ci.yml")
    clean_ci_env.setenv("GITHUB_RUN_ID", "12345")
    clean_ci_env.setenv("GITHUB_SHA", "a" * 40)
    clean_ci_env.setenv("GITHUB_JOB", "build")

    ci = _manifest(tmp_path)["build"]["ci"]
    assert ci is not None, "a CI build must record its identity"
    assert ci["workflow"] == "ci.yml"
    assert ci["run_id"] == "12345"
    assert ci["sha"] == "a" * 40
    assert ci["job"] == "build"


def test_every_named_variable_is_captured(clean_ci_env, tmp_path):
    """Each variable in the mapping must reach the manifest under its key."""
    for key, var in _CI_IDENTITY_ENV:
        clean_ci_env.setenv(var, "value-%s" % (key,))
    ci = _manifest(tmp_path)["build"]["ci"]
    for key, _var in _CI_IDENTITY_ENV:
        assert ci.get(key) == "value-%s" % (key,), (
            "the manifest does not record %r from its environment variable"
            % (key,))


def test_blank_values_are_not_recorded(clean_ci_env, tmp_path):
    """An empty variable is the same as an unset one, not an empty string.

    Recording `workflow: ""` would claim CI ran and told us the workflow name
    was the empty string, which is a different (and false) claim.
    """
    clean_ci_env.setenv("GITHUB_WORKFLOW", "   ")
    clean_ci_env.setenv("GITHUB_RUN_ID", "")
    assert _ci_identity() is None, (
        "whitespace-only or empty CI variables must be treated as unset")


def test_the_record_does_not_invoke_anything(clean_ci_env, tmp_path,
                                             monkeypatch):
    """Reading the identity must be a pure environment read.

    A helper that shelled out to `gh` or made a network call would make the
    build depend on network reachability, and would leak the build to a third
    party. Asserted by making subprocess explode.
    """
    import subprocess
    clean_ci_env.setenv("GITHUB_RUN_ID", "999")

    def boom(*_a, **_k):
        raise AssertionError("_ci_identity must not spawn a process")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    assert _ci_identity() == {"run_id": "999"}


# ── §7 is now fully recorded ──────────────────────────────────────────

def test_the_manifest_records_all_section7_fields(clean_ci_env, tmp_path):
    """The whole §7 list a bare build_manifest() records, in one place, so a
    regression names its field. The ninth field, pack format version, is written
    by the pipeline (extra.pack), not build_manifest; it is pinned by
    tests/test_manifest_pack_version.py."""
    manifest = _manifest(tmp_path)
    tool = manifest.get("toolchain") or {}
    build = manifest.get("build") or {}

    recorded = {
        "compiler/linker identity": bool(tool.get("gcc") or tool.get("ld")),
        "toolchain versions": bool(tool.get("python")),
        "build flags/configuration": isinstance(
            manifest.get("transforms"), list),
        "workflow/action identities": "ci" in build,
        "target OS/architecture": bool(tool.get("platform")
                                       and tool.get("machine")),
        "dependency-lock digest": "dependency_lock_digest" in build,
        "final artifact digest": bool((manifest.get("artefact") or {})
                                      .get("sha256")),
        "protection level": manifest.get("protection_level") is not None,
    }
    missing = [k for k, v in recorded.items() if not v]
    assert not missing, "the manifest no longer records: %r" % (missing,)
    # NOTE on "pack format version": it is written by the PIPELINE at build
    # time (extra.pack), not by build_manifest itself, so a bare
    # build_manifest() call cannot see it. The gate exercises the pipeline
    # path; tests/test_manifest_pack_version.py pins that field's shape.
