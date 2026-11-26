"""Regression tests for irgen/chaff_circuits.py (HIGH: generate_chaff_pipeline
emitted chaff `def` source inside a list literal -> SyntaxError; MEDIUM:
obfuscate_verification's router sent the CORRECT input to a chaff circuit)."""
import ast

import irgen.chaff_circuits as cc

SRC = "def f(x):\n    return x * 2 + 1\n"


def test_generated_pipeline_parses_and_runs():
    out = cc.generate_chaff_pipeline(SRC, ["f"], 3, 42)
    ast.parse(out)  # must be valid Python (was SyntaxError before the fix)
    ns = {}
    exec(out, ns)
    # The wrapper must call the REAL circuit.
    assert ns["verify_f"](5) == ns["f"](5) == 11


def test_chaff_pool_holds_names_not_source():
    out = cc.generate_chaff_pipeline(SRC, ["f"], 3, 42)
    tree = ast.parse(out)
    pools = [n for n in ast.walk(tree)
             if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id.startswith("__chaff_pool_") for t in n.targets)]
    assert pools, "expected a __chaff_pool_ assignment"
    for pool in pools:
        assert isinstance(pool.value, ast.List)
        for elt in pool.value.elts:
            assert isinstance(elt, ast.Name), "pool entries must be function names, not def source"


def test_obfuscated_router_routes_correct_input_to_real():
    gen = cc.ChaffCircuitGenerator(42, 3)
    node = ast.parse(SRC).body[0]
    chaff = [gen._transform_ast_func(node, "f", t) for t in ("xor", "rotate", "popcount")]
    names = [c.name for c in chaff]
    wrapper = gen.obfuscate_verification("f", names, 5)
    mod_src = SRC + "\n" + "\n".join(ast.unparse(c) for c in chaff) + "\n" + wrapper
    ast.parse(mod_src)
    ns = {}
    exec(mod_src, ns)
    # Correct input -> real circuit.
    assert ns["verify_obf_f"](5) == ns["f"](5)
    # Wrong input -> a chaff circuit (result differs from the real one).
    r = ns["verify_obf_f"](6)
    assert r != ns["f"](6)
    assert r in {ns[n](6) for n in names}


def test_router_compares_full_integer_before_mba():
    """Aliases outside 32 bits must not be mistaken for the expected input."""
    gen = cc.ChaffCircuitGenerator(42, 2)
    wrapper = gen.obfuscate_verification("real", ["chaff_a", "chaff_b"], 5)
    ns = {}
    exec(
        "def real(x):\n    return x\n"
        "def chaff_a(x):\n    return 101\n"
        "def chaff_b(x):\n    return 102\n",
        ns,
    )
    exec(wrapper, ns)
    verify = ns["verify_obf_real"]
    assert verify(5) == 5
    for alias in (5 + 2**32, 5 - 2**32, 5 + 2**64, 5 - 2**64):
        assert verify(alias) in (101, 102), alias
