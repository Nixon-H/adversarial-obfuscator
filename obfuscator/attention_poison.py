"""
Item 70: Attention Poisoning Graphs
Wraps function bodies in dispatcher structures that fan out to N parallel
dummy branches (with canceling noise) and fan back in, saturating LLM
attention windows.
"""

import ast
import random


class AttentionPoisonInjector(ast.NodeTransformer):
    def __init__(self, fan_out: int = 0):
        self.fan_out = fan_out
        self.input_ast_nodes = 0
        self.output_ast_nodes = 0

    def _count_nodes(self, node: ast.AST) -> int:
        return sum(1 for _ in ast.walk(node))

    def _make_opaque_predicate(self) -> ast.expr:
        a = random.randint(2, 250)
        b = random.randint(2, 250)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.Constant(value=a * b + a),
                op=ast.Mod(),
                right=ast.Constant(value=2),
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=((a * b + a) % 2))],
        )

    def _clone_stmt(self, stmt: ast.stmt) -> ast.stmt:
        try:
            return ast.parse(ast.unparse(stmt)).body[0]
        except (AttributeError, ValueError) as _e:
            import logging as _lg
            _lg.warning(f"Attention poison failed on statement: {_e}")
            ast.fix_missing_locations(stmt)
            return ast.parse(ast.unparse(stmt)).body[0]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.input_ast_nodes += self._count_nodes(node)
        self.generic_visit(node)

        if not node.body:
            return node

        if len(node.body) <= 1:
            return node

        real_stmts: list[ast.stmt] = []
        return_stmt = None
        for s in node.body:
            if isinstance(s, ast.Return):
                return_stmt = ast.parse(ast.unparse(s)).body[0]
            else:
                real_stmts.append(s)

        if not real_stmts:
            return node

        pred = self._make_opaque_predicate()

        body: list[ast.stmt] = []
        for i in range(self.fan_out):
            for j, stmt in enumerate(real_stmts):
                noise = random.randint(1, 0xFF)
                body.append(
                    ast.Assign(
                        targets=[ast.Name(id=f"_nx_d{i}_{j}", ctx=ast.Store())],
                        value=ast.Constant(value=noise),
                    )
                )
                body.append(self._clone_stmt(stmt))
                body.append(
                    ast.Assign(
                        targets=[ast.Name(id=f"_nx_c{i}_{j}", ctx=ast.Store())],
                        value=ast.Constant(value=noise ** 0),
                    )
                )

        dispatched: list[ast.stmt] = []
        opaque_var = "_nx_opaque"
        dispatched.append(
            ast.Assign(
                targets=[ast.Name(id=opaque_var, ctx=ast.Store())],
                value=pred,
            )
        )

        for i in range(self.fan_out):
            cond = ast.Compare(
                left=ast.Name(id=opaque_var, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=False)],
            )
            branch_start = i * len(real_stmts) * 3
            branch_end = branch_start + len(real_stmts) * 3
            branch_stmts = body[branch_start:branch_end]
            dispatched.append(ast.If(test=cond, body=branch_stmts, orelse=[]))

        real_block: list[ast.stmt] = [self._clone_stmt(s) for s in real_stmts]
        if return_stmt:
            real_block.append(return_stmt)

        dispatched.append(
            ast.If(
                test=ast.UnaryOp(op=ast.Not(), operand=ast.Name(id=opaque_var, ctx=ast.Load())),
                body=[ast.Pass()],
                orelse=real_block,
            )
        )

        node.body = dispatched
        ast.fix_missing_locations(node)
        self.output_ast_nodes += self._count_nodes(node)
        return node

    def explosion_ratio(self) -> float:
        if self.input_ast_nodes == 0:
            return 0.0
        return self.output_ast_nodes / self.input_ast_nodes
