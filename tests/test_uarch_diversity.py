import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


SIMPLE_SRC = """
def add(a, b):
    return a + b

def main():
    x = 10
    y = 20
    result = add(x, y)
    print(result)
"""


class TestMicroarchitecturalDiversity:
    """
    TestMicroarchitecturalDiversity
    
    Positive test cases for microarchitecturaldiversity.
    """
    def test_detect_microarchitecture(self):
        from scripts.diversity.uarch_diversity import detect_microarchitecture
        info = detect_microarchitecture()
        assert "arch" in info
        assert "vendor" in info
        assert "emulator" in info
        assert "cache_line" in info

    def test_select_variant_for_uarch(self):
        from scripts.diversity.uarch_diversity import select_variant_for_uarch
        variants = {"intel": "intel_code", "amd": "amd_code", "default": "default_code"}
        result = select_variant_for_uarch(variants)
        assert result in variants.values()

    def test_generate_cache_pattern_variant(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        result = gen.generate_cache_pattern_variant(SIMPLE_SRC)
        assert "_uarch_cache_pattern_" in result
        assert "def add" in result

    def test_generate_branch_pattern_variant(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        result = gen.generate_branch_pattern_variant(SIMPLE_SRC)
        assert "_bp_acc_" in result
        assert "def add" in result

    def test_generate_tlb_pressure_variant(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        result = gen.generate_tlb_pressure_variant(SIMPLE_SRC)
        assert "_tlb_buf_" in result
        assert "bytearray" in result

    def test_generate_simd_usage_variant(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        result = gen.generate_simd_usage_variant(SIMPLE_SRC)
        assert "_simd_buf_" in result
        assert "range" in result

    def test_generate_all_variant_types(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        variants = gen.generate_all_variant_types(SIMPLE_SRC)
        assert len(variants) == 4
        assert "cache" in variants
        assert "branch" in variants
        assert "tlb" in variants
        assert "simd" in variants

    def test_generate_uarch_aware_variants(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        result = gen.generate_uarch_aware_variants(SIMPLE_SRC)
        assert "all" in result
        assert "selected" in result
        assert "uarch" in result

    def test_uarch_fingerprint(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        fp = gen.uarch_fingerprint(SIMPLE_SRC)
        assert "cache_access_density" in fp
        assert "branch_density" in fp
        assert "instruction_count" in fp

    def test_uarch_aware_distance(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        src2 = SIMPLE_SRC + "\n# extra comment\n"
        dist = gen.uarch_aware_distance(SIMPLE_SRC, src2)
        assert 0.0 <= dist <= 1.0

    def test_source_similarity(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        sim = gen.source_similarity("a b c", "a b d")
        assert 0.0 <= sim <= 1.0

    def test_variants_produce_valid_python(self):
        import ast
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen = MicroarchitecturalDiversityGenerator(seed=42)
        variants = gen.generate_all_variant_types(SIMPLE_SRC)
        for vtype, vcode in variants.items():
            try:
                ast.parse(vcode)
            except SyntaxError as e:
                pytest.fail(f"Variant {vtype} is not valid Python: {e}")

    def test_different_seeds_different_variants(self):
        from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator
        gen1 = MicroarchitecturalDiversityGenerator(seed=42)
        gen2 = MicroarchitecturalDiversityGenerator(seed=99)
        v1 = gen1.generate_cache_pattern_variant(SIMPLE_SRC)
        v2 = gen2.generate_cache_pattern_variant(SIMPLE_SRC)
        assert v1 != v2
