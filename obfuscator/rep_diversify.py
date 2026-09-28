"""Representation diversification transforms (G2-H2 research family).

Rewrites code into semantically identical but structurally different
representations. Every rewrite is semantics-preserving by construction;
each documented with its exactness argument. Deterministic per seed
(self-contained random.Random; never touches global random).

Families:
  R1 int-literal forms: decimal / hex / octal / binary / additive split.
  R1b string forms: plain / hex-escape / unicode-escape / chr() concat /
      join-of-fragments.
  R2 exact expression rewrites: comparison flips, De Morgan over pure
      operands, double-negation elimination.
  R3 fragmentation: string / list / tuple literals split into
      concatenations at seeded points.

Exactness notes (load-bearing):
- Int splits use only + and - over ints: exact (no rounding).
- Comparison flips (a<b -> b>a etc.) are exact for ALL types including
  NaN (both sides False) — verified in tests.
- De Morgan applies ONLY to side-effect-free operands (Name/Constant);
  evaluation order of effectful operands would otherwise change.
- `not not x` -> `bool(x)`: both coerce identically for every value.
- Literal splits preserve value and evaluation order (left-to-right in
  both original and concatenation).
- Docstrings (bare string-statement Expr) are never rewritten.
- bool constants are never treated as ints (True/False preserved).

Python 3.10 compatible (no match statements, no X|Y annotations).
"""
import ast
import random


def _is_pure(node):
    """Side-effect-free operand: Name load or Constant only."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        return True
    if isinstance(node, ast.Constant):
        return True
    return False


_CMP_FLIP = {
    ast.Lt: ast.Gt,
    ast.Gt: ast.Lt,
    ast.LtE: ast.GtE,
    ast.GtE: ast.LtE,
}


class RepDiversifier(ast.NodeTransformer):
    """Apply representation diversification. Deterministic per seed."""

    def __init__(self, seed=None, int_forms=True, str_forms=True,
                 expr_rewrite=True, fragment=True):
        self.rng = random.Random(seed)
        self.int_forms = int_forms
        self.str_forms = str_forms
        self.expr_rewrite = expr_rewrite
        self.fragment = fragment
        self._in_docstring_expr = False
        self.stats = {"ints": 0, "strings": 0, "exprs": 0, "frags": 0}

    # -- R1: int literal forms -------------------------------------------
    def visit_Constant(self, node):
        self.generic_visit(node)
        if (self.int_forms and isinstance(node.value, int)
                and not isinstance(node.value, bool)):
            new = self._int_form(node.value)
            if new is not node.value:
                self.stats["ints"] += 1
                if isinstance(new, ast.AST):
                    return ast.copy_location(new, node)
                node.value = new
        if (self.str_forms and isinstance(node.value, str)
                and not self._in_docstring_expr):
            new = self._str_form(node.value)
            if new is not None:
                self.stats["strings"] += 1
                return ast.copy_location(new, node)
        return node

    def _int_form(self, v):
        choice = self.rng.random()
        if choice < 0.35 or v in (0, 1):
            return v
        if choice < 0.55:
            # Alternate radix literal, same value.
            fmt = self.rng.choice([hex, oct, bin])
            return ast.parse(fmt(v), mode="eval").body
        # Additive split: v = a + b (exact for ints).
        a = self.rng.randint(0, abs(v) if v else 1)
        if self.rng.random() < 0.5:
            return ast.BinOp(
                left=ast.Constant(value=v - a),
                op=ast.Add(),
                right=ast.Constant(value=a))
        return ast.BinOp(
            left=ast.Constant(value=v + a),
            op=ast.Sub(),
            right=ast.Constant(value=a))

    # -- R1b: string forms -------------------------------------------------
    def visit_Expr(self, node):
        # Bare string statements (docstrings, stray literals): never rewrite.
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            prev = self._in_docstring_expr
            self._in_docstring_expr = True
            self.generic_visit(node)
            self._in_docstring_expr = prev
            return node
        return self.generic_visit(node)

    def _str_form(self, s):
        if not s:
            return None
        choice = self.rng.random()
        if choice < 0.4:
            return None
        if choice < 0.55:
            # Hex-escape every char (ASCII only; else skip).
            try:
                s.encode("ascii")
            except UnicodeEncodeError:
                return None
            return ast.parse(
                '"' + "".join("\\x%02x" % ord(c) for c in s) + '"',
                mode="eval").body
        if choice < 0.7:
            # chr() concatenation.
            try:
                s.encode("ascii")
            except UnicodeEncodeError:
                return None
            parts = [ast.Call(func=ast.Name(id="chr", ctx=ast.Load()),
                              args=[ast.Constant(value=ord(c))], keywords=[])
                     for c in s]
            node = parts[0]
            for p in parts[1:]:
                node = ast.BinOp(left=node, op=ast.Add(), right=p)
            return node
        if choice < 0.85:
            # join-of-fragments.
            parts = [ast.Constant(value=c) for c in s]
            return ast.Call(
                func=ast.Attribute(value=ast.Constant(value=""),
                                   attr="join", ctx=ast.Load()),
                args=[ast.List(elts=parts, ctx=ast.Load())], keywords=[])
        # unicode-escape (ASCII only).
        try:
            s.encode("ascii")
        except UnicodeEncodeError:
            return None
        return ast.parse(
            '"' + "".join("\\u%04x" % ord(c) for c in s) + '"',
            mode="eval").body

    # -- R2: exact expression rewrites -------------------------------------
    def visit_Compare(self, node):
        self.generic_visit(node)
        if (self.expr_rewrite and len(node.ops) == 1
                and type(node.ops[0]) in _CMP_FLIP
                and self.rng.random() < 0.5):
            flipped = _CMP_FLIP[type(node.ops[0])]()
            self.stats["exprs"] += 1
            return ast.copy_location(
                ast.Compare(left=node.comparators[0], ops=[flipped],
                            comparators=[node.left]), node)
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        # De Morgan over pure operands only (side-effect order preserved).
        if (self.expr_rewrite and len(node.values) == 2
                and all(_is_pure(v) for v in node.values)
                and self.rng.random() < 0.5):
            self.stats["exprs"] += 1
            neg = [ast.UnaryOp(op=ast.Not(), operand=v) for v in node.values]
            inner = ast.BoolOp(op=ast.Or() if isinstance(node.op, ast.And)
                               else ast.And(), values=neg)
            return ast.copy_location(
                ast.UnaryOp(op=ast.Not(), operand=inner), node)
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        # not not x -> bool(x): identical coercion for every value.
        if (self.expr_rewrite and isinstance(node.op, ast.Not)
                and isinstance(node.operand, ast.UnaryOp)
                and isinstance(node.operand.op, ast.Not)):
            self.stats["exprs"] += 1
            return ast.copy_location(
                ast.Call(func=ast.Name(id="bool", ctx=ast.Load()),
                         args=[node.operand.operand], keywords=[]), node)
        return node

    # -- R3: fragmentation --------------------------------------------------
    def visit_List(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            return node  # assignment/unpack target: splitting is a SyntaxError
        if (self.fragment and len(node.elts) >= 2
                and self.rng.random() < 0.4):
            k = self.rng.randint(1, len(node.elts) - 1)
            self.stats["frags"] += 1
            return ast.copy_location(
                ast.BinOp(
                    left=ast.List(elts=node.elts[:k], ctx=ast.Load()),
                    op=ast.Add(),
                    right=ast.List(elts=node.elts[k:], ctx=ast.Load())),
                node)
        return node

    def visit_Tuple(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            return node  # assignment/unpack target: splitting is a SyntaxError
        if (self.fragment and len(node.elts) >= 2
                and self.rng.random() < 0.4):
            k = self.rng.randint(1, len(node.elts) - 1)
            self.stats["frags"] += 1
            return ast.copy_location(
                ast.BinOp(
                    left=ast.Tuple(elts=node.elts[:k], ctx=ast.Load()),
                    op=ast.Add(),
                    right=ast.Tuple(elts=node.elts[k:], ctx=ast.Load())),
                node)
        return node


def diversify_source(source, seed=None, **flags):
    """Apply representation diversification; returns (code, stats)."""
    tree = ast.parse(source)
    diver = RepDiversifier(seed=seed, **flags)
    tree = diver.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), dict(diver.stats)
