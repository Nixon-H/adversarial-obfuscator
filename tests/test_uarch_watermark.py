import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMicroarchitecturalWatermark:
    """
    TestMicroarchitecturalWatermark
    
    Positive test cases for microarchitecturalwatermark.
    """
    def test_embed_basic(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        wm = MicroarchitecturalWatermark()
        source = "def f():\n    return 42\n"
        result = wm.embed(source, "test")
        assert "_uarch_wm_check" in result
        assert "_uarch_wm_delta" in result

    def test_extract_after_embed(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        wm = MicroarchitecturalWatermark()
        source = "def f():\n    return 42\n"
        watermarked = wm.embed(source, "HelloWorld")
        extracted = wm.extract_from_source(watermarked)
        assert "HelloWorld" in extracted

    def test_roundtrip_preserves_original_code(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        wm = MicroarchitecturalWatermark()
        source = "x = 1\ny = 2\nz = x + y\n"
        watermarked = wm.embed(source, "test_msg")
        assert "x = 1" in watermarked
        assert "y = 2" in watermarked
        assert "z = x + y" in watermarked

    def test_measure_timing_signature(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        wm = MicroarchitecturalWatermark()
        source = "def f():\n    return 42\n"
        watermarked = wm.embed(source, "timing_test")
        timings, delta = wm.measure_timing_signature(watermarked)
        assert len(timings) >= 1
        assert delta > 0

    def test_detect_watermark(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        wm = MicroarchitecturalWatermark()
        source = "def f():\n    return 42\n"
        watermarked = wm.embed(source, "NixonCorp")
        assert wm.detect_watermark_from_timing(watermarked, "NixonCorp") is True
        assert wm.detect_watermark_from_timing(source, "NixonCorp") is False

    def test_empty_message(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        wm = MicroarchitecturalWatermark()
        source = "def f():\n    return 42\n"
        result = wm.embed(source, "")
        extracted = wm.extract_from_source(result)
        assert extracted == ""

    def test_different_messages_different_patterns(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        wm = MicroarchitecturalWatermark()
        source = "x = 1\n"
        r1 = wm.embed(source, "msg_a")
        r2 = wm.embed(source, "msg_b_longer")
        assert r1 != r2

    def test_bits_message_roundtrip(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        bits = MicroarchitecturalWatermark._message_to_bits("Hello")
        msg = MicroarchitecturalWatermark._bits_to_message(bits)
        assert msg == "Hello"

    def test_bits_message_empty(self):
        from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
        assert MicroarchitecturalWatermark._message_to_bits("") == []
        assert MicroarchitecturalWatermark._bits_to_message([]) == ""

    def test_rdtsc_fallback(self):
        from scripts.watermark.uarch_watermark import rdtsc
        val = rdtsc()
        assert val > 0

    def test_read_tsc_benchmark(self):
        from scripts.watermark.uarch_watermark import read_tsc_benchmark
        avg = read_tsc_benchmark(100)
        assert avg > 0
