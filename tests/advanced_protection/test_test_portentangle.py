import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestPortEntangle:

    def test_cpu_detection_returns_value(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "port_entangle::tests::test_detect_cpu_returns_value", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"CPU detection test failed:\n{result.stderr}"

    def test_timing_test_loop_nonzero(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "port_entangle::tests::test_timing_test_loop_nonzero", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Timing loop test failed:\n{result.stderr}"

    def test_timing_test_loop_different_seeds(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "port_entangle::tests::test_timing_test_loop_different_seeds", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Different seeds test failed:\n{result.stderr}"

    def test_key_derivation_deterministic(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "port_entangle::tests::test_derive_key_deterministic_same_seed", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Deterministic key test failed:\n{result.stderr}"

    def test_ir_prologue_epilogue_generation(self):
        from irgen.port_entangle import PortEntanglementPass
        p = PortEntanglementPass('raptor_lake')
        prologue = p.generate_timing_prologue()
        epilogue = p.generate_timing_epilogue()
        assert 'port_entangle_t0' in prologue
        assert 'port_entangle_seed' in prologue
        assert 'port_entangle_t1' in epilogue
        assert 'port_entangle_corrupt' in epilogue

    def test_different_target_cpus_produce_different_configs(self):
        from irgen.port_entangle import PortEntanglementPass, CPU_PORT_MAP
        rpl = PortEntanglementPass('raptor_lake')
        zn4 = PortEntanglementPass('zen4')
        assert rpl.port_config != zn4.port_config
        assert rpl.port_config['alu_ports'] == 4
        assert zn4.port_config['load_ports'] == 3

    def test_apply_to_ir_modifies_input(self):
        from irgen.port_entangle import PortEntanglementPass
        p = PortEntanglementPass()
        ir = 'define i32 @test(i32 %x) {\nentry:\n  %r = add i32 %x, 1\n  ret i32 %r\n}\n'
        result = p.apply_to_ir(ir)
        assert 'port_entangle_t0' in result
        assert 'port_entangle_corrupt' in result
        assert 'port_entangle_seed' in result
        assert 'port_entangle_t1' in result
        assert '__rdtsc' in result
        assert 'entry:' in result

    def test_embed_timing_check_adds_rdtsc(self):
        from irgen.port_entangle import PortEntanglementPass
        p = PortEntanglementPass()
        ir = 'define i32 @test(i32 %x) {\nentry:\n  ret i32 %x\n}\n'
        result = p.embed_timing_check(ir, {'timing_threshold': 5000})
        assert '__rdtsc' in result
        assert '__corrupt_key' in result
        assert 'pe_t0' in result
        assert 'pe_t1' in result

    def test_embed_timing_check_hard_exit(self):
        from irgen.port_entangle import PortEntanglementPass
        p = PortEntanglementPass()
        ir = 'define i32 @test(i32 %x) {\nentry:\n  ret i32 %x\n}\n'
        result = p.embed_timing_check(ir, {'timing_threshold': 100, 'timing_hard_exit': True})
        assert 'pe_exit' in result

    def test_all_rust_tests_pass(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "port_entangle::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some port_entangle tests failed:\n{result.stderr}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if "test port_entangle::tests::" in line and "FAILED" in line:
                fail_count += 1
            elif "test port_entangle::tests::" in line and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} port_entangle tests FAILED"
        assert pass_count >= 9, f"Expected at least 9 passing tests, got {pass_count}"
