import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestTimingInjection:
    SOURCE = """
def compute(x):
    return x * 2

def process(data):
    result = 0
    for d in data:
        result += d
    return result
"""

    def test_inject_timing_checks_adds_import(self):
        from obfuscator.timing_traps import inject_timing_checks
        result = inject_timing_checks(self.SOURCE, {})
        assert "import time" in result

    def test_inject_timing_checks_adds_timing_vars(self):
        from obfuscator.timing_traps import inject_timing_checks
        result = inject_timing_checks(self.SOURCE, {})
        assert "_t0_" in result
        assert "_t1_" in result

    def test_inject_timing_checks_default_threshold(self):
        from obfuscator.timing_traps import inject_timing_checks
        result = inject_timing_checks(self.SOURCE, {})
        assert "perf_counter_ns" in result

    def test_inject_timing_checks_hard_exit(self):
        from obfuscator.timing_traps import inject_timing_checks
        config = {"timing_hard_exit": True, "timing_threshold": 500}
        result = inject_timing_checks(self.SOURCE, config)
        assert "sys.exit" in result or "exit" in result

    def test_inject_timing_checks_silent_degradation(self):
        from obfuscator.timing_traps import inject_timing_checks
        config = {"timing_hard_exit": False, "timing_threshold": 1000}
        result = inject_timing_checks(self.SOURCE, config)
        assert "degradation" in result or "print" in result

    def test_inject_timing_checks_empty_source(self):
        from obfuscator.timing_traps import inject_timing_checks
        result = inject_timing_checks("", {})
        assert "import time" in result

    def test_inject_timing_checks_small_function(self):
        from obfuscator.timing_traps import inject_timing_checks
        src = "def f():\n    return 42\n"
        result = inject_timing_checks(src, {})
        assert "def f()" in result
        assert "_t0_" in result
        assert "_t1_" in result

    def test_generate_rdtsc_ir_pattern(self):
        from obfuscator.timing_traps import generate_rdtsc_ir_pattern
        ir = generate_rdtsc_ir_pattern({"timing_threshold": 5000})
        assert "@__rdtsc" in ir
        assert "@__timing_trap" in ir
        assert "5000" in ir

    def test_generate_rdtsc_ir_pattern_hard_exit(self):
        from obfuscator.timing_traps import generate_rdtsc_ir_pattern
        ir = generate_rdtsc_ir_pattern({"timing_threshold": 100, "timing_hard_exit": True})
        assert "degradation_exit" in ir
        assert "exit" in ir
