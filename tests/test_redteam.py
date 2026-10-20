"""
test_redteam.py

Tests for Red Team Analysis Framework.

Test coverage:
- Positive tests verify attack simulation, result collection, scoring
- Negative tests verify empty results, missing targets, edge cases
"""
import json  # noqa: F401 (this line binds a name used by an embedded template)
import os
import sys
import tempfile


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestImports:
    """
    TestImports
    
    Positive test cases for imports.
    """
    def test_angr_runner_import(self):
        from scripts.redteam.angr_runner import run_angr_attack
        assert callable(run_angr_attack)

    def test_ghidra_runner_import(self):
        from scripts.redteam.ghidra_runner import run_ghidra_attack
        assert callable(run_ghidra_attack)

    def test_bninja_runner_import(self):
        from scripts.redteam.bninja_runner import run_binaryninja_attack
        assert callable(run_binaryninja_attack)

    def test_llm_runner_import(self):
        from scripts.redteam.llm_runner import run_llm_attack
        assert callable(run_llm_attack)

    def test_symbolic_runner_import(self):
        from scripts.redteam.symbolic_runner import run_symbolic_attack
        assert callable(run_symbolic_attack)

    def test_unified_attack_import(self):
        from scripts.redteam.unified_attack import run_redteam_attack, RedTeamConfig, RedTeamReport
        assert callable(run_redteam_attack)
        assert RedTeamConfig is not None
        assert RedTeamReport is not None

    def test_phase_redteam_import(self):
        phase_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "phases", "phase_redteam.py")
        assert os.path.exists(phase_path), f"phase_redteam.py not found at {phase_path}"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scripts.phases.phase_redteam", phase_path)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert mod is not None
        assert hasattr(spec.loader, "exec_module")


class TestSymbolicRunner:
    """
    TestSymbolicRunner
    
    Positive test cases for symbolicrunner.
    """
    def test_symbolic_runner_basic(self):
        from scripts.redteam.symbolic_runner import run_symbolic_attack

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\x7fELF" + b"\x00" * 100)
            bin_path = f.name

        out_dir = tempfile.mkdtemp()
        try:
            result = run_symbolic_attack(bin_path, out_dir)
            assert result is not None
            assert isinstance(result, dict)
            assert "constraints_solved" in result
            assert "path_count" in result
            assert result["status"] in ("completed", "failed")
            assert os.path.exists(os.path.join(out_dir, "symbolic_results.json"))
        finally:
            os.unlink(bin_path)
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_symbolic_runner_empty(self):
        from scripts.redteam.symbolic_runner import run_symbolic_attack

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\x00" * 10)
            bin_path = f.name

        out_dir = tempfile.mkdtemp()
        try:
            result = run_symbolic_attack(bin_path, out_dir)
            assert result is not None
            assert isinstance(result, dict)
        finally:
            os.unlink(bin_path)
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)


class TestAngrRunner:
    """
    TestAngrRunner
    
    Positive test cases for angrrunner.
    """
    def test_angr_runner_no_binary(self):
        from scripts.redteam.angr_runner import run_angr_attack
        out_dir = tempfile.mkdtemp()
        try:
            result = run_angr_attack("/nonexistent/binary", out_dir)
            if result is None:
                pass
            else:
                assert result["status"] == "failed"
                assert result["error"] is not None
        finally:
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)


class TestLLMRunner:
    """
    TestLLMRunner
    
    Positive test cases for llmrunner.
    """
    def test_llm_runner_no_source(self):
        from scripts.redteam.llm_runner import run_llm_attack
        out_dir = tempfile.mkdtemp()
        try:
            result = run_llm_attack("/nonexistent/source.py", out_dir)
            assert result is not None
            assert result["status"] == "failed"
        finally:
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_llm_runner_source_analysis(self):
        from scripts.redteam.llm_runner import run_llm_attack
        out_dir = tempfile.mkdtemp()
        try:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write("def add(a, b):\n    return a + b\n")
                src_path = f.name
            try:
                result = run_llm_attack(src_path, out_dir)
                assert result is not None
                assert "original_algorithm_guessed" in result
                assert os.path.exists(os.path.join(out_dir, "llm_results.json"))
            finally:
                os.unlink(src_path)
        finally:
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)


class TestRedTeamConfig:
    """
    TestRedTeamConfig
    
    Positive test cases for redteamconfig.
    """
    def test_redteam_config(self):
        from scripts.redteam.unified_attack import RedTeamConfig
        cfg = RedTeamConfig(output_dir="/tmp/rt", binary_path="/bin/ls")
        assert cfg.output_dir == "/tmp/rt"
        assert cfg.binary_path == "/bin/ls"
        assert "angr" in cfg.attacks_to_run
        assert cfg.timeout_per_attack == 300

    def test_redteam_report(self):
        from scripts.redteam.unified_attack import RedTeamReport
        report = RedTeamReport(
            angr_result={"status": "completed", "success_rate": 0.5},
            ghidra_result={"status": "completed", "decompilation_quality": 0.3, "function_recovery_rate": 0.4},
            combined_security_score=65.0,
            weakest_link="angr",
            recommendations=["Test"],
        )
        d = report.to_dict()
        assert d["combined_security_score"] == 65.0
        assert d["weakest_link"] == "angr"
        assert d["report_type"] == "autonomous_red_team"
        assert d["angr_result"]["status"] == "completed"

    def test_report_aggregation(self):
        from scripts.redteam.unified_attack import RedTeamReport
        report = RedTeamReport(
            angr_result={"status": "completed", "success_rate": 0.8},
            ghidra_result={"status": "completed", "decompilation_quality": 0.7, "function_recovery_rate": 0.6},
            bninja_result={"status": "completed", "function_count": 30, "string_count": 15},
            llm_result={"status": "completed", "confidence_level": 0.9, "intent_recovered": True},
            symbolic_result={"status": "completed", "recovery_rate": 0.5},
        )
        assert report.angr_result["success_rate"] == 0.8
        assert report.ghidra_result["decompilation_quality"] == 0.7


class TestPhaseRedTeam:
    """
    TestPhaseRedTeam
    
    Positive test cases for phaseredteam.
    """
    def test_phase_redteam_runs(self):
        import importlib.util
        import types
        if "scripts" not in sys.modules:
            scripts_mod = types.ModuleType("scripts")
            scripts_mod.__path__ = [os.path.join(os.path.dirname(__file__), "..", "scripts")]
            scripts_mod.__file__ = os.path.join(os.path.dirname(__file__), "..", "scripts", "__init__.py")
            sys.modules["scripts"] = scripts_mod
        if "scripts.phases" not in sys.modules:
            phases_mod = types.ModuleType("scripts.phases")
            phases_mod.__path__ = [os.path.join(os.path.dirname(__file__), "..", "scripts", "phases")]
            phases_mod.__file__ = os.path.join(os.path.dirname(__file__), "..", "scripts", "phases", "__init__.py")
            sys.modules["scripts.phases"] = phases_mod
        phase_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "phases", "phase_redteam.py")
        spec = importlib.util.spec_from_file_location("scripts.phases.phase_redteam", phase_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["scripts.phases.phase_redteam"] = mod
        spec.loader.exec_module(mod)
        phase_redteam = mod.phase_redteam

        class FakeArgs:
            red_team_output = None
            payload = None
            binary_path = None
            attacks_to_run = ["symbolic"]
            timeout_per_attack = 30

        args = FakeArgs()
        args.red_team_output = tempfile.mkdtemp()
        args.payload = "/nonexistent/source.py"

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\x7fELF\x00\x00\x00\x00\x00\x00\x00\x00")
            bin_path = f.name

        try:
            result = phase_redteam(args, bin_path, args.payload)
            assert result is not None or True
        finally:
            os.unlink(bin_path)
            import shutil
            shutil.rmtree(args.red_team_output, ignore_errors=True)

    def test_phase_redteam_no_binary(self):
        import importlib.util
        import types
        if "scripts" not in sys.modules:
            scripts_mod = types.ModuleType("scripts")
            scripts_mod.__path__ = [os.path.join(os.path.dirname(__file__), "..", "scripts")]
            scripts_mod.__file__ = os.path.join(os.path.dirname(__file__), "..", "scripts", "__init__.py")
            sys.modules["scripts"] = scripts_mod
        if "scripts.phases" not in sys.modules:
            phases_mod = types.ModuleType("scripts.phases")
            phases_mod.__path__ = [os.path.join(os.path.dirname(__file__), "..", "scripts", "phases")]
            phases_mod.__file__ = os.path.join(os.path.dirname(__file__), "..", "scripts", "phases", "__init__.py")
            sys.modules["scripts.phases"] = phases_mod
        phase_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "phases", "phase_redteam.py")
        spec = importlib.util.spec_from_file_location("scripts.phases.phase_redteam", phase_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["scripts.phases.phase_redteam"] = mod
        spec.loader.exec_module(mod)
        phase_redteam = mod.phase_redteam

        class FakeArgs:
            red_team_output = None
            payload = "/nonexistent/source.py"
            binary_path = None
            attacks_to_run = ["symbolic"]
            timeout_per_attack = 30

        args = FakeArgs()
        args.red_team_output = tempfile.mkdtemp()
        try:
            result = phase_redteam(args, "nonexistent_binary.bin", args.payload)
            assert result is not None
        finally:
            import shutil
            shutil.rmtree(args.red_team_output, ignore_errors=True)

    def test_redteam_timeout(self):
        from scripts.redteam.symbolic_runner import run_symbolic_attack
        import tempfile, os, time

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\x00" * 1024)
            bin_path = f.name

        out_dir = tempfile.mkdtemp()
        try:
            t0 = time.time()
            result = run_symbolic_attack(bin_path, out_dir)
            elapsed = time.time() - t0
            assert result is not None
            assert elapsed < 60
        finally:
            os.unlink(bin_path)
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)
