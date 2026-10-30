"""A dataclass with plain fields must survive obfuscation intact.

The annotation-stripping pass removed valueless AnnAssign statements. In a
dataclass those annotations ARE the fields, so a class whose body was all
annotations became either invalid Python (`class X:` followed by a def) or a
fieldless class that constructs wrongly.

Found by running the obfuscator over an external module for the first time
(`more_itertools.recipes`, round 83). Every fixture in this repository was
written by one author and none used a bare-annotation dataclass, so internal
tests could not have found it.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.diversity.generator import generate_variant

MINIMAL = '''from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Stats:
    count: int
    total: float


def use(s):
    return s.count
'''


@pytest.mark.parametrize("build_index", [0, 2, 4])
def test_generated_code_compiles(build_index):
    code = generate_variant(MINIMAL, build_index, {"master_seed": 4242})
    compile(code, "<generated>", "exec")     # raises SyntaxError on regression


@pytest.mark.parametrize("build_index", [0, 2, 4])
def test_dataclass_keeps_its_fields(build_index):
    code = generate_variant(MINIMAL, build_index, {"master_seed": 4242})
    ns = {}
    exec(compile(code, "<generated>", "exec"), ns)
    classes = [v for v in ns.values() if isinstance(v, type)
               and hasattr(v, "__dataclass_fields__")]
    assert classes, "the dataclass disappeared entirely"
    fields = set(classes[0].__dataclass_fields__)
    assert fields == {"count", "total"}, (
        "dataclass lost fields: %r. Compiling is not enough; a fieldless "
        "dataclass constructs wrongly." % (fields,)
    )


def test_a_class_with_only_a_docstring_still_compiles():
    src = 'class Empty:\n    """Nothing here."""\n'
    for build_index in (0, 2, 4):
        code = generate_variant(src, build_index, {"master_seed": 4242})
        compile(code, "<generated>", "exec")
