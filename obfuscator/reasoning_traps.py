"""
Reasoning-Loop Traps — force automated analyzers into circular dependency chains.

ReasoningLoopInjector generates functions A→B→C→A with opaque predicates
that always break the cycle at runtime. Static analysis sees infinite loops;
actual execution completes normally.
"""

import ast
import secrets
import random as _random


class ReasoningLoopInjector:
    """Injects circular call graphs that are only resolvable at runtime."""

    def __init__(self, seed: int | None = None):
        self._rng = _random.Random(seed) if seed is not None else secrets.SystemRandom()

    def inject_loop(self, tree: ast.AST, depth: int = 5) -> ast.AST:
        """Wrap each function with a circular call chain of given depth."""
        if not isinstance(tree, ast.Module):
            return tree

        funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not funcs:
            return tree

        for func in funcs:
            if depth < 2:
                continue
            chain = self._build_chain(func.name, depth)
            trap_funcs = self._build_trap_functions(chain, func)
            self._inject_trap_into_func(func, chain)
            import_idx = 0
            for j, stmt in enumerate(tree.body):
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    import_idx = j + 1
            for tf in trap_funcs:
                tree.body.insert(import_idx, tf)
                import_idx += 1

        ast.fix_missing_locations(tree)
        return tree

    def _build_chain(self, entry_name: str, depth: int) -> list[str]:
        names = [entry_name]
        for _ in range(depth - 1):
            # Seeded RNG (self._rng), not secrets.token_hex: reproducible
            # per-seed builds instead of unseeded global randomness.
            names.append(f"_nx_trap_{self._rng.getrandbits(32):08x}")
        names.append(entry_name)
        return names

    def _build_trap_functions(
        self, chain: list[str],
        entry_func: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[ast.FunctionDef]:
        funcs: list[ast.FunctionDef] = []
        for i in range(1, len(chain) - 1):
            caller = chain[i]
            callee = chain[i + 1]
            is_last = (i + 1 == len(chain) - 1)
            if not caller.startswith("_nx_trap_"):
                continue
            predicate = self._make_opaque_predicate(is_last)
            trap_call = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id=callee, ctx=ast.Load()),
                    args=[ast.Constant(value=i)],
                    keywords=[],
                )
            )
            funcs.append(
                ast.FunctionDef(
                    name=caller,
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="x")],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=[
                        ast.If(
                            test=predicate,
                            body=[trap_call],
                            orelse=[],
                        ),
                        ast.Return(value=ast.Constant(value=None)),
                    ],
                    decorator_list=[],
                    returns=None,
                )
            )
        return funcs

    def _inject_trap_into_func(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        chain: list[str],
    ) -> None:
        if len(chain) < 2:
            return
        callee = chain[1]
        predicate = self._make_opaque_predicate(False)
        trap_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id=callee, ctx=ast.Load()),
                args=[ast.Constant(value=0)],
                keywords=[],
            )
        )
        wrapper = ast.If(
            test=predicate,
            body=[trap_call],
            orelse=[],
        )
        func.body.insert(0, wrapper)

    def _make_opaque_predicate(self, break_cycle: bool) -> ast.Compare:
        a = self._rng.randint(5, 50)
        b = self._rng.randint(5, 50)

        if break_cycle:
            return ast.Compare(
                left=ast.BinOp(
                    left=ast.Constant(value=a * b),
                    op=ast.Add(),
                    right=ast.Constant(value=1),
                ),
                ops=[ast.Lt()],
                comparators=[ast.Constant(value=a * b)],
            )
        else:
            return ast.Compare(
                left=ast.BinOp(
                    left=ast.BinOp(
                        left=ast.Constant(value=a),
                        op=ast.Mult(),
                        right=ast.Constant(value=b),
                    ),
                    op=ast.Add(),
                    right=ast.Constant(value=a),
                ),
                ops=[ast.Eq()],
                comparators=[
                    ast.BinOp(
                        left=ast.Constant(value=a),
                        op=ast.Mult(),
                        right=ast.BinOp(
                            left=ast.Constant(value=b),
                            op=ast.Add(),
                            right=ast.Constant(value=1),
                        ),
                    )
                ],
            )
