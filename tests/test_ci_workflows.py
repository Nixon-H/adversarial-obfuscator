"""Tests for the CI helpers themselves, not the product.

Two of this project's bugs were self-inflicted and would have been caught here:

* a step with two ``run:`` keys -- ``yaml.safe_load`` accepts the duplicate
  silently, GitHub rejects the whole file, and the run reports **0 jobs**;
* an audit script whose checks could not fail, so a green run proved nothing.

Both are checkable without a runner, which is why they are tests and not
something only the workflow notices after a push.
"""
import os
import subprocess
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys."""


def _no_duplicates(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError("duplicate key %r on line %d"
                             % (key, key_node.start_mark.line + 1))
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def _workflow_files():
    if not os.path.isdir(WORKFLOWS):
        return []
    return [os.path.join(WORKFLOWS, n) for n in sorted(os.listdir(WORKFLOWS))
            if n.endswith((".yml", ".yaml"))]


def test_there_are_workflows_to_check():
    assert _workflow_files(), "no workflow files found; the rest of this file would be vacuous"


@pytest.mark.parametrize("path", _workflow_files(), ids=os.path.basename)
def test_workflow_parses_without_duplicate_keys(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    # A duplicate key makes GitHub reject the file and run zero jobs, while
    # yaml.safe_load accepts it. This is the check that catches that.
    data = yaml.load(text, Loader=_StrictLoader)  # noqa: S506 - strict local loader
    assert isinstance(data, dict), "%s is not a mapping" % path
    assert "jobs" in data, "%s has no jobs" % path


@pytest.mark.parametrize("path", _workflow_files(), ids=os.path.basename)
def test_every_step_has_exactly_one_of_run_or_uses(path):
    with open(path, encoding="utf-8") as handle:
        data = yaml.load(handle.read(), Loader=_StrictLoader)  # noqa: S506
    for job_name, job in (data.get("jobs") or {}).items():
        for index, step in enumerate(job.get("steps") or []):
            has_run = "run" in step
            has_uses = "uses" in step
            assert has_run or has_uses, (
                "%s job %s step %d has neither run nor uses" % (path, job_name, index))
            assert not (has_run and has_uses), (
                "%s job %s step %d has both run and uses" % (path, job_name, index))


def test_the_audit_fails_on_a_broken_artefact(tmp_path):
    """An audit that cannot fail proves nothing.

    Runs the real checker against a file that prints the wrong thing and
    requires every check to report failure.
    """
    broken = tmp_path / "broken.py"
    broken.write_text('print("not the right output")\n', encoding="utf-8")
    env = dict(os.environ, AUDIT_ARTEFACT=str(broken))
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "ci", "audit_artefact.py")],
        cwd=ROOT, capture_output=True, timeout=1800, env=env)
    out = proc.stdout.decode("utf-8", "replace")
    assert proc.returncode != 0, "the audit exited 0 against a broken artefact"
    assert "12 checks, 12 failed" in out, (
        "expected every check to fail; got:\n" + out[-2000:])


def test_one_workflow_owns_the_push_trigger_and_calls_all_the_others():
    """A push must run everything, and only one file may decide that.

    The tiers used to have their own triggers: the exhaustive flag runs were
    release-only, the deep matrix and fuzz sweep weekly-only, two tiers manual.
    What a green push proved therefore depended on which file happened to have a
    push trigger. This asserts the merged arrangement that replaces it.
    """
    import yaml

    umbrella_path = os.path.join(WORKFLOWS, "all-checks.yml")
    assert os.path.exists(umbrella_path), "the merged entry point is missing"
    umbrella = yaml.safe_load(open(umbrella_path, encoding="utf-8"))
    on = umbrella.get(True) or umbrella.get("on") or {}
    assert "push" in on, "the merged workflow must run on push"
    assert "schedule" in on, "the time-drift tiers need a scheduled trigger too"

    called = {
        job["uses"][2:] for job in umbrella["jobs"].values()
        if str(job.get("uses", "")).startswith("./.")
    }
    assert called, "the merged workflow calls nothing"

    # Everything callable must be called, except the entry point itself.
    others = {
        ".github/workflows/" + n for n in os.listdir(WORKFLOWS)
        if n.endswith(".yml") and n != "all-checks.yml"
    }
    missing = others - called
    assert not missing, "workflows never reached from a push: %s" % sorted(missing)

    # And no other file may still claim the push trigger, or a push runs twice.
    for name in sorted(os.listdir(WORKFLOWS)):
        if not name.endswith(".yml") or name == "all-checks.yml":
            continue
        data = yaml.safe_load(open(os.path.join(WORKFLOWS, name), encoding="utf-8"))
        on = data.get(True) or data.get("on") or {}
        if isinstance(on, dict):
            assert "push" not in on, (
                "%s still triggers on push; the merged workflow owns that" % name)
            assert "workflow_call" in on, "%s is not callable from the entry point" % name


def test_every_tier_runs_on_every_push():
    """A push runs all of them -- measured at 2h39m for the full 539-job set.

    The tiers were briefly gated behind the weekly schedule, on an estimate that a
    full push needed ~21 hours. That estimate came from a run BEFORE the
    max-parallel caps, which were the actual fix: with the caps in place the
    complete set finishes in 2h39m and the trimmed one in 1h42m, so gating saved
    less than an hour while cutting 322 jobs of coverage.

    This pins the arrangement the cost actually supports.
    """
    import yaml

    umbrella = yaml.safe_load(
        open(os.path.join(WORKFLOWS, "all-checks.yml"), encoding="utf-8"))
    on = umbrella.get(True) or umbrella.get("on") or {}

    assert "push" in on, "the merged workflow must run on push"

    for name, job in umbrella["jobs"].items():
        assert "if" not in job, (
            "%s is conditional; a push is supposed to run every tier" % name)

    # And every callable workflow is still reached from the entry point.
    called = {
        job["uses"][2:] for job in umbrella["jobs"].values()
        if str(job.get("uses", "")).startswith("./.")
    }
    others = {
        ".github/workflows/" + n for n in os.listdir(WORKFLOWS)
        if n.endswith(".yml") and n != "all-checks.yml"
    }
    assert not (others - called), (
        "unreachable from a push: %s" % sorted(others - called))

    # No dead dispatch input left behind.
    inputs = (on.get("workflow_dispatch") or {}).get("inputs") or {}
    assert "full" not in inputs, "the full input is gone; nothing uses it now"


def test_the_placeholder_guard_matches_by_shape_not_by_file():
    """It must catch the inert-strict-mode class from ANY module, not just two.

    The guard used to read only sources.py and pipeline.py, so a placeholder that
    originated in a third module would sail through. It was narrowed that way to
    avoid a false positive on `{LKME}`, a legitimate set literal in generated code.

    Matching on the `<PREFIX>_<NAME>` form fixes both: every real placeholder in
    this project has that shape, and a bare word like LKME never does.
    """
    import re

    pat = re.compile(r"\{([A-Z][A-Z0-9_]{2,})\}")
    prefixes = set()
    for src in ("obfuscator/core/sources.py", "obfuscator/core/pipeline.py"):
        for n in pat.findall(open(os.path.join(ROOT, src), encoding="utf-8").read()):
            if "_" in n:
                prefixes.add(n.split("_")[0])

    def flagged(text):
        return {n for n in pat.findall(text)
                if "_" in n and n.split("_")[0] in prefixes}

    assert flagged("if not {VAR_STRICT_DETECTIONS}: pass")
    assert flagged("def {FUNC_NAME}(): pass")
    # from a module the old guard never read
    assert flagged("_k = {NATIVE_BLOB_KEY_HEX}")

    # the known false positive, and other bare words, must stay clean
    assert not flagged("LKME = {LKME}")
    assert not flagged("z = {OUTPUT}")
    assert not flagged("d = {'a': 1}")
