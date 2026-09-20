import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.fragment.micro_fragment import MicroFragmentExecutor, MicroFragment


def test_fragment_code_creates_fragments():
    executor = MicroFragmentExecutor(master_key=b"test-key-32-bytes-long!!!!!!", fragment_size=16)
    code = "x = 1\ny = 2\nz = x + y"
    fragments = executor.fragment_code(code)
    assert len(fragments) >= 1
    assert all(isinstance(f, MicroFragment) for f in fragments)
    assert all(f.index >= 0 for f in fragments)
    assert all(f.plaintext_len > 0 for f in fragments)
    assert all(len(f.encrypted) > 0 for f in fragments)


def test_execute_all_returns_namespace():
    executor = MicroFragmentExecutor(master_key=b"test-key-32-bytes-long!!!!!!", fragment_size=32)
    code = "result = 42\ndata = [1, 2, 3]"
    ns = executor.execute_all(code)
    assert ns.get("result") == 42
    assert ns.get("data") == [1, 2, 3]


def test_execution_summary():
    executor = MicroFragmentExecutor(master_key=b"test-key-32-bytes-long!!!!!!", fragment_size=16)
    code = "a = 1\nb = 2\nc = a + b\nd = c * 2"
    executor.execute_all(code)
    summary = executor.get_execution_summary()
    assert summary["all_executed"] is True
    assert summary["total_fragments"] == summary["executed"]
    assert summary["fragment_size"] == 16


def test_different_keys_produce_different_encryption():
    code = "x = 1"
    e1 = MicroFragmentExecutor(master_key=b"key-A-32-bytes-long!!!!!!!!!", fragment_size=16)
    e2 = MicroFragmentExecutor(master_key=b"key-B-32-bytes-long!!!!!!!!!", fragment_size=16)
    f1 = e1.fragment_code(code)
    f2 = e2.fragment_code(code)
    assert f1[0].encrypted != f2[0].encrypted


def test_fragment_ir_instructions():
    executor = MicroFragmentExecutor(master_key=b"test-key-32-bytes-long!!!!!!")
    instructions = ["LOAD r1 42", "LOAD r2 10", "ADD r3 r1 r2", "STORE r3 x"]
    fragments = executor.fragment_ir_instructions(instructions)
    assert len(fragments) >= 1
    assert all(f.index >= 0 for f in fragments)
    assert all(f.plaintext_len > 0 for f in fragments)


def test_execute_all_randomized_deterministic():
    executor = MicroFragmentExecutor(master_key=b"test-key-32-bytes-long!!!!!!")
    instructions = ["a = 1", "b = 2", "c = 3", "d = 4"]
    ns1 = executor.execute_all_randomized(instructions, seed=42)
    executor2 = MicroFragmentExecutor(master_key=b"test-key-32-bytes-long!!!!!!")
    ns2 = executor2.execute_all_randomized(instructions, seed=42)
    for key in ns1:
        assert ns1[key] == ns2.get(key), f"Mismatch for {key}: {ns1[key]} != {ns2.get(key)}"


def test_execute_all_randomized_independent_vars():
    executor = MicroFragmentExecutor(master_key=b"test-key-32-bytes-long!!!!!!")
    instructions = ["a = 10", "b = 20", "c = 30"]
    ns = executor.execute_all_randomized(instructions, seed=7)
    assert ns.get("a") == 10
    assert ns.get("b") == 20
    assert ns.get("c") == 30
