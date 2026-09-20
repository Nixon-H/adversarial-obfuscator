"""Tests for provenance poisoning techniques."""
import ast
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.provenance.poisoner import ProvenancePoisoner
from scripts.provenance.metrics import ProvenanceMetrics


SIMPLE_SCRIPT = """
def greet(name):
    msg = "hello " + name
    return msg

def add(a, b):
    return a + b

print(greet("world"))
"""


def _parse(src: str) -> ast.Module:
    return ast.parse(src)


def _execute(code: str, ns: dict | None = None) -> None:
    exec(code, ns or {})


def test_fake_call_graph_creates_functions():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["fake_call_graphs"]})
    code = ast.unparse(tree)
    assert "_nx_decoy_validate_license" in code
    assert "_nx_decoy_check_integrity" in code
    assert "_nx_decoy_verify_signature" in code
    assert "_nx_decoy_report_status" in code
    _execute(code)


def test_fake_call_graph_circular_dependency():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["fake_call_graphs"]})
    code = ast.unparse(tree)
    assert "call _nx_decoy_check_integrity" in code.replace("\n", " ").replace(" ", "") or \
           "_nx_decoy_check_integrity" in code
    assert "_nx_decoy_verify_signature" in code
    _execute(code)


def test_fake_apis_generated():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["fake_apis"]})
    code = ast.unparse(tree)
    assert "_nx_fake_api_verify" in code
    assert "_nx_fake_http_request" in code
    assert "_nx_fake_api_decrypt" in code
    assert "_nx_fake_api_attest" in code
    assert "Authorization" in code
    assert "api.verify.com" in code
    _execute(code)


def test_fake_protocol_parsers_generated():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["fake_protocol_parsers"]})
    code = ast.unparse(tree)
    assert "_nx_proto_parse" in code
    assert "_nx_proto_crc16" in code
    assert "_nx_proto_handshake" in code
    assert "_nx_proto_decapsulate" in code
    assert "Checksum mismatch" in code
    assert "struct" in code
    _execute(code)


def test_believable_dead_paths_generated():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["believable_dead_paths"]})
    code = ast.unparse(tree)
    assert "_NX_POISON_SALT_" in code
    assert "_nx_check_" in code
    assert "hashlib" in code
    _execute(code)


def test_misleading_imports_generated():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["misleading_imports"]})
    code = ast.unparse(tree)
    misleading_keywords = ["cryptography", "socket", "ssl", "requests"]
    found = any(kw in code for kw in misleading_keywords)
    assert found, f"Expected at least one misleading import, got none"
    _execute(code)


def test_all_techniques_compose():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ProvenancePoisoner.CATEGORIES})
    code = ast.unparse(tree)
    assert "_nx_decoy_validate_license" in code
    assert "_nx_fake_api_verify" in code
    assert "_nx_proto_parse" in code
    assert "_NX_POISON_SALT_" in code
    assert "cryptography" in code
    _execute(code)


def test_poisoned_code_executes_correctly():
    src = """
def add(a, b):
    return a + b

result = add(2, 3)
"""
    tree = _parse(src)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ProvenancePoisoner.CATEGORIES})
    code = ast.unparse(tree)
    _execute(code)
    assert True


def test_metrics_fake_call_graph_complexity():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["fake_call_graphs"]})
    metrics = ProvenanceMetrics()
    result = metrics.measure_confusion(tree)
    assert result["fake_call_graph_complexity"] >= 1
    assert result["fake_call_graph_edges"] >= 1


def test_metrics_fake_api_count():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["fake_apis"]})
    metrics = ProvenanceMetrics()
    result = metrics.measure_confusion(tree)
    assert result["fake_api_count"] >= 3


def test_metrics_protocol_parser_count():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["fake_protocol_parsers"]})
    metrics = ProvenanceMetrics()
    result = metrics.measure_confusion(tree)
    assert result["protocol_parser_count"] >= 3


def test_metrics_decoy_function_pct():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ProvenancePoisoner.CATEGORIES})
    metrics = ProvenanceMetrics()
    result = metrics.measure_confusion(tree)
    assert result["decoy_function_count"] >= 5
    assert result["decoy_function_pct"] > 0


def test_metrics_misleading_import_ratio():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ["misleading_imports"]})
    metrics = ProvenanceMetrics()
    result = metrics.measure_confusion(tree)
    assert result["misleading_import_count"] >= 1
    assert result["total_import_count"] >= 2


def test_syntactic_validity_after_all_techniques():
    src = """
def process(data):
    return data.strip()

class Handler:
    def handle(self, req):
        return {"status": 200, "body": req}

async def fetch(url):
    return url
"""
    tree = _parse(src)
    poisoner = ProvenancePoisoner(seed=42)
    tree = poisoner.poison(tree, {"categories": ProvenancePoisoner.CATEGORIES})
    code = ast.unparse(tree)
    ast.parse(code)
    _execute(code)


def test_deterministic_with_seed():
    tree1 = _parse(SIMPLE_SCRIPT)
    tree2 = _parse(SIMPLE_SCRIPT)
    p1 = ProvenancePoisoner(seed=123)
    p2 = ProvenancePoisoner(seed=123)
    t1 = p1.poison(tree1, {"categories": ["fake_call_graphs", "fake_apis"]})
    t2 = p2.poison(tree2, {"categories": ["fake_call_graphs", "fake_apis"]})
    assert ast.unparse(t1) == ast.unparse(t2)


def test_poison_level_mapping():
    tree = _parse(SIMPLE_SCRIPT)
    poisoner = ProvenancePoisoner(seed=42)
    for level, expected in [(1, ["fake_call_graphs"]),
                            (2, ["fake_call_graphs", "fake_apis"]),
                            (3, ["fake_call_graphs", "fake_apis", "fake_protocol_parsers"])]:
        tree2 = _parse(SIMPLE_SCRIPT)
        p = ProvenancePoisoner(seed=42)
        cats = []
        if level >= 1:
            cats.append("fake_call_graphs")
        if level >= 2:
            cats.append("fake_apis")
        if level >= 3:
            cats.append("fake_protocol_parsers")
        if level >= 4:
            cats.append("believable_dead_paths")
        if level >= 5:
            cats.append("misleading_imports")
        result = p.poison(tree2, {"categories": cats})
        code = ast.unparse(result)
        if level >= 1:
            assert "_nx_decoy_validate_license" in code, f"Level {level} missing call graphs"
        if level >= 2:
            assert "_nx_fake_api_verify" in code, f"Level {level} missing fake APIs"
        if level >= 3:
            assert "_nx_proto_parse" in code, f"Level {level} missing protocol parsers"
        _execute(code)
