import ast
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.data_obfuscation.data_protector import DataProtector
from scripts.runtime.oram_sim import PathORAM as PythonORAM


def _run(source: str, level: int = 3) -> str:
    tree = ast.parse(source)
    protector = DataProtector(level=level)
    tree = protector.protect(tree)
    return ast.unparse(tree)


def test_variable_layout_randomization_produces_valid_python():
    source = """
def foo():
    a = 1
    b = 2
    c = a + b
    return c
"""
    result = _run(source, level=1)
    try:
        ast.parse(result)
    except SyntaxError as e:
        assert False, f"Layout randomization produced invalid Python: {e}\n{result}"


def test_layouts_deterministic_with_same_seed():
    source = """
def foo():
    a = 1
    b = 2
    c = a + b
    return c
"""
    t1 = ast.parse(source)
    t2 = ast.parse(source)
    p = DataProtector(level=1, seed=b"fixed_seed")
    r1 = ast.unparse(p.protect(t1))
    p2 = DataProtector(level=1, seed=b"fixed_seed")
    r2 = ast.unparse(p2.protect(t2))
    assert r1 == r2, "Same seed should produce identical output"


def test_layouts_differ_with_different_seeds():
    source = """
def foo():
    a = 1
    b = 2
    c = a + b
    return c
"""
    tree1 = ast.parse(source)
    tree2 = ast.parse(source)
    p1 = DataProtector(level=1, seed=b"seed_a")
    p2 = DataProtector(level=1, seed=b"seed_b")
    r1 = ast.unparse(p1.protect(tree1))
    r2 = ast.unparse(p2.protect(tree2))
    assert r1 != r2, "Different seeds should produce different layouts"


def test_structure_mutation_on_dicts():
    source = """
def foo():
    user = {"name": "Alice"}
    return user["name"]
"""
    result = _run(source, level=2)
    assert ".encode(" in result, "Structure mutation should encode dict keys"


def test_storage_virtualization():
    source = """
def foo():
    a = 1
    b = 2
    return a + b
"""
    result = _run(source, level=3)
    assert "_vs_" in result, "Storage virtualization should introduce vstore array"


def test_oram_read_write_roundtrip():
    oram = PythonORAM(num_blocks=16)
    write_data = b"\xab" * 32
    oram.write(5, write_data)
    read_data = oram.read(5)
    assert read_data == write_data, f"Roundtrip failed: {read_data!r} != {write_data!r}"


def test_oram_different_addresses():
    oram = PythonORAM(num_blocks=16)
    oram.write(0, b"\x01" * 32)
    oram.write(7, b"\x02" * 32)
    assert oram.read(0) == b"\x01" * 32
    assert oram.read(7) == b"\x02" * 32


def test_oram_out_of_range():
    oram = PythonORAM(num_blocks=8)
    try:
        oram.read(100)
        assert False, "Should have raised error"
    except (ValueError, KeyError, IndexError):
        pass


def test_protected_code_produces_same_output():
    source = """
def compute(x, y):
    z = x + y
    return z
"""
    ns_orig = {}
    exec(compile(ast.parse(source), "<test>", "exec"), ns_orig)
    orig_out = ns_orig["compute"](3, 4)

    tree = DataProtector(level=1).protect(ast.parse(source))
    ns_prot = {}
    exec(compile(tree, "<test>", "exec"), ns_prot)
    prot_out = ns_prot["compute"](3, 4)

    assert orig_out == prot_out, f"Output mismatch: {orig_out} != {prot_out}"


def test_empty_variables():
    source = """
def empty():
    pass
"""
    result = _run(source, level=3)
    try:
        ast.parse(result)
    except SyntaxError as e:
        assert False, f"Empty function produced invalid Python: {e}"


def test_nested_structures():
    source = """
def nested():
    config = {"db": {"host": "localhost", "port": 5432}}
    return config["db"]["host"]
"""
    result = _run(source, level=2)
    assert ".encode(" in result, "Nested dict keys should be encoded"


def test_function_calls_with_sensitive_vars():
    source = """
def encrypt(key, data):
    result = key ^ data
    return result
"""
    result = _run(source, level=3)
    assert "PythonORAM" in result, "Sensitive vars should get ORAM protection"


def test_oram_stress_sequential():
    oram = PythonORAM(num_blocks=32)
    for i in range(32):
        data = i.to_bytes(32, "little")
        oram.write(i, data)
    for i in range(32):
        expected = i.to_bytes(32, "little")
        assert oram.read(i) == expected, f"Mismatch at block {i}"


def test_storage_virtualization_indirection():
    source = """
def bar():
    x = 10
    y = 20
    return x + y
"""
    result = _run(source, level=3)
    assert "_vmap_" in result, "Should have virtual address mapper"
    assert "_vs_" in result, "Should have virtual storage"
