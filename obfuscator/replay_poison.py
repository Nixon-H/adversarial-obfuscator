import ast
import os  # noqa: F401 (this line binds a name used by an embedded template)


class _EntropyBranchInjector(ast.NodeTransformer):
    def __init__(self, config: dict):
        self.config = config
        self._counter = 0
        self._entropy_var = "_nx_entropy_buf"
        self._idx_var = "_nx_entropy_idx"

    def _make_entropy_branch(self, body: list[ast.stmt]) -> list[ast.stmt]:
        idx = self._counter
        self._counter += 1

        entropy_branch = ast.If(
            test=ast.Compare(
                left=ast.Subscript(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="os", ctx=ast.Load()),
                            attr="urandom",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value=1)],
                        keywords=[],
                    ),
                    slice=ast.Constant(value=0),
                    ctx=ast.Load(),
                ),
                ops=[ast.Gt()],
                comparators=[ast.Constant(value=128)],
            ),
            body=[
                ast.Assign(
                    targets=[ast.Name(id=f"_{self._entropy_var}_{idx}", ctx=ast.Store())],
                    value=ast.Subscript(
                        value=ast.Name(id=self._entropy_var, ctx=ast.Load()),
                        slice=ast.Name(id=self._idx_var, ctx=ast.Load()),
                        ctx=ast.Load(),
                    ),
                ),
                ast.Assign(
                    targets=[ast.Name(id=self._idx_var, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.BinOp(
                            left=ast.Name(id=self._idx_var, ctx=ast.Load()),
                            op=ast.Add(),
                            right=ast.Constant(value=1),
                        ),
                        op=ast.Mod(),
                        right=ast.Constant(value=256),
                    ),
                ),
            ],
            orelse=[],
        )
        return body + [entropy_branch]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._make_entropy_branch(node.body)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        node.body = self._make_entropy_branch(node.body)
        self.generic_visit(node)
        return node


def inject_entropy_branches(source: str, config: dict) -> str:
    if not source.strip():
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not funcs:
        # Nothing to instrument: do not touch the foreign module at all
        # (no import, no globals).
        return source

    # Avoid clobbering names the target module already binds: never
    # inject globals (a foreign setattr equivalent) when unsupported.
    bound = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    bound |= {n.name for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    if "_nx_entropy_buf" in bound or "_nx_entropy_idx" in bound:
        return source

    # Guarded import: only add `import os` when no bare `import os`
    # already binds the name in the target module — and never when the
    # target binds its own `os` (importing would clobber it).
    has_bare_os = any(
        isinstance(n, ast.Import)
        and any(a.name == "os" and a.asname is None for a in n.names)
        for n in ast.walk(tree)
    )
    if "os" in bound and not has_bare_os:
        return source
    at = 0
    if not has_bare_os:
        import_os = ast.Import(names=[ast.alias(name="os", asname=None)])
        tree.body.insert(0, import_os)
        at = 1

    tree.body.insert(at, ast.Assign(
        targets=[ast.Name(id="_nx_entropy_buf", ctx=ast.Store())],
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="os", ctx=ast.Load()),
                attr="urandom",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value=256)],
            keywords=[],
        ),
    ))

    tree.body.insert(at + 1, ast.Assign(
        targets=[ast.Name(id="_nx_entropy_idx", ctx=ast.Store())],
        value=ast.Constant(value=0),
    ))

    injector = _EntropyBranchInjector(config)
    tree = injector.visit(tree)
    ast.fix_missing_locations(tree)

    return ast.unparse(tree)


def inject_cfg_poisoning(ir_module, config: dict):
    num_dead_cases = config.get("cfgp_num_dead_cases", 4)

    if hasattr(ir_module, "functions"):
        for func in ir_module.functions:
            if hasattr(func, "blocks") and func.blocks:
                for block in func.blocks:
                    _add_dead_dispatcher_cases(block, num_dead_cases)
        return ir_module
    return ir_module


def _add_dead_dispatcher_cases(block, num_cases: int):
    import random
    if not hasattr(block, "instructions") or not block.instructions:
        return
    terminator = block.instructions[-1] if block.instructions else None
    if terminator is None:
        return
    if getattr(terminator, "opcode", "") not in ("switch", "br"):
        return
    for _ in range(num_cases):
        fake_label = f"entropy_dead_{random.randint(0, 0xFFFF)}"
        if not hasattr(block, "dead_cases"):
            block.dead_cases = []
        block.dead_cases.append(fake_label)


def generate_rdrand_ir_stub() -> str:
    return """
declare i64 @llvm.readcyclecounter()

define internal i64 @__rdrand_stub() {
entry:
  %val = call i64 @llvm.readcyclecounter()
  %entropy = xor i64 %val, 123456789
  ret i64 %entropy
}

define internal void @__replay_poison_entropy() {
entry:
  %e = call i64 @__rdrand_stub()
  %ptr = alloca i64, align 8
  store i64 %e, ptr %ptr, align 8
  %loaded = load i64, ptr %ptr, align 8
  %dead = icmp eq i64 %loaded, 0
  br i1 %dead, label %reentry, label %reentry
reentry:
  ret void
}
"""
