"""
LLM-Resilient AST obfuscation passes.

ContextCollapseObfuscator   — saturates LLM context windows with deeply nested
                              control flow, dead variable chains, guard variables,
                              and base64-encoded string literals.

HoneyFunctionInjector       — injects plausible dead functions (real algorithms,
                              zero data-flow) that look essential to superficial
                              inspection but are never reached.
"""

import ast
import base64
import random
import secrets
import hashlib
import struct


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOOKALIKE_PREFIXES = ["_a", "_b", "_c", "_d", "_e", "_f", "_g"]
_LOOKALIKE_NAMES = [
    "temp", "tmp", "val", "buf", "ctx", "acc", "ptr",
    "offset", "index", "count", "seed", "nonce", "tag",
    "state", "slot", "key", "iv", "mac", "sig", "pad",
]

_COLLAPSED_DEPTH = 20

_GUARD_VAR_POOL = [
    "_nx_gc_enabled",
    "_nx_crypto_init",
    "_nx_vm_ready",
    "_nx_license_valid",
    "_nx_hw_bound",
    "_nx_self_check",
    "_nx_integrity_ok",
    "_nx_tamper_protect",
    "_nx_debug_mode",
    "_nx_fork_safe",
]

from .algo_templates import _REAL_ALGO_SOURCES


# ---------------------------------------------------------------------------
# ContextCollapseObfuscator
# ---------------------------------------------------------------------------

class ContextCollapseObfuscator(ast.NodeTransformer):
    """Saturates LLM context windows with deeply nested irrelevant structures."""

    def __init__(self, depth: int = _COLLAPSED_DEPTH, dead_vars: int = 50):
        self.depth = depth
        self.dead_vars = dead_vars
        self._guard_vars: list[str] = []
        self._guard_counter = 0

    def obfuscate(self, tree: ast.AST) -> ast.AST:
        self._guard_vars = random.sample(_GUARD_VAR_POOL, min(4, len(_GUARD_VAR_POOL)))
        self.visit(tree)
        ast.fix_missing_locations(tree)
        return tree

    # -- string encoding ---------------------------------------------------

    def _encode_string(self, s: str) -> ast.Call:
        encoded = base64.b64encode(s.encode("utf-8")).decode("ascii")
        decode_call = ast.Call(
            func=ast.Attribute(
                value=ast.Call(
                    func=ast.Name(id="__import__", ctx=ast.Load()),
                    args=[ast.Constant(value="base64")],
                    keywords=[],
                ),
                attr="b64decode",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value=encoded)],
            keywords=[],
        )
        return ast.Call(
            func=ast.Attribute(value=decode_call, attr="decode", ctx=ast.Load()),
            args=[ast.Constant(value="utf-8")],
            keywords=[],
        )



    # -- guard variables ---------------------------------------------------

    def _inject_guard_vars(self, body: list[ast.stmt]) -> list[ast.stmt]:
        stmts: list[ast.stmt] = []
        for gv in self._guard_vars:
            stmts.append(
                ast.Assign(
                    targets=[ast.Name(id=gv, ctx=ast.Store())],
                    value=ast.Constant(value=True),
                )
            )
        return stmts + body

    def _inject_guard_checks(self, body: list[ast.stmt]) -> list[ast.stmt]:
        stmts: list[ast.stmt] = []
        for gv in self._guard_vars:
            stmts.append(
                ast.If(
                    test=ast.UnaryOp(
                        op=ast.Not(),
                        operand=ast.Name(id=gv, ctx=ast.Load()),
                    ),
                    body=[ast.Pass()],
                    orelse=[],
                )
            )
        return stmts + body

    # -- dead variable chains ----------------------------------------------

    def _dead_var_chain(self) -> list[ast.stmt]:
        stmts: list[ast.stmt] = []
        prev = None
        for i in range(self.dead_vars):
            vname = f"_nx_dc_{i}_{random.randint(1000, 9999)}"
            if prev is None:
                val = ast.Constant(value=random.randint(0, 2**32))
            else:
                val = ast.BinOp(
                    left=ast.Name(id=prev, ctx=ast.Load()),
                    op=random.choice(
                        [
                            ast.Add(),
                            ast.Sub(),
                            ast.BitXor(),
                            ast.BitAnd(),
                            ast.BitOr(),
                        ]
                    ),
                    right=ast.Constant(value=random.randint(1, 255)),
                )
            stmts.append(
                ast.Assign(
                    targets=[ast.Name(id=vname, ctx=ast.Store())],
                    value=val,
                )
            )
            prev = vname
        return stmts

    # -- deep nesting ------------------------------------------------------

    def _build_nested_if(self, inner: ast.stmt) -> ast.stmt:
        node: ast.stmt = inner
        for level in range(self.depth):
            a = random.randint(2, 250)
            b = random.randint(2, 250)
            c = a + random.randint(1, 100)
            d = c - a
            node = ast.If(
                test=ast.Compare(
                    left=ast.BinOp(
                        left=ast.Constant(value=a),
                        op=ast.Mult(),
                        right=ast.BinOp(
                            left=ast.Constant(value=b),
                            op=ast.Add(),
                            right=ast.Constant(value=c),
                        ),
                    ),
                    ops=[ast.Eq()],
                    comparators=[
                        ast.BinOp(
                            left=ast.BinOp(
                                left=ast.Constant(value=a),
                                op=ast.Mult(),
                                right=ast.Constant(value=b),
                            ),
                            op=ast.Add(),
                            right=ast.BinOp(
                                left=ast.Constant(value=a),
                                op=ast.Mult(),
                                right=ast.Constant(value=c),
                            ),
                        )
                    ],
                ),
                body=[node],
                orelse=[ast.Pass()],
            )
        return node

    # -- visit overrides ---------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        body = node.body

        guard_checks = self._inject_guard_checks(body)
        body_with_vars = self._dead_var_chain() + guard_checks
        nested = self._build_nested_if(
            ast.Try(
                body=body_with_vars,
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(id="Exception", ctx=ast.Load()),
                        name="_nx_skip",
                        body=[ast.Pass()],
                    )
                ],
                orelse=[],
                finalbody=[],
            )
        )
        node.body = self._inject_guard_vars([nested])
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if (
            isinstance(node.value, str)
            and len(node.value) >= 4
            and len(node.value) <= 2000
        ):
            return self._encode_string(node.value)
        return node


# ---------------------------------------------------------------------------
# HoneyFunctionInjector
# ---------------------------------------------------------------------------

class HoneyFunctionInjector(ast.NodeTransformer):
    """Injects plausible dead functions with zero data-flow to real code."""

    def __init__(self, count: int = 5, naming_prefix: str | None = None):
        self.count = count
        self._naming_prefix = naming_prefix or "_nx_honey"

    def inject(self, tree: ast.AST) -> ast.AST:
        source_algo_names = list(_REAL_ALGO_SOURCES.keys())
        chosen = random.sample(source_algo_names, min(self.count, len(source_algo_names)))
        for _ in range(self.count - len(chosen)):
            chosen.append(random.choice(source_algo_names))

        new_funcs: list[ast.FunctionDef] = []
        for algo_key in chosen:
            source_template = _REAL_ALGO_SOURCES[algo_key]
            func_name = f"{self._naming_prefix}_{algo_key}_{secrets.token_hex(4)}"
            source = source_template.replace("{name}", func_name)
            try:
                parsed = ast.parse(source)
                for stmt in parsed.body:
                    if isinstance(stmt, ast.FunctionDef):
                        new_funcs.append(stmt)
            except SyntaxError:
                continue

        if isinstance(tree, ast.Module):
            import_idx = 0
            for i, stmt in enumerate(tree.body):
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    import_idx = i + 1
            for func_node in new_funcs:
                tree.body.insert(import_idx, func_node)

        ast.fix_missing_locations(tree)
        return tree

    def visit(self, node: ast.AST) -> ast.AST:
        return self.generic_visit(node)
