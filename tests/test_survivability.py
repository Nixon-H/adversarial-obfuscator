import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.survivability import SurvivabilityIndex, SurvivabilityResult
from scripts.evaluation.survivability_probes import (
    probe_watermark,
    probe_vm_opcodes,
    probe_cfg,
    probe_fragments,
)


WATERMARKED_SRC = """# watermark: nx_secret_42
import hashlib

def main():
    x = __watermark__
    y = "_nx_wm_marker"
    return x
"""

NO_WATERMARK_SRC = """def main():
    return 42
"""

VM_OPCODE_SRC = """OP_ADD = 1
OP_SUB = 2
OP_MUL = 3
OP_CALL = 4
OP_JMP = 5
OP_RET = 6
"""

CFG_SRC = """def func_a():
    x = 1
    return x

def func_b():
    if x > 0:
        return 1
    else:
        return 0
"""

FRAGMENT_SRC = """def main():
    frag_start_0()
    frag_start_1()
    mid_code()
    frag_start_2()
    return
"""


class TestSurvivabilityIndex:
    """
    TestSurvivabilityIndex
    
    Positive test cases for survivabilityindex.
    """
    def test_watermark_survival_returns_float(self):
        index = SurvivabilityIndex()
        result = index.measure_watermark_survival(WATERMARKED_SRC)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_vm_opcode_recovery_range(self):
        index = SurvivabilityIndex()
        result = index.measure_vm_opcode_recovery(VM_OPCODE_SRC)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_cfg_reconstruction_jaccard(self):
        index = SurvivabilityIndex()
        identical = index.measure_cfg_reconstruction(CFG_SRC)
        assert isinstance(identical, float)
        assert 0.0 <= identical <= 1.0

    def test_fragment_isolation_symmetric(self):
        index = SurvivabilityIndex()
        result = index.measure_fragment_isolation(FRAGMENT_SRC)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_combined_index_in_range(self):
        index = SurvivabilityIndex()
        result = index.measure(WATERMARKED_SRC, {'layers': {'watermark': True, 'vm_opcode': False, 'cfg': False, 'fragment': False}})
        assert 0.0 <= result.combined_index <= 1.0

    def test_active_layers_detected(self):
        index = SurvivabilityIndex()
        config = {'layers': {'watermark': True, 'vm_opcode': True, 'cfg': False, 'fragment': False}}
        result = index.measure(WATERMARKED_SRC, config)
        assert 'watermark' in result.active_layers
        assert 'vm_opcode' in result.active_layers
        assert 'cfg' not in result.active_layers
        assert 'fragment' not in result.active_layers

    def test_survivability_weight_distribution(self):
        index = SurvivabilityIndex()
        config = {'layers': {'watermark': True, 'vm_opcode': False, 'cfg': True, 'fragment': False}}
        result = index.measure(CFG_SRC, config)
        assert 'watermark' in result.active_layers
        assert 'cfg' in result.active_layers
        assert 'vm_opcode' not in result.active_layers
        assert 'fragment' not in result.active_layers
        assert 0.0 <= result.combined_index <= 1.0

    def test_measure_returns_result_dataclass(self):
        index = SurvivabilityIndex()
        result = index.measure(CFG_SRC)
        assert isinstance(result, SurvivabilityResult)
        assert isinstance(result.combined_index, float)

    def test_no_active_layers_returns_zero(self):
        index = SurvivabilityIndex()
        config = {'layers': {'watermark': False, 'vm_opcode': False, 'cfg': False, 'fragment': False}}
        result = index.measure(CFG_SRC, config)
        assert result.combined_index == 0.0
        assert result.active_layers == []


class TestSurvivabilityProbes:
    """
    TestSurvivabilityProbes
    
    Positive test cases for survivabilityprobes.
    """
    def test_probe_watermark_finds_markers(self):
        score = probe_watermark(WATERMARKED_SRC)
        assert score >= 0.6

    def test_probe_watermark_no_markers_low(self):
        score = probe_watermark(NO_WATERMARK_SRC)
        assert score <= 0.5

    def test_probe_vm_opcodes_returns_float(self):
        score = probe_vm_opcodes(VM_OPCODE_SRC)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_probe_vm_opcodes_empty(self):
        score = probe_vm_opcodes("")
        assert isinstance(score, float)

    def test_probe_cfg_identical_cfgs(self):
        score = probe_cfg(CFG_SRC)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_probe_cfg_empty(self):
        score = probe_cfg("")
        assert isinstance(score, float)

    def test_probe_fragments_returns_float(self):
        score = probe_fragments(FRAGMENT_SRC)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_probe_fragments_no_fragments(self):
        score = probe_fragments(NO_WATERMARK_SRC)
        assert isinstance(score, float)
