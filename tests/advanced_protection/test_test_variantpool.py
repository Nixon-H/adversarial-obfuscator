import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestVariantPool:
    SOURCE = """
def add(a, b):
    return a + b
"""

    def test_affine_encode_decode(self):
        from irgen.variant_pool import affine_encode, affine_decode
        x = 42
        A = 0x9E3779B9 | 1
        b = 0x61C88647
        enc = affine_encode(x, A, b)
        dec = affine_decode(enc, A, b)
        assert dec == x

    def test_generate_variants_phase2_disabled(self, monkeypatch):
        from irgen.variant_pool import generate_variants
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: False)
        with pytest.raises(RuntimeError, match="Advanced Protection must be enabled"):
            generate_variants(self.SOURCE, "add", num_variants=4)

    def test_generate_variants_phase2_enabled(self, monkeypatch):
        from irgen.variant_pool import generate_variants
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: True)
        result = generate_variants(self.SOURCE, "add", num_variants=4, seed=b"test_seed")
        assert len(result) == 4
        assert all(isinstance(v, str) for v in result)

    def test_select_variant_phase2_disabled(self, monkeypatch):
        from irgen.variant_pool import select_variant
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: False)
        variants = ["a", "b", "c"]
        result = select_variant(variants, b"seed", 0)
        assert result == "a"

    def test_select_variant_phase2_enabled(self, monkeypatch):
        from irgen.variant_pool import select_variant
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: True)
        variants = ["v0", "v1", "v2", "v3"]
        result = select_variant(variants, b"build_seed", 0)
        assert result in variants

    def test_select_variant_empty(self, monkeypatch):
        from irgen.variant_pool import select_variant
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: True)
        with pytest.raises(IndexError):
            select_variant([], b"seed", 0)

    def test_variant_pool_add_and_get(self, monkeypatch):
        from irgen.variant_pool import VariantPool
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: True)
        pool = VariantPool(b"build_seed")
        pool.add_function("add", self.SOURCE, num_variants=3)
        assert "add" in pool.pool
        assert len(pool.pool["add"]) == 3

    def test_variant_pool_get_selected(self, monkeypatch):
        from irgen.variant_pool import VariantPool
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: True)
        pool = VariantPool(b"seed")
        pool.add_function("add", self.SOURCE, num_variants=2)
        selected = pool.get_selected("add", 0)
        assert isinstance(selected, str)
        assert len(selected) > 0

    def test_variant_pool_get_selected_missing(self, monkeypatch):
        from irgen.variant_pool import VariantPool
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: True)
        pool = VariantPool(b"seed")
        with pytest.raises(IndexError):
            pool.get_selected("nonexistent", 0)

    def test_select_variant_runtime(self, monkeypatch):
        from irgen.variant_pool import select_variant_runtime
        monkeypatch.setattr("irgen.variant_pool._phase2_enabled", lambda: True)
        idx = select_variant_runtime(b"master_key", 1, 100, 4)
        assert 0 <= idx < 4
