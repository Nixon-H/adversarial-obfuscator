"""Execution regressions for collision-free variant renaming."""

import irgen.variant_pool as vp


def _candidate(name, seed=b"seed"):
    return f"v_{int.from_bytes(vp._blake2b(seed + name.encode(), 4), 'little'):08x}"


def test_scrambler_does_not_shadow_unbound_identifier():
    candidate = _candidate("x")
    source = f"def f(x):\n    return {candidate} + x\n"
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {candidate: 7}
    exec(renamed, ns)
    assert ns["f"](5) == 12


def test_scrambler_does_not_collide_with_callable_name():
    candidate = _candidate("x")
    source = (
        f"def {candidate}():\n    return 7\n"
        "def f(x):\n    return " + candidate + "() + x\n"
    )
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["f"](5) == 12


def test_scrambler_does_not_collide_with_import_alias():
    candidate = _candidate("x")
    source = (
        f"import math as {candidate}\n"
        "def f(x):\n    return " + candidate + ".floor(2.5) + x\n"
    )
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["f"](5) == 7


def test_renamed_copy_allocates_fresh_function_name(monkeypatch):
    monkeypatch.setattr(vp, "_phase2_enabled", lambda: True)
    source = "def f():\n    return 1\ndef f_loop():\n    return 99\n"
    variants = vp.generate_variants(source, "f", 1, b"seed")
    ns = {}
    exec(variants[0], ns)
    assert ns["f_loop"]() == 99
    assert ns["f_loop_1"]() == 1


def test_renamed_copy_preserves_recursive_and_external_calls():
    source = """\
def factorial(n):
    return 1 if n <= 1 else n * factorial(n - 1)

def caller(value):
    return factorial(value)

result = caller(6)
"""
    renamed = vp._renamed_copy(source, "factorial", "loop")
    ns = {}
    exec(renamed, ns)
    assert ns["result"] == 720
    assert ns["factorial_loop"](5) == 120
    assert ns["caller"](4) == 24


def test_renamed_copy_does_not_rewrite_shadowed_function_name():
    source = """\
def factorial(n):
    def factorial(value):
        return value + 1
    return factorial(n)

result = factorial(3)
"""
    renamed = vp._renamed_copy(source, "factorial", "loop")
    ns = {}
    exec(renamed, ns)
    assert ns["result"] == 4
    assert ns["factorial_loop"](3) == 4


def test_scrambler_preserves_parameters_and_keyword_labels():
    source = """\
def calculate(a, /, b, *, scale=1):
    return (a + b) * scale
"""
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["calculate"](2, b=3, scale=4) == 20


def test_scrambler_preserves_exception_capture_binding():
    source = """\
def capture():
    try:
        raise ValueError("bad")
    except ValueError as error:
        message = str(error)
    error = "reset"
    return message, error
"""
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["capture"]() == ("bad", "reset")


def test_scrambler_preserves_match_as_binding():
    source = """\
def capture():
    match 3:
        case captured if captured > 2:
            message = captured
    captured = "reset"
    return message, captured
"""
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["capture"]() == (3, "reset")


def test_scrambler_preserves_match_star_binding():
    source = """\
def capture():
    match [1, 2, 3]:
        case [first, *rest]:
            total = first + len(rest)
    first = "reset"
    rest = "tail"
    return total, first, rest
"""
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["capture"]() == (3, "reset", "tail")


def test_scrambler_preserves_match_mapping_rest_binding():
    source = """\
def capture():
    match {"value": 3, "extra": 4}:
        case {"value": captured, **rest}:
            total = captured + len(rest)
    captured = "reset"
    rest = "tail"
    return total, captured, rest
"""
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["capture"]() == (4, "reset", "tail")


def test_scrambler_preserves_direct_class_body_bindings():
    source = """\
class Container:
    value = 2

    def read(self):
        return Container.value
"""
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["Container"]().read() == 2


def test_scrambler_visits_parameter_and_return_annotations():
    source = """\
class Marker:
    pass

Annotation = Marker

def identity(value: Annotation) -> Annotation:
    return value
"""
    renamed = vp._scramble_variable_names(source, b"seed")
    ns = {}
    exec(renamed, ns)
    assert ns["identity"](3) == 3
    assert list(ns["identity"].__annotations__.values()) == [ns["Marker"], ns["Marker"]]
