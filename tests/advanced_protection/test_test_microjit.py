import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestMicroJIT:

    def test_microjit_generates_valid_prologue(self):
        from irgen.microjit import MicroJITEngine
        engine = MicroJITEngine(seed=42)
        prologue = engine.generate_prologue()
        assert isinstance(prologue, bytes)
        assert len(prologue) > 0
        assert len(prologue) < 256

    def test_microjit_generates_valid_epilogue(self):
        from irgen.microjit import MicroJITEngine
        engine = MicroJITEngine(seed=42)
        epilogue = engine.generate_epilogue()
        assert isinstance(epilogue, bytes)
        assert len(epilogue) > 0
        assert len(epilogue) < 256

    def test_microjit_nops_are_diverse(self):
        from irgen.microjit import MicroJITEngine, _NOP_TEMPLATES
        engine = MicroJITEngine(seed=1)
        sled = engine.generate_nop_sled(64)
        assert isinstance(sled, bytes)
        assert len(sled) == 64
        seen = set()
        for t in _NOP_TEMPLATES:
            if t in sled:
                seen.add(t)
        assert len(seen) >= 3

    def test_microjit_polymorphic_rewrite_different_seeds(self):
        from irgen.microjit import MicroJITEngine
        block = bytes([0x48, 0x31, 0xc0, 0xc3])
        e1 = MicroJITEngine(seed=1)
        e2 = MicroJITEngine(seed=2)
        r1 = e1.polymorphic_rewrite(block)
        r2 = e2.polymorphic_rewrite(block)
        assert r1 != r2

    def test_microjit_register_swap_changes_code(self):
        from irgen.microjit import MicroJITEngine
        engine = MicroJITEngine(seed=0)
        code = bytes([0x48, 0x89, 0xd0])
        reg_map = {0: 1, 1: 0, 2: 3, 3: 2, 4: 5, 5: 4, 6: 7, 7: 6}
        swapped = engine.swap_registers(code, reg_map)
        assert swapped != code

    def test_microjit_stack_offset_alteration(self):
        from irgen.microjit import MicroJITEngine
        engine = MicroJITEngine(seed=0)
        code = bytes([0x48, 0x89, 0x45, 0xf8])
        altered = engine.alter_stack_offsets(code, 16)
        assert altered != code

    def test_microjit_polymorphic_rewrite_deterministic(self):
        from irgen.microjit import MicroJITEngine
        block = bytes([0x48, 0x31, 0xc0, 0xc3])
        e1 = MicroJITEngine(seed=42)
        e2 = MicroJITEngine(seed=42)
        assert e1.polymorphic_rewrite(block) == e2.polymorphic_rewrite(block)

    def test_microjit_random_register_map(self):
        from irgen.microjit import MicroJITEngine
        engine = MicroJITEngine(seed=7)
        m1 = engine.generate_random_register_map()
        m2 = engine.generate_random_register_map()
        assert m1 != m2
        assert set(m1.keys()) == set(range(8))
        assert set(m1.values()) == set(range(8))

    def test_rust_register_randomization(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "jit::tests::test_randomize_register_allocation", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Rust register test failed:\n{result.stderr}"

    def test_rust_nop_insertion(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "jit::tests::test_insert_functional_nops", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Rust NOP test failed:\n{result.stderr}"

    def test_rust_polymorphic_jit_compile(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "jit::tests::test_polymorphic_jit_compile_runs", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Rust JIT compile test failed:\n{result.stderr}"
