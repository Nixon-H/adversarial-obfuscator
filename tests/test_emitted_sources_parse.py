"""Every emitted source block must be valid Python.

The loader is assembled from dozens of `*_SOURCE` templates in
``obfuscator/core/sources.py``.  Each is a string with ``{PLACEHOLDER}``
names that are substituted at build time.  A template whose indentation is
wrong still renders — it just renders into code that does not parse, and
the artifact dies at import with a SyntaxError.

That is not hypothetical: ``ANTMAN_SOURCE`` had an ``except`` clause at
the wrong indent level, so the *pipeline* loader
(``obfuscator/core/pipeline.py::build_project``) emitted a file that
could not be parsed at all.  Nothing caught it because no test rendered a
template and parsed the result.

This test renders each template (placeholders -> dummy identifiers) and
parses it.
"""
import ast
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import obfuscator.core.sources as sources
from obfuscator.core.sources import apply_vars

#: Placeholders that are not plain identifiers (f-string braces, dict
#: literals, numeric formats).  They are neutralised before parsing.
_DUMMY = "_nx_dummy_"


def _render(text):
    """Substitute every {placeholder} with a dummy identifier."""
    text = apply_vars(text)
    # str.format-style escapes first, then any remaining {name}.
    text = text.replace("{{", "{").replace("}}", "}")
    text = re.sub(r"\{[^{}]*\}", _DUMMY, text)
    # f-strings in the templates may contain {res} style holes; those are
    # already covered above.
    return text


def _is_cython(text):
    """True for Cython/C source blocks, which are not Python."""
    return ("cimport " in text) or ("cdef " in text) or ("#include <" in text)


def _source_constants():
    names = [n for n in dir(sources)
             if n.endswith("_SOURCE") or n.endswith("_SOURCE_BODY")]
    return sorted(names)


@pytest.mark.parametrize("name", _source_constants())
def test_emitted_source_block_parses(name):
    block = getattr(sources, name)
    if not isinstance(block, str):
        pytest.skip("%s is not a string" % (name,))
    if _is_cython(block):
        pytest.skip("%s is a Cython/C block, not Python" % (name,))
    rendered = _render(block)
    try:
        ast.parse(rendered)
    except SyntaxError as exc:
        pytest.fail("%s renders to invalid Python: %s (line %s)\n%s"
                    % (name, exc.msg, exc.lineno, _excerpt(rendered, exc.lineno)))


def _excerpt(text, lineno, span=3):
    lines = text.splitlines()
    lo = max(0, (lineno or 1) - span - 1)
    hi = min(len(lines), lo + span * 2 + 1)
    return "\n".join("    %4d | %s" % (i + 1, lines[i])
                     for i in range(lo, hi))


def test_loader_body_renders_to_valid_python():
    """The two loader templates must render into parseable code."""
    from obfuscator.core.sources import LOADER_BODY, LOADER_HEAD
    for name, block in (("LOADER_HEAD", LOADER_HEAD), ("LOADER_BODY", LOADER_BODY)):
        rendered = _render(block)
        try:
            ast.parse(rendered)
        except SyntaxError as exc:
            pytest.fail("%s renders to invalid Python: %s (line %s)\n%s"
                        % (name, exc.msg, exc.lineno,
                           _excerpt(rendered, exc.lineno)))
