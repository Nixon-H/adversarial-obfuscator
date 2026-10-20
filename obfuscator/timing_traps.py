import ast

TIMING_THRESHOLD_DEFAULT = 1_000_000


class _TimingInjector(ast.NodeTransformer):
    def __init__(self, threshold: int, hard_exit: bool):
        self.threshold = threshold
        self.hard_exit = hard_exit
        self._counter = 0

    def _make_timing_check(self, body: list[ast.stmt]) -> list[ast.stmt]:
        t0_name = f"_t0_{self._counter}"
        t1_name = f"_t1_{self._counter}"
        self._counter += 1

        t0_assign = ast.Assign(
            targets=[ast.Name(id=t0_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="time", ctx=ast.Load()),
                        attr="perf_counter_ns",
                        ctx=ast.Load(),
                    ),
                    attr="__call__",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            ),
        )

        t1_assign = ast.Assign(
            targets=[ast.Name(id=t1_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="time", ctx=ast.Load()),
                        attr="perf_counter_ns",
                        ctx=ast.Load(),
                    ),
                    attr="__call__",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            ),
        )

        delta_compare = ast.Compare(
            left=ast.BinOp(
                left=ast.Name(id=t1_name, ctx=ast.Load()),
                op=ast.Sub(),
                right=ast.Name(id=t0_name, ctx=ast.Load()),
            ),
            ops=[ast.Gt()],
            comparators=[ast.Constant(value=self.threshold)],
        )

        if self.hard_exit:
            degradation = ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="sys", ctx=ast.Load()),
                        attr="exit",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value=1)],
                    keywords=[],
                ),
            )
        else:
            degradation = ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="print", ctx=ast.Load()),
                        attr="__call__",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value="[degradation] timing check triggered")],
                    keywords=[],
                ),
            )

        if_node = ast.If(test=delta_compare, body=[degradation], orelse=[])
        return [t0_assign] + body + [t1_assign, if_node]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._make_timing_check(node.body)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        node.body = self._make_timing_check(node.body)
        self.generic_visit(node)
        return node


def inject_timing_checks(source: str, config: dict) -> str:
    threshold = config.get("timing_threshold", TIMING_THRESHOLD_DEFAULT)
    hard_exit = config.get("timing_hard_exit", False)

    tree = ast.parse(source)

    import_time = ast.Import(names=[ast.alias(name="time", asname=None)])
    tree.body.insert(0, import_time)
    if hard_exit:
        # The trap body calls sys.exit(); import sys as well (without it
        # the emitted module raises NameError instead of exiting).
        tree.body.insert(1, ast.Import(names=[ast.alias(name="sys", asname=None)]))

    injector = _TimingInjector(threshold=threshold, hard_exit=hard_exit)
    tree = injector.visit(tree)
    ast.fix_missing_locations(tree)

    return ast.unparse(tree)


def generate_rdtsc_ir_pattern(config: dict) -> str:
    threshold = config.get("timing_threshold", TIMING_THRESHOLD_DEFAULT)
    hard_exit = config.get("timing_hard_exit", False)
    exit_label = "degradation_exit" if hard_exit else "degradation_silent"

    # The newline lives in a plain string: a backslash inside an f-string
    # expression is Python 3.12+ only, and this module must import on
    # 3.10.
    _exit_body = ("call void @exit(i32 1)" + chr(10) + "  unreachable"
                  if hard_exit else "ret void")
    _exit_line = "  " + _exit_body + chr(10)

    ir = (
        f"\n"
        f"; RDTSC check pattern injected at IR level\n"
        f"define internal i64 @__rdtsc() {{\n"
        f"entry:\n"
        f"  %t = call i64 @llvm.readcyclecounter()\n"
        f"  ret i64 %t\n"
        f"}}\n"
        f"\n"
        f"define internal void @__timing_trap() {{\n"
        f"entry:\n"
        f"  %t0 = call i64 @__rdtsc()\n"
        f"  ; noop loop placeholder\n"
        f"  %t1 = call i64 @__rdtsc()\n"
        f"  %delta = sub i64 %t1, %t0\n"
        f"  %threshold = icmp ugt i64 %delta, {threshold}\n"
        f"  br i1 %threshold, label %{exit_label}, label %ok\n"
        f"\n"
        f"ok:\n"
        f"  ret void\n"
        f"\n"
        f"{exit_label}:\n"
        f"{_exit_line}"
        f"}}\n"
    )
    return ir
