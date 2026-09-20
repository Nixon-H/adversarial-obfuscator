"""
bench_redteam.py

Benchmarks for autonomous red team pipeline.

Measures attack runner initialization and result collection performance.
"""
import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestRedTeamBenchmarks:
    """Benchmark red team pipeline performance."""

    @pytest.fixture
    def test_binary(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\x7fELF" + b"\x00" * 1024)
            bin_path = f.name
        yield bin_path
        if os.path.exists(bin_path):
            os.unlink(bin_path)

    @pytest.fixture
    def test_source(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def add(a, b):\n    return a + b\n")
            src_path = f.name
        yield src_path
        if os.path.exists(src_path):
            os.unlink(src_path)

    @pytest.fixture
    def output_dir(self):
        d = tempfile.mkdtemp()
        yield d
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    def test_symbolic_analysis_time(self, test_binary, output_dir, benchmark):
        from scripts.redteam.symbolic_runner import run_symbolic_attack

        def run():
            return run_symbolic_attack(test_binary, output_dir)

        result = benchmark(run)
        assert result is not None
        assert "execution_time_ms" in result

    def test_report_generation_time(self, benchmark):
        from scripts.redteam.unified_attack import RedTeamReport, _compute_security_score, _find_weakest_link, _generate_recommendations

        report = RedTeamReport(
            angr_result={"status": "completed", "cfg_recovered": True, "num_functions_found": 10, "strings_recovered": ["a"], "symbolic_paths": 3, "success_rate": 0.6},
            ghidra_result={"status": "completed", "decompilation_quality": 0.5, "function_recovery_rate": 0.4, "strings_recovered": 5},
            bninja_result={"status": "completed", "function_count": 15, "string_count": 8, "strings_recovered": ["b"]},
            llm_result={"status": "completed", "intent_recovered": True, "confidence_level": 0.7, "original_algorithm_guessed": "addition", "deobfuscation_suggestions": ["rename vars"]},
            symbolic_result={"status": "completed", "constraints_solved": 4, "path_count": 3, "execution_time_ms": 100.0, "recovery_rate": 0.75},
        )

        def run():
            score = _compute_security_score(report)
            weak = _find_weakest_link(report)
            recs = _generate_recommendations(report)
            return score, weak, recs

        result = benchmark(run)
        assert len(result) == 3
        assert 0 <= result[0] <= 100

    def test_unified_orchestration_time(self, test_binary, test_source, output_dir, benchmark):
        from scripts.redteam.unified_attack import RedTeamConfig, RedTeamReport, run_redteam_attack

        class Args:
            red_team_output = None
            payload = None
            binary_path = None
            attacks_to_run = ["symbolic"]
            timeout_per_attack = 30

        args = Args()
        args.red_team_output = output_dir
        args.payload = test_source
        args.binary_path = test_binary

        def run():
            return run_redteam_attack(args)

        result = benchmark(run)
        assert result is not None
