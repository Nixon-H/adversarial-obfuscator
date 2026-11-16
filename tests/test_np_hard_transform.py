"""NP-hard opaque predicates and MBA substitution: the advanced C transforms.

These transforms make the C source exponentially harder to reverse:

* subset-sum predicates require the analyst to recognise and solve a
  subset-sum instance embedded in the generated C;
* multi-round MBA substitution creates nested boolean-arithmetic expressions
  that require exponential work to simplify back to the original constant.

Both are polymorphic per build: the subset-sum instance and the MBA
decomposition are randomised per build seed.
"""
import re


from scripts.c_transform import (
    generate_subset_sum_instance, insert_subset_sum_predicates,
    transform_c, _mba_substitute_constant,
)

CYX_C = r'''
#include "Python.h"
static char __pyx_k_key[] = "secret_key_data";
static char __pyx_k_url[] = "https://api.example.com/v2";

static int __pyx_f_1f(int x) {
  int result = 0;
  if (x > 0) {
    result = 1;
  }
  return result;
}
'''

SEED = b"np-hard-test-seed"


def test_subset_sum_instance_is_solvable():
    inst = generate_subset_sum_instance(b"test", n=8)
    assert inst["target"] > 0
    assert len(inst["set"]) == 8
    # The target must be achievable from the set (we constructed it).
    mask = inst["mask"]
    achieved = sum(v for i, v in enumerate(inst["set"]) if mask & (1 << i))
    assert achieved == inst["target"]


def test_subset_sum_predicates_are_emitted():
    new, count = insert_subset_sum_predicates(CYX_C, SEED, __import__("random").Random(42), count=3)
    assert count >= 2
    assert "__nx_ss_check" in new
    assert "__nx_ss_set_00" in new
    # The set arrays must contain the actual values (not encrypted).
    assert re.search(r"static const unsigned __nx_ss_set_\d+\[\] = \{\d+", new)


def test_subset_sum_predicate_wraps_if_conditions():
    new, count = insert_subset_sum_predicates(CYX_C, SEED, __import__("random").Random(42), count=3)
    # At least one `if` should be wrapped with a subset-sum predicate.
    assert "__nx_ss_check(" in new
    assert count > 0


def test_subset_sum_is_polymorphic():
    a, _ = insert_subset_sum_predicates(CYX_C, b"seed-a", __import__("random").Random(1), count=2)
    b, _ = insert_subset_sum_predicates(CYX_C, b"seed-b", __import__("random").Random(2), count=2)
    assert a != b, "different seeds produced the same subset-sum predicates"


def test_mba_substitution_creates_nested_expressions():
    rng = __import__("random").Random(42)
    expr = _mba_substitute_constant(42, rng, rounds=3)
    # The expression must evaluate to 42.
    assert eval(expr) == 42
    # Multi-round should be longer than the raw constant.
    assert len(expr) > 10


def test_mba_is_polymorphic():
    rng1 = __import__("random").Random(1)
    rng2 = __import__("random").Random(2)
    a = _mba_substitute_constant(100, rng1, rounds=2)
    b = _mba_substitute_constant(100, rng2, rounds=2)
    assert eval(a) == 100 and eval(b) == 100
    assert a != b, "different RNG produced the same MBA expression"


def test_negative_constants_are_handled():
    rng = __import__("random").Random(42)
    expr = _mba_substitute_constant(-42, rng, rounds=2)
    assert eval(expr) == -42


def test_zero_is_not_substituted():
    rng = __import__("random").Random(42)
    assert _mba_substitute_constant(0, rng, rounds=3) == "0"


def test_full_transform_includes_new_transforms():
    result = transform_c(CYX_C, b"np-hard", do_subset_sum=True, do_mba=True)
    assert result.ss_predicates > 0
    assert result.mba_substituted > 0
    assert result.transforms_applied


def test_full_transform_compiles():
    import subprocess
    import sysconfig

    result = transform_c(CYX_C, b"np-hard-compile")
    py_inc = sysconfig.get_paths()["include"]
    out = "/tmp/test_np_hard.c"
    with open(out, "w") as fh:
        fh.write(result.source)
    proc = subprocess.run(
        ["gcc", "-fsyntax-only", "-std=c99", "-I", py_inc, out],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, (
        "transformed C does not compile:\n%s\n---\n%s"
        % (proc.stderr[:800], result.source[:400]))
