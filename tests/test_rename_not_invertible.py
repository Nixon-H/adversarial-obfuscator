"""Renamed identifiers must not be a hash of the name they replaced.

Regression for the 2026-11-14 bench finding. The `dynamic_unbounds` branch of
`SymbolRenamer` spelled a renamed name as ``_nx_`` + ``md5(original)[:6]``, and
`UnicodeIdentifierEncoder._encode_name` derived its homoglyph spelling from
``md5(original)`` the same way. Both are stable within a build, which is what
the passes need, but both are also a lookup table over candidate names: an
attacker who captures the payload (the audit-hook route does capture it) can
run a word list through the same hash and read the original names straight
back out.

Measured before the fix, against the bench artefact's own payload: a 60-word
list recovered 10 of the 12 original top-level names.

The fix keys the derivation with a per-build secret. These tests pin the two
properties that matter and the one that must not regress:

* stable within a build (both renamers, repeated visits);
* not recoverable from the build (no bare hash of the original name);
* still per-build, so two builds do not share a mapping.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.transforms import SymbolRenamer, UnicodeIdentifierEncoder

# The bench payload's original top-level names, plus the two the pre-fix
# artefact happened not to route through the hash branch.
_ORIGINAL_NAMES = [
    "Descriptor", "Holder", "Point", "cached", "slow_square", "evens",
    "classify", "walrus_count", "eg_sum", "make_counter", "deliver", "main",
]

# A word list an attacker would plausibly try, including every original name.
_ATTACK_WORDS = sorted(set(_ORIGINAL_NAMES + """
norm wrapper bump count values limit point fn args init get set value slot
square squares match origin walrus except_star closure dataclass async
run start process handle compute render parse validate
""".split()))


def _renamer_for(names):
    renamer = SymbolRenamer()
    renamer.dynamic_unbounds = set(names)
    return renamer


def _md5_spelling(name):
    return "_nx_" + hashlib.md5(name.encode()).hexdigest()[:6]


def test_dynamic_unbounds_rename_is_not_a_bare_hash_of_the_original():
    """The exact defect: `_nx_` + md5(name)[:6] is invertible with a word list."""
    renamer = _renamer_for(_ORIGINAL_NAMES)
    for name in _ORIGINAL_NAMES:
        renamed = renamer.get_new_name(name)
        assert renamed != _md5_spelling(name), (
            f"{name} was renamed to {renamed}, which is md5({name})[:6] -- "
            "anyone holding the payload can invert that with a word list"
        )


def test_dictionary_attack_recovers_no_original_name():
    """Replays the bench attack: hash every candidate, match against the build."""
    renamer = _renamer_for(_ORIGINAL_NAMES)
    produced = {renamer.get_new_name(n) for n in _ORIGINAL_NAMES}

    recovered = {}
    for candidate in _ATTACK_WORDS:
        spelling = _md5_spelling(candidate)
        if spelling in produced:
            recovered[spelling] = candidate

    assert recovered == {}, (
        "a word list recovered original names from the renamed payload: "
        f"{recovered}"
    )


def test_dynamic_unbounds_rename_is_stable_within_one_build():
    """Both renamers and repeated visits must agree, or defs desync from uses."""
    renamer = _renamer_for(_ORIGINAL_NAMES)
    first = {name: renamer.get_new_name(name) for name in _ORIGINAL_NAMES}
    second = {name: renamer.get_new_name(name) for name in _ORIGINAL_NAMES}
    assert first == second, "the same renamer produced two spellings for one name"

    # A fresh renamer is a fresh build: it must not reproduce the mapping.
    other = _renamer_for(_ORIGINAL_NAMES)
    third = {name: other.get_new_name(name) for name in _ORIGINAL_NAMES}
    assert third != first, (
        "two independent builds produced the same rename mapping; the "
        "derivation is not keyed per build"
    )


def test_rename_key_is_per_instance_not_a_module_constant():
    """A module-level key would make every build share one mapping."""
    a = SymbolRenamer()
    b = SymbolRenamer()
    assert a._rename_key != b._rename_key, (
        "two SymbolRenamer instances share a rename key; every build would "
        "then share one mapping"
    )
    ea = UnicodeIdentifierEncoder()
    eb = UnicodeIdentifierEncoder()
    assert ea._rename_key != eb._rename_key, (
        "two UnicodeIdentifierEncoder instances share a rename key"
    )


def test_encoder_spelling_is_not_a_bare_hash_of_the_original():
    """Same defect in the homoglyph encoder, which also derived from md5(name)."""
    encoder = UnicodeIdentifierEncoder()
    for name in ("evens", "classify", "walrus_count", "slow_square"):
        spelling = encoder._encode_name(name)
        assert spelling == encoder._encode_name(name), "encoder is not stable"
        # The pre-fix spelling was a pure function of md5(name); reproduce it
        # and require the build to differ.
        digest = hashlib.md5(name.encode()).hexdigest()
        use_cyrillic = int(digest[0], 16) % 2 == 0
        legacy = ""
        for char in digest:
            if char.isdigit():
                legacy += (
                    chr(ord("\u0410") + int(char))
                    if use_cyrillic
                    else chr(ord("A") + int(char))
                )
            else:
                upper = char.upper()
                legacy += (
                    UnicodeIdentifierEncoder.HOMOGLYPHS.get(upper, upper)
                    if use_cyrillic
                    else upper
                )
        assert spelling != legacy, (
            f"{name} encoded to {spelling}, which is md5({name}) mapped to "
            "homoglyphs -- invertible with a word list"
        )


def test_encoder_spelling_is_stable_within_one_build():
    encoder = UnicodeIdentifierEncoder()
    first = encoder._encode_name("evens")
    second = encoder._encode_name("evens")
    assert first == second, "the encoder produced two spellings for one name"


# A source shaped like the bench payload: a class with `self`, a closure with
# `nonlocal`, and plain functions. This is what routes names through the
# `dynamic_unbounds` branch of SymbolRenamer.
_BRANCH_SOURCE = '''
class Holder:
    def __init__(self):
        self.value = 0

def make_counter():
    count = 0
    def bump():
        nonlocal count
        count += 1
        return count
    return bump

def evens(limit):
    return [i for i in range(limit) if i % 2 == 0]

def classify(point):
    return point

def main():
    print(evens(10))

main()
'''

_MIN_OPTS = {
    "cfg_flatten": False, "opaque_predicates": False, "exception_flow": False,
    "fragment_strings": False, "mba_subs": False, "obf_calls": False,
    "bogus_exceptions": False, "split_vars": False, "unfold_constants": False,
    "strip_meta": False, "dynamic_code": False, "enhanced_junk": False,
    "break_decompiler": False, "code_checksums": False, "unicode_ids": False,
    "symbol_rename": True,
}


def test_transform_uses_the_keyed_branch_not_md5():
    """End-to-end through apply_ast_mutation.

    The pre-fix build spelled these `_nx_` + md5(name)[:6]; this asserts the
    transform still reaches that branch (so the test is not vacuous) and that
    nothing it emits is a bare hash of a name in the source.
    """
    import ast

    from obfuscator.core.sources import apply_ast_mutation

    out, _ = apply_ast_mutation(_BRANCH_SOURCE, dict(_MIN_OPTS), strict=True)
    tree = ast.parse(out)
    top = [
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]

    branch_names = [name for name in top if name.startswith("_nx_")]
    assert branch_names, (
        "no name reached the dynamic_unbounds branch; this test would pass "
        "vacuously -- the source shape no longer triggers it"
    )

    source_names = ["Holder", "make_counter", "evens", "classify", "main"]
    cracked = [name for name in source_names if _md5_spelling(name) in top]
    assert cracked == [], (
        f"the transform emitted md5-derived names for {cracked}; a word list "
        "recovers them from the built artefact"
    )

