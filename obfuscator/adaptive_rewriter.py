"""
Item 74: Adaptive Adversarial Rewriting - Applies replacement protections
based on WeaknessProfile from benchmark feedback.
"""

import ast
import base64
import json
import os
import random
import secrets

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_HISTORY = os.path.join(_ROOT, "build", "feedback_history.json")


class AdaptiveRewriter:
    def __init__(self, history_path: str = _DEFAULT_HISTORY):
        self.history_path = history_path
        self._history: list[dict] = []
        self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path) as f:
                    self._history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._history = []

    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        with open(self.history_path, "w") as f:
            json.dump(self._history, f, indent=2)

    def rewrite(self, profile, source: str) -> str:
        try:
            tree = ast.parse(source)
        except SyntaxError as _e:
            import logging as _lg
            _lg.warning(f"Adaptive rewriter: SyntaxError in source, returning original: {_e}")
            return source

        entry = {
            "profile": profile.to_dict(),
            "source_hash": hash(source) & 0xFFFFFFFF,
        }

        for action in profile.recommended_actions:
            if action == "strengthen_symbol_renaming":
                tree = self._apply_homoglyph_renaming(tree)
            elif action == "add_opaque_predicates":
                tree = self._inject_opaque_predicates(tree)
            elif action == "add_exec_eval_patterns":
                tree = self._inject_exec_eval(tree)
            elif action == "add_junk_ast_patterns":
                tree = self._inject_mimicking_junk(tree)
            elif action == "add_decoy_apis":
                tree = self._inject_decoy_apis(tree)
            elif action == "add_misleading_imports":
                tree = self._inject_misleading_imports(tree)
            elif action == "increase_dispatch_fan_out":
                tree = self._duplicate_dispatch(tree)
            elif action == "add_string_encoding":
                tree = self._encode_strings(tree)

        ast.fix_missing_locations(tree)
        result = ast.unparse(tree)

        self._history.append(entry)
        self._save_history()
        return result

    BUILTIN_NAMES = {
        "print", "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
        "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
        "min", "max", "abs", "round", "pow", "divmod", "chr", "ord", "hex", "oct", "bin",
        "ascii", "repr", "type", "isinstance", "issubclass", "callable",
        "hasattr", "getattr", "setattr", "delattr", "open", "input",
        "eval", "exec", "compile", "globals", "locals", "vars", "dir",
        "id", "hash", "object", "super", "bytes", "bytearray", "memoryview",
        "format", "slice", "iter", "next", "any", "all", "complex", "frozenset",
        "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
        "AttributeError", "RuntimeError", "StopIteration", "ImportError",
        "NameError", "OSError", "True", "False", "None",
        "__import__",
    }

    def _apply_homoglyph_renaming(self, tree: ast.AST) -> ast.AST:
        homoglyphs = {
            "a": "а", "c": "с", "e": "е", "o": "о", "p": "р",
            "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name not in self.BUILTIN_NAMES:
                    for orig, repl in homoglyphs.items():
                        node.name = node.name.replace(orig, repl)
            if isinstance(node, ast.arg):
                if node.arg not in self.BUILTIN_NAMES:
                    for orig, repl in homoglyphs.items():
                        node.arg = node.arg.replace(orig, repl)
            if isinstance(node, ast.Name):
                if node.id in self.BUILTIN_NAMES:
                    continue
                for orig, repl in homoglyphs.items():
                    node.id = node.id.replace(orig, repl)
        return tree

    def _inject_opaque_predicates(self, tree: ast.AST) -> ast.AST:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and len(node.body) >= 2:
                a = random.randint(2, 50)
                pred = ast.Compare(
                    left=ast.BinOp(
                        left=ast.Constant(value=a * a + a),
                        op=ast.Mod(),
                        right=ast.Constant(value=2),
                    ),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=0)],
                )
                wrapper = ast.If(test=pred, body=list(node.body), orelse=[ast.Pass()])
                node.body = [wrapper]
        return tree

    def _inject_exec_eval(self, tree: ast.AST) -> ast.AST:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and len(node.body) >= 2:
                enc = base64.b64encode(b"pass").decode()
                # b64decode() returns bytes; eval() requires str, so decode
                # first. Guarded with try/except like the module-path
                # injection so a failure can never break the host function.
                guarded = ast.Try(
                    body=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Name(id="eval", ctx=ast.Load()),
                                args=[
                                    ast.Call(
                                        func=ast.Attribute(
                                            value=ast.Call(
                                                func=ast.Attribute(
                                                    value=ast.Call(
                                                        func=ast.Name(id="__import__", ctx=ast.Load()),
                                                        args=[ast.Constant(value="base64")],
                                                        keywords=[],
                                                    ),
                                                    attr="b64decode",
                                                    ctx=ast.Load(),
                                                ),
                                                args=[ast.Constant(value=enc)],
                                                keywords=[],
                                            ),
                                            attr="decode",
                                            ctx=ast.Load(),
                                        ),
                                        args=[],
                                        keywords=[],
                                    )
                                ],
                                keywords=[],
                            )
                        ),
                    ],
                    handlers=[
                        ast.ExceptHandler(
                            type=ast.Name(id="Exception", ctx=ast.Load()),
                            name=None,
                            body=[ast.Pass()],
                        )
                    ],
                    orelse=[],
                    finalbody=[],
                )
                node.body.insert(0, guarded)
        return tree

    def _inject_mimicking_junk(self, tree: ast.AST) -> ast.AST:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for _ in range(random.randint(1, 3)):
                    junk_var = f"_nx_junk_{secrets.token_hex(2)}"
                    node.body.insert(
                        0,
                        ast.Assign(
                            targets=[ast.Name(id=junk_var, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Name(id="len", ctx=ast.Load()),
                                args=[ast.Constant(value="a")],
                                keywords=[],
                            ),
                        ),
                    )
        return tree

    def _inject_decoy_apis(self, tree: ast.AST) -> ast.AST:
        try:
            from obfuscator.decoy_apis import SemanticDecoyApiInjector
            injector = SemanticDecoyApiInjector(count=2)
            if isinstance(tree, ast.Module):
                tree = injector.inject(tree)
        except ImportError:
            pass
        return tree

    def _inject_misleading_imports(self, tree: ast.AST) -> ast.AST:
        if not isinstance(tree, ast.Module):
            return tree
        misleading = ["cryptography", "requests", "ssl", "nacl"]
        for imp in misleading:
            guarded = ast.Try(
                body=[ast.Import(names=[ast.alias(name=imp, asname=None)])],
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(id="Exception", ctx=ast.Load()),
                        name=None,
                        body=[ast.Pass()],
                    )
                ],
                orelse=[],
                finalbody=[],
            )
            tree.body.insert(0, guarded)
        return tree

    @staticmethod
    def _is_duplication_safe(stmts: list[ast.stmt]) -> bool:
        """True if every statement is provably pure (re-execution harmless)."""
        for s in stmts:
            if isinstance(s, ast.Pass):
                continue
            if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant):
                continue
            if (
                isinstance(s, ast.Assign)
                and isinstance(s.value, ast.Constant)
                and all(isinstance(t, ast.Name) for t in s.targets)
            ):
                continue
            return False
        return True

    def _duplicate_dispatch(self, tree: ast.AST) -> ast.AST:
        import copy
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and len(node.body) >= 2:
                # Duplicating arbitrary bodies runs side effects twice.
                # Only duplicate provably-pure bodies; otherwise skip.
                if not self._is_duplication_safe(node.body):
                    continue
                dup = copy.deepcopy(node.body)
                node.body.extend(dup)
        return tree

    def _encode_strings(self, tree: ast.AST) -> ast.AST:
        import base64
        skip_ids = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '__import__':
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        skip_ids.add(id(arg))
                for kw in node.keywords:
                    if isinstance(kw.value, (ast.List, ast.Tuple)):
                        for elt in ast.walk(kw.value):
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                skip_ids.add(id(elt))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) >= 4:
                if id(node) in skip_ids:
                    continue
                if all(c in '0123456789abcdefABCDEF' for c in node.value):
                    continue
                encoded = base64.b64encode(node.value.encode()).decode()
                node.value = encoded
        return tree

    def get_history(self) -> list[dict]:
        return list(self._history)
