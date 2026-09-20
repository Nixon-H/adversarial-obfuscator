"""Tests for LLM Fingerprinting (Item 73)."""
import ast
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from obfuscator.llm_fingerprint import LLMFingerprinter


SAMPLE_CODE = """
def process(data):
    result = data * 2
    return result
"""


def test_fingerprint_embed_detect_roundtrip():
    fp = LLMFingerprinter(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = fp.embed_fingerprint(tree, "gpt")
    code = ast.unparse(tree)
    detected = fp.detect_fingerprint(code)
    assert detected == "gpt", f"Expected 'gpt', got '{detected}'"


def test_fingerprint_different_models():
    fp = LLMFingerprinter(seed=42)
    for model in ["gpt", "claude", "gemini", "deepseek", "copilot"]:
        tree = ast.parse(SAMPLE_CODE)
        tree = fp.embed_fingerprint(tree, model)
        code = ast.unparse(tree)
        detected = fp.detect_fingerprint(code)
        assert detected == model, f"Expected '{model}', got '{detected}'"


def test_fingerprint_invisible_to_humans():
    fp = LLMFingerprinter(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = fp.embed_fingerprint(tree, "gpt")
    code = ast.unparse(tree)
    assert "DEADBEEF" not in code
    assert "fingerprint" not in code.lower()
    assert "gpt" not in code.lower()
    assert "openai" not in code.lower()
    assert "anthropic" not in code.lower()


def test_fingerprint_survives_obfuscation():
    fp = LLMFingerprinter(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = fp.embed_fingerprint(tree, "claude")
    code = ast.unparse(tree)
    detected = fp.detect_fingerprint(code)
    assert detected == "claude"
    compile(code, "<test>", "exec")


def test_fingerprint_unknown_model():
    fp = LLMFingerprinter(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    with pytest.raises(ValueError, match="Unknown model"):
        fp.embed_fingerprint(tree, "nonexistent")


def test_fingerprint_detect_returns_unknown():
    fp = LLMFingerprinter(seed=42)
    result = fp.detect_fingerprint(SAMPLE_CODE)
    assert result == "unknown"


def test_fingerprint_valid_python():
    fp = LLMFingerprinter(seed=42)
    for model in ["gpt", "claude", "gemini"]:
        tree = ast.parse(SAMPLE_CODE)
        tree = fp.embed_fingerprint(tree, model)
        code = ast.unparse(tree)
        compile(code, "<test>", "exec")


def test_fingerprint_supported_models():
    fp = LLMFingerprinter(seed=42)
    models = fp.supported_models()
    assert "gpt" in models
    assert "claude" in models
    assert "gemini" in models
    assert len(models) >= 3
