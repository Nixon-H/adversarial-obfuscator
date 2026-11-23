"""Workflow inline-Python blocks must import every module they use.

AI-SC-001: `.github/workflows/release.yml` and `ci.yml` each contained a
`python3 - <<'PY'` acceptance block that imported
`base64, hashlib, json, os, secrets, subprocess, sys` and then called
`re.search(...)` / `re.sub(...)`. `re` was never imported, so the step raised
`NameError` AFTER the build had already run, and the release-acceptance gate
could never reach a verdict. A gate that always crashes is worse than no gate:
it is a green-looking step in the logs until someone reads the failure.

Nothing caught it because the block is a heredoc inside YAML -- no linter in
this repository parses it, and the surrounding workflow is valid YAML. This test
closes that gap by extracting every `<<'PY'` block from every workflow and
checking, with a static analysis of the AST, that each module attribute used
resolves to an import or an assignment in the same block.

Scope note: this is a STATIC check of name resolution for module-style usage
(`mod.attr`). It does not execute the blocks -- they build real artefacts and
need a release key. It therefore catches the class of defect that actually
occurred (missing import of a stdlib module used as `mod.attr`) and does not
pretend to prove the blocks are otherwise correct.
"""
import ast
import glob
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")

BLOCK_START = re.compile(r"^(\s*)python3 - <<'PY'\s*$")


def _blocks(path):
    """Yield (first_line_no, source) for each `python3 - <<'PY'` heredoc."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    i = 0
    while i < len(lines):
        m = BLOCK_START.match(lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group(1))
        start = i + 1
        body = []
        i += 1
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped == "PY":
                break
            # the heredoc body is indented at least as deep as the `run:` key
            body.append(line[indent:] if line[:indent].strip() == "" else line)
            i += 1
        yield start, "".join(body)
        i += 1


def _module_attrs_used(tree):
    """Return the set of names used as `name.attr` (i.e. module-style access)."""
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            base = node
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                used.add(base.id)
    return used


def _imported_or_bound(tree):
    """Names bound by import, assignment, function/class def, or import-from."""
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                bound.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                bound.add(a.asname or a.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        bound.add(n.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    bound.add(n.id)
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                for n in ast.walk(node.optional_vars):
                    if isinstance(n, ast.Name):
                        bound.add(n.id)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
    return bound


def _workflow_files():
    return sorted(glob.glob(os.path.join(WORKFLOWS, "*.yml"))
                  + glob.glob(os.path.join(WORKFLOWS, "*.yaml")))


@pytest.mark.parametrize("workflow", _workflow_files(),
                         ids=lambda p: os.path.basename(p))
def test_inline_python_imports_what_it_uses(workflow):
    """Every module used as `mod.attr` in a heredoc must be imported there."""
    problems = []
    for line_no, source in _blocks(workflow):
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            # A block that does not parse is its own defect, reported plainly
            # rather than skipped.
            problems.append("%s:%d inline block does not parse: %s"
                            % (os.path.basename(workflow), line_no, exc))
            continue
        imported = _imported_or_bound(tree)
        used = _module_attrs_used(tree)
        # Only complain about names that LOOK like modules: lowercase, and not
        # a locally-bound object. A false positive here would be noise that
        # trains people to ignore the test, so the check is deliberately
        # narrow: a name is suspicious only if it is used as `x.attr` and is
        # neither imported/bound nor a known local.
        for name in sorted(used - imported):
            if not name.isidentifier() or name[:1].isupper():
                continue
            # Attribute access on a name that was never bound in this block is
            # a NameError at runtime unless it is a builtin. Whitelist the two
            # builtin containers that are legitimately subscripted/attributed.
            if name in ("self", "cls"):
                continue
            problems.append(
                "%s:%d uses `%s.…` but never imports or binds `%s`"
                % (os.path.basename(workflow), line_no, name, name))
    assert not problems, (
        "workflow inline-Python blocks reference modules they never import "
        "(this is AI-SC-001, which made the release-acceptance gate raise "
        "NameError after the build):\n  " + "\n  ".join(problems))


def test_the_known_broken_import_list_is_gone():
    """Pin the specific defect: no heredoc imports that list without `re`."""
    offenders = []
    for path in _workflow_files():
        for line_no, source in _blocks(path):
            uses_re = re.search(r"\bre\.(search|sub|match|findall)\b", source)
            if not uses_re:
                continue
            tree = ast.parse(source)
            imported = _imported_or_bound(tree)
            if "re" not in imported:
                offenders.append("%s:%d" % (os.path.basename(path), line_no))
    assert not offenders, (
        "these inline blocks call re.* without importing re: %s"
        % ", ".join(offenders))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
