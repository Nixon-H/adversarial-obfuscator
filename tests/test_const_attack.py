"""Tests for the constant-literal attack (v2.0, T_const_split).

Gate-keeping tests assert instrument properties (type tagging, determinism,
flattening per amendment 2, hit-rate arithmetic, sensitivity). Cross-arm
NUMBERS belong to the experiment run, not to tests.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.transfer import arms as A
from scripts.transfer import const_attack as K
from scripts.diversity.generator import DiversityGenerator

# 60 primes in (1, 1000): a literal-rich program whose list display the
# compiler folds into one tuple constant. Amendment 1 would see none.
PRIMES = [101, 103, 107, 109, 113, 127, 131, 137, 139, 149,
          151, 157, 163, 167, 173, 179, 181, 191, 193, 197,
          199, 211, 223, 227, 229, 233, 239, 241, 251, 257,
          263, 269, 271, 277, 281, 283, 293, 307, 311, 313,
          317, 331, 337, 347, 349, 353, 359, 367, 373, 379,
          383, 389, 397, 401, 409, 419, 421, 431, 433, 439]


def _fixture_source():
    body = ", ".join(str(p) for p in PRIMES)
    return (
        "def values():\n"
        "    return [%s]\n"
        "\n"
        "\n"
        "def label():\n"
        "    return \"alpha-beta-gamma\"\n" % body
    )


def _build(src_path, options, seed):
    cfg = {
        "master_seed": seed,
        "pass_sets": [["rename"]],
        "extra_options": dict(A.ISOLATION_OFF, **options),
    }
    gen = DiversityGenerator(config=cfg)
    with tempfile.TemporaryDirectory(prefix="nxk_const_test_") as td:
        path = gen.generate(str(src_path), 1, td)[0]
        with open(path, encoding="utf-8") as fh:
            return fh.read()


# --- type tagging -------------------------------------------------------

def test_bool_is_not_a_literal():
    prof = K.extract("def f():\n    return (True, False, 1)\n")
    assert prof["ok"]
    # True == 1 and False == 0; tagging must not let them in as ints.
    assert prof["by_tag"]["i"] == {1}


def test_int_and_float_do_not_collapse():
    prof = K.extract("def f():\n    return (1, 1.0)\n")
    assert prof["by_tag"]["i"] == {1}
    assert prof["by_tag"]["f"] == {1.0}
    assert ("i", 1) in prof["values"]
    assert ("f", 1.0) in prof["values"]


def test_short_strings_and_code_objects_are_dropped():
    prof = K.extract("def f():\n    x = 'a'\n    return 'ok'\n")
    assert prof["by_tag"]["s"] == {"ok"}


def test_uncompilable_source_is_reported():
    prof = K.extract("def broken(:\n")
    assert prof["ok"] is False
    assert "uncompilable" in prof["reason"]


# --- amendment 2: folded sequences -------------------------------------

def test_folded_sequence_is_flattened():
    src = "def f():\n    return [101, [103, 107], (109, 113)]\n"
    prof = K.extract(src)
    assert prof["ok"]
    assert prof["by_tag"]["i"] >= {101, 103, 107, 109, 113}

    legacy = K.extract(src, flatten=False)
    # The tuple element stays folded in co_consts; amendment 1 dropped it.
    assert legacy["by_tag"]["i"] == {101, 103, 107}
    assert prof["by_tag"]["i"] - legacy["by_tag"]["i"] == {109, 113}


def test_flatten_is_recursive_and_excludes_container_itself():
    src = "def f():\n    return [[[7, 11]]]\n"
    prof = K.extract(src)
    assert prof["by_tag"]["i"] == {7, 11}
    # The tuple container is not itself a tagged literal.
    assert all(not isinstance(v, tuple) for _, v in prof["values"])


# --- scoring ------------------------------------------------------------

def test_self_score_is_one():
    s, total, hits, status = K.self_score(_fixture_source())
    assert status == "ok"
    assert total == len(PRIMES) + 1        # 60 ints + one string
    assert hits == total
    assert abs(s - 1.0) < 1e-12


def test_hit_rate_arithmetic():
    p_i = "def f():\n    return (10, 20, 30)\n"
    b_j = "def f():\n    return (10, 20, 40)\n"
    s, total, hits = K.score(K.extract(p_i), K.extract(b_j))
    assert (s, total, hits) == (2 / 3, 3, 2)


def test_type_subset_scoring_uses_matching_denominator():
    p_i = "def f():\n    return (10, 20, 'aa')\n"
    b_j = "def f():\n    return (10, 'bb')\n"
    prof_i, prof_j = K.extract(p_i), K.extract(b_j)
    assert K.score(prof_i, prof_j, tag="i") == (0.5, 2, 1)
    assert K.score(prof_i, prof_j, tag="s") == (0.0, 1, 0)


def test_empty_subset_is_not_measurable():
    p_i = K.extract("def f():\n    return 3\n")
    b_j = K.extract("def f():\n    return 4\n")
    assert K.score(p_i, b_j, tag="s") == (None, 0, 0)


# --- sensitivity: the instrument can see hiding ------------------------

def test_unfold_constants_lowers_int_recovery(tmp_path):
    src_path = tmp_path / "literal_rich.py"
    src_path.write_text(_fixture_source(), encoding="utf-8")
    source = _fixture_source()
    source_prof = K.extract(source)
    assert len(source_prof["by_tag"]["i"]) == len(PRIMES)

    # Control: renaming alone must not move the literal pool.
    c0 = _build(src_path, {}, 7001)
    s_int, n_int, hits = K.score(source_prof, K.extract(c0), tag="i")
    assert (s_int, n_int, hits) == (1.0, len(PRIMES), len(PRIMES))

    # 30% of eligible ints are rewritten; only the `sum([parts])` branch
    # survives bytecode constant folding, so ~10% of the pool moves per
    # build. Four seeds make a zero-move run astronomically unlikely.
    seen = []
    for seed in (7001, 7002, 7003, 7004):
        built = _build(src_path, {"unfold_constants": True}, seed)
        s_int, _, _ = K.score(source_prof, K.extract(built), tag="i")
        s_str, n_str, _ = K.score(source_prof, K.extract(built), tag="s")
        seen.append(s_int)
        # Specificity control: no arm touches string literals.
        assert n_str == 1
        assert abs(s_str - 1.0) < 1e-12
    assert min(seen) < 1.0


def test_rebuild_same_seed_is_deterministic(tmp_path):
    src_path = tmp_path / "literal_rich.py"
    src_path.write_text(_fixture_source(), encoding="utf-8")
    a = _build(src_path, {"unfold_constants": True}, 7101)
    b = _build(src_path, {"unfold_constants": True}, 7101)
    assert a == b
