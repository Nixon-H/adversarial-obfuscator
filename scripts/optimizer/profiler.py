import ast
from typing import List
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    name: str
    lines_of_code: int = 0
    cyclomatic_complexity: int = 1
    exec_frequency: float = 1.0
    import_dependencies: List[str] = field(default_factory=list)
    category: str = 'simple_helper'


class FunctionProfiler:
    def profile(self, tree: ast.AST) -> List[FunctionInfo]:
        functions = []
        imports = self._collect_imports(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                info = self._profile_function(node, imports)
                functions.append(info)
        return functions

    def profile_from_source(self, source: str) -> List[FunctionInfo]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        return self.profile(tree)

    def _collect_imports(self, tree: ast.AST) -> set:
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
                    if alias.asname:
                        imports.add(alias.asname)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
                for alias in node.names:
                    if alias.asname:
                        imports.add(alias.asname)
        return imports

    def _profile_function(self, node: ast.FunctionDef, module_imports: set) -> FunctionInfo:
        lines = self._count_lines(node)
        complexity = self._cyclomatic_complexity(node)
        exec_freq = self._estimate_frequency(node)
        deps = self._find_dependencies(node, module_imports)
        category = self._classify_function(node, deps, complexity)
        return FunctionInfo(
            name=node.name,
            lines_of_code=lines,
            cyclomatic_complexity=complexity,
            exec_frequency=exec_freq,
            import_dependencies=deps,
            category=category,
        )

    def _count_lines(self, node: ast.FunctionDef) -> int:
        if not node.body:
            return 0
        first = node.body[0].lineno if hasattr(node.body[0], 'lineno') else 0
        last = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else 0
        return max(0, last - first + 1)

    def _cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        complexity = 1
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                              ast.With, ast.Try, ast.Assert)):
                complexity += 1
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values) - 1
            elif isinstance(n, ast.IfExp):
                complexity += 1
        return complexity

    def _estimate_frequency(self, node: ast.FunctionDef) -> float:
        name_lower = node.name.lower()
        startup_indicators = ('init', 'setup', 'config', 'bootstrap', 'load',
                              'register', 'parse_args', 'read_config', 'import_')
        if any(name_lower.startswith(s) for s in startup_indicators):
            return 0.1
        hot_indicators = ('main', 'run', 'process', 'handle', 'exec', 'loop',
                          'callback', 'dispatch', 'event', 'tick')
        if any(name_lower.startswith(s) for s in hot_indicators):
            return 5.0
        if self._count_lines(node) < 10:
            return 0.5
        return 1.0

    def _find_dependencies(self, node: ast.FunctionDef, module_imports: set) -> List[str]:
        deps = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in module_imports:
                deps.add(n.id)
            if isinstance(n, ast.Attribute):
                if isinstance(n.value, ast.Name) and n.value.id in module_imports:
                    deps.add(n.value.id)
        return sorted(deps)

    def _classify_function(self, node: ast.FunctionDef, deps: List[str],
                           complexity: int) -> str:
        crypto_keywords = frozenset({
            'aes', 'encrypt', 'decrypt', 'cipher', 'hash', 'sha', 'md5',
            'hmac', 'rsa', 'dsa', 'ecc', 'sign', 'verify', 'digest',
            'bcrypt', 'argon', 'pbkdf', 'kdf', 'derive',
        })
        license_keywords = frozenset({
            'license', 'verify', 'validate', 'check', 'auth', 'register',
        })
        key_derive_keywords = frozenset({
            'key', 'derive', 'pbkdf', 'scrypt', 'argon', 'kdf',
        })

        name_lower = node.name.lower()

        if complexity >= 8:
            return 'sensitive_algo'

        if any(kw in name_lower for kw in key_derive_keywords):
            if deps:
                return 'key_derivation'
            return 'key_derivation'

        if any(kw in name_lower for kw in license_keywords):
            return 'license_check'

        if any(kw in name_lower for kw in crypto_keywords):
            return 'crypto'

        if complexity >= 5:
            return 'sensitive_algo'

        return 'simple_helper'

    def assign_categories(self, functions: List[FunctionInfo]) -> None:
        for fn in functions:
            fn.category = self._classify_by_info(fn)

    def _classify_by_info(self, fn: FunctionInfo) -> str:
        if fn.cyclomatic_complexity >= 8:
            return 'sensitive_algo'
        if fn.cyclomatic_complexity >= 5:
            return 'key_derivation'
        if any(kw in fn.name.lower() for kw in ('encrypt', 'decrypt', 'cipher', 'hash')):
            return 'crypto'
        if any(kw in fn.name.lower() for kw in ('license', 'verify', 'validate', 'auth')):
            return 'license_check'
        return 'simple_helper'
