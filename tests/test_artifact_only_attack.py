"""The artifact-only attacker must not touch evaluator information.

The repository's static attack develops against the original source and
confirms candidates with the target's test vectors. Both are evaluator
information: a real attacker holding only an emitted artefact has neither.
That is why its success rate cannot support a resilience claim -- it
measures its own oracle (found in the 2026-10-30 review and confirmed in
code).

This guard keeps the replacement honest. It fails if the artifact-only
arm ever acquires a reference to ground truth, test vectors, or the
original source, and it fails if apply() returns a semantically confirmed
map rather than a ranking.

A textual check rather than a behavioural one, deliberately: the failure
mode being guarded against is a future edit that imports an oracle for
convenience, and that is visible in the source far more reliably than in
any single run.
"""

import ast
import os

import pytest

ATTACK = os.path.join(os.path.dirname(__file__), "..", "scripts", "transfer", "attack.py")


def _class_code(name):
    """The class's CODE, with docstrings removed.

    The docstring has to explain what the arm must not do, so it mentions
    ground truth and vectors; checking prose would fail on its own
    documentation. Strip string constants and check only the code.
    """
    text = open(ATTACK, encoding="utf-8").read()
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    body = sub.body
                    if body and isinstance(body[0], ast.Expr) and isinstance(
                        body[0].value, ast.Constant
                    ) and isinstance(body[0].value.value, str):
                        sub.body = body[1:] or [ast.Pass()]
            return ast.unparse(ast.Module(body=[node], type_ignores=[]))
    pytest.fail("class %s not found in attack.py" % name)


def test_artifact_only_attack_never_reads_ground_truth():
    src = _class_code("ArtifactOnlyAttack")
    assert "ground_truth" not in src, (
        "the artifact-only attacker referenced ground truth; that makes it "
        "an oracle-assisted attacker and invalidates its success rate"
    )


def test_artifact_only_attack_never_reads_test_vectors():
    src = _class_code("ArtifactOnlyAttack")
    assert "vectors" not in src, (
        "the artifact-only attacker referenced the evaluator's test vectors"
    )


def test_artifact_only_attack_never_reads_the_original_source():
    src = _class_code("ArtifactOnlyAttack")
    assert "original_source" not in src, (
        "the artifact-only attacker referenced the clean source"
    )


def test_artifact_only_attack_returns_a_ranking_not_a_confirmed_map():
    src = _class_code("ArtifactOnlyAttack")
    assert "ranking" in src, (
        "apply() must return a ranking for the evaluator to score; a "
        "confirmed mapping implies the attacker could verify candidates, "
        "which requires an oracle"
    )


def test_artifact_only_develop_takes_no_source_argument():
    tree = ast.parse(open(ATTACK, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ArtifactOnlyAttack":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "develop":
                    args = [a.arg for a in item.args.args]
                    assert args == ["self", "build", "workdir"], (
                        "develop() must take only the build: an extra "
                        "argument is an oracle channel. got %r" % (args,)
                    )
                    return
    pytest.fail("ArtifactOnlyAttack.develop not found")
