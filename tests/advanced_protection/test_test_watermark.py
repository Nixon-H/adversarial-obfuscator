import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestWatermark:
    def test_gf_mul_div_inv(self):
        from irgen.watermark import _gf
        a, b = 0x57, 0x83
        assert _gf.mul(a, b) == _gf.mul(b, a)
        c = _gf.mul(a, b)
        assert _gf.div(c, b) == a

    def test_gf_inv_zero(self):
        from irgen.watermark import _gf
        assert _gf.inv(0) == 0

    def test_gf_pow(self):
        from irgen.watermark import _gf
        assert _gf.pow(2, 0) == 1
        assert _gf.pow(0, 5) == 0

    def test_poly_add_sub(self):
        from irgen.watermark import _Poly
        a = _Poly([1, 2, 3])
        b = _Poly([3, 2, 1])
        c = a + b
        assert c.coeffs == [2, 0, 2]

    def test_poly_mul(self):
        from irgen.watermark import _Poly
        a = _Poly([1, 1])
        b = _Poly([1, 1])
        c = a * b
        assert c.deg() == 2

    def test_poly_mod(self):
        from irgen.watermark import _Poly
        a = _Poly([1, 0, 1, 0, 1])
        b = _Poly([1, 1, 1])
        r = a % b
        assert r.deg() < b.deg()

    def test_poly_div(self):
        from irgen.watermark import _Poly
        a = _Poly([1, 0, 1])
        b = _Poly([1, 1])
        q = a / b
        assert isinstance(q, _Poly)

    def test_poly_eval(self):
        from irgen.watermark import _Poly
        p = _Poly([1, 2, 3])
        v = p.eval(0)
        assert v == 1

    def test_bch_encode_decode(self):
        from irgen.watermark import BCHCode
        bch = BCHCode(n=255, t=20)
        data = b"\xAB" * 8
        codeword = bch.encode(data)
        assert len(codeword) > 0
        decoded = bch.decode(codeword, len(data) * 8)
        assert decoded[:len(data)] == data

    def test_bch_encode_empty(self):
        from irgen.watermark import BCHCode
        bch = BCHCode()
        assert bch.encode(b"") == b""

    def test_bch_error_correction(self):
        from irgen.watermark import BCHCode
        bch = BCHCode(n=255, t=20)
        data = b"\x42" * 8
        codeword = bytearray(bch.encode(data))
        codeword[10] ^= 0xFF
        codeword[20] ^= 0xFF
        decoded = bch.decode(bytes(codeword), len(data) * 8)
        assert decoded[:len(data)] == data

    def test_generate_watermark_disabled(self):
        import irgen.watermark as wm
        was = wm._PHASE2_ENABLED
        wm._PHASE2_ENABLED = False
        try:
            with pytest.raises(RuntimeError, match="Advanced Protection must be enabled"):
                wm.generate_watermark(b"customer", b"build")
        finally:
            wm._PHASE2_ENABLED = was

    def test_generate_watermark_enabled(self):
        import irgen.watermark as wm
        was = wm._PHASE2_ENABLED
        wm._PHASE2_ENABLED = True
        try:
            result, meta = wm.generate_watermark(b"cust1234", b"build5678")
            assert len(result) > 0
            assert "bits" in meta
            assert "encoded" in meta
            assert meta["bch_used"] is True
        finally:
            wm._PHASE2_ENABLED = was

    def test_generate_watermark_no_ecc(self):
        import irgen.watermark as wm
        was = wm._PHASE2_ENABLED
        wm._PHASE2_ENABLED = True
        try:
            result, meta = wm.generate_watermark(b"cust", b"build", error_correct=False)
            assert "bch_used" in meta
            assert meta["bch_used"] is False
        finally:
            wm._PHASE2_ENABLED = was

    def test_embed_watermark_empty_module(self):
        import irgen.watermark as wm
        from irgen.compile import IrModule
        was = wm._PHASE2_ENABLED
        wm._PHASE2_ENABLED = True
        try:
            mod = IrModule("test")
            result = wm.embed_watermark(mod, b"\x01", {"encoded": [1, 0], "patterns": {}})
            assert isinstance(result, IrModule)
        finally:
            wm._PHASE2_ENABLED = was

    def test_detect_watermark_no_watermark(self):
        import irgen.watermark as wm
        from irgen.compile import IrModule
        was = wm._PHASE2_ENABLED
        wm._PHASE2_ENABLED = True
        try:
            mod = IrModule("empty")
            result = wm.detect_watermark(mod, b"seed")
            assert result is None
        finally:
            wm._PHASE2_ENABLED = was
