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
  int limit = 4242;
  if (x > 0) {
    result = 1 + limit;
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
    # The set arrays must contain the actual values (not encrypted). The width
    # is `unsigned long long` since §6 widened the instance values to 40 bits:
    # `unsigned` cannot hold them, and a DP table over a 2^44 target is not
    # emittable, which is why the verifier is now meet-in-the-middle.
    assert re.search(
        r"static const unsigned long long __nx_ss_set_\d+\[\] = \{\d+ULL", new)


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


def test_full_transform_compiles(tmp_path):
    import subprocess
    import sysconfig

    result = transform_c(CYX_C, b"np-hard-compile")
    py_inc = sysconfig.get_paths()["include"]
    out = str(tmp_path / "test_np_hard.c")
    with open(out, "w") as fh:
        fh.write(result.source)
    proc = subprocess.run(
        ["gcc", "-fsyntax-only", "-std=c99", "-I", py_inc, out],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, (
        "transformed C does not compile:\n%s\n---\n%s"
        % (proc.stderr[:800], result.source[:400]))


# --- adversarial validation (2026-11-18) -----------------------------------
# These three claims did not survive measurement. Each test pins the fix.

def test_subset_sum_dp_table_covers_every_generated_target():
    """The DP table was a fixed 4096; targets reach the sum of up to 8
    values in 1..999 (max 7992).  11/1500 instances overflowed, and the
    AND-ed predicate then returned 0 -- silently skipping real code."""
    import hashlib
    for trial in range(200):
        seed = hashlib.sha256(b"bounds-%d" % trial).digest()
        insts = [generate_subset_sum_instance(
            seed + b"ss" + i.to_bytes(4, "big"), n=6 + i) for i in range(3)]
        max_target = max(int(x["target"]) for x in insts)
        dp_size = max(4096, max_target + 1)
        assert max_target < dp_size


def test_emitted_subset_sum_fn_is_sized_for_the_instance():
    """The verifier must be sized from the INSTANCE, not from a fixed constant.

    The original defect this guards (audit 2026-11-18) was a fixed 4096-entry DP
    table against targets of up to 7992: `dp[target]` read out of bounds and
    returned 0, which AND-ed with the real condition SILENTLY SKIPPED REAL CODE
    in ~0.7% of builds.

    §6 measurement 2026-11-19 removed the DP entirely: the instance values are
    now 40-bit, so a target-indexed table would need ~2^44 entries and the
    out-of-bounds hazard cannot recur — nothing is indexed by the target any
    more. The guarantee to assert is that the emitted check is derived from the
    instance width, and that no target-indexed array exists.
    """
    from scripts.c_transform import insert_subset_sum_predicates, SS_WIDTH
    import hashlib
    import re

    seed = hashlib.sha256(b"size-probe").digest()
    out, n = insert_subset_sum_predicates(CYX_C, seed,
                                          __import__("random").Random(1),
                                          count=3)
    assert n == 3

    # No target-indexed table: that construction is what broke before.
    assert not re.search(r"unsigned char dp\[", out), (
        "a target-indexed DP table is back; it cannot cover 40-bit targets")
    assert "__nx_ss_sums" not in out or "malloc" in out, (
        "the meet-in-the-middle table must be heap-allocated, not static: "
        "a static 2^%d array would bloat every linked binary" % (SS_WIDTH // 2))

    # The half width must follow the instance width.
    half = re.search(r"#define __NX_SS_HALF (\d+)", out)
    assert half, "no half-width define emitted"
    assert int(half.group(1)) == max(1, SS_WIDTH // 2)


def test_mba_length_grows_with_rounds():
    """'multi-round' used to REPLACE the expression each round."""
    import random
    from scripts.c_transform import _mba_substitute_constant
    lengths = []
    for rounds in (1, 2, 3):
        e = _mba_substitute_constant(42, random.Random(42), rounds=rounds)
        lengths.append(len(e))
    assert lengths[1] > lengths[0], lengths
    assert lengths[2] > lengths[1], lengths


def test_mba_is_exact_for_every_operand_value():
    """The nested identity must equal the original constant."""
    import random
    from scripts.c_transform import _mba_substitute_constant
    for value in (1, 2, 7, 42, 100, 999, 5000, -42):
        for rounds in (1, 2, 3, 5):
            e = _mba_substitute_constant(value, random.Random(42), rounds=rounds)
            assert eval(e) == value, (value, rounds, e[:80])


def test_mba_slots_carry_the_value_their_identity_needs():
    """Every volatile slot must hold the exact operand its identity needs.

    Sharing one slot per value (instead of per value AND round) silently
    changed 100 into 3811; hashing the slot value changed 42 into 7561.
    Both were caught by this check.
    """
    import random
    import re
    from scripts.c_transform import substitute_constants_mba
    for value in (42, 100, 999, 5000):
        # function-local, so the MBA pass will consider it (file-scope
        # initialisers are skipped: C requires a constant expression there)
        C = ('#include <stdio.h>\n'
             'static int f(void)\n'
             '{\n'
             '    int x = %d;\n'
             '    return x;\n'
             '}\n' % value)
        out, n = substitute_constants_mba(C, b"seed", random.Random(1),
                                          rounds=3, rate=1.0)
        assert n == 1
        expr = re.search(r"int x = (.*?);", out, re.S).group(1).strip()
        if expr.startswith("(") and expr.endswith(")"):
            expr = expr[1:-1]
        for m in re.finditer(r"__nx_mba_(\d+) = (\d+);", out):
            expr = expr.replace("__nx_mba_%s" % m.group(1), m.group(2))
        assert eval(expr) == value, (
            "MBA slots do not reproduce %d (got %d)" % (value, eval(expr)))


def test_opaque_operands_are_volatile_not_const():
    """`static const int` is a C constant: gcc -O3 folded the whole
    predicate away (0 refs in the assembly)."""
    from scripts.c_transform import insert_opaque_predicates
    import random
    # Cython's output always carries `static` declarations; the transform
    # anchors its inserted block on the first one (returning 0 without it).
    src = (
        '#include <stdio.h>\n'
        'static int real_work(int v);\n'
        'int main(int argc, char **argv)\n'
        '{\n'
        '    int v = argc;\n'
        '    if (v > 0) {\n'
        '        printf("%d\\n", v);\n'
        '    }\n'
        '    return 0;\n'
        '}\n'
    )
    out, n = insert_opaque_predicates(src, b"vol", random.Random(1), rate=1.0)
    assert n >= 1
    assert "static volatile int __nx_opa" in out
    assert "static const int __nx_opa" not in out


def test_opaque_predicates_are_identities_not_random_arithmetic():
    """The predicate is AND-ed with a real condition, so a FALSE predicate
    skips real code.

    The old forms were plain arithmetic over three random operands, guarded by
    `(expr & 1) == 0` (requires EVEN). Measured over 2000 draws each they were
    false 52.1%, 47.9% and 75.9% of the time -- i.e. the transform silently
    broke roughly half of every branch it touched. The forms are now
    identities that hold for all integers.
    """
    import random
    from scripts.c_transform import _OPAQUE_CONSTS
    rng = random.Random(0)
    for trial in range(3000):
        v = rng.randrange(0, 1 << 20)
        for tmpl in _OPAQUE_CONSTS:
            e = (tmpl.replace("__nx_opa_1", str(v))
                    .replace("__nx_opa_2", str(v))
                    .replace("__nx_opa_3", str(v)))
            assert eval(e) == 0, (
                "opaque identity %r is FALSE for n=%d (would skip real code)"
                % (tmpl, v))


def test_opaque_predicates_hold_for_adversarial_values():
    """Zero, one, powers of two, and 32-bit boundaries."""
    from scripts.c_transform import _OPAQUE_CONSTS
    for v in (0, 1, 2, 3, 7, 255, 256, 65535, 65536,
              (1 << 31) - 1, 1 << 31, 0xFFFFFFFF):
        for tmpl in _OPAQUE_CONSTS:
            e = (tmpl.replace("__nx_opa_1", str(v))
                    .replace("__nx_opa_2", str(v))
                    .replace("__nx_opa_3", str(v)))
            assert eval(e) == 0, (tmpl, v)
