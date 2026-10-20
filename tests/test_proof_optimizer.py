import json
import os

from scripts.optimizer.proof_aware import ProofAwareOptimizer, PROVEN_PROTECTIONS, UNPROVEN_PROTECTIONS
from scripts.optimizer.profiler import FunctionInfo
from scripts.optimizer.cost_optimizer import PROTECTION_COSTS


def _make_function(name: str, loc: int = 10, freq: float = 1.0, cat: str = "general") -> FunctionInfo:
    return FunctionInfo(name=name, lines_of_code=loc, exec_frequency=freq, category=cat)


def test_prefers_proven_protections():
    optimizer = ProofAwareOptimizer(max_overhead_pct=50.0, max_size_mult=5.0, min_security=0.0)
    functions = [_make_function("test_fn", loc=5, freq=1.0)]
    proofs = {
        "ast_rename": True,
        "ast_dead_code": True,
        "ast_mba": True,
        "cfg_flatten": True,
        "vm_exec": False,
        "jit_compile": False,
    }
    assignment = optimizer.optimize_with_proofs(functions, proofs)
    assert "test_fn" in assignment
    assigned = assignment["test_fn"]
    proven_in_assignment = [p for p in assigned if proofs.get(p, False)]
    assert len(proven_in_assignment) > 0, (
        f"Expected at least one proven protection in assignment, got {assigned}"
    )


def test_avoids_unproven_when_possible():
    optimizer = ProofAwareOptimizer(max_overhead_pct=10.0, max_size_mult=1.5, min_security=0.0)
    functions = [_make_function("small_fn", loc=3, freq=0.5)]
    proofs = {
        p: False for p in PROTECTION_COSTS.keys()
    }
    proofs["ast_rename"] = True
    assignment = optimizer.optimize_with_proofs(functions, proofs)
    assigned = assignment.get("small_fn", [])
    assert "ast_rename" in assigned, "ast_rename should always be assigned"


def test_budget_respected():
    optimizer = ProofAwareOptimizer(max_overhead_pct=1.0, max_size_mult=1.1, min_security=0.0)
    functions = [_make_function("budget_fn", loc=100, freq=10.0)]
    proofs = {
        "ast_rename": True,
        "vm_exec": False,
        "oram_exec": False,
    }
    assignment = optimizer.optimize_with_proofs(functions, proofs)
    total_cpu = sum(
        (PROTECTION_COSTS[p]["cpu"] - 1.0) * functions[0].exec_frequency * max(functions[0].lines_of_code, 1)
        for p in assignment.get("budget_fn", [])
        if p in PROTECTION_COSTS
    )
    total_weight = functions[0].exec_frequency * max(functions[0].lines_of_code, 1)
    cpu_pct = (total_cpu / total_weight) * 100 if total_weight else 0
    assert cpu_pct <= 2.0, f"CPU overhead {cpu_pct:.1f}% should be within budget"


def test_integration_with_cost_optimizer():
    optimizer = ProofAwareOptimizer(max_overhead_pct=30.0, max_size_mult=3.0, min_security=0.3)
    functions = [
        _make_function("fn_a", loc=20, freq=2.0, cat="crypto"),
        _make_function("fn_b", loc=5, freq=0.5, cat="simple_helper"),
    ]
    proofs = {p: True for p in PROTECTION_COSTS.keys()}
    assignment = optimizer.optimize_with_proofs(functions, proofs)
    assert "fn_a" in assignment
    assert "fn_b" in assignment
    for fn_name in assignment:
        assert len(assignment[fn_name]) > 0


def test_proof_confidence_map():
    optimizer = ProofAwareOptimizer()
    for p in PROVEN_PROTECTIONS:
        assert p in optimizer._confidence_map
    for p in UNPROVEN_PROTECTIONS:
        assert p in optimizer._confidence_map


def test_update_proof_status():
    optimizer = ProofAwareOptimizer()
    optimizer.update_proof_status({"ast_rename": False})
    conf = optimizer._confidence_map.get("ast_rename", 0.0)
    assert conf < 0.7, f"ast_rename should have lower confidence when unproven, got {conf}"


def test_generate_proof_report():
    optimizer = ProofAwareOptimizer(max_overhead_pct=30.0, max_size_mult=3.0, min_security=0.3)
    functions = [_make_function("report_fn", loc=10, freq=1.0)]
    proofs = {"ast_rename": True, "ast_dead_code": True}
    assignment = optimizer.optimize_with_proofs(functions, proofs)
    report = optimizer.generate_proof_report(functions, assignment, proofs)
    assert "Proof-Aware Optimizer Report" in report
    assert "report_fn" in report


def test_optimize_fallback():
    optimizer = ProofAwareOptimizer()
    functions = [_make_function("fallback_fn")]
    assignment = optimizer.optimize(functions, list(PROTECTION_COSTS.keys()))
    assert "fallback_fn" in assignment


def test_proofs_from_certificate_directory():
    import tempfile
    import shutil
    base_dir = tempfile.mkdtemp()
    try:
        cert_dir = os.path.join(base_dir, "certificates")
        vm_dir = os.path.join(base_dir, "proofs", "vm")
        os.makedirs(cert_dir, exist_ok=True)
        os.makedirs(vm_dir, exist_ok=True)

        cert = {
            "pass_name": "obfuscation",
            "input_hash": "a",
            "output_hash": "b",
            "equivalence_proof": {"equivalent": True},
            "duration_ms": 1.0,
            "timestamp": "2025-01-01T00:00:00Z",
            "validated": True,
        }
        with open(os.path.join(cert_dir, "cert_0000_obfuscation.json"), "w") as f:
            json.dump(cert, f)

        vm_cert = {
            "pass_name": "vm_correctness",
            "input_hash": "c",
            "output_hash": "d",
            "equivalence_proof": {"equivalent": True},
            "duration_ms": 1.0,
            "timestamp": "2025-01-01T00:00:00Z",
            "validated": True,
        }
        with open(os.path.join(vm_dir, "vm_proof_add.json"), "w") as f:
            json.dump(vm_cert, f)

        proofs = {
            "ast_rename": False,
            "ast_dead_code": False,
            "ast_mba": False,
            "cfg_flatten": False,
            "vm_exec": False,
            "jit_compile": False,
            "rop_exec": False,
        }
        for fname in sorted(os.listdir(cert_dir)):
            if fname.endswith(".json") and fname != "certificate_chain.json":
                fpath = os.path.join(cert_dir, fname)
                with open(fpath) as _f:
                    cert_data = json.load(_f)
                pass_name = cert_data.get("pass_name", "")
                validated = cert_data.get("validated", False)
                if validated and pass_name == "obfuscation":
                    proofs["ast_rename"] = True
                    proofs["ast_dead_code"] = True
                    proofs["ast_mba"] = True
                    proofs["cfg_flatten"] = True

        if os.path.isdir(vm_dir):
            vm_pass = True
            for fname in sorted(os.listdir(vm_dir)):
                if fname.endswith(".json"):
                    with open(os.path.join(vm_dir, fname)) as _f:
                        data = json.load(_f)
                    if not data.get("validated", False):
                        vm_pass = False
                        break
            proofs["vm_exec"] = vm_pass

        optimizer = ProofAwareOptimizer(max_overhead_pct=50.0, max_size_mult=5.0, min_security=0.0)
        functions = [_make_function("cert_test_fn", loc=5, freq=1.0)]
        assignment = optimizer.optimize_with_proofs(functions, proofs)
        assert "cert_test_fn" in assignment
        assigned = assignment["cert_test_fn"]
        ast_proven = "ast_rename" in assigned
        assert ast_proven, "ast_rename should be assigned when certificate-based proof is True"
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)
