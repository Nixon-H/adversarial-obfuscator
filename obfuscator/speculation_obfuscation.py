import ast
import random
from typing import List, Optional, Set


class SpeculationObfuscator(ast.NodeTransformer):
    TRAINING_SEQUENCE_LEN = 8

    def __init__(self, seed: int = 0xCAFEBABE):
        self.rng = random.Random(seed)
        self.gadget_count = 0
        self.inserted_vars: Set[str] = set()
        self._array_sizes: dict = {}

    def _make_spectre_training(self, guard_var: str) -> ast.stmt:
        var_name = f"_spec_train_{self.gadget_count}"
        self.inserted_vars.add(var_name)

        body: List[ast.stmt] = [
            ast.Assign(
                targets=[ast.Name(id=var_name, ctx=ast.Store())],
                value=ast.Constant(value=self.rng.randint(0, 255)),
            ),
        ]

        for i in range(self.TRAINING_SEQUENCE_LEN):
            train_body: List[ast.stmt] = [
                ast.Assign(
                    targets=[ast.Name(id=var_name, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Name(id=var_name, ctx=ast.Load()),
                        op=ast.Mult(),
                        right=ast.Constant(value=(i + 1)),
                    ),
                )
            ]
            train_orelse: List[ast.stmt] = [
                ast.Assign(
                    targets=[ast.Name(id=var_name, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Name(id=var_name, ctx=ast.Load()),
                        op=ast.Add(),
                        right=ast.Constant(value=(i + 2)),
                    ),
                )
            ]
            cond_var = ast.Compare(
                left=ast.BinOp(
                    left=ast.Name(id=var_name, ctx=ast.Load()),
                    op=ast.Add(),
                    right=ast.Constant(value=i),
                ),
                ops=[ast.Gt()],
                comparators=[ast.Constant(value=128)],
            )
            body.append(ast.If(test=cond_var, body=train_body, orelse=train_orelse))

        return ast.If(
            test=ast.Compare(
                left=ast.Name(id=guard_var, ctx=ast.Load()),
                ops=[ast.Gt()],
                comparators=[ast.Constant(value=0)],
            ),
            body=body,
            orelse=[],
        )

    def _make_speculation_gadget(self, guard_var: str) -> ast.stmt:
        gadget_name = f"_spec_gadget_{self.gadget_count}"
        self.inserted_vars.add(gadget_name)

        init = ast.Assign(
            targets=[ast.Name(id=gadget_name, ctx=ast.Store())],
            value=ast.Constant(value=0),
        )

        update = ast.Assign(
            targets=[ast.Name(id=gadget_name, ctx=ast.Store())],
            value=ast.BinOp(
                left=ast.Name(id=gadget_name, ctx=ast.Load()),
                op=ast.Add(),
                right=ast.Constant(value=1),
            ),
        )

        inner_if = ast.If(
            test=ast.Compare(
                left=ast.Name(id=guard_var, ctx=ast.Load()),
                ops=[ast.Gt()],
                comparators=[ast.Constant(value=self.rng.randint(100, 1000))],
            ),
            body=[init, update],
            orelse=[],
        )

        return ast.If(
            test=ast.Compare(
                left=ast.Name(id=guard_var, ctx=ast.Load()),
                ops=[ast.Lt()],
                comparators=[ast.Constant(value=self.rng.randint(1000, 10000))],
            ),
            body=[init, inner_if],
            orelse=[],
        )

    def _make_misprediction_training(self, guard_var: str) -> ast.stmt:
        pred_var = f"_spec_pred_{self.gadget_count}"
        self.inserted_vars.add(pred_var)

        init = ast.Assign(
            targets=[ast.Name(id=pred_var, ctx=ast.Store())],
            value=ast.Constant(value=self.rng.randint(0, 1)),
        )

        body: List[ast.stmt] = [init]

        for i in range(self.TRAINING_SEQUENCE_LEN):
            flag = (i % 2) == 0
            cond = ast.Compare(
                left=ast.Name(id=pred_var, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=flag)],
            )
            if_body = [
                ast.Assign(
                    targets=[ast.Name(id=pred_var, ctx=ast.Store())],
                    value=ast.Constant(value=1),
                )
            ]
            else_body = [
                ast.Assign(
                    targets=[ast.Name(id=pred_var, ctx=ast.Store())],
                    value=ast.Constant(value=0),
                )
            ]
            body.append(ast.If(test=cond, body=if_body, orelse=else_body))

        return ast.If(
            test=ast.Compare(
                left=ast.Name(id=guard_var, ctx=ast.Load()),
                ops=[ast.Gt()],
                comparators=[ast.Constant(value=self.rng.randint(0, 100))],
            ),
            body=body,
            orelse=[],
        )

    def _make_array_bounds_gadget(self, guard_var: str) -> ast.stmt:
        arr_name = f"_spec_arr_{self.gadget_count}"
        idx_name = f"_spec_idx_{self.gadget_count}"
        self.inserted_vars.add(arr_name)
        self.inserted_vars.add(idx_name)

        arr_size = self.rng.randint(32, 128)
        self._array_sizes[arr_name] = arr_size

        arr_init = ast.Assign(
            targets=[ast.Name(id=arr_name, ctx=ast.Store())],
            value=ast.List(
                elts=[ast.Constant(value=self.rng.randint(0, 255)) for _ in range(arr_size)],
                ctx=ast.Load(),
            ),
        )

        idx_init = ast.Assign(
            targets=[ast.Name(id=idx_name, ctx=ast.Store())],
            value=ast.Constant(value=self.rng.randint(0, arr_size - 1)),
        )

        bounds_check = ast.Compare(
            left=ast.BinOp(
                left=ast.Name(id=idx_name, ctx=ast.Load()),
                op=ast.Add(),
                right=ast.Constant(value=self.rng.randint(1, 8)),
            ),
            ops=[ast.Lt()],
            comparators=[ast.Constant(value=arr_size)],
        )

        # Type-correct speculative probe: arr[idx] (a real bounds-check-
        # bypass gadget shape). The old list-minus-int BinOp always raised
        # TypeError whenever the (always-true) guard let it execute.
        speculative_access = ast.Assign(
            targets=[ast.Name(id=idx_name, ctx=ast.Store())],
            value=ast.Subscript(
                value=ast.Name(id=arr_name, ctx=ast.Load()),
                slice=ast.Name(id=idx_name, ctx=ast.Load()),
                ctx=ast.Load(),
            ),
        )

        access_if = ast.If(
            test=bounds_check,
            body=[speculative_access],
            orelse=[ast.Assign(
                targets=[ast.Name(id=idx_name, ctx=ast.Store())],
                value=ast.Constant(value=0),
            )],
        )

        outer_if = ast.If(
            test=ast.Compare(
                left=ast.Name(id=guard_var, ctx=ast.Load()),
                ops=[ast.Gt()],
                comparators=[ast.Constant(value=0)],
            ),
            body=[arr_init, idx_init, access_if],
            orelse=[],
        )

        return outer_if

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.gadget_count = 0
        self.inserted_vars.clear()
        self._array_sizes.clear()

        guard_var = f"_spec_guard_{node.name}"
        self.inserted_vars.add(guard_var)

        node.body.insert(
            0,
            ast.Assign(
                targets=[ast.Name(id=guard_var, ctx=ast.Store())],
                value=ast.Constant(value=self.rng.randint(0x1000, 0x10000)),
            ),
        )

        insert_positions = sorted(
            self.rng.sample(range(1, len(node.body)), min(4, len(node.body) - 1))
        )

        for pos in reversed(insert_positions):
            gadget_type = self.rng.choice(["spectre", "gadget", "misprediction", "bounds"])
            if gadget_type == "spectre":
                gadget = self._make_spectre_training(guard_var)
            elif gadget_type == "gadget":
                gadget = self._make_speculation_gadget(guard_var)
            elif gadget_type == "bounds":
                gadget = self._make_array_bounds_gadget(guard_var)
            else:
                gadget = self._make_misprediction_training(guard_var)
            node.body.insert(pos, gadget)
            self.gadget_count += 1

        return self.generic_visit(node)

    def visit_If(self, node: ast.If) -> ast.If:
        node = self.generic_visit(node)
        if self.rng.random() < 0.15 and isinstance(node.test, ast.Compare):
            miss_var = f"_spec_miss_{self.gadget_count}"
            self.inserted_vars.add(miss_var)
            self.gadget_count += 1

            init = ast.Assign(
                targets=[ast.Name(id=miss_var, ctx=ast.Store())],
                value=ast.Constant(value=0),
            )

            bad_test = ast.Compare(
                left=ast.Compare(
                    left=ast.Constant(value=self.rng.randint(0, 100)),
                    ops=[ast.Gt()],
                    comparators=[ast.Constant(value=50)],
                ),
                ops=[ast.Gt()],
                comparators=[ast.Constant(value=0)],
            )

            outer_if = ast.If(
                test=bad_test,
                body=[init],
                orelse=[],
            )

            new_node = ast.If(
                test=node.test,
                body=[outer_if] + node.body,
                orelse=node.orelse,
            )
            return new_node
        return node

    def insert_speculation_barrier(self, node: ast.stmt) -> ast.stmt:
        barrier_var = f"_spec_lfence_{self.gadget_count}"
        self.inserted_vars.add(barrier_var)

        barrier = ast.Assign(
            targets=[ast.Name(id=barrier_var, ctx=ast.Store())],
            value=ast.BinOp(
                left=ast.Constant(value=self.gadget_count),
                op=ast.Add(),
                right=ast.Constant(value=1),
            ),
        )

        if isinstance(node, ast.If):
            node.body.insert(0, barrier)
        elif isinstance(node, ast.FunctionDef):
            node.body.insert(0, barrier)

        self.gadget_count += 1
        return node


def obfuscate_with_speculation(source: str, seed: int = 0xCAFEBABE) -> str:
    tree = ast.parse(source)
    obfuscator = SpeculationObfuscator(seed=seed)
    tree = obfuscator.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <source.py> [seed]", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        source = f.read()

    seed = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xCAFEBABE
    result = obfuscate_with_speculation(source, seed)
    sys.stdout.write(result)
