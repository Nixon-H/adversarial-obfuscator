"""Golden-file tests: deterministic output with fixed seed."""
import hashlib
import pytest
from obfuscator.core import ObfuscationTransformer

GOLDEN_SEED = 12345

SIMPLE_SOURCE = "def add(a, b): return a + b\n"

def test_golden_obfuscation_deterministic():
    t1 = ObfuscationTransformer(seed=GOLDEN_SEED)
    t2 = ObfuscationTransformer(seed=GOLDEN_SEED)
    r1 = t1.transform(SIMPLE_SOURCE)
    r2 = t2.transform(SIMPLE_SOURCE)
    assert r1 == r2, "Golden output must be deterministic"
    h = hashlib.sha256(r1.encode()).hexdigest()
    assert len(h) == 64

def test_golden_output_changes_with_seed():
    t1 = ObfuscationTransformer(seed=GOLDEN_SEED)
    t2 = ObfuscationTransformer(seed=GOLDEN_SEED + 1)
    r1 = t1.transform(SIMPLE_SOURCE)
    r2 = t2.transform(SIMPLE_SOURCE)
    assert r1 != r2, "Different seeds must produce different output"

def test_golden_pipeline_deterministic():
    from obfuscator.core import build_pipeline
    result1 = build_pipeline(SIMPLE_SOURCE, seed=GOLDEN_SEED)
    result2 = build_pipeline(SIMPLE_SOURCE, seed=GOLDEN_SEED)
    assert result1 == result2
