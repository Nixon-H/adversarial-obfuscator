import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestClassification:
    def test_extract_decorations_crown_jewel(self):
        from obfuscator.classification import extract_decorations
        src = """
@protect('crown_jewel')
def decrypt_data():
    pass

@protect('standard')
def helper():
    pass
"""
        dec = extract_decorations(src)
        assert dec == {"decrypt_data": "crown_jewel", "helper": "standard"}

    def test_extract_decorations_jit(self):
        from obfuscator.classification import extract_decorations
        src = """
@protect('jit')
def hot_path():
    pass
"""
        dec = extract_decorations(src)
        assert dec == {"hot_path": "jit_target"}

    def test_extract_decorations_no_protect(self):
        from obfuscator.classification import extract_decorations
        src = "def foo():\n    pass"
        assert extract_decorations(src) == {}

    def test_extract_decorations_syntax_error(self):
        from obfuscator.classification import extract_decorations
        assert extract_decorations("def foo(:") == {}

    def test_extract_decorations_async(self):
        from obfuscator.classification import extract_decorations
        src = """
@protect('crown_jewel')
async def process():
    pass
"""
        dec = extract_decorations(src)
        assert dec == {"process": "crown_jewel"}

    def test_classify_functions_standard_default(self):
        from obfuscator.classification import classify_functions
        src = "def simple():\n    return 1\n"
        result = classify_functions(src)
        assert result == {"simple": "standard"}

    def test_classify_functions_explicit_wins(self):
        from obfuscator.classification import classify_functions
        src = """
@protect('crown_jewel')
def small():
    return 42
"""
        result = classify_functions(src)
        assert result == {"small": "crown_jewel"}

    def test_classify_functions_crypto_heuristic(self):
        from obfuscator.classification import classify_functions
        src = """
def encrypt_data(key):
    from Crypto.Cipher import AES
    cipher = AES.new(key)
    return cipher.encrypt(b'data')
"""
        result = classify_functions(src)
        assert result["encrypt_data"] in ("crown_jewel", "standard")

    def test_classify_functions_empty_source(self):
        from obfuscator.classification import classify_functions
        with pytest.raises(ValueError):
            classify_functions("def broken(")

    def test_classify_functions_with_config(self):
        from obfuscator.classification import classify_functions
        src = "def validate_license():\n    return True\n"
        config = {"crown_jewel_patterns": ["license"]}
        result = classify_functions(src, config)
        assert result == {"validate_license": "crown_jewel"}

    def test_classify_functions_jit_pattern(self):
        from obfuscator.classification import classify_functions
        src = "def early_init():\n    return 42\n"
        config = {"jit_patterns": ["init"]}
        result = classify_functions(src, config)
        assert result == {"early_init": "jit_target"}

    def test_generate_classification_report(self):
        from obfuscator.classification import generate_classification_report
        classifications = {"a": "standard", "b": "crown_jewel", "c": "jit_target"}
        src = "def a(): pass\ndef b(): pass\ndef c(): pass\n"
        report = generate_classification_report(classifications, src)
        assert "Classification Report" in report
        assert "Crown Jewel" in report
        assert "JIT Target" in report

    def test_generate_classification_report_empty(self):
        from obfuscator.classification import generate_classification_report
        report = generate_classification_report({}, "")
        assert "No functions found" in report
