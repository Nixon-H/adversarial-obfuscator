import math
import os
from collections import Counter
from typing import Dict, List


class EntropyAnalyzer:
    @staticmethod
    def compute_shannon_entropy(data: bytes) -> float:
        if not data:
            return 0.0
        freq = Counter(data)
        n = len(data)
        return -sum((c / n) * math.log2(c / n) for c in freq.values())

    def page_entropy_map(self, binary_path: str) -> Dict[int, float]:
        page_size = 4096
        with open(binary_path, 'rb') as f:
            data = f.read()
        result = {}
        for offset in range(0, len(data), page_size):
            page = data[offset:offset + page_size]
            result[offset] = self.compute_shannon_entropy(page)
        return result

    def _text_entropies(self, binary_path: str) -> List[float]:
        from encrypt.elf import ELFParser
        with open(binary_path, 'rb') as f:
            data = f.read()
        elf = ELFParser(data)
        _, text_sec = elf.get_text_section()
        text_data = elf.section_data(text_sec)
        page_size = 4096
        entropies = []
        for offset in range(0, len(text_data), page_size):
            page = text_data[offset:offset + page_size]
            entropies.append(self.compute_shannon_entropy(page))
        return entropies

    def _median(self, values: List[float]) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        return sorted_vals[mid]

    def find_anomalous_pages(self, binary_path: str, threshold: float = 0.5) -> List[int]:
        text_entropies = self._text_entropies(binary_path)
        if not text_entropies:
            return []
        median = self._median(text_entropies)
        page_map = self.page_entropy_map(binary_path)
        return [off for off, ent in page_map.items() if abs(ent - median) > threshold]

    def target_entropy(self, binary_path: str) -> float:
        return self._median(self._text_entropies(binary_path))


class EntropyFlattener:
    def __init__(self, target_entropy: float):
        self.target_entropy = target_entropy

    def generate_chaff_block(self, target_size: int) -> bytes:
        if target_size <= 0:
            return b''
        if self.target_entropy <= 0.0:
            return bytes([0x90] * target_size)
        if self.target_entropy >= 8.0:
            return os.urandom(target_size)

        lo, hi = 0, target_size
        best_chaff = None
        best_diff = float('inf')

        for _ in range(20):
            mid = max(0, min(target_size, (lo + hi) // 2))

            random_part = os.urandom(mid)
            structured_part = self._generate_structured_data(target_size - mid)
            chaff = random_part + structured_part

            entropy = EntropyAnalyzer.compute_shannon_entropy(chaff)
            diff = abs(entropy - self.target_entropy)

            if diff < best_diff:
                best_diff = diff
                best_chaff = chaff

            if diff < 0.05:
                break

            if entropy > self.target_entropy:
                hi = mid - 1
            else:
                lo = mid + 1

            if lo > hi:
                break

        return best_chaff or os.urandom(target_size)

    @staticmethod
    def _generate_structured_data(size: int) -> bytes:
        patterns = [
            bytes([0x90, 0x90]),
            bytes([0x48, 0x89, 0xc0]),
            bytes([0x48, 0x31, 0xc0]),
            bytes([0x48, 0x83, 0xc0, 0x00]),
            bytes([0x48, 0x8d, 0x40, 0x00]),
            bytes([0x48, 0x89, 0xdb]),
            bytes([0x48, 0x89, 0xc9]),
            bytes([0x48, 0x89, 0xd2]),
            bytes([0x66, 0x90]),
        ]
        result = bytearray()
        idx = 0
        while len(result) < size:
            pat = patterns[idx % len(patterns)]
            take = min(len(pat), size - len(result))
            result.extend(pat[:take])
            idx += 1
        return bytes(result)

    def flatten_binary(self, input_path: str, output_path: str, config: dict):
        from encrypt.elf import ELFParser

        tolerance = config.get('tolerance', 0.3)
        chaff_per_page = config.get('chaff_per_page', 64)

        with open(input_path, 'rb') as f:
            data = f.read()

        elf = ELFParser(data)
        _, text_sec = elf.get_text_section()
        text_data = elf.section_data(text_sec)

        analyzer = EntropyAnalyzer()
        page_size = 4096

        total_chaff = 0
        for offset in range(0, len(text_data), page_size):
            page = text_data[offset:offset + page_size]
            entropy = analyzer.compute_shannon_entropy(page)
            if entropy > self.target_entropy + tolerance:
                total_chaff += chaff_per_page

        if total_chaff > 0:
            chaff = self.generate_chaff_block(total_chaff)
            new_text = text_data + chaff
            elf.replace_text(new_text)

        elf.save(output_path)


def generate_low_entropy_stub(size: int, seed: int) -> bytes:
    import random
    rng = random.Random(seed)
    # 'random' is acceptable here — this is cosmetic padding (NOP-like patterns),
    # not a security/cryptographic primitive. Determinism via seed is desired for
    # reproducibility in testing/verification.

    patterns = [
        bytes([0x90, 0x90]),
        bytes([0x48, 0x89, 0xc0]),
        bytes([0x48, 0x31, 0xc0, 0x48, 0x83, 0xc0, 0x00]),
        bytes([0x48, 0x8d, 0x40, 0x00]),
        bytes([0x66, 0x90]),
    ]

    result = bytearray()
    while len(result) < size:
        pat = rng.choice(patterns)
        remaining = size - len(result)
        if len(pat) <= remaining:
            result.extend(pat)
        else:
            result.extend(pat[:remaining])
    return bytes(result)
