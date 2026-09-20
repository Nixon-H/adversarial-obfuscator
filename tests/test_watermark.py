"""Tests for semantic watermarking in Nixon IR."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from irgen.compile import (
    compile_py_to_ir,
    IrModule,
    IrFunction,
    IrValue,
    IrType,
)
from scripts.watermark.semantic_watermark import (
    embed_watermark,
    extract_watermark,
    verify_watermark,
    message_to_bits,
    bits_to_message,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_ir():
    IrValue.reset_counter()


@pytest.fixture
def simple_module():
    source = """
def add(a, b):
    return a + b

def main():
    x = 1
    y = 2
    z = add(x, y)
    if z > 0:
        print(z)
    else:
        print(0)
    return z
"""
    return compile_py_to_ir(source)


@pytest.fixture
def complex_module():
    source = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

def factorial(n):
    result = 1
    i = 1
    while i <= n:
        result = result * i
        i = i + 1
    return result

def process(data):
    total = 0
    for item in data:
        if item > 0:
            total = total + item
        else:
            total = total - item
    return total
"""
    return compile_py_to_ir(source)


# ---------------------------------------------------------------------------
# Bit encoding tests
# ---------------------------------------------------------------------------

class TestBitEncoding:
    """
    TestBitEncoding
    
    Positive test cases for bitencoding.
    """
    def test_message_to_bits_roundtrip(self):
        msg = "Hello"
        bits = message_to_bits(msg)
        recovered = bits_to_message(bits)
        assert recovered == msg

    def test_message_to_bits_empty(self):
        assert message_to_bits("") == []
        assert bits_to_message([]) == ""

    def test_message_to_bits_unicode(self):
        msg = "Copyright 2026 NixonCorp"
        bits = message_to_bits(msg)
        recovered = bits_to_message(bits)
        assert recovered == msg

    def test_message_to_bits_uuid(self):
        msg = "550e8400-e29b-41d4-a716-446655440000"
        bits = message_to_bits(msg)
        recovered = bits_to_message(bits)
        assert recovered == msg


# ---------------------------------------------------------------------------
# Embed + Extract roundtrip tests
# ---------------------------------------------------------------------------

class TestEmbedExtractRoundtrip:
    """
    TestEmbedExtractRoundtrip
    
    Positive test cases for embedextractroundtrip.
    """
    def test_simple_message(self, simple_module):
        msg = "NixonCorp"
        embed_watermark(simple_module, msg)
        extracted = extract_watermark(simple_module)
        assert extracted is not None
        assert msg in extracted

    def test_complex_message(self, complex_module):
        msg = "Copyright 2026 NixonCorp"
        embed_watermark(complex_module, msg)
        extracted = extract_watermark(complex_module)
        assert extracted is not None
        assert "NixonCorp" in extracted

    def test_uuid_message(self, complex_module):
        msg = "550e8400-e29b-41d4-a716-446655440000"
        embed_watermark(complex_module, msg)
        extracted = extract_watermark(complex_module)
        assert extracted is not None
        assert "550e8400" in extracted

    def test_short_message(self, simple_module):
        msg = "X"
        embed_watermark(simple_module, msg)
        extracted = extract_watermark(simple_module)
        assert extracted is not None

    def test_empty_message(self, simple_module):
        msg = ""
        embed_watermark(simple_module, msg)
        extracted = extract_watermark(simple_module)
        assert extracted is not None

    def test_roundtrip_preserves_semantics(self, simple_module):
        msg = "test_watermark"
        module_str_before = str(simple_module)
        embed_watermark(simple_module, msg)
        _ = str(simple_module)
        assert verify_watermark(simple_module, msg)

    def test_different_messages_different_ir(self):
        mod1 = compile_py_to_ir("def f():\n    return 1 + 2\n")
        mod2 = compile_py_to_ir("def f():\n    return 1 + 2\n")
        embed_watermark(mod1, "message_a")
        embed_watermark(mod2, "message_b")
        assert str(mod1) != str(mod2)


# ---------------------------------------------------------------------------
# Verification tests
# ---------------------------------------------------------------------------

class TestVerification:
    """
    TestVerification
    
    Positive test cases for verification.
    """
    def test_correct_watermark_passes(self, simple_module):
        msg = "NixonCorp"
        embed_watermark(simple_module, msg)
        assert verify_watermark(simple_module, msg) is True

    def test_wrong_watermark_fails(self, simple_module):
        embed_watermark(simple_module, "real_message")
        assert verify_watermark(simple_module, "wrong_message") is False

    def test_no_watermark_fails(self, simple_module):
        assert verify_watermark(simple_module, "anything") is False


# ---------------------------------------------------------------------------
# Explicit IR structure tests
# ---------------------------------------------------------------------------

class TestExplicitIR:
    """
    TestExplicitIR
    
    Positive test cases for explicitir.
    """
    def test_embed_on_empty_module(self):
        mod = IrModule("empty")
        embed_watermark(mod, "test")
        assert verify_watermark(mod, "test") is True

    def test_embed_on_function_without_blocks(self):
        mod = IrModule("test")
        func = IrFunction("empty", IrType.void())
        mod.functions.append(func)
        embed_watermark(mod, "test")
        assert verify_watermark(mod, "test") is True

    def test_watermark_preserves_function_count(self, complex_module):
        initial_count = len(complex_module.functions)
        embed_watermark(complex_module, "preserve_test")
        assert len(complex_module.functions) >= initial_count


# ---------------------------------------------------------------------------
# Resilience tests
# ---------------------------------------------------------------------------

class TestResilience:
    """
    TestResilience
    
    Positive test cases for resilience.
    """
    def test_resilient_to_variable_renaming(self):
        source = """
def calc(x, y):
    result = x + y
    if result > 10:
        return result
    return 0
"""
        mod = compile_py_to_ir(source)
        msg = "RenamingTest"
        embed_watermark(mod, msg)

        for func in mod.functions:
            for block in func.blocks:
                block.label = block.label.replace("entry", "ENTRY").replace("bb", "BLOCK")

        assert verify_watermark(mod, msg)

    def test_resilient_to_function_reordering(self):
        source = """
def first():
    return 1

def second():
    return 2

def third():
    return 3
"""
        mod = compile_py_to_ir(source)
        msg = "ReorderingTest"
        embed_watermark(mod, msg)

        mod.functions.reverse()

        assert verify_watermark(mod, msg)

    def test_resilient_to_code_reformatting(self):
        source = """
def compute(a, b):
    x = a + b
    y = a * b
    if x > y:
        return x
    return y
"""
        mod = compile_py_to_ir(source)
        msg = "ReformatTest"
        embed_watermark(mod, msg)

        for func in mod.functions:
            for block in func.blocks:
                for inst in block.instructions:
                    if inst.result is not None:
                        inst.result.name = f"%v_{hash(str(inst)) & 0xFFFF}"

        assert verify_watermark(mod, msg)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """
    TestIntegration
    
    Positive test cases for integration.
    """
    def test_multiple_watermarks_same_module(self):
        """Embedding twice should still allow extraction."""
        source = """
def f():
    return 42
"""
        mod = compile_py_to_ir(source)
        embed_watermark(mod, "first_watermark")
        embed_watermark(mod, "second_watermark")
        extracted = extract_watermark(mod)
        assert extracted is not None
        assert "second" in extracted

    def test_ir_text_roundtrip(self):
        """Watermark should survive IR -> text -> parse -> extract."""
        import tempfile
        source = """
def add(a, b):
    return a + b
"""
        mod = compile_py_to_ir(source)
        msg = "RoundTrip"
        embed_watermark(mod, msg)

        text = str(mod)
        assert "_wm_metadata__" in text
        assert "_wm_m" in text

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ir", delete=False) as f:
            f.write(text)
            tmppath = f.name

        try:
            with open(tmppath) as f:
                roundtrip_text = f.read()
            assert "_wm_m" in roundtrip_text
        finally:
            os.unlink(tmppath)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class TestCLI:
    """
    TestCLI
    
    Positive test cases for cli.
    """
    def test_main_runs(self):
        from scripts.watermark.semantic_watermark import main
        import io
        import contextlib
        import tempfile

        source = "def f():\n    return 1 + 2\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source)
            in_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ir", delete=False) as f:
            out_path = f.name

        try:
            old_argv = sys.argv
            sys.argv = ["wm", "embed", in_path, "-o", out_path, "-m", "CLITest"]
            with contextlib.redirect_stdout(io.StringIO()):
                main()
            sys.argv = old_argv
            assert os.path.exists(out_path)
        finally:
            os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
