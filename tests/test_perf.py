import time


def test_obfuscation_overhead():
    """Profile obfuscation pipeline time."""
    from obfuscator.core import ObfuscationTransformer
    t = ObfuscationTransformer(seed=42)
    source = "def add(a, b):\n    return a + b\n"
    start = time.perf_counter()
    result = t.transform(source)
    elapsed = time.perf_counter() - start
    print(f"\nObfuscation: {elapsed:.3f}s for {len(source)} bytes source")
    assert len(result) > 0
    assert elapsed < 30.0


def test_aes_throughput():
    """Benchmark AES-256-CTR throughput."""
    from encrypt.aes import aes256_ctr_keystream, aes256_encrypt_block
    key = b"K" * 32
    nonce = b"\x00" * 8
    data = b"X" * 1000

    aes256_ctr_keystream(key, nonce, len(data))

    pt = b"Y" * 16
    for _ in range(100):
        aes256_encrypt_block(pt, key)


def test_pipeline_phases_timing():
    """Time each phase of the pipeline."""
    from obfuscator.core import ObfuscationTransformer
    source = "x = 1\ny = x + 2\nprint(y)\n" * 10

    start = time.perf_counter()
    t = ObfuscationTransformer(seed=42)
    t.transform(source)
    elapsed = time.perf_counter() - start
    print(f"\nObfuscation: {elapsed:.3f}s")
    assert elapsed < 60.0
