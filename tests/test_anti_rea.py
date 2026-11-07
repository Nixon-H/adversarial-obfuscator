"""Counter-REA shields ported from BLA (qybaihe/bla).

BLA's three layers act on what an analyzer EXTRACTS rather than on how the code
runs: poison what it reads, exhaust its budget, muddle its inventory. Ported here
for Python payloads.

The one property that matters most is that they stay inert: a shield that changes
payload behaviour is a bug that ships to users.
"""

import ast
import contextlib
import io

from obfuscator.anti_rea import (
    AntiReaInjector,
    bait_procedures,
    canary_tokens,
    chaff_payloads,
    decoy_call_graph,
    evidence_poison,
    compliance_notices,
    inject,
    opaque_false_expression,
    url_differential_canaries,
)

SOURCE = "def add(a, b):\n    return a + b\nprint(add(2, 3))\n"


def _run(code):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<anti-rea>", "exec"), {})
    return buf.getvalue().strip()


def test_the_payload_still_behaves_identically():
    """The added names are never referenced, so behaviour cannot change."""
    out, stats = inject(SOURCE, "balanced", 42)
    assert _run(out) == _run(SOURCE) == "5"
    assert stats["decoy_functions"] > 0


def test_the_shields_actually_enlarge_the_analysis_surface():
    out, stats = inject(SOURCE, "maximum", 1)
    assert len(out) > len(SOURCE) * 50
    assert stats["chaff"] > 0 and stats["canaries"] > 0


def test_importing_the_payload_runs_no_decoy_work():
    """Decoys are defined and never called; nothing executes at import."""
    out, _ = inject(SOURCE, "balanced", 3)
    tree = ast.parse(out)
    called = {
        n.func.id for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "add" in called
    decoys = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)} - {"add"}
    assert decoys
    assert not (decoys & called), "a decoy function is invoked at module scope"


def test_seeding_is_deterministic_and_varied():
    a, _ = inject(SOURCE, "balanced", 7)
    b, _ = inject(SOURCE, "balanced", 7)
    c, _ = inject(SOURCE, "balanced", 8)
    assert a == b, "the same seed must reproduce the same shields"
    assert a != c, "a different seed must produce different shields"


def test_intensity_scales_the_amount_of_decoy_material():
    small, s1 = inject(SOURCE, "stealth", 5)
    big, s2 = inject(SOURCE, "maximum", 5)
    assert len(big) > len(small)
    assert s2["decoy_functions"] > s1["decoy_functions"]


def test_canaries_use_the_documentation_designated_shape():
    """Credential scanners are specified to recognise this form and redact it.

    A model that redacts the canary tends to take the surrounding context with it.
    The shape must stay clearly synthetic for that to be defensible.
    """
    import random
    toks = canary_tokens(random.Random(1), 2)
    assert all(t.startswith("AKIA") for t in toks[:2])
    assert all(t.endswith("EXAMPLE") for t in toks[:2])
    assert any(t.startswith("bla_canary_synthetic_") for t in toks)


def test_the_decoy_call_graph_does_not_terminate_at_a_leaf():
    """An analyzer following references should not reach a quick dead end."""
    import random
    rng = random.Random(2)
    src = decoy_call_graph(rng, chaff_payloads(rng, 3), 6)
    tree = ast.parse(src)
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(names) == 6
    text = ast.unparse(tree)
    # every decoy references at least one other decoy
    for name in names:
        others = [n for n in names if n != name]
        assert any(o in text for o in others)


def test_opaque_predicate_is_false_for_the_seed_variables_it_uses():
    """It is an opaque predicate: always false, but not obviously so."""
    import random
    rng = random.Random(0)
    expr = opaque_false_expression(rng, "s")
    for s in (0, 1, 7, 12345, 255):
        assert eval(expr, {"s": s}) is False, expr


def test_evidence_poison_claims_analysis_is_already_complete():
    """The point is to leave an analyzer with a 'nothing to do here' artifact."""
    import random
    lines = evidence_poison(random.Random(3), 3)
    assert lines
    assert all(("EVIDENCE_CONTRACT_SUMMARY" in ln) or ("PROJECTION" in ln)
               or ("LEDGER" in ln) or ("NOTE" in ln) or ("CONTRACT" in ln)
               for ln in lines)


def test_bait_procedures_are_named_for_what_an_analyst_would_hunt_for():
    import random
    src = bait_procedures(random.Random(4), 4)
    tree = ast.parse(src)
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(names) == 4
    joined = " ".join(names)
    assert "license" in joined or "key" in joined or "entitlement" in joined


def test_chaff_is_labelled_so_two_builds_are_distinguishable():
    import random
    a = chaff_payloads(random.Random(5), 4)
    b = chaff_payloads(random.Random(6), 4)
    assert a != b
    assert all(ln.startswith("[") for ln in a)


def test_the_injector_can_be_applied_twice_without_colliding():
    """Two passes must not raise a duplicate-definition or syntax error."""
    once, _ = inject(SOURCE, "stealth", 11)
    twice = AntiReaInjector(intensity="stealth", seed=12).visit(ast.parse(once))
    ast.fix_missing_locations(twice)
    compile(ast.unparse(twice), "<twice>", "exec")


def test_decoy_calls_are_woven_into_the_payloads_own_functions():
    """Appending decoys is not enough: nothing in the real code would reach them.

    An analyzer starts from a named function. If that function never references the
    labyrinth, the decoys are dead weight. BLA solves this by weaving a decoy call
    into each customer function, and this port does the same -- but ONLY into
    customer functions. Weaving into a decoy puts a depth=0 call at the top of its
    own body, resetting the recursion guard and recursing to RecursionError; and
    weaving into a bait procedure called it with an int where it expects a string.
    Both were found by executing the result, not by reading it.
    """
    src = ("def add(a, b):\n    total = a + b\n    return total\n"
           "def mul(a, b):\n    prod = a * b\n    return prod\n"
           "print(add(2, 3), mul(2, 3))\n")
    out, stats = inject(src, "maximum", 5)
    assert stats["woven_calls"] == 2, "both customer functions should be woven"

    tree = ast.parse(out)
    customer = {n.name: n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name in ("add", "mul")}
    assert customer, "customer functions vanished"
    for fn in customer.values():
        assert ast.unparse(fn.body[0]).startswith("_ = "), (
            "%s did not receive a decoy call" % fn.name)
    assert _run(out) == "5 6"


def test_weaving_never_changes_the_result():
    src = ("def add(a, b):\n    total = a + b\n    return total\n"
           "print(add(2, 3))\n")
    for level in ("stealth", "balanced", "maximum"):
        for seed in range(12):
            out, _ = inject(src, level, seed)
            assert _run(out) == "5", (level, seed)


def test_url_canaries_exercise_parser_differentials():
    """Parser disagreement is the property, not one parser's bug.

    Four constructs that at least two mainstream parsers read differently: a
    single-slash scheme with userinfo, duplicate query keys, a backslash after the
    authority, and a userinfo section containing '@'.
    """
    import random
    urls = url_differential_canaries(random.Random(9), 4)
    assert len(urls) == 4
    assert any("https:/" in u and "://" not in u for u in urls), "no single-slash form"
    assert any(u.count("lease=") == 2 for u in urls), "no duplicate query key"
    assert any("\\@" in u for u in urls), "no backslash-after-authority form"
    assert any(u.count("@") >= 2 for u in urls), "no multi-@ userinfo form"


def test_compliance_bait_is_off_unless_explicitly_requested():
    """It targets classifier behaviour, so it is the user's decision, not a default."""
    src = "def f(x):\n    return x * 2\n"
    _, off = inject(src, "balanced", 1)
    _, on = inject(src, "balanced", 1, compliance_bait=True)
    assert off["compliance_notices"] == 0
    assert on["compliance_notices"] > 0


def test_compliance_bait_does_not_claim_a_certification():
    """It must not assert the software IS a regulated device.

    A false compliance claim follows the user into an audit. These say the data is
    sensitive and the authoritative logic is elsewhere -- which steers the same
    classifier without inventing a certification.
    """
    import random
    notices = compliance_notices(random.Random(2), 3)
    assert notices
    lowered = " ".join(notices).lower()
    for forbidden in ("is certified", "is a class c device", "complies with",
                      "this device is"):
        assert forbidden not in lowered, "asserts a certification: %r" % forbidden
    assert ("remote" in lowered) or ("not present in this unit" in lowered)


def test_url_canaries_reach_the_injected_source():
    src = "def f(x):\n    return x * 2\n"
    out, stats = inject(src, "balanced", 4)
    assert stats["url_canaries"] > 0
    assert "internal" in out
