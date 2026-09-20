import ast
import json
import hashlib

from scripts.preservation.report import StageResult, PreservationReport
from scripts.preservation.engine import PreservationEngine
from scripts.preservation.stage_ast_ir import check_ast_ir
from scripts.preservation.stage_ir_llvm import check_ir_llvm


def _make_simple_ir():
    from irgen.compile import IrModule, IrFunction, IrType, IrBlock
    mod = IrModule("test")
    func = IrFunction("test_func", IrType.i32())
    mod.functions.append(func)
    entry = func.new_block("entry")
    return mod


def test_preservation_ast_ir():
    source = """
def f(x):
    return x + 1
"""
    tree = ast.parse(source)
    from irgen.compile import compile_py_to_ir
    ir_mod = compile_py_to_ir(source)
    result = check_ast_ir(tree, ir_mod)
    assert result.stage_name == "ast_ir"
    assert result.input_hash is not None
    assert result.output_hash is not None
    assert result.duration_ms >= 0


def test_preservation_report_format():
    report = PreservationReport(
        stages=[
            StageResult(
                stage_name="ast_ir", passed=True,
                input_hash="abc", output_hash="def",
                duration_ms=10.0,
            ),
        ],
        all_passed=True,
        total_duration_ms=10.0,
    )
    json_str = report.to_json()
    data = json.loads(json_str)
    assert data["all_passed"] == True
    assert len(data["stages"]) == 1
    assert data["stages"][0]["stage_name"] == "ast_ir"


def test_preservation_stage_tracking():
    engine = PreservationEngine()
    pipe_ctx = {"stage_fns": []}
    report = engine.run_all(pipe_ctx)
    assert isinstance(report, PreservationReport)
    # Without any stage_fns, the engine falls through to default checks
    # which will fail gracefully without source data
    assert report.all_passed is False
    assert len(report.stages) > 0


def test_preservation_identity():
    source = """
def f(x):
    return x
"""
    tree = ast.parse(source)
    from irgen.compile import compile_py_to_ir
    ir_mod = compile_py_to_ir(source)
    result = check_ast_ir(tree, ir_mod)
    assert result.stage_name == "ast_ir"


def test_preservation_stage_result():
    result = StageResult(
        stage_name="test", passed=True,
        input_hash="in", output_hash="out",
        counterexample=None, duration_ms=5.0,
    )
    d = result.to_dict()
    assert d["stage_name"] == "test"
    assert d["passed"] == True
    assert d["duration_ms"] == 5.0


def test_preservation_report_print_summary(capsys):
    report = PreservationReport(
        stages=[
            StageResult(
                stage_name="ast_ir", passed=True,
                input_hash="abc", output_hash="def",
                duration_ms=10.0,
            ),
        ],
        all_passed=True,
        total_duration_ms=10.0,
    )
    report.print_summary()
    captured = capsys.readouterr()
    assert "Preservation Report" in captured.out
    assert "PASS" in captured.out
    assert "ast_ir" in captured.out


def test_preservation_ir_llvm():
    source = """
def f(x):
    return x + 1
"""
    from irgen.compile import compile_py_to_ir
    from llvmgen.lower import lower_ir_to_llvm
    from scripts.validation.ir_to_smt import IRToSMT
    ir_module = compile_py_to_ir(source)
    ir_text = str(ir_module)
    llvm_ir = lower_ir_to_llvm(ir_text)
    result = check_ir_llvm(ir_module, llvm_ir)
    assert result.stage_name == "ir_llvm"
    assert result.input_hash is not None
    assert result.output_hash is not None
    assert result.duration_ms >= 0


def test_preservation_engine_check_stage():
    engine = PreservationEngine()
    from irgen.compile import compile_py_to_ir
    from scripts.validation.ast_to_smt import ASTToSMT
    from scripts.validation.ir_to_smt import IRToSMT
    source = """
def f(x):
    return x + 1
"""
    tree = ast.parse(source)
    ir_module = compile_py_to_ir(source)
    result = engine.check_stage(
        "test_stage", tree, ir_module,
        lambda x: (ASTToSMT().translate(x), ASTToSMT()),
        lambda x: (IRToSMT().translate(x), IRToSMT()),
    )
    assert result.stage_name == "test_stage"
    assert result.passed is not None
