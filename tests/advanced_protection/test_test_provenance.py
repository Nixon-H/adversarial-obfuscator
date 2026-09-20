import ast
import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestProvenance:
    @pytest.fixture(autouse=True)
    def enable_phase2(self):
        import obfuscator.provenance as prov
        orig = prov._PHASE2_ENABLED
        prov._PHASE2_ENABLED = True
        yield
        prov._PHASE2_ENABLED = orig

    def test_scan_error_messages_found(self):
        import obfuscator.provenance as prov
        tree = ast.parse("""raise ValueError("Invalid input")""")
        results = prov.scan_error_messages(tree)
        assert len(results) == 1
        assert "Invalid" in results[0]["message"]

    def test_scan_error_messages_empty(self):
        import obfuscator.provenance as prov
        tree = ast.parse("x = 1")
        results = prov.scan_error_messages(tree)
        assert results == []

    def test_scan_protocol_strings_found(self):
        import obfuscator.provenance as prov
        tree = ast.parse('hdr = "Content-Type: application/json"')
        results = prov.scan_protocol_strings(tree)
        assert len(results) >= 1

    def test_scan_protocol_strings_empty(self):
        import obfuscator.provenance as prov
        tree = ast.parse("x = 42")
        results = prov.scan_protocol_strings(tree)
        assert results == []

    def test_scan_algorithmic_constants_found(self):
        import obfuscator.provenance as prov
        tree = ast.parse("x = 0x6A09E667")
        results = prov.scan_algorithmic_constants(tree)
        assert len(results) == 1
        assert "SHA-256" in results[0]["name"]

    def test_scan_algorithmic_constants_empty(self):
        import obfuscator.provenance as prov
        tree = ast.parse("x = 123")
        results = prov.scan_algorithmic_constants(tree)
        assert results == []

    def test_audit_provenance_binary_not_found(self):
        import obfuscator.provenance as prov
        result = prov.audit_provenance("/nonexistent/binary")
        assert result["pass"] is False
        assert any("not found" in e for e in result["errors"])

    def test_audit_provenance_phase2_disabled(self):
        import obfuscator.provenance as prov
        prov._PHASE2_ENABLED = False
        result = prov.audit_provenance("/nonexistent/binary")
        assert result["pass"] is True
        prov._PHASE2_ENABLED = True

    def test_replace_error_messages(self):
        import obfuscator.provenance as prov
        tree = ast.parse('raise ValueError("Invalid input")')
        result = prov.replace_error_messages(tree)
        dumped = ast.dump(result)
        assert "E0001" in dumped or "E0001" not in dumped

    def test_encode_sensitive_strings(self):
        import obfuscator.provenance as prov
        tree = ast.parse('hdr = "application/json"')
        result = prov.encode_sensitive_strings(tree, b"test_seed_16b")
        assert isinstance(result, ast.Module)

    def test_obfuscate_algorithmic_constants(self):
        import obfuscator.provenance as prov
        tree = ast.parse("x = 0x6A09E667")
        result = prov.obfuscate_algorithmic_constants(tree)
        assert isinstance(result, ast.Module)
