"""
Item 74: Adaptive Adversarial Rewriting - Applies replacement protections
based on WeaknessProfile from benchmark feedback.
"""

import ast
import hashlib
import base64
import json
import os
import random

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_HISTORY = os.path.join(_ROOT, "build", "feedback_history.json")


class AdaptiveRewriter:
    def __init__(self, history_path: str = _DEFAULT_HISTORY, nonce=None):
        self.history_path = history_path
        self._nonce = nonce
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

        if self._nonce is None:
            _nonce = os.urandom(8)
        else:
            _nonce = self._nonce
        entry = {
            "profile": profile.to_dict(),
            # Per-BUILD, not per-source.
            #
            # A plain sha256 of the source is stable, which made two builds of the
            # same input produce the same generated names. An analyst holding both
            # can diff them and cancel the naming entirely -- the polymorphism
            # that makes the output expensive to study disappears.
            #
            # So a fresh nonce is mixed in by default. Passing --seed supplies a
            # fixed nonce instead, which restores byte-reproducible builds for
            # anyone who needs them (debugging, bisection, release verification).
            "source_hash": int.from_bytes(
                hashlib.sha256(
                    source.encode("utf-8", "replace") + _nonce
                ).digest()[:4], "little"),
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

        def _repl(name: str) -> str:
            if name in self.BUILTIN_NAMES:
                return name
            for orig, repl in homoglyphs.items():
                name = name.replace(orig, repl)
            return name

        # Pass 1: decide the mapping for def names and params ONLY. Pass 2
        # rewrites uses that are provably local:
        #   * Name / arg / def names -- always local;
        #   * Attribute.attr -- only names that are methods defined in a
        #     local class.  Renaming every attribute also renamed external
        #     APIs (`obj.data` -> `obj.dаtа`), which the first fix did;
        #   * keyword.arg -- only a direct call to a local function whose
        #     signature has that parameter.  Renaming every keyword broke
        #     external APIs (`json.dumps(..., default=...)`).
        rename_map: dict[str, str] = {}
        local_funcs: dict[str, set[str]] = {}
        method_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name not in self.BUILTIN_NAMES:
                    rename_map[node.name] = _repl(node.name)
                args = (list(getattr(node.args, "posonlyargs", []))
                        + list(node.args.args)
                        + list(getattr(node.args, "kwonlyargs", [])))
                local_funcs[node.name] = {a.arg for a in args}
            if isinstance(node, ast.arg):
                if node.arg not in self.BUILTIN_NAMES:
                    rename_map[node.arg] = _repl(node.arg)
            if isinstance(node, ast.ClassDef):
                for stmt in node.body:
                    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_names.add(stmt.name)
        rename_map = {k: v for k, v in rename_map.items() if k != v}

        class _Rename(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name) -> ast.Name:
                if node.id in rename_map:
                    node.id = rename_map[node.id]
                return node

            def visit_arg(self, node: ast.arg) -> ast.arg:
                if node.arg in rename_map:
                    node.arg = rename_map[node.arg]
                return node

            def visit_FunctionDef(self, node):
                if node.name in rename_map:
                    node.name = rename_map[node.name]
                self.generic_visit(node)
                return node

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
                if node.attr in method_names and node.attr in rename_map:
                    node.attr = rename_map[node.attr]
                self.generic_visit(node)
                return node

            def visit_Call(self, node: ast.Call) -> ast.Call:
                if isinstance(node.func, ast.Name):
                    params = local_funcs.get(node.func.id)
                    if params:
                        for kw in node.keywords:
                            if (kw.arg and kw.arg in params
                                    and kw.arg in rename_map):
                                kw.arg = rename_map[kw.arg]
                self.generic_visit(node)
                return node

        return _Rename().visit(tree)

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
                    # Derive the name from the GLOBAL random state, which --seed
                    # pins, instead of secrets. The adaptive pass was the last
                    # source of non-determinism in the ladder: every build picked
                    # different junk names, so two seeded builds differed and a
                    # Windows failure could not be reproduced.
                    junk_var = "_nx_junk_%04x" % random.getrandbits(16)
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
        from obfuscator.core.ast_prologue import insert_module_prologue
        misleading = ["cryptography", "requests", "ssl", "nacl"]
        guards = []
        for imp in misleading:
            guards.append(ast.Try(
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
            ))
        insert_module_prologue(tree, guards)
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

    _DECODER_NAME = "_nx_rev_b64d"

    def _ensure_b64_decoder(self, tree: ast.AST) -> None:
        """Inject the reversible decoder once at module top."""
        import ast as _ast
        for node in tree.body:
            if isinstance(node, _ast.FunctionDef) and node.name == self._DECODER_NAME:
                return
        decoder = _ast.FunctionDef(
            name=self._DECODER_NAME,
            args=_ast.arguments(
                posonlyargs=[],
                args=[_ast.arg(arg="s", annotation=None)],
                kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[
                _ast.Return(
                    value=_ast.Call(
                        func=_ast.Attribute(
                            value=_ast.Call(
                                func=_ast.Attribute(
                                    value=_ast.Call(
                                        func=_ast.Name(id="__import__", ctx=_ast.Load()),
                                        args=[_ast.Constant(value="base64")],
                                        keywords=[]),
                                    attr="b64decode", ctx=_ast.Load()),
                                args=[_ast.Name(id="s", ctx=_ast.Load())],
                                keywords=[]),
                            attr="decode", ctx=_ast.Load()),
                        args=[_ast.Constant(value="utf-8")],
                        keywords=[]))
            ],
            decorator_list=[],
            returns=None,
            type_params=[],
        )
        from obfuscator.core.ast_prologue import insert_module_prologue
        insert_module_prologue(tree, [_ast.fix_missing_locations(decoder)])

    def _encode_strings(self, tree: ast.AST) -> ast.AST:
        import base64
        skip_ids = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                for part in ast.walk(node):
                    if isinstance(part, ast.Constant):
                        skip_ids.add(id(part))
            # A `case "literal":` pattern must stay a literal: wrapping it
            # in a call turns a value pattern into a class pattern and the
            # match raises "called match pattern must be a class".
            if hasattr(ast, "pattern") and isinstance(node, ast.pattern):
                for part in ast.walk(node):
                    if isinstance(part, ast.Constant):
                        skip_ids.add(id(part))
            if isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", [])
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    skip_ids.add(id(body[0].value))
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name) and t.id == "__all__":
                        for elt in ast.walk(node.value):
                            if isinstance(elt, ast.Constant):
                                skip_ids.add(id(elt))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '__import__':
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        skip_ids.add(id(arg))
                for kw in node.keywords:
                    if isinstance(kw.value, (ast.List, ast.Tuple)):
                        for elt in ast.walk(kw.value):
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                skip_ids.add(id(elt))
        class _Encode(ast.NodeTransformer):
            def __init__(self, skip_ids, decoder_name):
                self._skip = skip_ids
                self._decoder_name = decoder_name

            def visit_Constant(self, node: ast.Constant) -> ast.AST:
                if (isinstance(node.value, str) and len(node.value) >= 4
                        and id(node) not in self._skip
                        and not all(c in '0123456789abcdefABCDEF'
                                    for c in node.value)):
                    # Reversible: wrap in a decoder call instead of
                    # corrupting the constant in place with no decode step.
                    encoded = base64.b64encode(node.value.encode()).decode()
                    return ast.copy_location(ast.Call(
                        func=ast.Name(id=self._decoder_name, ctx=ast.Load()),
                        args=[ast.Constant(value=encoded)],
                        keywords=[]), node)
                return node

        tree = _Encode(skip_ids, self._DECODER_NAME).visit(tree)
        ast.fix_missing_locations(tree)
        # Injected AFTER encoding so the decoder's own literals ("utf-8")
        # are never fed through the encoder (that would recurse at runtime).
        self._ensure_b64_decoder(tree)
        ast.fix_missing_locations(tree)
        return tree

    def get_history(self) -> list[dict]:
        return list(self._history)
