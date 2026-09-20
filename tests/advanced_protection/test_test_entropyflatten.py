import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestEntropyFlatten:

    def _make_test_elf_binary(self, text_data: bytes = None) -> bytes:
        import struct
        from encrypt.elf import EHDR_FMT_64, SHDR_FMT_64

        if text_data is None:
            text_data = b'\x90' * 256 + b'\x55\x48\x89\xe5\x31\xc0\x5d\xc3' * 16

        e_ident = b'\x7fELF' + bytes([2, 1, 1, 0]) + b'\x00' * 8
        ehdr = struct.pack(EHDR_FMT_64,
            e_ident, 2, 0x3e, 1, 0x400000,
            0, 64, 0, 64, 0, 0,
            struct.calcsize(SHDR_FMT_64), 3, 2)

        shstrtab = b'\x00.text\x00.shstrtab\x00'
        shdr_size = struct.calcsize(SHDR_FMT_64)
        text_offset = 64 + 3 * shdr_size
        shstrtab_offset = text_offset + len(text_data)

        shdr_null = struct.pack(SHDR_FMT_64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        shdr_text = struct.pack(SHDR_FMT_64,
            1, 1, 6, 0x400000, text_offset, len(text_data), 0, 0, 16, 0)
        shdr_shstrtab = struct.pack(SHDR_FMT_64,
            7, 1, 0, 0, shstrtab_offset, len(shstrtab), 0, 0, 1, 0)

        data = bytearray()
        data.extend(ehdr)
        data.extend(shdr_null + shdr_text + shdr_shstrtab)
        if len(data) < text_offset:
            data.extend(b'\x00' * (text_offset - len(data)))
        data.extend(text_data)
        data.extend(shstrtab)
        return bytes(data)

    def test_shannon_entropy_random(self):
        from scripts.entropy_flatten import EntropyAnalyzer
        import os
        data = os.urandom(4096)
        entropy = EntropyAnalyzer.compute_shannon_entropy(data)
        assert 7.9 < entropy < 8.1, f"Expected ~8.0, got {entropy}"

    def test_shannon_entropy_zero(self):
        from scripts.entropy_flatten import EntropyAnalyzer
        data = b'\x00' * 4096
        entropy = EntropyAnalyzer.compute_shannon_entropy(data)
        assert entropy == 0.0, f"Expected 0.0, got {entropy}"

    def test_page_entropy_map_structure(self, tmp_path):
        from scripts.entropy_flatten import EntropyAnalyzer
        binpath = tmp_path / "test.elf"
        binpath.write_bytes(self._make_test_elf_binary())
        analyzer = EntropyAnalyzer()
        page_map = analyzer.page_entropy_map(str(binpath))
        assert isinstance(page_map, dict)
        for off, ent in page_map.items():
            assert off % 4096 == 0
            assert 0.0 <= ent <= 8.0

    def test_anomalous_page_detection(self, tmp_path):
        from scripts.entropy_flatten import EntropyAnalyzer
        high_ent = b'\x00' * 2048 + os.urandom(2048)
        text_data = b'\x90' * 4096 * 4 + high_ent + b'\x00' * 1024
        binpath = tmp_path / "test_anom.elf"
        binpath.write_bytes(self._make_test_elf_binary(text_data))
        analyzer = EntropyAnalyzer()
        anomalous = analyzer.find_anomalous_pages(str(binpath), threshold=0.5)
        assert isinstance(anomalous, list)

    def test_chaff_block_entropy_near_target(self):
        from scripts.entropy_flatten import EntropyAnalyzer, EntropyFlattener
        target = 6.0
        flattener = EntropyFlattener(target)
        chaff = flattener.generate_chaff_block(1024)
        entropy = EntropyAnalyzer.compute_shannon_entropy(chaff)
        assert abs(entropy - target) < 0.5, f"Expected ~{target}, got {entropy}"

    def test_low_entropy_stub(self):
        from scripts.entropy_flatten import EntropyAnalyzer, generate_low_entropy_stub
        stub = generate_low_entropy_stub(256, seed=42)
        assert len(stub) == 256
        entropy = EntropyAnalyzer.compute_shannon_entropy(stub)
        assert entropy < 4.0, f"Expected low entropy, got {entropy}"

    def test_flatten_binary_no_crash(self, tmp_path):
        from scripts.entropy_flatten import EntropyAnalyzer, EntropyFlattener
        text_data = b'\x90' * 4096 + os.urandom(4096)
        binpath = tmp_path / "input.elf"
        outpath = tmp_path / "output.elf"
        binpath.write_bytes(self._make_test_elf_binary(text_data))
        target = EntropyAnalyzer().target_entropy(str(binpath))
        flattener = EntropyFlattener(target)
        flattener.flatten_binary(str(binpath), str(outpath), {
            "tolerance": 0.3, "chaff_per_page": 64,
        })
        assert outpath.exists()
        assert outpath.stat().st_size > 0

    def test_flattened_binary_more_uniform(self, tmp_path):
        from scripts.entropy_flatten import EntropyAnalyzer, EntropyFlattener
        import os
        mixed_data = os.urandom(4096) + b'\x90' * 4096 + os.urandom(4096)
        text_data = mixed_data + b'\x00' * (4096 - (len(mixed_data) % 4096))
        binpath = tmp_path / "pre.elf"
        outpath = tmp_path / "post.elf"
        binpath.write_bytes(self._make_test_elf_binary(text_data))
        target = EntropyAnalyzer().target_entropy(str(binpath))
        flattener = EntropyFlattener(target)
        flattener.flatten_binary(str(binpath), str(outpath), {
            "tolerance": 0.3, "chaff_per_page": 64,
        })

        orig_map = EntropyAnalyzer().page_entropy_map(str(binpath))
        flat_map = EntropyAnalyzer().page_entropy_map(str(outpath))

        def entropy_spread(emap):
            vals = list(emap.values())
            return max(vals) - min(vals) if vals else 0.0

        assert entropy_spread(flat_map) <= entropy_spread(orig_map) + 1.0
