"""
test_coverage.py

Tests for Protection Coverage Mapping: FunctionCoverage, CoverageMap, merging,
pipeline tracking, IR scanning, classification, serialization.

Test coverage:
- Positive tests verify dataclasses, merging, tracker recording, IR scanner, classifier
- Negative tests verify empty modules, no protections, none opts, invalid names
"""
import json
import os
import sys
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.coverage.coverage_map import (
    CoverageMap, FunctionCoverage, generate_coverage_map,
    merge_coverage_maps, coverage_to_json, coverage_to_html,
    coverage_to_text, PROTECTION_NAMES,
)
from scripts.coverage.pipeline_tracker import PipelineTracker
from scripts.coverage.ir_scanner import scan_ir_module, classify_function

from irgen.compile import IrModule, IrFunction, IrType, compile_py_to_ir
from irgen.compile import IrValue


# =========================================================================
# Positive Tests
# =========================================================================


def test_function_coverage_dataclass():
    fc = FunctionCoverage(
        function_name="test_fn",
        ir_block_count=5,
        protections={"VM": True, "ROP": False},
        protection_details={"VM": {"type": "state_isa"}},
        uncovered_paths=["No ROP protection applied"],
    )
    assert fc.function_name == "test_fn"
    assert fc.ir_block_count == 5
    assert fc.protections["VM"] is True
    assert fc.protections["ROP"] is False
    assert fc.coverage_count() == 1
    assert fc.protection_percent() == 50.0


def test_function_coverage_empty_protections():
    fc = FunctionCoverage(function_name="empty", ir_block_count=0)
    assert fc.coverage_count() == 0
    assert fc.protection_percent() == 0.0


def test_coverage_map_dataclass():
    fc = FunctionCoverage(function_name="f1", ir_block_count=3)
    cm = CoverageMap(
        module_name="test",
        total_functions=1,
        covered_functions=1,
        coverage_percent=100.0,
        functions={"f1": fc},
        per_protection_stats={"VM": {"functions_covered": 1, "total_functions": 1, "coverage_ratio": 1.0}},
        generated_at="2025-01-01T00:00:00",
    )
    assert cm.module_name == "test"
    assert cm.total_functions == 1
    assert cm.coverage_percent == 100.0
    assert cm.functions["f1"].function_name == "f1"


def test_coverage_map_creation():
    fc1 = FunctionCoverage(function_name="func_a", ir_block_count=4)
    fc1.protections = {p: True for p in PROTECTION_NAMES[:3]}
    fc2 = FunctionCoverage(function_name="func_b", ir_block_count=2)
    fc2.protections = {p: False for p in PROTECTION_NAMES}
    cm = CoverageMap(
        module_name="sample",
        total_functions=2,
        covered_functions=1,
        coverage_percent=50.0,
        functions={"func_a": fc1, "func_b": fc2},
        generated_at=datetime.datetime.utcnow().isoformat(),
    )
    assert cm.total_functions == 2
    assert cm.covered_functions == 1
    assert cm.coverage_percent == 50.0


def test_coverage_serialization():
    fc = FunctionCoverage(
        function_name="f1",
        ir_block_count=3,
        protections={"VM": True, "ROP": False},
        uncovered_paths=["No ROP"],
    )
    cm = CoverageMap(
        module_name="test",
        total_functions=1,
        covered_functions=0,
        coverage_percent=0.0,
        functions={"f1": fc},
    )
    d = coverage_to_json(cm)
    assert d["module_name"] == "test"
    assert d["functions"]["f1"]["function_name"] == "f1"
    assert d["functions"]["f1"]["ir_block_count"] == 3
    assert d["functions"]["f1"]["protections"]["VM"] is True
    assert d["functions"]["f1"]["coverage_count"] == 1
    roundtrip = json.dumps(d)
    loaded = json.loads(roundtrip)
    assert loaded["module_name"] == "test"


def test_merge_coverage_maps():
    fc_a = FunctionCoverage(function_name="f1", ir_block_count=3)
    fc_a.protections = {"VM": True, "ROP": False}
    fc_b = FunctionCoverage(function_name="f1", ir_block_count=3)
    fc_b.protections = {"VM": False, "ROP": True}
    cm1 = CoverageMap(
        module_name="m1", total_functions=1, covered_functions=1,
        coverage_percent=50.0, functions={"f1": fc_a},
    )
    cm2 = CoverageMap(
        module_name="m2", total_functions=1, covered_functions=1,
        coverage_percent=50.0, functions={"f1": fc_b},
    )
    merged = merge_coverage_maps([cm1, cm2])
    assert merged.total_functions == 1
    assert merged.functions["f1"].protections["VM"] is True
    assert merged.functions["f1"].protections["ROP"] is True


def test_merge_coverage_maps_empty():
    merged = merge_coverage_maps([])
    assert merged.total_functions == 0
    assert merged.coverage_percent == 0.0


def test_merge_coverage_maps_multiple_functions():
    fc1 = FunctionCoverage(function_name="f1", ir_block_count=2)
    fc1.protections = {"VM": True}
    fc2 = FunctionCoverage(function_name="f2", ir_block_count=5)
    fc2.protections = {"ROP": True}
    cm1 = CoverageMap(
        module_name="m1", total_functions=1, covered_functions=1,
        coverage_percent=100.0, functions={"f1": fc1},
    )
    cm2 = CoverageMap(
        module_name="m2", total_functions=1, covered_functions=1,
        coverage_percent=100.0, functions={"f2": fc2},
    )
    merged = merge_coverage_maps([cm1, cm2])
    assert merged.total_functions == 2
    assert merged.functions["f1"].protections.get("VM") is True
    assert merged.functions["f2"].protections.get("ROP") is True


def test_pipeline_tracker_record():
    tracker = PipelineTracker()
    tracker.record_protection("func_a", "VM", {"type": "state_isa", "opcodes": 128})
    state = tracker.get_function_state("func_a")
    assert "VM" in state["applied"]
    assert state["details"]["VM"]["type"] == "state_isa"


def test_pipeline_tracker_skip():
    tracker = PipelineTracker()
    tracker.record_skip("func_b", "ROP", "Function too small")
    state = tracker.get_function_state("func_b")
    assert state["skipped"]["ROP"] == "Function too small"


def test_pipeline_tracker_summary():
    tracker = PipelineTracker()
    tracker.record_protection("f1", "VM")
    tracker.record_protection("f1", "ROP")
    tracker.record_protection("f2", "VM")
    summary = tracker.get_summary()
    assert summary["total_functions"] == 2
    assert "VM" in summary["protections_applied"]
    assert "ROP" in summary["protections_applied"]
    assert summary["total_recordings"] == 3


def test_pipeline_tracker_to_dict():
    tracker = PipelineTracker()
    tracker.record_protection("f1", "VM", {"key": "val"})
    tracker.record_skip("f1", "ROP", "skip reason")
    d = tracker.to_dict()
    assert "f1" in d["functions"]
    assert "VM" in d["functions"]["f1"]["applied"]
    assert "ROP" in d["functions"]["f1"]["skipped"]
    assert "summary" in d


def test_pipeline_tracker_multiple_functions():
    tracker = PipelineTracker()
    tracker.record_protection("f1", "VM")
    tracker.record_protection("f2", "ROP")
    tracker.record_protection("f3", "FHE")
    summary = tracker.get_summary()
    assert summary["total_functions"] == 3
    assert summary["total_recordings"] == 3
    assert summary["per_protection"]["VM"]["functions_covered"] == 1
    assert summary["per_protection"]["ROP"]["functions_covered"] == 1
    assert summary["per_protection"]["FHE"]["functions_covered"] == 1


def test_generate_coverage_map():
    source = """
def add(a, b):
    return a + b

def sub(a, b):
    return a - b
"""
    ir_module = compile_py_to_ir(source, "test_mod")
    opts = type('Opts', (), {
        "state_isa": True, "rop": False, "fragment": False,
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
    })()
    pipeline_state = type('PipelineState', (), {'opts': opts, 'globals': {}})()
    cm = generate_coverage_map(ir_module, pipeline_state)
    assert cm.module_name == "test_mod"
    assert cm.total_functions >= 2
    assert cm.functions["add"].ir_block_count >= 1
    assert cm.functions["add"].protections.get("VM") is True
    assert cm.functions["add"].protections.get("ROP") is False


def test_coverage_to_json():
    fc = FunctionCoverage(function_name="f1", ir_block_count=2,
                          protections={"VM": True, "ROP": False})
    cm = CoverageMap(
        module_name="t", total_functions=1, covered_functions=0,
        coverage_percent=0.0, functions={"f1": fc},
    )
    j = coverage_to_json(cm)
    assert isinstance(j, dict)
    assert j["module_name"] == "t"
    assert j["functions"]["f1"]["protections"]["VM"] is True
    assert j["functions"]["f1"]["coverage_count"] == 1


def test_coverage_to_html():
    fc = FunctionCoverage(function_name="f1", ir_block_count=2,
                          protections={p: True for p in PROTECTION_NAMES[:3]})
    cm = CoverageMap(
        module_name="test", total_functions=1, covered_functions=0,
        coverage_percent=0.0, functions={"f1": fc},
    )
    html = coverage_to_html(cm)
    assert "<!DOCTYPE html>" in html
    assert "Protection Coverage Map" in html
    assert "f1" in html
    assert "VM" in html


def test_coverage_to_text():
    fc = FunctionCoverage(function_name="f1", ir_block_count=3,
                          protections={"VM": True, "ROP": False})
    cm = CoverageMap(
        module_name="test", total_functions=1, covered_functions=0,
        coverage_percent=0.0, functions={"f1": fc},
    )
    text = coverage_to_text(cm)
    assert "Protection Coverage Map:" in text
    assert "f1" in text
    assert "VM" in text


def test_ir_scanner():
    source = """
def calc(x, y):
    z = x + y
    if z > 10:
        return z
    return 0

def empty():
    pass
"""
    ir_module = compile_py_to_ir(source, "scan_mod")
    scan = scan_ir_module(ir_module)
    assert "calc" in scan
    assert "empty" in scan
    assert scan["calc"]["block_count"] >= 1
    assert scan["calc"]["has_control_flow"] is True
    assert scan["empty"]["instruction_count"] >= 0


def test_ir_scanner_call_detection():
    source = """
def runner():
    return helper(42)

def helper(x):
    return x + 1
"""
    ir_module = compile_py_to_ir(source, "call_mod")
    scan = scan_ir_module(ir_module)
    assert scan["runner"]["has_calls"] is True
    assert "helper" in scan["runner"]["call_targets"]


def test_func_classify_arithmetic():
    source = """
def add(a, b):
    return a + b
"""
    ir_module = compile_py_to_ir(source, "arith_mod")
    classification = classify_function(ir_module.functions[0])
    assert classification == "arithmetic"


def test_func_classify_control():
    source = """
def check(x):
    if x > 0:
        return 1
    return 0
"""
    ir_module = compile_py_to_ir(source, "ctrl_mod")
    for func in ir_module.functions:
        cls = classify_function(func)
        if func.name == "check":
            assert cls == "control"
            break


def test_func_classify_dispatch():
    source = """
def dispatcher(x):
    return run(x)

def run(v):
    return v + 1
"""
    ir_module = compile_py_to_ir(source, "disp_mod")
    for func in ir_module.functions:
        cls = classify_function(func)
        if func.name == "dispatcher" or func.name == "run":
            assert cls in ("dispatch", "arithmetic", "general")


# =========================================================================
# Negative Tests
# =========================================================================


def test_empty_module():
    ir_module = IrModule("empty_mod")
    opts = type('Opts', (), {
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
    })()
    pipeline_state = type('PipelineState', (), {'opts': opts, 'globals': {}})()
    cm = generate_coverage_map(ir_module, pipeline_state)
    assert cm.total_functions == 0
    assert cm.covered_functions == 0
    assert cm.coverage_percent == 0.0


def test_no_protections():
    source = """
def foo():
    return 1
"""
    ir_module = compile_py_to_ir(source, "no_prot_mod")
    opts = type('Opts', (), {
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
    })()
    pipeline_state = type('PipelineState', (), {'opts': opts, 'globals': {}})()
    cm = generate_coverage_map(ir_module, pipeline_state)
    assert cm.total_functions == 1
    assert cm.covered_functions == 0
    assert cm.coverage_percent == 0.0
    for pname in PROTECTION_NAMES:
        assert cm.functions["foo"].protections.get(pname, False) is False


def test_invalid_function_name():
    tracker = PipelineTracker()
    state = tracker.get_function_state("nonexistent_function")
    assert state["applied"] == []
    assert state["skipped"] == {}
    assert state["details"] == {}


def test_empty_ir_scanner():
    ir_module = IrModule("empty")
    scan = scan_ir_module(ir_module)
    assert scan == {}


def test_none_opts_no_crash():
    source = """
def f():
    return 0
"""
    ir_module = compile_py_to_ir(source, "test")
    cm = generate_coverage_map(ir_module, None)
    assert cm.total_functions == 1
    assert cm.covered_functions == 0


def test_coverage_to_html_empty_module():
    cm = CoverageMap(module_name="empty", total_functions=0, covered_functions=0, coverage_percent=0.0)
    html = coverage_to_html(cm)
    assert "Coverage" in html


def test_merge_with_empty_list():
    cm1 = CoverageMap(module_name="a", total_functions=0, covered_functions=0, coverage_percent=0.0)
    merged = merge_coverage_maps([cm1])
    assert merged.total_functions == 0


def test_pipeline_tracker_nonexistent_function_details():
    tracker = PipelineTracker()
    state = tracker.get_function_state("ghost")
    assert "applied" in state
    assert "skipped" in state
    assert "details" in state
    assert state["details"] == {}


def test_function_coverage_serializes_all_protections():
    fc = FunctionCoverage(function_name="full", ir_block_count=10)
    for p in PROTECTION_NAMES:
        fc.protections[p] = True
    d = coverage_to_json(CoverageMap(
        module_name="test", total_functions=1, covered_functions=1,
        coverage_percent=100.0, functions={"full": fc},
    ))
    assert len(d["functions"]["full"]["protections"]) == len(PROTECTION_NAMES)
    assert all(d["functions"]["full"]["protections"].values())
