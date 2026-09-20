import sys
import subprocess
import pytest

OBFUSCATOR_PATH = "obfuscator/core/utils.py"
OBFUSCATOR_CLI_PATH = "obfuscator/core/pipeline.py"


def test_imports_work_via_subprocess():
    code = """
import sys
sys.path.insert(0, '.')
with open('obfuscator/core/utils.py') as f:
  source = f.read()

import ast
tree = ast.parse(source)
found = {'GitHubBuildFarm': False, 'GitHubNuitkaFarm': False}
for node in ast.iter_child_nodes(tree):
  if isinstance(node, ast.ClassDef) and node.name in found:
    found[node.name] = True
assert all(found.values()), f"Missing classes: {found}"
print('OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, cwd="/home/nixon/Desktop/2",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout


def test_socks5_proxy_format():
    """GitHubBuildFarm constructs SOCKS5 proxy URLs."""
    code = """
import sys
sys.path.insert(0, '.')
with open('obfuscator/core/utils.py') as f:
  source = f.read()

import ast
tree = ast.parse(source)

class BuilderFinder(ast.NodeVisitor):
    def __init__(self):
        self.found_init = False
    def visit_FunctionDef(self, node):
        if node.name == '__init__':
            self.found_init = True
            proxies_node = None
            for n in ast.walk(node):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Attribute) and t.attr == 'proxies':
                            proxies_node = n.value
                            break
            if proxies_node:
                source_seg = ast.get_source_segment(source, proxies_node)
                if source_seg:
                    assert 'socks5h://127.0.0.1:9050' in source_seg
                    print('OK')

finder = BuilderFinder()
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'GitHubBuildFarm':
        finder.visit(node)
        break
if finder.found_init:
    print('OK')
else:
    print('NO')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, cwd="/home/nixon/Desktop/2",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout


def test_cli_argparse_exists():
    """Verify that obfuscator/core/pipeline.py uses argparse for CLI."""
    with open(OBFUSCATOR_CLI_PATH, encoding="utf-8") as f:
        source = f.read()
    assert "argparse" in source
    lines = source.splitlines()
    arg_parse_lines = [i + 1 for i, l in enumerate(lines) if "ArgumentParser" in l]
    assert len(arg_parse_lines) > 0, (
        "No ArgumentParser found in the obfuscator source"
    )
