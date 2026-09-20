import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.survivability import SurvivabilityIndex, SurvivabilityResult


WATERMARKED = """# watermark: nx_test
def main():
    x = __watermark__
    return x
"""

CFG_SRC = """def func_a():
    x = 1
    if x > 0:
        return 1
    return 0
"""


class TestSurvivabilityIndexExtended:
    """
    TestSurvivabilityIndexExtended
    
    Positive test cases for survivabilityindexextended.
    """
    def test_watermark_survival(self):
        index = SurvivabilityIndex()
        score = index.measure_watermark_survival(WATERMARKED)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_vm_recovery(self):
        index = SurvivabilityIndex()
        score = index.measure_vm_opcode_recovery("OP_ADD = 1\nOP_SUB = 2\n")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_cfg_reconstruction(self):
        index = SurvivabilityIndex()
        score = index.measure_cfg_reconstruction(CFG_SRC)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_fragment_isolation(self):
        index = SurvivabilityIndex()
        score = index.measure_fragment_isolation("frag_start_0\ndef main(): pass")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_combined_index(self):
        index = SurvivabilityIndex()
        result = index.measure(WATERMARKED, {'layers': {'watermark': True, 'vm_opcode': False, 'cfg': False, 'fragment': False}})
        assert isinstance(result, SurvivabilityResult)
        assert 0.0 <= result.combined_index <= 1.0

    def test_combined_all_layers(self):
        index = SurvivabilityIndex()
        result = index.measure("test")
        assert isinstance(result, SurvivabilityResult)
        assert 0.0 <= result.combined_index <= 1.0

    def test_no_active_layers_zero(self):
        index = SurvivabilityIndex()
        result = index.measure("test", {'layers': {'watermark': False, 'vm_opcode': False, 'cfg': False, 'fragment': False}})
        assert result.combined_index == 0.0
