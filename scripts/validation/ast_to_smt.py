"""
validation/ast_to_smt.py

Purpose:
Translates Python AST nodes into Z3 BitVec formulas. Supports assignments,
returns, conditionals (If/IfExp), binary/unary/compare operations, and
function definitions. Used as the front-end for SMT-based equivalence
checking of source-level transformations.

Security Relevance:
This translator defines the formal semantics of the Python subset that
the obfuscation pipeline can safely transform. Any mismatch between this
model and actual Python semantics can cause the proof system to certify
incorrect transformations as safe.

Dependencies:
- ast (Python standard library)
- z3 (BitVec solver)
"""
import ast
import z3

BITWIDTH = 64


def _bv(name):
    """Create a BitVec variable with the given name."""
    return z3.BitVec(name, BITWIDTH)


def _bvslt(a, b):
    """Signed less-than for BitVec."""
    return a < b


def _bvsle(a, b):
    """Signed less-or-equal for BitVec."""
    return a <= b


def _bvsgt(a, b):
    """Signed greater-than for BitVec."""
    return a > b


def _bvsge(a, b):
    """Signed greater-or-equal for BitVec."""
    return a >= b


def _bvudiv(a, b):
    """Unsigned division for BitVec."""
    return z3.BVUDiv(a, b)


def _bvsdiv(a, b):
    """Signed division for BitVec."""
    return z3.BVSDiv(a, b)


def _bvsmod(a, b):
    """Signed modulo for BitVec."""
    return z3.SRem(a, b)


class ASTToSMT:
    """
    Translates a Python AST into a Z3 Bool formula encoding the program's
    semantics. Tracks assigned variables and the single output variable.

    What it validates:
    - Assignment stores the RHS BitVec expression to the LHS variable.
    - Return sets the output variable.
    - If/IfExp creates an ITE (if-then-else) in Z3.
    - Binary, unary, and comparison ops are translated to BitVec operations.

    Security impact:
    If this translator is too permissive (e.g., ignores a side effect), the
    proof system may certify transformations that actually change behavior.

    Failure mode:
    Unsupported AST nodes return BitVecVal(0), silently truncating the
    program's semantics. This can cause false equivalence claims.
    """
    def __init__(self):
        self.z3_vars: dict[str, z3.BitVecRef] = {}
        self._output_var: z3.BitVecRef | None = None

    def _ensure_var(self, name: str) -> z3.BitVecRef:
        if name not in self.z3_vars:
            self.z3_vars[name] = _bv(name)
        return self.z3_vars[name]

    def translate(self, node: ast.AST) -> z3.BoolRef:
        if isinstance(node, ast.Module):
            stmts = node.body
        elif isinstance(node, ast.FunctionDef):
            return self._translate_function(node)
        else:
            stmts = [node]

        asserts = []
        for stmt in stmts:
            result = self._translate_stmt(stmt)
            if result is not None:
                asserts.append(result)
        return z3.And(*asserts) if asserts else z3.BoolVal(True)

    def _translate_stmt(self, stmt: ast.AST):
        if isinstance(stmt, ast.Assign):
            return self._translate_assign(stmt)
        elif isinstance(stmt, ast.Return):
            return self._translate_return(stmt)
        elif isinstance(stmt, ast.If):
            return self._translate_if(stmt)
        elif isinstance(stmt, ast.Expr):
            return self._translate_expr(stmt.value)
        elif isinstance(stmt, ast.Pass):
            return None
        elif isinstance(stmt, ast.FunctionDef):
            return self._translate_function(stmt)
        return None

    def _translate_function(self, node: ast.FunctionDef) -> z3.BoolRef:
        body_asserts = []
        self._output_var = None
        for stmt in node.body:
            result = self._translate_stmt(stmt)
            if result is not None:
                body_asserts.append(result)
        return z3.And(*body_asserts) if body_asserts else z3.BoolVal(True)

    def _translate_assign(self, node: ast.Assign) -> z3.BoolRef | None:
        val = self._translate_expr(node.value)
        targets = []
        for t in node.targets:
            if isinstance(t, ast.Name):
                var = self._ensure_var(t.id)
                targets.append(var == val)
        return z3.And(*targets) if targets else None

    def _translate_return(self, node: ast.Return):
        if node.value is not None:
            val = self._translate_expr(node.value)
            self._output_var = val
        return None

    def _translate_if(self, node: ast.If) -> z3.BoolRef | None:
        cond = self._translate_expr(node.test)
        cond_bool = (cond != 0)

        prev_output = self._output_var

        self._output_var = None
        then_asserts = []
        for stmt in node.body:
            r = self._translate_stmt(stmt)
            if r is not None:
                then_asserts.append(r)
        then_output = self._output_var

        self._output_var = None
        else_asserts = []
        for stmt in node.orelse:
            r = self._translate_stmt(stmt)
            if r is not None:
                else_asserts.append(r)
        else_output = self._output_var

        if then_output is not None and else_output is not None:
            self._output_var = z3.If(cond_bool, then_output, else_output)
        elif then_output is not None:
            self._output_var = z3.If(cond_bool, then_output, z3.BitVecVal(0, BITWIDTH))
        elif else_output is not None:
            self._output_var = else_output
        else:
            self._output_var = prev_output

        then_expr = z3.And(*then_asserts) if then_asserts else z3.BoolVal(True)
        else_expr = z3.And(*else_asserts) if else_asserts else z3.BoolVal(True)
        return z3.If(cond_bool, then_expr, else_expr)

    def _translate_expr(self, node: ast.AST) -> z3.BitVecRef:
        if isinstance(node, ast.Constant):
            if node.value is None:
                return z3.BitVecVal(0, BITWIDTH)
            if isinstance(node.value, bool):
                return z3.BitVecVal(1 if node.value else 0, BITWIDTH)
            if isinstance(node.value, (int, float)):
                return z3.BitVecVal(int(node.value) & ((1 << BITWIDTH) - 1), BITWIDTH)
            return z3.BitVecVal(0, BITWIDTH)
        elif isinstance(node, ast.Name):
            return self._ensure_var(node.id)
        elif isinstance(node, ast.UnaryOp):
            return self._translate_unaryop(node)
        elif isinstance(node, ast.BinOp):
            return self._translate_binop(node)
        elif isinstance(node, ast.Compare):
            return self._translate_compare(node)
        elif isinstance(node, ast.IfExp):
            return self._translate_ifexp(node)
        elif isinstance(node, ast.Call):
            return self._translate_call(node)
        return z3.BitVecVal(0, BITWIDTH)

    def _translate_unaryop(self, node: ast.UnaryOp) -> z3.BitVecRef:
        operand = self._translate_expr(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        elif isinstance(node.op, ast.USub):
            return -operand
        elif isinstance(node.op, ast.Invert):
            return ~operand
        elif isinstance(node.op, ast.Not):
            return z3.If((operand != 0), z3.BitVecVal(0, BITWIDTH), z3.BitVecVal(1, BITWIDTH))
        return operand

    def _translate_binop(self, node: ast.BinOp) -> z3.BitVecRef:
        lhs = self._translate_expr(node.left)
        rhs = self._translate_expr(node.right)
        if isinstance(node.op, ast.Add):
            return lhs + rhs
        elif isinstance(node.op, ast.Sub):
            return lhs - rhs
        elif isinstance(node.op, ast.Mult):
            return lhs * rhs
        elif isinstance(node.op, ast.Div):
            return z3.UDiv(lhs, rhs)
        elif isinstance(node.op, ast.FloorDiv):
            return z3.UDiv(lhs, rhs)
        elif isinstance(node.op, ast.Mod):
            return _bvsmod(lhs, rhs)
        elif isinstance(node.op, ast.BitXor):
            return lhs ^ rhs
        elif isinstance(node.op, ast.BitAnd):
            return lhs & rhs
        elif isinstance(node.op, ast.BitOr):
            return lhs | rhs
        elif isinstance(node.op, ast.LShift):
            return lhs << rhs
        elif isinstance(node.op, ast.RShift):
            return z3.LShR(lhs, rhs)
        elif isinstance(node.op, ast.Pow):
            return z3.BitVecVal(1, BITWIDTH)
        return lhs

    def _translate_compare(self, node: ast.Compare) -> z3.BitVecRef:
        left = self._translate_expr(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self._translate_expr(comparator)
            if isinstance(op, ast.Eq):
                cond = (left == right)
            elif isinstance(op, ast.NotEq):
                cond = (left != right)
            elif isinstance(op, ast.Lt):
                cond = _bvslt(left, right)
            elif isinstance(op, ast.LtE):
                cond = _bvsle(left, right)
            elif isinstance(op, ast.Gt):
                cond = _bvsgt(left, right)
            elif isinstance(op, ast.GtE):
                cond = _bvsge(left, right)
            elif isinstance(op, ast.Is):
                cond = (left == right)
            elif isinstance(op, ast.IsNot):
                cond = (left != right)
            else:
                cond = (left == right)
            left = z3.If(cond, z3.BitVecVal(1, BITWIDTH), z3.BitVecVal(0, BITWIDTH))
        return left

    def _translate_ifexp(self, node: ast.IfExp) -> z3.BitVecRef:
        cond = self._translate_expr(node.test)
        cond_bool = (cond != 0)
        true_val = self._translate_expr(node.body)
        false_val = self._translate_expr(node.orelse)
        return z3.If(cond_bool, true_val, false_val)

    def _translate_call(self, node: ast.Call) -> z3.BitVecRef:
        call_id = len(self.z3_vars)
        fresh = z3.BitVec(f"_call_{call_id}", BITWIDTH)
        self.z3_vars[f"_call_{call_id}"] = fresh
        return fresh

    def get_output_var(self) -> z3.BitVecRef | None:
        return self._output_var

    def get_input_vars(self) -> list[z3.BitVecRef]:
        return list(self.z3_vars.values())

    def get_input_var_names(self) -> list[str]:
        return list(self.z3_vars.keys())


def ast_to_smt_formula(source_code: str) -> tuple[z3.BoolRef, ASTToSMT]:
    tree = ast.parse(source_code)
    translator = ASTToSMT()
    formula = translator.translate(tree)
    return formula, translator
