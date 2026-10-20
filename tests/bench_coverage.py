"""
bench_coverage.py

Benchmarks for Protection Coverage Mapping (Feature 147).

Measures coverage map generation, merging, and serialization performance.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.coverage.coverage_map import generate_coverage_map, coverage_to_json, coverage_to_text, coverage_to_html, PROTECTION_NAMES
from scripts.coverage.pipeline_tracker import PipelineTracker
from scripts.coverage.ir_scanner import scan_ir_module
from irgen.compile import compile_py_to_ir


def _make_opts(**overrides):
    defaults = {
        "state_isa": False, "rop": False, "fragment": False,
        "watermark": None, "attestation": False, "proof_carrying": False,
        "fhe_vm": False, "zk_state": False, "kernel_assist": False,
        "io_research": False, "microjit": False, "data_obfuscation": False,
        "hw_entropy": False, "entropy_flatten": False, "crypto_binding": False,
        "flow_entangle": False, "challenge_response": False,
        "diversity": 0, "multi_binary": False, "cross_process": False,
        "distributed_vm": False, "dist_attestation": False,
        "embed_proof": False, "verify_preservation_formal": False,
        "ephemeral_isa": False, "simd_vm": False,
        "micro_fragment": False,
    }
    defaults.update(overrides)
    return type('Opts', (), defaults)()


def _make_pipeline_state(opts):
    return type('PipelineState', (), {'opts': opts, 'globals': {}})()


def test_bench_coverage_map_generation_small(benchmark):
    source = """
def add(a, b):
    return a + b
def sub(a, b):
    return a - b
def mul(a, b):
    return a * b
"""
    ir_module = compile_py_to_ir(source, "bench_small")
    opts = _make_opts(state_isa=True, rop=True, watermark="test",
                       fhe_vm=True, crypto_binding=True)
    ps = _make_pipeline_state(opts)

    def run():
        cm = generate_coverage_map(ir_module, ps)
        return cm

    result = benchmark(run)
    assert result.total_functions >= 3
    assert result.coverage_percent > 0


def test_bench_coverage_map_generation_large(benchmark):
    lines = []
    for i in range(100):
        lines.append(f"def func_{i}(x):")
        lines.append("    r = x")
        for j in range(10):
            lines.append(f"    r = r + {j}")
        lines.append("    return r")
    source = "\n".join(lines)
    ir_module = compile_py_to_ir(source, "bench_large")
    opts = _make_opts(state_isa=True, rop=True, fragment=True,
                       watermark="wm", attestation=True, proof_carrying=True,
                       fhe_vm=True, zk_state=True, kernel_assist=True,
                       io_research=True, microjit=True, data_obfuscation=True,
                       hw_entropy=True, crypto_binding=True, flow_entangle=True,
                       challenge_response=True, diversity=5,
                       multi_binary=True)
    ps = _make_pipeline_state(opts)

    def run():
        cm = generate_coverage_map(ir_module, ps)
        return cm

    result = benchmark(run)
    assert result.total_functions == 100
    assert result.coverage_percent > 0


def test_bench_pipeline_tracker_overhead(benchmark):
    def run():
        tracker = PipelineTracker()
        for i in range(100):
            for p in PROTECTION_NAMES[:5]:
                tracker.record_protection(f"func_{i}", p, {"key": i})
            if i % 5 == 0:
                tracker.record_skip(f"func_{i}", "ROP", "bench skip")
        _ = tracker.get_summary()
        _ = tracker.to_dict()
    benchmark(run)


def test_bench_ir_scanner_small(benchmark):
    source = "def f(x): return x + 1\n" * 10
    ir_module = compile_py_to_ir(source, "bench_scan")
    benchmark(lambda: scan_ir_module(ir_module))


def test_bench_ir_scanner_large(benchmark):
    lines = []
    for i in range(200):
        lines.append(f"def fn_{i}(x):")
        lines.append("    if x > 0:")
        lines.append("        return x + 1")
        lines.append("    return 0")
    source = "\n".join(lines)
    ir_module = compile_py_to_ir(source, "bench_scan_large")
    benchmark(lambda: scan_ir_module(ir_module))


def test_bench_serialization(benchmark):
    source = "def f(x): return x + 1\n" * 50
    ir_module = compile_py_to_ir(source, "bench_ser")
    opts = _make_opts(state_isa=True, rop=True, fragment=True)
    ps = _make_pipeline_state(opts)
    cm = generate_coverage_map(ir_module, ps)

    def run():
        _ = coverage_to_json(cm)
        _ = coverage_to_text(cm)
    benchmark(run)


def test_bench_html_report(benchmark):
    source = "def f(x): return x + 1\n" * 50
    ir_module = compile_py_to_ir(source, "bench_html")
    opts = _make_opts(state_isa=True, rop=True, fragment=True, watermark="test")
    ps = _make_pipeline_state(opts)
    cm = generate_coverage_map(ir_module, ps)
    benchmark(lambda: coverage_to_html(cm))
