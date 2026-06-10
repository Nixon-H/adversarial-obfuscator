import time
import os
import sys
import subprocess
import pytest

OBFUSCATOR_PATH = "15(14).py"


def _run_obfuscator_code(payload: str) -> subprocess.CompletedProcess:
    """Run Python code that inspects the obfuscator source via subprocess.

    The subprocess parses ``15(14).py``, extracts classes/functions by name,
    then exec()s them with the required imports already in scope.
    """
    script = rf"""
import sys, os, ast, warnings, random, hashlib, secrets, base64, time
sys.path.insert(0, '.')
sys.setrecursionlimit(10000)
warnings.filterwarnings("ignore")

with open('{OBFUSCATOR_PATH}', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

# -- extract helper -------------------------------------------------
def _extract(name, kind=(ast.FunctionDef, ast.ClassDef)):
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, kind) and node.name == name:
            return ast.unparse(node)
    raise NameError(f"{{name}} not found")

# -- pre-load deps used by the extracted code -----------------------
import_re = r'^import\s+'
import_lines = []
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.Import):
        import_lines.append(ast.unparse(node))
for line in import_lines:
    exec(compile(ast.parse(line), '<imports>', 'exec'))

{payload}
"""
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
        cwd="/home/nixon/Desktop/2",
    )


@pytest.mark.parametrize("transformer", ["TypeHintStripper", "FStringLowering"])
def test_ast_transformer_runs(transformer):
    code = f"""
cls_src = _extract('{transformer}')
exec(compile(ast.parse(cls_src), '<cls>', 'exec'))
tr = {transformer}()
t = ast.parse('x=1\\ny=2\\ndef f(): pass')
tr.visit(t)
ast.fix_missing_locations(t)
print('OK')
"""
    r = _run_obfuscator_code(code)
    assert r.returncode == 0, f"stderr: {r.stderr}"
    assert "OK" in r.stdout


def test_symbol_renamer_works():
    code = """
get_random_var_name = _extract('get_random_var_name')
exec(compile(ast.parse(get_random_var_name), '<dep>', 'exec'))
sr = _extract('SymbolRenamer')
exec(compile(ast.parse(sr), '<cls>', 'exec'))

tr = SymbolRenamer()
t = ast.parse('def my_func(a, b):\\n    return a + b')
tr.visit(t)
assert t.body[0].name.startswith('_nixon_'), f"Bad rename: {t.body[0].name}"
print('OK')
"""
    r = _run_obfuscator_code(code)
    assert r.returncode == 0, f"stderr: {r.stderr}"
    assert "OK" in r.stdout


def test_string_literal_obfuscator_works():
    code = """
get_random_var_name = _extract('get_random_var_name')
exec(compile(ast.parse(get_random_var_name), '<dep>', 'exec'))
slo = _extract('StringLiteralObfuscator')
exec(compile(ast.parse(slo), '<cls>', 'exec'))

slo = StringLiteralObfuscator()
t = ast.parse('x = "secretsauce"')
slo.visit(t)
assert not isinstance(t.body[0].value, ast.Constant), "String wasn't obfuscated"
assert isinstance(t.body[0].value, ast.Call), "Expected Call node after obfuscation"
print('OK')
"""
    r = _run_obfuscator_code(code)
    assert r.returncode == 0, f"stderr: {r.stderr}"
    assert "OK" in r.stdout
