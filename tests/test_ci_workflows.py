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


def test_the_heaviest_tiers_are_not_on_every_push():
    """536 jobs per push starved the pool; the 340 heaviest now run weekly.

    Measured before the split: tier B advanced ~2 jobs per 20 minutes, so a single
    push needed about 21 hours to finish. A per-push gate that never completes
    proves less than a weekly one that does -- and the failures it was supposed to
    catch never surfaced, because the run never got to them.

    Everything is still reachable: the weekly schedule and workflow_dispatch (with
    full: true) run the complete set.
    """
    import yaml

    umbrella = yaml.safe_load(
        open(os.path.join(WORKFLOWS, "all-checks.yml"), encoding="utf-8"))
    on = umbrella.get(True) or umbrella.get("on") or {}

    heavy = {"flag-all-platforms", "flag-all-pythons", "flag-exhaustive"}
    for name in heavy:
        job = umbrella["jobs"][name]
        assert "if" in job, "%s must be conditional or it floods every push" % name
        assert "github.event_name" in job["if"], (
            "%s must key off the trigger, not a flag that is always true" % name)

    # The light tiers still run on every push.
    for name in ("ci", "build", "cross-platform", "portable-matrix", "flag-isolation"):
        assert "if" not in umbrella["jobs"][name], (
            "%s must keep running on every push" % name)

    # And a dispatch can ask for everything.
    inputs = (on.get("workflow_dispatch") or {}).get("inputs") or {}
    assert "full" in inputs, "there must be a way to request the complete set"
