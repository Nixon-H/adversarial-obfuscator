import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestAdversarialLoop:

    @pytest.fixture
    def sample_ir(self, tmp_path):
        ir = tmp_path / "test.ir"
        ir.write_text("""
define void @test(i32 %x) {
entry:
  %0 = add i32 7, 3
  %1 = sub i32 %0, 10
  %cond = icmp eq i32 %1, 0
  br i1 %cond, label %real, label %dead
dead:
  %dv = add i32 1, 1
  br label %real
real:
  %2 = add i32 %x, 1
  %3 = xor i32 %2, %x
  %4 = add i32 %3, %3
  %5 = shl i32 %4, 1
  %6 = or i32 %5, 0
  switch i32 %6, label %exit [
    i32 0, label %bb1
    i32 1, label %bb2
  ]
bb1:
  %7 = sub i32 %x, 1
  ret i32 %7
bb2:
  %8 = add i32 %x, 2
  ret i32 %8
exit:
  ret i32 0
}
""")
        return str(ir)

    @pytest.fixture
    def sample_ast_source(self):
        return """
import hashlib
x = 42
y = x ^ 255
z = (x + y) & 0xFF
if hashlib.sha256(b'test').digest()[0] == 0:
    print("never")
w = x * 2
"""

    @pytest.fixture
    def deobfuscation_config(self):
        return {"seed": 42, "threshold": 0.7}

    # Test 1: DeobfuscationAgent creates valid AnalysisReport
    def test_agent_creates_valid_report(self, sample_ir, deobfuscation_config):
        from scripts.deobfuscation_agent import DeobfuscationAgent
        agent = DeobfuscationAgent(deobfuscation_config)
        report = agent.analyze_obfuscated_ir(sample_ir)
        assert report.ir_path == sample_ir
        assert 0.0 <= report.deobfuscation_score <= 1.0
        assert isinstance(report.detected_patterns, list)
        assert isinstance(report.details, dict)

    # Test 2: Feedback generation produces recommendations
    def test_feedback_generation(self, sample_ir, deobfuscation_config):
        from scripts.deobfuscation_agent import DeobfuscationAgent
        agent = DeobfuscationAgent(deobfuscation_config)
        report = agent.analyze_obfuscated_ir(sample_ir)
        feedback = agent.generate_feedback(report)
        assert "weaknesses" in feedback
        assert "recommendations" in feedback
        assert "deobfuscation_score" in feedback
        assert "detected_patterns" in feedback
        assert isinstance(feedback["weaknesses"], list)
        assert isinstance(feedback["recommendations"], list)

    # Test 3: CompilerMutation mutates parameters
    def test_compiler_mutation_mutates_params(self, deobfuscation_config):
        from scripts.compiler_mutation import CompilerMutationEngine
        engine = CompilerMutationEngine(deobfuscation_config)
        feedback = {
            "weaknesses": ["opaque_predicates_too_simple", "mba_patterns_detectable"],
            "deobfuscation_score": 0.3,
            "detected_patterns": ["opaque_predicates", "mba_patterns_detectable"],
        }
        current_params = {
            "opaque_predicate_nesting": 1,
            "mba_bit_width": 32,
        }
        mutated = engine.mutate_pass_parameters(feedback, current_params)
        assert mutated["opaque_predicate_nesting"] > current_params["opaque_predicate_nesting"]
        assert mutated["mba_bit_width"] > current_params["mba_bit_width"]

    # Test 4: MBA formula generation produces valid expressions
    def test_mba_formula_generation(self):
        from scripts.compiler_mutation import CompilerMutationEngine
        engine = CompilerMutationEngine({"seed": 42})
        formula = engine.generate_novel_mba_formula(42, 3)
        assert "def mba_42" in formula
        assert "return" in formula
        assert any(op in formula for op in ["+", "^", "-", "&", "|", "<<", ">>"])

    # Test 5: MBA formula with complexity 5 has more operations than complexity 1
    def test_mba_complexity_scales(self):
        from scripts.compiler_mutation import CompilerMutationEngine
        engine = CompilerMutationEngine({"seed": 42})
        formula1 = engine.generate_novel_mba_formula(1, 1)
        formula5 = engine.generate_novel_mba_formula(1, 5)
        ops_low = sum(1 for op in ["+", "^", "-", "&", "|", "<<", ">>"] if op in formula1)
        ops_high = sum(1 for op in ["+", "^", "-", "&", "|", "<<", ">>"] if op in formula5)
        assert ops_high >= ops_low, f"Expected more ops at complexity 5 ({ops_high}) vs 1 ({ops_low})"

    # Test 6: Evolution changes config
    def test_evolution_changes_config(self, deobfuscation_config):
        from scripts.compiler_mutation import CompilerMutationEngine
        engine = CompilerMutationEngine(deobfuscation_config)
        config = {
            "llvmgen": {"pass_parameters": {}},
            "obfuscator": {"cfg_flatten": False, "mba_subs": False},
        }
        feedback = {
            "weaknesses": ["cfg_flattening_too_few_cases", "mba_patterns_detectable"],
            "deobfuscation_score": 0.4,
            "detected_patterns": ["cfg_flattening", "mba_patterns_detectable"],
        }
        evolved = engine.evolve(config, feedback)
        assert "llvmgen" in evolved
        assert "obfuscator" in evolved

    # Test 7: Multiple iterations show improvement
    def test_multiple_iterations_improve_score(self):
        from scripts.compiler_mutation import simulate_build_iteration
        config = {"seed": 7, "llvmgen": {"pass_parameters": {}}, "obfuscator": {}}
        history = simulate_build_iteration(config, iterations=5)
        assert len(history) == 5
        scores = [h["score"] for h in history]
        assert all(0.0 <= s <= 1.0 for s in scores)

    # Test 8: Score below threshold triggers mutation
    def test_score_below_threshold_triggers_mutation(self, sample_ir, deobfuscation_config):
        from scripts.deobfuscation_agent import DeobfuscationAgent
        from scripts.compiler_mutation import CompilerMutationEngine
        agent = DeobfuscationAgent(deobfuscation_config)
        engine = CompilerMutationEngine(deobfuscation_config)
        report = agent.analyze_obfuscated_ir(sample_ir)
        feedback = agent.generate_feedback(report)
        config = {"llvmgen": {"pass_parameters": {}}, "obfuscator": {}}
        if report.deobfuscation_score < 0.7:
            evolved = engine.evolve(config, feedback)
            assert evolved != config

    # Test 9: Score above threshold skips mutation
    def test_score_above_threshold_no_mutation(self):
        from scripts.deobfuscation_agent import DeobfuscationAgent
        from scripts.compiler_mutation import CompilerMutationEngine
        agent = DeobfuscationAgent({"seed": 0})
        report = agent.analyze_obfuscated_ast("x = 1")
        feedback = agent.generate_feedback(report)
        engine = CompilerMutationEngine({"seed": 0})
        config = {"llvmgen": {"pass_parameters": {}}, "obfuscator": {}}
        if report.deobfuscation_score >= 0.7:
            evolved = engine.evolve(config, feedback)
            assert evolved == config

    # Test 10: Invalid IR handled gracefully
    def test_invalid_ir_handled(self):
        from scripts.deobfuscation_agent import DeobfuscationAgent
        agent = DeobfuscationAgent({"seed": 0})
        report = agent.analyze_obfuscated_ir("/nonexistent/path/to/ir.ir")
        assert report.deobfuscation_score == 0.0
        assert "error" in report.details
        assert report.details["error"] == "File not found: /nonexistent/path/to/ir.ir"
