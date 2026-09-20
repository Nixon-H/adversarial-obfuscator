import ast
import copy
import hashlib
import os
import random
import secrets
from typing import Any


class DataProtector:
    """Applies data-oriented obfuscation to a Python AST.

    Protects data layout at four levels:
      1 — Variable Layout Randomization
      2 — + Runtime Structure Mutation
      3 — + Storage Virtualization + ORAM-backed sensitive state
    """

    def __init__(self, level: int = 3, seed: bytes | None = None):
        self.level = level
        self.seed = seed or secrets.token_bytes(32)
        self._rng = random.Random(self.seed)
        self._sensitive_keywords = {
            "key", "secret", "token", "password", "priv", "hash",
            "encrypt", "decrypt", "cipher", "auth", "credential",
            "salt", "iv", "nonce", "sign", "hmac",
        }

    # ── Public entry point ──────────────────────────────────────────────

    def protect(self, tree: ast.AST) -> ast.AST:
        tree = copy.deepcopy(tree)
        if self.level >= 3:
            tree = self._virtualize_storage(tree)
            tree = self._oram_protect(tree)
        if self.level >= 2:
            tree = self._mutate_structures(tree)
        if self.level >= 1 and self.level < 3:
            tree = self._randomize_layout(tree)
        ast.fix_missing_locations(tree)
        return tree

    # ── Helpers ─────────────────────────────────────────────────────────

    def _make_rand_name(self, prefix: str = "_do") -> str:
        suffix = self._rng.randint(10000, 99999)
        return f"{prefix}_{suffix}"

    def _detect_sensitive(self, node: ast.AST) -> set[str]:
        sensitive: set[str] = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        for kw in self._sensitive_keywords:
                            if kw in t.id.lower():
                                sensitive.add(t.id)
            if isinstance(n, ast.FunctionDef):
                for kw in self._sensitive_keywords:
                    if kw in n.name.lower():
                        for arg in n.args.args:
                            sensitive.add(arg.arg)
        return sensitive

    @staticmethod
    def _xor_string(s: str, key: int) -> str:
        key_bytes = key.to_bytes(8, "little")
        result = []
        for i, ch in enumerate(s):
            result.append(chr(ord(ch) ^ key_bytes[i % 8]))
        return "".join(result)

    @staticmethod
    def _encode_dict_key(key: str, runtime_key: int) -> str:
        return DataProtector._xor_string(key, runtime_key)

    # ── Pass 1: Variable Layout Randomization ──────────────────────────
    # (only for level 1 / 2 — level 3 uses storage virtualization instead)

    def _randomize_layout(self, tree: ast.AST) -> ast.Module:
        class LayoutRandomizer(ast.NodeTransformer):
            def __init__(self, parent: "DataProtector"):
                self.parent = parent

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                body: list[ast.stmt] = []
                vars_in_function: list[str] = []
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for t in stmt.targets:
                            if isinstance(t, ast.Name) and not t.id.startswith("_"):
                                if t.id not in vars_in_function:
                                    vars_in_function.append(t.id)

                if len(vars_in_function) < 2:
                    return node

                rng = self.parent._rng
                nvars = len(vars_in_function)

                layout_a = list(range(nvars))
                rng.shuffle(layout_a)
                layout_b = list(range(nvars))
                rng.shuffle(layout_b)

                layout_name = self.parent._make_rand_name("_lyt")
                vars_name = self.parent._make_rand_name("_vtab")

                layout_init = ast.Assign(
                    targets=[ast.Name(id=layout_name, ctx=ast.Store())],
                    value=ast.Constant(value=0),
                )

                vars_init_list = [ast.Constant(value=0) for _ in range(nvars)]
                vars_init = ast.Assign(
                    targets=[ast.Name(id=vars_name, ctx=ast.Store())],
                    value=ast.List(elts=vars_init_list, ctx=ast.Load()),
                )

                body.append(layout_init)
                body.append(vars_init)

                layout_table_name = self.parent._make_rand_name("_lmap")
                layout_table = ast.Assign(
                    targets=[ast.Name(id=layout_table_name, ctx=ast.Store())],
                    value=ast.List(
                        elts=[
                            ast.List(
                                elts=[ast.Constant(value=i) for i in layout_a],
                                ctx=ast.Load(),
                            ),
                            ast.List(
                                elts=[ast.Constant(value=i) for i in layout_b],
                                ctx=ast.Load(),
                            ),
                        ],
                        ctx=ast.Load(),
                    ),
                )
                body.append(layout_table)

                var_to_idx = {v: i for i, v in enumerate(vars_in_function)}

                def _indirect_read(varname: str) -> ast.AST:
                    idx = var_to_idx[varname]
                    return ast.Subscript(
                        value=ast.Name(id=vars_name, ctx=ast.Load()),
                        slice=ast.Subscript(
                            value=ast.Subscript(
                                value=ast.Name(id=layout_table_name, ctx=ast.Load()),
                                slice=ast.Name(id=layout_name, ctx=ast.Load()),
                                ctx=ast.Load(),
                            ),
                            slice=ast.Constant(value=idx),
                            ctx=ast.Load(),
                        ),
                        ctx=ast.Load(),
                    )

                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        has_target = False
                        for t in stmt.targets:
                            if isinstance(t, ast.Name) and t.id in var_to_idx:
                                has_target = True
                                break
                        if has_target:
                            new_assigns = []
                            for t in stmt.targets:
                                if isinstance(t, ast.Name) and t.id in var_to_idx:
                                    idx = var_to_idx[t.id]
                                    new_rhs = self._rewrite_rvalue(
                                        stmt.value, var_to_idx, _indirect_read,
                                    )
                                    store = ast.Assign(
                                        targets=[
                                            ast.Subscript(
                                                value=ast.Name(id=vars_name, ctx=ast.Load()),
                                                slice=ast.Subscript(
                                                    value=ast.Subscript(
                                                        value=ast.Name(id=layout_table_name, ctx=ast.Load()),
                                                        slice=ast.Name(id=layout_name, ctx=ast.Load()),
                                                        ctx=ast.Load(),
                                                    ),
                                                    slice=ast.Constant(value=idx),
                                                    ctx=ast.Load(),
                                                ),
                                                ctx=ast.Store(),
                                            )
                                        ],
                                        value=new_rhs,
                                    )
                                    new_assigns.append(store)
                                else:
                                    new_assigns.append(stmt)
                            body.extend(new_assigns)
                        else:
                            body.append(stmt)

                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        call.args = [
                            self._rewrite_rvalue(a, var_to_idx, _indirect_read)
                            for a in call.args
                        ]
                        body.append(stmt)

                    elif isinstance(stmt, ast.Return):
                        stmt.value = self._rewrite_rvalue(
                            stmt.value, var_to_idx, _indirect_read,
                        )
                        body.append(stmt)

                    else:
                        body.append(stmt)

                layout_switch = ast.Assign(
                    targets=[ast.Name(id=layout_name, ctx=ast.Store())],
                    value=ast.Constant(value=1),
                )
                body.append(layout_switch)

                node.body = body
                return node

            def _rewrite_rvalue(self, expr: ast.AST, var_to_idx: dict, indirect_read) -> ast.AST:
                if isinstance(expr, ast.Name) and expr.id in var_to_idx:
                    return indirect_read(expr.id)
                if isinstance(expr, ast.BinOp):
                    return ast.BinOp(
                        left=self._rewrite_rvalue(expr.left, var_to_idx, indirect_read),
                        op=expr.op,
                        right=self._rewrite_rvalue(expr.right, var_to_idx, indirect_read),
                    )
                if isinstance(expr, ast.UnaryOp):
                    return ast.UnaryOp(
                        op=expr.op,
                        operand=self._rewrite_rvalue(expr.operand, var_to_idx, indirect_read),
                    )
                if isinstance(expr, ast.Subscript):
                    if isinstance(expr.value, ast.Name) and expr.value.id in var_to_idx:
                        expr.value = indirect_read(expr.value.id)
                    else:
                        expr.value = self._rewrite_rvalue(
                            expr.value, var_to_idx, indirect_read,
                        )
                    if isinstance(expr.slice, ast.AST):
                        expr.slice = self._rewrite_rvalue(
                            expr.slice, var_to_idx, indirect_read,
                        )
                    return expr
                if isinstance(expr, ast.Call):
                    expr.args = [
                        self._rewrite_rvalue(a, var_to_idx, indirect_read)
                        for a in expr.args
                    ]
                    return expr
                if isinstance(expr, ast.Compare):
                    expr.left = self._rewrite_rvalue(
                        expr.left, var_to_idx, indirect_read,
                    )
                    expr.comparators = [
                        self._rewrite_rvalue(c, var_to_idx, indirect_read)
                        for c in expr.comparators
                    ]
                    return expr
                return expr

        return LayoutRandomizer(self).visit(tree)

    # ── Pass 2: Structure Mutation ──────────────────────────────────────

    def _mutate_structures(self, tree: ast.AST) -> ast.Module:
        class StructureMutator(ast.NodeTransformer):
            def __init__(self, parent: "DataProtector"):
                self.parent = parent
                self._runtime_key = parent._rng.randint(0, 0xFFFFFFFFFFFFFFFF)

            def visit_Assign(self, node: ast.Assign) -> ast.Assign | list[ast.stmt]:
                if not (isinstance(node.value, ast.Dict) or
                        (isinstance(node.value, ast.Call) and
                         isinstance(node.value.func, ast.Name) and
                         node.value.func.id == "dict")):
                    return self.generic_visit(node)

                if isinstance(node.value, ast.Dict):
                    mutated = self._mutate_dict_literal(node.value)
                else:
                    mutated = node.value

                stmts: list[ast.stmt] = [ast.Assign(targets=node.targets, value=mutated)]

                target_id = None
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        target_id = t.id
                        break

                if target_id:
                    decoy_keys = self.parent._generate_decoy_keys()
                    for dk in decoy_keys:
                        stmts.append(
                            ast.Assign(
                                targets=[
                                    ast.Subscript(
                                        value=ast.Name(id=target_id, ctx=ast.Load()),
                                        slice=ast.Call(
                                            func=ast.Attribute(
                                                value=ast.Constant(
                                                    value=self.parent._encode_dict_key(dk, self._runtime_key)
                                                ),
                                                attr="encode",
                                                ctx=ast.Load(),
                                            ),
                                            args=[ast.Constant(value="utf-8")],
                                            keywords=[],
                                        ),
                                        ctx=ast.Store(),
                                    )
                                ],
                                value=ast.Constant(value=0),
                            )
                        )

                return stmts

            def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
                if (isinstance(node.slice, ast.Constant) and
                        isinstance(node.slice.value, str)):
                    enc_key = self.parent._encode_dict_key(
                        node.slice.value, self._runtime_key
                    )
                    new_slice = ast.Call(
                        func=ast.Attribute(
                            value=ast.Constant(value=enc_key),
                            attr="encode",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value="utf-8")],
                        keywords=[],
                    )
                    node.slice = new_slice
                return node

            def _mutate_dict_literal(self, d: ast.Dict) -> ast.Dict:
                new_keys: list[ast.AST] = []
                new_values: list[ast.AST] = []
                rk = self._runtime_key
                for k, v in zip(d.keys, d.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        enc = self.parent._encode_dict_key(k.value, rk)
                        new_keys.append(
                            ast.Call(
                                func=ast.Attribute(
                                    value=ast.Constant(value=enc),
                                    attr="encode",
                                    ctx=ast.Load(),
                                ),
                                args=[ast.Constant(value="utf-8")],
                                keywords=[],
                            )
                        )
                        new_values.append(v)
                    else:
                        new_keys.append(k)
                        new_values.append(v)

                rng = self.parent._rng
                combined = list(zip(new_keys, new_values))
                rng.shuffle(combined)
                new_keys, new_values = zip(*combined) if combined else ([], [])

                return ast.Dict(keys=list(new_keys), values=list(new_values))

        return StructureMutator(self).visit(tree)

    def _generate_decoy_keys(self) -> list[str]:
        candidates = [
            "__meta__", "_hidden", "checksum", "signature", "version",
            "timestamp", "nonce", "padding", "_reserved", "tag",
        ]
        count = self._rng.randint(1, 3)
        return self._rng.sample(candidates, count)

    # ── Pass 3a: Storage Virtualization ─────────────────────────────────

    def _virtualize_storage(self, tree: ast.AST) -> ast.Module:
        class StorageVirtualizer(ast.NodeTransformer):
            def __init__(self, parent: "DataProtector"):
                self.parent = parent
                self._func_counter = 0

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                self._func_counter += 1
                vars_found: list[str] = []
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for t in stmt.targets:
                            if isinstance(t, ast.Name) and not t.id.startswith("_"):
                                if t.id not in vars_found:
                                    vars_found.append(t.id)

                if not vars_found:
                    return node

                rng = self.parent._rng
                nvars = len(vars_found)
                vaddr_map = list(range(nvars))
                rng.shuffle(vaddr_map)

                vstore_name = self.parent._make_rand_name("_vs")
                vmap_name = self.parent._make_rand_name("_vmap")

                new_body: list[ast.stmt] = []

                vstore_init = ast.Assign(
                    targets=[ast.Name(id=vstore_name, ctx=ast.Store())],
                    value=ast.List(
                        elts=[ast.Constant(value=0) for _ in range(nvars)],
                        ctx=ast.Load(),
                    ),
                )
                new_body.append(vstore_init)

                vmap_init = ast.Assign(
                    targets=[ast.Name(id=vmap_name, ctx=ast.Store())],
                    value=ast.List(
                        elts=[ast.Constant(value=i) for i in vaddr_map],
                        ctx=ast.Load(),
                    ),
                )
                new_body.append(vmap_init)

                var_to_vaddr = {}
                for v, addr in zip(vars_found, vaddr_map):
                    var_to_vaddr[v] = addr

                def _virt_read(varname: str) -> ast.AST:
                    vaddr = var_to_vaddr[varname]
                    return ast.Subscript(
                        value=ast.Name(id=vstore_name, ctx=ast.Load()),
                        slice=ast.Subscript(
                            value=ast.Name(id=vmap_name, ctx=ast.Load()),
                            slice=ast.Constant(value=vaddr),
                            ctx=ast.Load(),
                        ),
                        ctx=ast.Load(),
                    )

                def _virt_write(varname: str, rhs: ast.AST) -> ast.stmt:
                    vaddr = var_to_vaddr[varname]
                    return ast.Assign(
                        targets=[
                            ast.Subscript(
                                value=ast.Name(id=vstore_name, ctx=ast.Load()),
                                slice=ast.Subscript(
                                    value=ast.Name(id=vmap_name, ctx=ast.Load()),
                                    slice=ast.Constant(value=vaddr),
                                    ctx=ast.Load(),
                                ),
                                ctx=ast.Store(),
                            )
                        ],
                        value=rhs,
                    )

                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        handled = False
                        for t in stmt.targets:
                            if isinstance(t, ast.Name) and t.id in var_to_vaddr:
                                new_rhs = self._rewrite_expr(
                                    stmt.value, var_to_vaddr, _virt_read,
                                )
                                new_body.append(_virt_write(t.id, new_rhs))
                                handled = True
                                break
                        if not handled:
                            new_body.append(stmt)

                    elif isinstance(stmt, ast.Return):
                        stmt.value = self._rewrite_expr(
                            stmt.value, var_to_vaddr, _virt_read,
                        )
                        new_body.append(stmt)

                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        call.args = [
                            self._rewrite_expr(a, var_to_vaddr, _virt_read)
                            for a in call.args
                        ]
                        new_body.append(stmt)

                    elif isinstance(stmt, ast.If):
                        transformed = self._rewrite_if(
                            stmt, var_to_vaddr, _virt_read,
                        )
                        new_body.append(transformed)

                    else:
                        new_body.append(stmt)

                node.body = new_body
                return node

            def _rewrite_expr(
                self, expr: ast.AST, var_to_vaddr: dict, virt_read,
            ) -> ast.AST:
                if isinstance(expr, ast.Name) and expr.id in var_to_vaddr:
                    return virt_read(expr.id)
                if isinstance(expr, ast.BinOp):
                    return ast.BinOp(
                        left=self._rewrite_expr(expr.left, var_to_vaddr, virt_read),
                        op=expr.op,
                        right=self._rewrite_expr(expr.right, var_to_vaddr, virt_read),
                    )
                if isinstance(expr, ast.UnaryOp):
                    return ast.UnaryOp(
                        op=expr.op,
                        operand=self._rewrite_expr(expr.operand, var_to_vaddr, virt_read),
                    )
                if isinstance(expr, ast.Subscript):
                    if isinstance(expr.value, ast.Name) and expr.value.id in var_to_vaddr:
                        expr.value = virt_read(expr.value.id)
                    else:
                        expr.value = self._rewrite_expr(
                            expr.value, var_to_vaddr, virt_read,
                        )
                    if isinstance(expr.slice, ast.AST):
                        expr.slice = self._rewrite_expr(
                            expr.slice, var_to_vaddr, virt_read,
                        )
                    return expr
                if isinstance(expr, ast.Call):
                    expr.args = [
                        self._rewrite_expr(a, var_to_vaddr, virt_read)
                        for a in expr.args
                    ]
                    return expr
                if isinstance(expr, ast.Compare):
                    expr.left = self._rewrite_expr(expr.left, var_to_vaddr, virt_read)
                    expr.comparators = [
                        self._rewrite_expr(c, var_to_vaddr, virt_read)
                        for c in expr.comparators
                    ]
                    return expr
                return expr

            def _rewrite_if(
                self, stmt: ast.If, var_to_vaddr: dict, virt_read,
            ) -> ast.If:
                stmt.test = self._rewrite_expr(stmt.test, var_to_vaddr, virt_read)
                stmt.body = [
                    self._rewrite_if(b, var_to_vaddr, virt_read) if isinstance(b, ast.If)
                    else self._rewrite_stmt(b, var_to_vaddr, virt_read)
                    for b in stmt.body
                ]
                stmt.orelse = [
                    self._rewrite_if(b, var_to_vaddr, virt_read) if isinstance(b, ast.If)
                    else self._rewrite_stmt(b, var_to_vaddr, virt_read)
                    for b in stmt.orelse
                ]
                return stmt

            def _rewrite_stmt(
                self, stmt: ast.stmt, var_to_vaddr: dict, virt_read,
            ) -> ast.stmt:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name) and t.id in var_to_vaddr:
                            new_rhs = self._rewrite_expr(
                                stmt.value, var_to_vaddr, virt_read,
                            )
                            return _virt_write(t.id, new_rhs)
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    stmt.value.args = [
                        virt_read(a.id) if isinstance(a, ast.Name) and a.id in var_to_vaddr else a
                        for a in stmt.value.args
                    ]
                return stmt

        return StorageVirtualizer(self).visit(tree)

    # ── Pass 3b: ORAM-backed sensitive state ────────────────────────────

    def _oram_protect(self, tree: ast.AST) -> ast.Module:
        sensitive = self._detect_sensitive(tree)
        if not sensitive:
            return tree

        class ORAMProtector(ast.NodeTransformer):
            def __init__(self, parent: "DataProtector", sensitive_vars: set[str]):
                self.parent = parent
                self.sensitive_vars = sensitive_vars
                self._oram_name = parent._make_rand_name("_oram")
                self._oram_injected = False

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                func_sensitive = [
                    v for v in self.sensitive_vars
                    if any(
                        isinstance(s, ast.Name) and s.id == v
                        for stmt in node.body
                        for s in ast.walk(stmt)
                        if isinstance(s, ast.Name)
                    )
                ]
                if not func_sensitive:
                    return node

                self._oram_injected = True
                oram_init = ast.Assign(
                    targets=[ast.Name(id=self._oram_name, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Attribute(
                                value=ast.Attribute(
                                    value=ast.Name(id="scripts", ctx=ast.Load()),
                                    attr="runtime",
                                    ctx=ast.Load(),
                                ),
                                attr="oram_sim",
                                ctx=ast.Load(),
                            ),
                            attr="PythonORAM",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value=64)],
                        keywords=[],
                    ),
                )

                body: list[ast.stmt] = [oram_init]
                var_slots: dict[str, int] = {}
                for sv in func_sensitive:
                    slot = self.parent._rng.randint(0, 63)
                    var_slots[sv] = slot

                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        handled = False
                        for t in stmt.targets:
                            if isinstance(t, ast.Name) and t.id in var_slots:
                                slot = var_slots[t.id]
                                rhs = stmt.value
                                write_call = ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(id=self._oram_name, ctx=ast.Load()),
                                        attr="write",
                                        ctx=ast.Load(),
                                    ),
                                    args=[
                                        ast.Constant(value=slot),
                                        ast.Call(
                                            func=ast.Attribute(
                                                value=ast.Call(
                                                    func=ast.Attribute(
                                                        value=ast.Name(id="struct", ctx=ast.Load()),
                                                        attr="pack",
                                                        ctx=ast.Load(),
                                                    ),
                                                    args=[
                                                        ast.Constant(value="<q"),
                                                        rhs,
                                                    ],
                                                    keywords=[],
                                                ),
                                                attr="ljust",
                                                ctx=ast.Load(),
                                            ),
                                            args=[ast.Constant(value=32), ast.Constant(value=b"\x00")],
                                            keywords=[],
                                        ),
                                    ],
                                    keywords=[],
                                )
                                body.append(ast.Expr(value=write_call))
                                handled = True
                                break
                        if not handled:
                            body.append(stmt)

                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        for i, arg in enumerate(call.args):
                            if isinstance(arg, ast.Name) and arg.id in var_slots:
                                slot = var_slots[arg.id]
                                new_arg = ast.Subscript(
                                    value=ast.Call(
                                        func=ast.Attribute(
                                            value=ast.Name(id="struct", ctx=ast.Load()),
                                            attr="unpack",
                                            ctx=ast.Load(),
                                        ),
                                        args=[
                                            ast.Constant(value="<q"),
                                            ast.Call(
                                                func=ast.Attribute(
                                                    value=ast.Name(id=self._oram_name, ctx=ast.Load()),
                                                    attr="read",
                                                    ctx=ast.Load(),
                                                ),
                                                args=[ast.Constant(value=slot)],
                                                keywords=[],
                                            ),
                                        ],
                                        keywords=[],
                                    ),
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                )
                                call.args[i] = new_arg
                        body.append(stmt)
                    else:
                        body.append(stmt)

                node.body = body
                return node

            def visit_Module(self, node: ast.Module) -> ast.Module:
                node = self.generic_visit(node)
                if self._oram_injected:
                    node.body.insert(0, ast.Import(
                        names=[ast.alias(name="struct", asname=None)],
                    ))
                    node.body.insert(0, ast.Import(
                        names=[ast.alias(name="scripts.runtime.oram_sim", asname=None)],
                    ))
                return node

        return ORAMProtector(self, sensitive).visit(tree)
