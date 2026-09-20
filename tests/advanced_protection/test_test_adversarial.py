import ast
import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestAdversarial:

    SIMPLE_SOURCE = """import os
import sys

def greet(name):
    \"\"\"Greet a user by name.\"\"\"
    return f"Hello, {name}"

def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""

    def test_dead_code_inserted_after_imports(self):
        from obfuscator.adversarial import inject_adversarial_code
        result = inject_adversarial_code(self.SIMPLE_SOURCE, {"seed": 42, "level": 3})
        tree = ast.parse(result)
        imports = 0
        dead_after_imports = 0
        in_imports = True
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports += 1
            elif in_imports:
                in_imports = False
                # These should be dead code statements, not function defs
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    dead_after_imports += 1
        assert imports == 2, "Original imports should remain"
        assert dead_after_imports >= 1, "Dead code should appear after imports"

    def test_prompt_injection_strings_appear(self):
        from obfuscator.adversarial import (
            inject_adversarial_code,
            _PROMPT_STRINGS,
            _FAKE_COMMENTS,
        )
        result = inject_adversarial_code(self.SIMPLE_SOURCE, {
            "seed": 7, "level": 5, "prompt_injection": True,
        })
        found_any = False
        for s in _PROMPT_STRINGS:
            if s in result or s[:30] in result:
                found_any = True
                break
        assert found_any, "At least one prompt string should be embedded in output"

    def test_deterministic_with_same_seed(self):
        from obfuscator.adversarial import inject_adversarial_code
        config = {"seed": 99, "level": 4, "prompt_injection": True}
        r1 = inject_adversarial_code(self.SIMPLE_SOURCE, config)
        r2 = inject_adversarial_code(self.SIMPLE_SOURCE, config)
        assert r1 == r2, "Same seed should produce identical output"

    def test_different_output_with_different_seed(self):
        from obfuscator.adversarial import inject_adversarial_code
        r1 = inject_adversarial_code(self.SIMPLE_SOURCE, {"seed": 1, "level": 3})
        r2 = inject_adversarial_code(self.SIMPLE_SOURCE, {"seed": 999, "level": 3})
        assert r1 != r2, "Different seeds should produce different output"

    def test_invalid_source_handled_gracefully(self):
        from obfuscator.adversarial import inject_adversarial_code
        result = inject_adversarial_code("def foo(::", {"seed": 0, "level": 1})
        assert result == "def foo(::", "Invalid source should be returned unchanged"

    def test_empty_source_handled_gracefully(self):
        from obfuscator.adversarial import inject_adversarial_code
        assert inject_adversarial_code("", {}) == ""
        assert inject_adversarial_code("   ", {}) == "   "

    def test_multiple_injections_dont_break_syntax(self):
        from obfuscator.adversarial import inject_adversarial_code
        for level in range(1, 6):
            for seed in [0, 1, 42, 99]:
                result = inject_adversarial_code(self.SIMPLE_SOURCE, {
                    "seed": seed, "level": level, "prompt_injection": True,
                })
                try:
                    ast.parse(result)
                except SyntaxError as e:
                    pytest.fail(f"Syntax broken at level={level}, seed={seed}: {e}")

    def test_config_level_controls_aggressiveness(self):
        from obfuscator.adversarial import inject_adversarial_code
        results = {}
        for level in [1, 3, 5]:
            results[level] = inject_adversarial_code(self.SIMPLE_SOURCE, {
                "seed": 42, "level": level, "prompt_injection": True,
            })
        len1 = len(results[1])
        len3 = len(results[3])
        len5 = len(results[5])
        assert len3 >= len1, "Level 3 should be at least as large as level 1"
        assert len5 >= len3, "Level 5 should be at least as large as level 3"

    def test_dead_code_types_filter(self):
        from obfuscator.adversarial import inject_adversarial_code
        r_all = inject_adversarial_code(self.SIMPLE_SOURCE, {
            "seed": 42, "level": 3, "dead_code_types": None,
        })
        r_hash = inject_adversarial_code(self.SIMPLE_SOURCE, {
            "seed": 42, "level": 3, "dead_code_types": ["hashlib"],
        })
        assert "hashlib" in r_hash
        assert r_all != r_hash or "hashlib" in r_all, (
            "Filtered output should differ or already contain hashlib"
        )

    def test_prompt_injection_can_be_disabled(self):
        from obfuscator.adversarial import inject_adversarial_code
        enabled = inject_adversarial_code(self.SIMPLE_SOURCE, {
            "seed": 7, "level": 5, "prompt_injection": True,
        })
        disabled = inject_adversarial_code(self.SIMPLE_SOURCE, {
            "seed": 7, "level": 5, "prompt_injection": False,
        })
        assert len(disabled) < len(enabled) or disabled == self.SIMPLE_SOURCE, (
            "Disabling prompt injection should produce shorter or unchanged output"
        )

    def test_dead_code_injected_inside_function(self):
        from obfuscator.adversarial import inject_adversarial_code
        result = inject_adversarial_code(self.SIMPLE_SOURCE, {
            "seed": 42, "level": 4,
        })
        tree = ast.parse(result)
        func_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_count += 1
                assert len(node.body) >= 2, (
                    f"Function {node.name} should have dead code + original body"
                )
        assert func_count >= 2

    def test_output_is_valid_python(self):
        from obfuscator.adversarial import inject_adversarial_code
        sources = [
            "x = 1\n",
            "def foo():\n    return 42\n",
            "import os\n\ndef bar(x):\n    return x + 1\n",
            "class A:\n    def meth(self):\n        pass\n",
            "async def fetch():\n    return None\n",
            "from typing import List\n\ndef process(items: List[int]) -> int:\n    return sum(items)\n",
        ]
        for src in sources:
            for level in [1, 3, 5]:
                result = inject_adversarial_code(src, {
                    "seed": 0, "level": level, "prompt_injection": True,
                })
                try:
                    ast.parse(result)
                except SyntaxError as e:
                    pytest.fail(f"Syntax broken for {src!r} at level {level}: {e}")
