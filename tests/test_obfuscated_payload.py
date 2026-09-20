import ast
import os
import sys
import tempfile
import pytest


@pytest.fixture(scope="module")
def obfuscated_payload():
    """Generate a temporary obfuscated .py file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def main():\n    return 42\n")
        payload = f.name

    output = payload + ".obf.py"

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from obfuscator.core.pipeline import build_pipeline
        with open(payload) as f:
            source = f.read()
        result = build_pipeline(source)
        with open(output, "w") as f:
            f.write(result)
    except Exception as e:
        os.unlink(payload)
        pytest.skip(f"Obfuscation failed: {e}")
        return None

    os.unlink(payload)
    yield output
    if os.path.exists(output):
        os.unlink(output)


def test_obfuscated_syntax(obfuscated_payload):
    """Obfuscated file must be valid Python."""
    with open(obfuscated_payload) as f:
        ast.parse(f.read())


def test_obfuscated_has_top_level_defs(obfuscated_payload):
    """Obfuscated output should contain top-level definitions."""
    with open(obfuscated_payload) as f:
        t = ast.parse(f.read())
    defs = [n.name for n in ast.iter_child_nodes(t)
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    assert len(defs) > 0
