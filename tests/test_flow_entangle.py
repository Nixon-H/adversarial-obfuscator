import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.whitebox.flow_entangle import FlowEntangler, EntangledState
from obfuscator.flow_entangle import WhiteboxFlowEntangler


def test_make_decision_returns_bool():
    entangler = FlowEntangler()
    result = entangler.make_decision("path_a", 1)
    assert isinstance(result, bool)


def test_decisions_affect_state():
    e1 = FlowEntangler(seed=b"0123456789abcdef")
    e2 = FlowEntangler(seed=b"0123456789abcdef")
    for i in range(5):
        e1.make_decision(f"path_{i}", i)
        e2.make_decision(f"path_{i}", i)
    assert e1.get_state_bytes() == e2.get_state_bytes()


def test_different_seeds_different_state():
    e1 = FlowEntangler(seed=b"aaaaaaaaaaaaaaaa")
    e2 = FlowEntangler(seed=b"bbbbbbbbbbbbbbbb")
    for i in range(3):
        e1.make_decision(f"path_{i}", i)
        e2.make_decision(f"path_{i}", i)
    assert e1.get_state_bytes() != e2.get_state_bytes()


def test_entangled_paths_tracked():
    entangler = FlowEntangler()
    entangler.make_decision("test_path", 42)
    summary = entangler.get_entanglement_summary()
    assert summary["decisions"] == 1
    assert 42 in summary["paths"]
    assert summary["paths"][42] == "test_path"


def test_entangled_state_round_increments():
    state = EntangledState()
    v1 = state.process_path_decision(1)
    v2 = state.process_path_decision(2)
    assert state.round == 2
    assert state.path_history == [1, 2]
    assert isinstance(v1, int) and isinstance(v2, int)


# WhiteboxFlowEntangler tests

def test_whitebox_sbox_lookup_returns_byte():
    entangler = WhiteboxFlowEntangler(seed=b"0123456789abcdef")
    result = entangler.entangled_sbox_lookup(0x42, 0)
    assert 0 <= result <= 255


def test_whitebox_different_inputs_different_outputs():
    entangler = WhiteboxFlowEntangler(seed=b"0123456789abcdef")
    r1 = entangler.entangled_sbox_lookup(0x00, 0)
    r2 = entangler.entangled_sbox_lookup(0xFF, 1)
    assert r1 != r2


def test_whitebox_round_processes_state():
    entangler = WhiteboxFlowEntangler(seed=b"0123456789abcdef")
    state = list(range(16))
    round_key = [0x2b] * 16
    new_state = entangler.process_round(state, round_key)
    assert len(new_state) == 16
    assert all(0 <= b <= 255 for b in new_state)


def test_whitebox_entanglement_graph():
    entangler = WhiteboxFlowEntangler(seed=b"0123456789abcdef")
    for i in range(8):
        entangler.entangled_sbox_lookup(i, i)
    graph = entangler.get_entanglement_graph()
    assert graph["nodes"] == 8
    assert graph["edges"] >= 0


def test_whitebox_feedback_state():
    entangler = WhiteboxFlowEntangler(seed=b"0123456789abcdef")
    for i in range(4):
        entangler.entangled_sbox_lookup(i, i)
    state = entangler.get_feedback_state()
    assert len(state) == 16
    assert state != bytes(16)


def test_whitebox_sbox_history():
    entangler = WhiteboxFlowEntangler(seed=b"0123456789abcdef")
    entangler.entangled_sbox_lookup(0x42, 0)
    history = entangler.get_sbox_history()
    assert len(history) == 1
    assert "input" in history[0]
    assert "branch" in history[0]
    assert "output" in history[0]
