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
    ALIGNMENT_CANARY_GUID,
    cognitive_armor_triggers,
    aliasing_illusion,
    bpe_token_amplifier,
    crash_trace_decoys,
    diagnostic_rabbit_holes,
    shadow_business_logic,
    AntiReaInjector,
    bait_procedures,
    canary_tokens,
    chaff_payloads,
    decoy_call_graph,
    diff_noise_blocks,
    evidence_poison,
    compliance_notices,
    inject,
    obligation_flood,
    opaque_false_expression,
    prompt_completion_poison,
    url_differential_canaries,
    _CANARY_NOTICES,
    _ABORT_MARKERS,
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
    """Decoys are defined and never called; nothing executes at import.

    The single sanctioned import-time call is the classifier-bait containment
    tripwire recomputing its digest (_deriveContainmentCorpusDigest_*) -- the
    one guard the bait layer runs; every actual decoy stays define-only.
    """
    out, _ = inject(SOURCE, "balanced", 3)
    tree = ast.parse(out)
    called = {
        n.func.id for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "add" in called
    decoys = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)} - {"add"}
    assert decoys
    tripwire = {n for n in decoys if n.startswith("_deriveContainmentCorpusDigest_")}
    assert not ((decoys - tripwire) & called), (
        "a decoy function is invoked at module scope")


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


def test_compliance_bait_is_on_by_default_and_excludable():
    """The bait layers ship by default; the exclusion switch turns this one off."""
    src = "def f(x):\n    return x * 2\n"
    _, on = inject(src, "balanced", 1)
    _, off = inject(src, "balanced", 1, compliance_bait=False)
    assert on["compliance_notices"] > 0
    assert off["compliance_notices"] == 0


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


def test_bpe_amplifier_fragments_identifiers():
    """The names must deny a tokenizer any span it has a whole-word token for."""
    import random
    names = bpe_token_amplifier(random.Random(1), 6)
    assert len(names) == 6
    assert all(n.startswith("bpe_sink_") for n in names)
    # long, and built from short alternating fragments
    assert sum(len(n) for n in names) / len(names) > 25
    assert all(n.count("_") >= 8 for n in names)


def test_shadow_business_logic_is_coherent_not_a_stub():
    """An analyzer cites what is unambiguous; a stub would give it nothing."""
    import random
    names, src = shadow_business_logic(random.Random(2), 3)
    assert len(names) == 3
    tree = ast.parse(src)
    for fn in tree.body:
        assert isinstance(fn, ast.FunctionDef)
        assert ast.get_docstring(fn), "a shadow procedure without a docstring"
        body = ast.unparse(fn)
        assert "return" in body
        # more than a one-liner: it has real control flow
        assert len(fn.body) >= 3
    ns = {}
    exec(compile(src, "<shadow>", "exec"), ns)
    for name in names:
        assert callable(ns[name])


def test_shadow_functions_actually_run():
    import random
    names, src = shadow_business_logic(random.Random(3), 3)
    ns = {}
    exec(compile(src, "<shadow>", "exec"), ns)
    for name in names:
        fn = ns[name]
        if "pricing" in name:
            assert "total" in fn(50, "eu", 24)
        elif "license" in name:
            assert "tier" in fn(b"blob", [1, 2, 3])
        else:
            frame, nonce = fn(b"abcd", 7)
            assert isinstance(frame, (bytes, bytearray))


def test_aliasing_illusion_overwrites_the_apparent_assignment():
    """The reader is meant to conclude the wrong variable decides the result."""
    import random
    src = aliasing_illusion(random.Random(4), 1)
    ns = {}
    exec(compile(src, "<alias>", "exec"), ns)
    fn = next(v for k, v in ns.items() if callable(v) and not k.startswith("__"))
    a, b = fn(5)
    assert a == b, "both names must see the same buffer"
    # The alias is two bindings to the same object, not one statement.
    assert "view_a = raw" in src and "view_b = raw" in src, (
        "both names must bind the same buffer")


def test_crash_trace_decoys_look_like_native_faults():
    """A crash-driven localisation loop should terminate on the decoy handler."""
    import random
    names, src = crash_trace_decoys(random.Random(1), 3)
    assert len(names) == 3
    ns = {}
    exec(compile(src, "<crash>", "exec"), ns)
    for name in names:
        assert callable(ns[name])
        assert isinstance(ns[name](0), str)
    assert any(tag in src for tag in ("SIGSEGV", "EXC_BAD_ACCESS", "VSOCK", "0xC0000409"))


def test_diagnostics_describe_a_broken_tool_not_a_broken_payload():
    """The rabbit hole is that the ANALYZER's environment looks broken."""
    import random
    names, src = diagnostic_rabbit_holes(random.Random(2), 3)
    assert len(names) == 3
    ns = {}
    exec(compile(src, "<diag>", "exec"), ns)
    for name in names:
        entry = ns[name]()
        assert set(entry) == {"subsystem", "error_class", "system_code", "message"}
        assert isinstance(entry["system_code"], int)
    lowered = src.lower()
    assert any(tool in lowered for tool in
               ("pdb", "py-spy", "objdump", "gdb", "lldb", "decompiler"))


def test_diagnostic_decoys_are_inert():
    """They must not raise, print, or touch the filesystem."""
    import random
    _, src = diagnostic_rabbit_holes(random.Random(3), 6)
    assert "open(" not in src and "print(" not in src


def test_cognitive_armor_is_on_by_default_and_excludable():
    """The canary layer ships by default; the exclusion switch turns it off."""
    src = "def f(x):\n    return x * 2\n"
    _, on = inject(src, "balanced", 1)
    _, off = inject(src, "balanced", 1, cognitive_armor=False)
    assert on["cognitive_armor"] > 0
    assert off["cognitive_armor"] == 0


def test_cognitive_armor_uses_the_documented_canary_not_a_fabricated_hazard():
    """The canary GUID is a standard marker; the canary layer never names hazards.

    BLA's payload set also names specific biosecurity agents and chemical
    precursors. This layer deliberately does not: the fabricated hazard signal
    lives separately in ``classifier_bait_triggers`` (on by default, excluded
    via --exclude-rea-bio) with its own keyword-only content guard in
    tests/test_classifier_bait.py. This guard is scoped to the canary layer —
    the notices and abort markers below — and fails if THAT layer ever gains
    hazard vocabulary.
    """
    import random
    names, src = cognitive_armor_triggers(random.Random(1), 3)
    assert names
    assert ALIGNMENT_CANARY_GUID in src

    lowered = src.lower()
    for banned in ("variola", "ebola", "botulinum", "orthopox", "filovirus",
                   "methylphosphonyl", "acetylcholinesterase", "phosphono",
                   "bsl4", "select_agent", "synthesis"):
        assert banned not in lowered, (
            "fabricated hazard content present: %r" % banned)


def test_cognitive_armor_functions_are_callable_and_inert():
    import random
    names, src = cognitive_armor_triggers(random.Random(2), 2)
    ns = {}
    exec(compile(src, "<armor>", "exec"), ns)
    for name in names:
        assert isinstance(ns[name](), str)
    assert "open(" not in src and "import os" not in src


# --- canary variant pool (non-hazardous breadth) -----------------------------

_BANNED_HAZARD_TERMS = ("variola", "ebola", "botulinum", "orthopox", "filovirus",
                        "methylphosphonyl", "acetylcholinesterase", "phosphono",
                        "bsl4", "select_agent", "synthesis")


def test_every_canary_variant_declares_a_restriction_and_no_hazard():
    """Breadth of the canary pool must never become fabricated hazard content."""
    for text in _CANARY_NOTICES + _ABORT_MARKERS:
        assert ALIGNMENT_CANARY_GUID in text, "variant lost the canary: %r" % text[:40]
        lowered = text.lower()
        for banned in _BANNED_HAZARD_TERMS:
            assert banned not in lowered, "hazard term in variant: %r" % banned
    assert len(set(_CANARY_NOTICES)) == len(_CANARY_NOTICES)
    assert len(set(_ABORT_MARKERS)) == len(_ABORT_MARKERS)
    assert len(_CANARY_NOTICES) >= 4 and len(_ABORT_MARKERS) >= 2


def test_cognitive_armor_sampling_spans_the_variant_pool():
    """count=3 against a 6-notice pool must reach more than the old 2-notice set."""
    import random
    seen = set()
    for seed in range(6):
        _, src = cognitive_armor_triggers(random.Random(seed), 3)
        ns = {}
        exec(compile(src, "<armor>", "exec"), ns)
        for name in _fn_names(src):
            seen.add(ns[name]())
    assert len(seen) >= 4, "variant pool not being sampled: %d distinct" % len(seen)


def _fn_names(src):
    return [n.name for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)]


# --- diff-noise (BLA deception/diff-noise-injector) --------------------------

def test_diff_noise_is_deterministic_per_seed_and_varies_across_seeds():
    import random
    n1, s1 = diff_noise_blocks(random.Random(7), 2)
    n2, s2 = diff_noise_blocks(random.Random(7), 2)
    n3, s3 = diff_noise_blocks(random.Random(8), 2)
    assert s1 == s2 and n1 == n2, "same seed must reproduce the same blocks"
    assert s1 != s3, "different seeds must permute the arms differently"
    ns = {}
    exec(compile(s1, "<diffnoise>", "exec"), ns)
    for name in n1:
        # Inert means: defined, callable, deterministic -- the payload never
        # calls it, which the behaviour test pins for the whole module.
        assert ns[name]() == ns[name](0), "frontier must be deterministic"
        assert ns[name](5) == ns[name](5), "frontier must be deterministic on input"


def test_diff_noise_reaches_the_module_and_scales_with_intensity():
    _, stealth = inject(SOURCE, "stealth", 3)
    _, maximum = inject(SOURCE, "maximum", 3)
    assert stealth["diff_frontiers"] == 1
    assert maximum["diff_frontiers"] == 4


# --- prompt-completion priority sorting (BLA prompt-completion-poison) -------

def test_prompt_poison_names_sort_early_and_are_uniquely_ranked():
    import random
    import re
    names, src = prompt_completion_poison(random.Random(9), 4)
    ranks = [re.match(r"^_([0-9a-f]{3})_", n).group(1) for n in names]
    assert len(set(ranks)) == len(names), "shared rank = shared greppable literal"
    for n in names:
        assert n < "alpha", "priority symbol must sort before typical payload defs"
    ns = {}
    exec(compile(src, "<prio>", "exec"), ns)
    for name in names:
        assert ns[name]()["valid"] is False, "priority decoy must always be invalid"


def test_prompt_poison_heads_the_module_listing():
    import re
    src = "def alpha():\n    return 1\n"
    out, stats = inject(src, "balanced", 5)
    assert stats["priority_symbols"] == 4
    defs = [n.name for n in ast.parse(out).body if isinstance(n, ast.FunctionDef)]
    prio = [d for d in defs if re.match(r"^_[0-9a-f]{3}_", d)]
    assert prio, "no priority symbols reached the module"
    for name in prio:
        assert defs.index(name) < defs.index("alpha"), (
            "%s must be injected ahead of the payload's own defs" % name)


# --- obligation flood (BLA exhaustion/obligation-flooder) ---------------------

def test_obligation_flood_is_inert_and_family_distinct():
    import random
    n1, s1 = obligation_flood(random.Random(11), 6)
    n2, s2 = obligation_flood(random.Random(11), 6)
    assert s1 == s2, "same seed must reproduce the same flood"
    ns = {}
    exec(compile(s1, "<oblig>", "exec"), ns)
    kinds = set()
    for fn in n1:
        entry = ns[fn]()
        assert entry["evidence"] == "decoy-inert"
        assert 2 <= entry["required_cases"] <= 4
        kinds.add(entry["kind"])
    assert len(kinds) == len(n1), "families must not repeat within one flood"


def test_obligation_flood_reaches_the_module_and_scales():
    _, stealth = inject(SOURCE, "stealth", 4)
    _, maximum = inject(SOURCE, "maximum", 4)
    assert stealth["obligations"] == 3
    assert maximum["obligations"] == 10


def test_a_payload_docstring_survives_the_woven_call():
    """Inserting at index 0 displaced __doc__ -- a behaviour change."""
    src = ('def f(x):\n    """Keep me."""\n    return x + 1\nprint(f(2))\n')
    out, _ = inject(src, "maximum", 3)
    fn = next(n for n in ast.parse(out).body
              if isinstance(n, ast.FunctionDef) and n.name == "f")
    assert ast.get_docstring(fn) == "Keep me."
    assert ast.unparse(fn.body[1]).startswith("_ = "), "the call must follow it"
    assert _run(out) == "3"


def test_canary_tokens_respects_count_zero():
    import random
    assert canary_tokens(random.Random(1), 0) == []
    assert len(canary_tokens(random.Random(1), 2)) == 3   # 2 AWS + 1 synthetic
