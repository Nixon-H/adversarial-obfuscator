import ast
import copy
import random
import secrets


def _oram_inline_stmts():
    """The ORAM implementation as AST statements, for embedding in an artefact.

    Emitted instead of `import scripts.runtime.oram_sim`, which made every
    --data-obfuscation artefact depend on the builder's source tree. The module
    imports only stdlib (math, random, typing), so it can be carried inside the
    payload and the result is self-contained.
    """
    import ast as _a
    import os as _os
    path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__)))), "scripts", "runtime", "oram_sim.py")
    with open(path, encoding="utf-8") as fh:
        tree = _a.parse(fh.read())

    # Rename the two public classes to _nx_-prefixed names. The renamers leave
    # `_nx_` identifiers alone, so inlining cannot be broken by one pass
    # renaming `PathORAM` in the base-class reference and another not renaming
    # it in the class definition ("NameError: name 'PathORAM' is not defined").
    _RENAMES = {"PathORAM": "_nx_oram_base", "PythonORAM": "_nx_oram"}

    for sub in _a.walk(tree):
        if isinstance(sub, _a.Name) and sub.id in _RENAMES:
            sub.id = _RENAMES[sub.id]
        elif isinstance(sub, _a.ClassDef) and sub.name in _RENAMES:
            sub.name = _RENAMES[sub.name]

    keep = []
    for stmt in tree.body:
        # `from __future__` must stay first in a module; typing is stdlib and
        # harmless, so keep imports and definitions, drop nothing else.
        if isinstance(stmt, _a.ImportFrom) and stmt.module == "__future__":
            continue
        keep.append(stmt)
    return keep


# Builtins that always return an int.  Used by the ORAM pass to decide
# whether an assignment can be stored through struct.pack('<q', ...).
_INT_RETURNING_CALLS = frozenset({"int", "len", "ord", "hash", "id"})

_INT_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.Pow,
               ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr, ast.BitXor)


def _is_int_expr(node, int_names=frozenset()) -> bool:
    """True when ``node`` is provably an int at run time.

    ``int_names`` are the names already proven int-valued in this scope, so
    ``counter = counter + 1`` counts as int once ``counter`` does.

    Conservative on purpose.  The ORAM pass stores a virtualized value as
    ``struct.pack('<q', value)``, which raises "required argument is not an
    integer" for anything that is not an int.  An expression this function
    cannot prove is left alone, so the assignment stays an ordinary local
    instead of producing an artefact that dies at import.
    """
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int) and not isinstance(node.value, bool)
    if isinstance(node, ast.Name):
        return node.id in int_names
    if isinstance(node, ast.BinOp):
        return (isinstance(node.op, _INT_BINOPS)
                and _is_int_expr(node.left, int_names)
                and _is_int_expr(node.right, int_names))
    if isinstance(node, ast.UnaryOp):
        return (isinstance(node.op, (ast.USub, ast.UAdd, ast.Invert))
                and _is_int_expr(node.operand, int_names))
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id in _INT_RETURNING_CALLS:
            return True
    return False


_BITWISE_BINOPS = (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)


def _arg_int_only(func, name: str) -> bool:
    """True when every read of argument ``name`` is a bitwise operand.

    ``&``, ``|``, ``^``, ``<<`` and ``>>`` only accept ints (sets aside), so
    a function that uses its argument exclusively that way can only be
    called with ints.  That makes it safe to store the argument through
    struct.pack('<q', ...) at function entry, which is what gives the ORAM
    pass something to read back.  Before this, arguments were added to the
    slot table but never written, so every read returned 0 -- the ORAM was
    injected and never used.
    """
    parents = {}
    for node in ast.walk(func):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    used = False
    for node in ast.walk(func):
        if not (isinstance(node, ast.Name) and node.id == name
                and isinstance(node.ctx, ast.Load)):
            continue
        parent = parents.get(id(node))
        if isinstance(parent, ast.BinOp) and isinstance(parent.op, _BITWISE_BINOPS):
            used = True
            continue
        if isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.Invert):
            used = True
            continue
        return False
    return used


def _int_safe_names(func, candidates) -> set:
    """Return the subset of ``candidates`` that is int-valued throughout.

    Two conditions, both required:

    * the name is assigned at the TOP LEVEL of ``func``'s body -- that is
      the only place the write path rewrites, so a name bound elsewhere
      (a module-level constant, a loop variable, a ``with ... as``) has no
      slot to read back.  ``NATIVE_BLOBS`` is the case that bit: it is
      spelled with "iv" in "native", so the keyword scan flagged it, and
      the read path rewrote it to an ORAM slot that was never written --
      the loader then compared against 0 instead of the blob table.
    * every assignment to it anywhere in ``func`` is provably int.

    Fixed point: start with every candidate, drop any name that fails
    either condition given the names still standing, and repeat until
    nothing more drops.
    """
    top_level = set()
    for stmt in func.body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name):
                    top_level.add(t.id)
        elif isinstance(stmt, (ast.AugAssign, ast.AnnAssign)):
            if isinstance(stmt.target, ast.Name):
                top_level.add(stmt.target.id)
    arg_names = {a.arg for a in func.args.args}
    int_only_args = {n for n in (set(candidates) & arg_names)
                     if _arg_int_only(func, n)}
    alive = (set(candidates) & top_level) | int_only_args
    while True:
        dropped = set()
        for name in alive:
            for stmt in ast.walk(func):
                if isinstance(stmt, ast.Assign):
                    if not any(isinstance(t, ast.Name) and t.id == name
                               for t in stmt.targets):
                        continue
                    if not _is_int_expr(stmt.value, alive):
                        dropped.add(name)
                        break
                elif isinstance(stmt, ast.AugAssign):
                    if not (isinstance(stmt.target, ast.Name)
                            and stmt.target.id == name):
                        continue
                    if not _is_int_expr(stmt.value, alive):
                        dropped.add(name)
                        break
                elif isinstance(stmt, ast.AnnAssign):
                    if not (isinstance(stmt.target, ast.Name)
                            and stmt.target.id == name):
                        continue
                    if stmt.value is not None and not _is_int_expr(stmt.value, alive):
                        dropped.add(name)
                        break
        if not dropped:
            return alive
        alive -= dropped


def _oram_write_call(slot: int, value, oram_name: str) -> ast.Call:
    """``<oram>.write(slot, struct.pack('<q', value).ljust(32, b'\\x00'))``."""
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=oram_name, ctx=ast.Load()),
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
                        args=[ast.Constant(value="<q"), value],
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


def _oram_read_expr(slot: int, oram_name: str) -> ast.expr:
    """``struct.unpack('<q', <oram>.read(slot)[:8])[0]`` -- the int read path.

    The write path pads the packed int to the 32-byte slot width, so the
    read has to slice the first 8 bytes back out.  Without the slice
    struct.unpack raised "unpack requires a buffer of 8 bytes" on every
    read, which made the whole int path unusable.
    """
    return ast.Subscript(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="struct", ctx=ast.Load()),
                attr="unpack",
                ctx=ast.Load(),
            ),
            args=[
                ast.Constant(value="<q"),
                ast.Subscript(
                    # read() returns None for a slot that was never written;
                    # `or bytes(8)` keeps the unpack from raising on it. This
                    # is bytes(8) rather than the equivalent b"\x00" * 8
                    # because the read substitution can land inside an
                    # f-string expression, where a backslash spelling is
                    # unparseable on Python < 3.12 (pre-PEP-701).
                    value=ast.BoolOp(
                        op=ast.Or(),
                        values=[
                            ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id=oram_name, ctx=ast.Load()),
                                    attr="read",
                                    ctx=ast.Load(),
                                ),
                                args=[ast.Constant(value=slot)],
                                keywords=[],
                            ),
                            ast.Call(
                                func=ast.Name(id="bytes", ctx=ast.Load()),
                                args=[ast.Constant(value=8)],
                                keywords=[],
                            ),
                        ],
                    ),
                    slice=ast.Slice(
                        lower=ast.Constant(value=0),
                        upper=ast.Constant(value=8),
                        step=None,
                    ),
                    ctx=ast.Load(),
                ),
            ],
            keywords=[],
        ),
        slice=ast.Constant(value=0),
        ctx=ast.Load(),
    )


def _oram_read_substitute(node, var_slots, oram_name):
    """Replace reads of virtualized names inside ``node`` with slot reads.

    The write path stores ``struct.pack('<q', rhs)`` and then the binding is
    gone, so a self-referential update -- ``counter = counter + 1`` -- must
    read the slot instead of the (now undefined) name.  Without this the
    emitted function raised NameError on its first update.
    """
    class _Sub(ast.NodeTransformer):
        def visit_Name(self, n):
            if isinstance(n.ctx, ast.Load) and n.id in var_slots:
                return ast.copy_location(
                    _oram_read_expr(var_slots[n.id], oram_name), n)
            return n

    return _Sub().visit(copy.deepcopy(node))


class _StorageRewriter(ast.NodeTransformer):
    """Rewrite every read/write of a virtualized name to its storage slot.

    Generic on purpose. The previous hand-written rewriter covered only
    Name / BinOp / UnaryOp / Subscript / Call-arguments / Compare, so a read
    in any other position kept the original spelling while the binding had
    moved into the virtual store. The first one to bite was a bare call
    target -- `bump = make_counter(); bump()` became
    `_vs_1[_vmap_1[0]] = make_counter(); bump()` -- and the module died with
    NameError at import. Attribute receivers, boolops, f-strings,
    comprehensions, `for` targets and `with ... as` bindings had the same
    hole.

    Nested scopes are left untouched: they bind their own names, and any
    name they capture from this frame was filtered out of the candidate set
    before this rewriter ran.
    """

    def __init__(self, var_to_vaddr, virt_read, virt_write):
        self.var_to_vaddr = var_to_vaddr
        self.virt_read = virt_read
        self.virt_write = virt_write

    def visit_FunctionDef(self, node):
        return node

    def visit_AsyncFunctionDef(self, node):
        return node

    def visit_Lambda(self, node):
        return node

    def visit_ClassDef(self, node):
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.var_to_vaddr:
            return ast.copy_location(self.virt_read(node.id), node)
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in self.var_to_vaddr:
                return ast.copy_location(
                    self.virt_write(target.id, node.value), node)
        return node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        if (isinstance(node.target, ast.Name)
                and node.target.id in self.var_to_vaddr
                and node.value is not None):
            return ast.copy_location(
                self.virt_write(node.target.id, node.value), node)
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        target = node.target
        if isinstance(target, ast.Name) and target.id in self.var_to_vaddr:
            combined = ast.BinOp(
                left=self.virt_read(target.id), op=node.op, right=node.value)
            return ast.copy_location(
                self.virt_write(target.id, combined), node)
        return node


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

                # Never virtualize a name a NESTED function declares `nonlocal`.
                # Moving `count = 0` into a state slot removes the binding the
                # inner `nonlocal count` refers to, and the module dies at import
                # with "SyntaxError: no binding for nonlocal 'count' found".
                # Found by isolating --data-obfuscation.
                _captured = set()
                for _child in ast.walk(node):
                    if _child is not node and isinstance(_child, (ast.Nonlocal, ast.Global)):
                        _captured.update(_child.names)
                if _captured:
                    vars_in_function = [v for v in vars_in_function if v not in _captured]
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
                # Names bound to a dict literal in the CURRENT scope.  Only
                # those dicts have encrypted keys (see _mutate_dict_literal),
                # so only those may have their string subscript keys
                # rewritten.  A dict that arrives from json.loads() or any
                # other external producer keeps plaintext keys, and
                # rewriting the lookup turned every access into a KeyError
                # (the section-split join read pack['sections'] from a JSON
                # pack and failed closed on every host).
                self._dict_names: set[str] = set()

            def _enter_scope(self, node: ast.AST) -> ast.AST:
                saved = self._dict_names
                self._dict_names = set()
                self.generic_visit(node)
                self._dict_names = saved
                return node

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                return self._enter_scope(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
                return self._enter_scope(node)

            def _is_local_dict(self, value: ast.AST) -> bool:
                if isinstance(value, ast.Dict):
                    return True
                return (isinstance(value, ast.Name)
                        and value.id in self._dict_names)

            def visit_Assign(self, node: ast.Assign) -> ast.Assign | list[ast.stmt]:
                if not (isinstance(node.value, ast.Dict) or
                        (isinstance(node.value, ast.Call) and
                         isinstance(node.value.func, ast.Name) and
                         node.value.func.id == "dict")):
                    # A name rebound to a non-dict no longer owns a local
                    # dict, so its subscripts must keep plaintext keys.
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            self._dict_names.discard(t.id)
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
                    # This name now owns a dict whose keys are encrypted
                    # below, so its string subscripts must be encrypted too.
                    self._dict_names.add(target_id)
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
                        isinstance(node.slice.value, str) and
                        self._is_local_dict(node.value)):
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

                # Never virtualize a name a NESTED function declares `nonlocal`:
                # replacing `count = 0` with a state slot removes the binding the
                # inner `nonlocal count` refers to, and the module cannot be
                # imported ("SyntaxError: no binding for nonlocal 'count' found").
                # Every virtualization visitor needs this filter, not just one --
                # found by isolating --data-obfuscation on a closure payload.
                _captured = set()
                for _child in ast.walk(node):
                    if _child is not node and isinstance(_child, (ast.Nonlocal, ast.Global)):
                        _captured.update(_child.names)
                if _captured:
                    vars_found = [v for v in vars_found if v not in _captured]

                # Same reasoning for a plain closure READ: a nested scope that
                # reads this binding cannot see a slot that lives in the outer
                # frame, so moving the binding there turns the read into a
                # NameError. Leave any name a nested scope touches alone.
                _nested_reads = set()
                for _child in ast.walk(node):
                    if _child is node:
                        continue
                    if isinstance(_child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                           ast.Lambda, ast.ClassDef)):
                        for _n in ast.walk(_child):
                            if isinstance(_n, ast.Name) and isinstance(_n.ctx, ast.Load):
                                _nested_reads.add(_n.id)
                if _nested_reads:
                    vars_found = [v for v in vars_found if v not in _nested_reads]

                # A name bound anywhere other than a plain top-level
                # assignment -- a `for` target, `with ... as`, `except ... as`,
                # a walrus, a `del` -- has a second write path this pass does
                # not rewrite, so the slot and the real local would diverge:
                # `total = 0; for total in range(4): pass; return total`
                # returned 0 instead of 3. Leave those names alone.
                _handled_targets = set()
                for _stmt in node.body:
                    if isinstance(_stmt, ast.Assign):
                        for _t in _stmt.targets:
                            if isinstance(_t, ast.Name):
                                _handled_targets.add(id(_t))
                    elif isinstance(_stmt, (ast.AugAssign, ast.AnnAssign)):
                        if isinstance(_stmt.target, ast.Name):
                            _handled_targets.add(id(_stmt.target))
                _other_stores = set()
                for _n in ast.walk(node):
                    if (isinstance(_n, ast.Name)
                            and isinstance(_n.ctx, (ast.Store, ast.Del))
                            and id(_n) not in _handled_targets):
                        _other_stores.add(_n.id)
                    # These bind a name held as a plain string, so the Store
                    # scan above cannot see them: `except E as e` rebinds `e`
                    # and Python deletes it at the end of the handler.
                    elif isinstance(_n, ast.ExceptHandler) and _n.name:
                        _other_stores.add(_n.name)
                    elif isinstance(_n, (ast.MatchAs, ast.MatchStar)) and _n.name:
                        _other_stores.add(_n.name)
                    elif isinstance(_n, ast.MatchMapping) and _n.rest:
                        _other_stores.add(_n.rest)
                if _other_stores:
                    vars_found = [v for v in vars_found if v not in _other_stores]

                if not vars_found:
                    return node

                rng = self.parent._rng
                nvars = len(vars_found)
                vaddr_map = list(range(nvars))
                rng.shuffle(vaddr_map)

                vstore_name = self.parent._make_rand_name("_vs")
                vmap_name = self.parent._make_rand_name("_vmap")

                vstore_init = ast.Assign(
                    targets=[ast.Name(id=vstore_name, ctx=ast.Store())],
                    value=ast.List(
                        elts=[ast.Constant(value=0) for _ in range(nvars)],
                        ctx=ast.Load(),
                    ),
                )
                vmap_init = ast.Assign(
                    targets=[ast.Name(id=vmap_name, ctx=ast.Store())],
                    value=ast.List(
                        elts=[ast.Constant(value=i) for i in vaddr_map],
                        ctx=ast.Load(),
                    ),
                )

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

                rewriter = _StorageRewriter(var_to_vaddr, _virt_read, _virt_write)
                node.body = [vstore_init, vmap_init] + [
                    rewriter.visit(stmt) for stmt in node.body
                ]
                return node

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
                # struct.pack('<q', ...) only accepts an int.  This pass
                # used to virtualize EVERY sensitive name, so an assignment
                # whose right-hand side was bytes (a key) or None (a
                # sentinel) emitted struct.pack('<q', b'...') and the
                # artefact died at import with "required argument is not an
                # integer" -- the failure that killed the native build's
                # Python fallback.  Keep only names whose every assignment
                # is provably int-valued; the rest stay ordinary locals,
                # exactly as they were before this pass existed.
                func_sensitive = [
                    v for v in func_sensitive
                    if v in _int_safe_names(node, func_sensitive)
                ]
                if not func_sensitive:
                    return node

                self._oram_injected = True
                oram_init = ast.Assign(
                    targets=[ast.Name(id=self._oram_name, ctx=ast.Store())],
                    value=ast.Call(
                        # Reference the class inlined into the artefact by
                        # visit_Module. The old dotted reference required the
                        # builder's own source tree on sys.path, so a
                        # --data-obfuscation artefact was not standalone
                        # ("ModuleNotFoundError: No module named 'scripts'").
                        func=ast.Name(id="_nx_oram", ctx=ast.Load()),
                        args=[ast.Constant(value=64)],
                        keywords=[],
                    ),
                )

                body: list[ast.stmt] = [oram_init]
                var_slots: dict[str, int] = {}
                # DISTINCT SLOTS, ALWAYS (measured 2026-11-20). This used to
                # be `rng.randint(0, 63)` per variable with no collision
                # check, so two variables could land in the SAME slot. The
                # symptom is silent and catastrophic for correctness: for
                # `result = key ^ data`, both arguments picked slot 34, the
                # transform emitted write(34, key); write(34, data) and then
                # read(34) ^ read(34), which is always 0 -- encrypt(10, 6)
                # returned 0 instead of 12. Measured rate: 8 wrong answers in
                # 400 runs (~2%), matching the birthday collision probability
                # for 2 draws from 64 slots. A protection that changes the
                # program's answer is worse than no protection, and this
                # surfaced only as an intermittent test failure -- the
                # "isolated rerun makes it pass" pattern the review warned
                # about.
                #
                # Allocation now draws WITHOUT replacement. If a function has
                # more sensitive variables than slots, the pool widens rather
                # than aliasing.
                _slot_space = max(64, len(func_sensitive))
                _slot_pool = list(range(_slot_space))
                self.parent._rng.shuffle(_slot_pool)
                for _sv_index, sv in enumerate(func_sensitive):
                    var_slots[sv] = _slot_pool[_sv_index]

                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        handled = False
                        for t in stmt.targets:
                            if isinstance(t, ast.Name) and t.id in var_slots:
                                slot = var_slots[t.id]
                                rhs = _oram_read_substitute(
                                    stmt.value, var_slots, self._oram_name)
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
                                new_arg = _oram_read_expr(
                                    slot, self._oram_name)
                                call.args[i] = new_arg
                        body.append(stmt)
                    else:
                        body.append(stmt)

                # Complete the read path.  The loop above only rewrote
                # reads in call-argument position, so `return counter` or
                # `abs(counter)` still referenced a name whose binding had
                # moved into the slot -- NameError on first use.  Rewrite
                # every remaining read of a virtualized name.
                body = [_oram_read_substitute(st, var_slots, self._oram_name)
                        for st in body]
                # Arguments have no assignment to rewrite, so bind them into
                # their slots at entry.  Built AFTER the substitution pass on
                # purpose: the value here is the argument itself, and running
                # it through the rewriter turned it into a read of the slot
                # it was about to fill.
                arg_names = {a.arg for a in node.args.args}
                arg_writes = [
                    ast.Expr(value=_oram_write_call(
                        var_slots[sv], ast.Name(id=sv, ctx=ast.Load()),
                        self._oram_name))
                    for sv in func_sensitive if sv in arg_names
                ]
                body = [oram_init] + arg_writes + body[1:]
                node.body = body
                return node

            def visit_Module(self, node: ast.Module) -> ast.Module:
                node = self.generic_visit(node)
                if self._oram_injected:
                    node.body.insert(0, ast.Import(
                        names=[ast.alias(name="struct", asname=None)],
                    ))
                    # Insert as ONE block, in order. Inserting each statement
                    # at index 0 in a loop reverses them, so `class PythonORAM`
                    # landed before the base class it inherits from:
                    # "NameError: name '_nx_oram_base' is not defined".
                    node.body[0:0] = _oram_inline_stmts()
                return node

        return ORAMProtector(self, sensitive).visit(tree)
