"""The live tree must stay importable on the oldest supported Python.

The project claims CPython 3.10 - 3.14 support (``obfuscator/py_matrix.py``,
the README, the CI matrix).  PEP 701 (Python 3.12) allowed f-strings to
reuse the outer quote character and to contain backslashes in the
expression part; that syntax is a **SyntaxError** on 3.10 and 3.11.

Four modules used it (``obfuscator/decoy_apis.py``,
``obfuscator/llm_resilient.py``, ``obfuscator/timing_traps.py``,
``scripts/compiler_mutation.py``), so a default build died with a
SyntaxError on 3.10/3.11 even though the pipeline's own
``ast.parse(feature_version=(3, 10))`` check did not catch it -- that
check runs the *current* tokenizer, which already accepts the new syntax.

The lint gate (``ruff check`` with ``target-version = "py310"``) does
catch it; this test makes the same check part of the test suite.
"""
import os
import subprocess

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

#: Directories that hold live, hand-maintained Python.
LIVE_DIRS = ("obfuscator", "scripts", "tests", "irgen", "vm", "llvmgen",
             "encrypt")

#: Files that are deliberately not valid Python 3.10:
#:   tests/test_data/  decoy and prompt-poison fixtures (test data).
EXCLUDE = ("tests/test_data",)


def _live_python_files():
    for base in LIVE_DIRS:
        root = os.path.join(REPO_ROOT, base)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            if any(dirpath.startswith(os.path.join(REPO_ROOT, x))
                   for x in EXCLUDE):
                continue
            for fn in filenames:
                if fn.endswith(".py"):
                    yield os.path.join(dirpath, fn)
    for fn in os.listdir(REPO_ROOT):
        if fn.endswith(".py"):
            yield os.path.join(REPO_ROOT, fn)


def test_ruff_is_available():
    """The gate needs ruff; fail loudly if it is missing rather than skip.

    CI installs ruff for the lint step, so a missing ruff here means the
    environment is wrong, not that the check is inapplicable.
    """
    try:
        proc = subprocess.run(["ruff", "--version"], capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        pytest.fail("ruff is not installed: %r" % (exc,))
    assert proc.returncode == 0, proc.stderr


def test_no_python_312_only_syntax_in_live_tree():
    """No live module may use 3.12+-only f-string syntax."""
    proc = subprocess.run(
        ["ruff", "check", "--no-cache", "--target-version", "py310",
         "--select", "UP", "--output-format", "concise"] + list(LIVE_DIRS),
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
    # UP is pyupgrade's rule set; the 3.12-only f-strings are reported
    # by ruff as syntax errors, which surface on stderr and a non-zero
    # exit even when no rule matches.
    if proc.returncode != 0 and "SyntaxError" in (proc.stderr + proc.stdout):
        pytest.fail("3.12-only syntax in the live tree:\n%s"
                    % ((proc.stderr + proc.stdout)[:4000]))


def test_live_modules_parse_on_python_310():
    """Every live module must parse under 3.10 rules.

    ``ast.parse(feature_version=(3, 10))`` does NOT catch PEP 701 (the
    current tokenizer already accepts it), so this is a best-effort
    check that is complemented by the ruff gate above.
    """
    import ast
    broken = []
    for path in _live_python_files():
        try:
            ast.parse(open(path, encoding="utf-8", errors="replace").read(),
                      feature_version=(3, 10))
        except SyntaxError as exc:
            broken.append("%s:%s %s" % (os.path.relpath(path, REPO_ROOT),
                                         exc.lineno, exc.msg))
    assert not broken, "modules that do not parse as 3.10: %r" % (broken,)


def test_no_nested_quote_fstrings_in_live_tree():
    """Guard the specific 3.12-only construct directly.

    A f-string whose expression part contains a string literal with the
    SAME quote character as the f-string itself (or a backslash) is
    Python 3.12+ only.  Different quote characters are fine on 3.10.
    """
    import io
    import tokenize
    fstring_start = getattr(tokenize, "FSTRING_START", None)
    fstring_end = getattr(tokenize, "FSTRING_END", None)
    if fstring_start is None:
        # 3.12 was the first tokenizer to expose f-strings as their own
        # tokens.  On 3.10/3.11 an f-string is a single opaque STRING
        # token, so the nesting walk below cannot see inside it -- the
        # old code died with AttributeError here, on exactly the
        # interpreters this file protects.
        #
        # The parser can see it: PEP 701 syntax is a SyntaxError on these
        # interpreters.  So parse every live file here instead.  That is
        # the property the file exists to protect, checked directly, with
        # nothing skipped.
        broken = []
        for path in _live_python_files():
            src = open(path, encoding="utf-8", errors="replace").read()
            try:
                compile(src, path, "exec")
            except SyntaxError as exc:
                broken.append("%s:%s %s"
                              % (os.path.relpath(path, REPO_ROOT),
                                 exc.lineno, exc.msg))
        assert not broken, (
            "files that do not parse on this interpreter (PEP 701 "
            "f-strings are a SyntaxError before 3.12): %r" % (broken,))
        return
    offenders = []
    for path in _live_python_files():
        src = open(path, encoding="utf-8", errors="replace").read()
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            continue
        stack = []
        for tok in tokens:
            if tok.type == fstring_start:
                quote = tok.string[-1]
                if stack and stack[-1] == quote:
                    offenders.append("%s:%d %s"
                                     % (os.path.relpath(path, REPO_ROOT),
                                        tok.start[0], tok.string))
                stack.append(quote)
            elif tok.type == fstring_end:
                if stack:
                    stack.pop()
    assert not offenders, ("f-strings nested inside f-string expressions "
                           "with the same quote character (Python 3.12+ only): "
                           "%r" % (offenders,))
