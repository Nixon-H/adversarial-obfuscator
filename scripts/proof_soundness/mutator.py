"""
proof_soundness/mutator.py — Code mutation engine for proof soundness testing (F174)

Purpose:
    Generates semantically incorrect code variants by applying AST-level
    mutations (swap operators, flip comparisons, remove statements, change
    literals, swap branches, etc.). Used to stress-test proof modules.

Architectural Role:
    Mutation generation layer for the ProofSoundnessHarness. Provides both
    high-level generate_mutations and individual strategy methods.

Security Relevance:
    The quality of soundness testing depends on the diversity and correctness
    of mutations. Each mutation should (usually) change semantics so the
    proof system can demonstrate its ability to detect incorrect code.
"""

from __future__ import annotations

import ast
import random
from typing import List, Optional


class ProofMutationEngine:
    """Applies AST-level and IR-level mutations to generate semantically incorrect variants.

    Supports ten mutation strategies (swap_add_sub, flip_comparison,
    remove_statement, change_literal, swap_operands, insert_dead_code,
    negate_condition, swap_assignment_targets, change_function_name,
    swap_return_value) plus IR-level mutations.
    """
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def mutate_ast(self, source: str) -> str:
        """Apply random AST-level mutations using _ASTMutator transformer."""
        tree = ast.parse(source, mode="exec")
        transformer = _ASTMutator(self.rng)
        mutated = transformer.visit(tree)
        ast.fix_missing_locations(mutated)
        return ast.unparse(mutated)

    def mutate_ir(self, ir_module: str) -> str:
        """Mutate IR-style code by replacing arithmetic/logical operators in assignment lines."""
        lines = ir_module.split("\n")
        mutated = list(lines)
        op_replacements = {
            "+": "-",
            "-": "+",
            "*": "//",
            "//": "*",
            "<<": ">>",
            ">>": "<<",
            "&": "|",
            "|": "&",
        }
        for i, line in enumerate(lines):
            line = line.strip()
            if "=" in line and not line.startswith("func @"):
                for old_op, new_op in op_replacements.items():
                    if old_op in line:
                        mutated[i] = mutated[i].replace(old_op, new_op, 1)
                        if mutated[i] != lines[i]:
                            break
        return "\n".join(mutated)

    def mutate_add_to_sub(self, ir: str) -> str:
        """Replace all '+' with '-' in IR source."""
        result = ir.replace("+", "-")
        return result if result != ir else ir

    def mutate_swap_operands(self, ir: str) -> str:
        """Swap the two operands of the first addition expression found in IR."""
        lines = ir.split("\n")
        swapped = list(lines)
        for i, line in enumerate(lines):
            if "=" in line and "+" in line:
                parts = line.split("=", 1)
                rhs = parts[1].strip()
                if "+" in rhs:
                    ops = rhs.split("+")
                    if len(ops) == 2:
                        swapped[i] = f"{parts[0]} = {ops[1].strip()} + {ops[0].strip()}"
                        break
        return "\n".join(swapped)

    def mutate_remove_block(self, ir: str) -> str:
        """Remove the last block from an IR module."""
        lines = ir.split("\n")
        block_starts = [i for i, l in enumerate(lines) if l.strip().startswith("block ")]
        if len(block_starts) > 1:
            del lines[block_starts[-1]]
        return "\n".join(lines)

    def mutate_change_constant(self, ir: str) -> str:
        """Increment the first numeric constant found in an IR assignment."""
        result = []
        changed = False
        for line in ir.split("\n"):
            if not changed and "=" in line:
                parts = line.split("=", 1)
                rhs = parts[1].strip()
                import re
                consts = re.findall(r'\b\d+\b', rhs)
                if consts:
                    old = consts[0]
                    new_val = str(int(old) + 1)
                    new_rhs = rhs.replace(old, new_val, 1)
                    line = f"{parts[0]} = {new_rhs}"
                    changed = True
            result.append(line)
        return "\n".join(result)

    def generate_mutations(self, source: str, count: int = 10) -> List[str]:
        """Generate up to `count` unique mutations using randomly selected strategies.

        Tries each strategy; if fewer than `count` are produced, fills with
        swap_add_sub variants.
        """
        mutations: List[str] = []
        seen: set = set()
        strategies = [
            self._mutate_swap_add_sub,
            self._mutate_flip_comparison,
            self._mutate_remove_statement,
            self._mutate_change_literal,
            self._mutate_swap_binary_operands,
            self._mutate_insert_dead_code,
            self._mutate_negate_condition,
            self._mutate_swap_assignment_targets,
            self._mutate_change_function_name,
            self._mutate_swap_return_value,
        ]
        for _ in range(count * 3):
            if len(mutations) >= count:
                break
            strat = self.rng.choice(strategies)
            try:
                mutated = strat(source)
                if mutated != source and mutated not in seen:
                    seen.add(mutated)
                    mutations.append(mutated)
            except Exception:
                continue
        # Bounded fallback.  This used to be an open `while`: if
        # _mutate_swap_add_sub cannot change the source (no '+' to swap --
        # "def f():\n    pass\n" is exactly that) or keeps producing a
        # value already in `seen`, the condition never advances and the
        # call spins forever.  That is the intermittent hang the suite hit
        # after ~3200 tests: whether the fallback is even reached depends
        # on the RNG picking an effective strategy among the first three
        # tries, so it looked version- and runner-specific.
        attempts = 0
        limit = max(count * 10, 10)
        while len(mutations) < count and attempts < limit:
            attempts += 1
            mutated = self._mutate_swap_add_sub(source)
            if mutated != source and mutated not in seen:
                seen.add(mutated)
                mutations.append(mutated)
        return mutations[:count]

    def _mutate_swap_add_sub(self, source: str) -> str:
        """Swap the first '+' with '-' and vice versa to create a semantic change."""
        result = source.replace("+", "-")
        result = result.replace("-", "+", 1)
        result = result.replace("+", "-", 1)
        return result

    def _mutate_flip_comparison(self, source: str) -> str:
        """Flip a comparison operator (<= → >=, < → >, == → !=, etc.) or negate the if condition."""
        result = source
        for old, new in [("<=", ">="), (">=", "<="), ("<", ">"), (">", "<"),
                         ("==", "!="), ("!=", "==")]:
            if old in result:
                result = result.replace(old, new, 1)
                break
        if result == source:
            result = source.replace("if ", "if not (", 1) + ")" if "if " in source else source
        return result

    def _mutate_remove_statement(self, source: str) -> str:
        """Remove a random non-def, non-class, non-import, non-pass, non-return statement."""
        lines = source.split("\n")
        body_lines = [i for i, l in enumerate(lines) if l.strip() and not l.strip().startswith("def ") and not l.strip().startswith("class ") and not l.strip().startswith("import ") and not l.strip().startswith("from ")]
        removable = [i for i in body_lines if lines[i].strip() not in ("pass", "return")]
        if removable:
            idx = self.rng.choice(removable)
            lines.pop(idx)
        return "\n".join(lines)

    def _mutate_change_literal(self, source: str) -> str:
        """Change the first numeric literal by adding a random delta."""
        result = list(source)
        found = False
        for idx, ch in enumerate(source):
            if ch.isdigit() and not found:
                start = idx
                while idx < len(source) and source[idx].isdigit():
                    idx += 1
                val = int(source[start:idx])
                if val != 0:
                    delta = self.rng.choice([1, -1, 2, -2, 10, -10])
                    new_val = max(0, val + delta)
                    if new_val != val:
                        result[start:idx] = str(new_val)
                        found = True
                        break
            else:
                idx += 1
        return "".join(result)

    def _mutate_swap_binary_operands(self, source: str) -> str:
        """Swap left and right operands of a binary operation using _BinaryOperandSwapper."""
        tree = ast.parse(source, mode="exec")
        transformer = _BinaryOperandSwapper(self.rng)
        mutated = transformer.visit(tree)
        ast.fix_missing_locations(mutated)
        result = ast.unparse(mutated)
        return result if result != source else source

    def _mutate_insert_dead_code(self, source: str) -> str:
        """Insert a dead-code line (e.g. if False: x = 1) after the first def or return."""
        lines = source.split("\n")
        dead_lines = [
            "    _ = None",
            "    pass  # dead",
            "    if False: x = 1",
        ]
        insert_positions = [i for i, l in enumerate(lines) if l.strip().startswith("def ") or l.strip().startswith("    return")]
        if insert_positions:
            pos = insert_positions[0] + 1
            dead_line = self.rng.choice(dead_lines)
            lines.insert(min(pos, len(lines)), dead_line)
        return "\n".join(lines)

    def _mutate_negate_condition(self, source: str) -> str:
        """Wrap the if-test in a not() using _ConditionNegator."""
        tree = ast.parse(source, mode="exec")
        transformer = _ConditionNegator(self.rng)
        mutated = transformer.visit(tree)
        ast.fix_missing_locations(mutated)
        result = ast.unparse(mutated)
        return result if result != source else source

    def _mutate_swap_assignment_targets(self, source: str) -> str:
        """Swap the left-hand sides of two random assignment statements."""
        lines = source.split("\n")
        assigns = [i for i, l in enumerate(lines) if "=" in l and l.strip().startswith("    ") and not l.strip().startswith("    if ") and not l.strip().startswith("    for ") and not l.strip().startswith("    while ") and not l.strip().startswith("    def ")]
        if len(assigns) >= 2:
            i, j = self.rng.sample(assigns, 2)
            lines[i], lines[j] = lines[j], lines[i]
        return "\n".join(lines)

    def _mutate_change_function_name(self, source: str) -> str:
        """Append '_mutated' to the first function definition's name."""
        tree = ast.parse(source, mode="exec")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                node.name = node.name + "_mutated"
                break
        return ast.unparse(tree)

    def _mutate_swap_return_value(self, source: str) -> str:
        """Modify the first return value: add a random offset, flip sign, or swap add/sub."""
        tree = ast.parse(source, mode="exec")
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is not None:
                if isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, (int, float)):
                        node.value.value = node.value.value + self.rng.randint(1, 100)
                elif isinstance(node.value, ast.UnaryOp) and isinstance(node.value.op, ast.USub):
                    node.value = node.value.operand
                elif isinstance(node.value, ast.BinOp):
                    if isinstance(node.value.op, ast.Add):
                        node.value.op = ast.Sub()
                    elif isinstance(node.value.op, ast.Sub):
                        node.value.op = ast.Add()
                break
        return ast.unparse(tree)


class _ASTMutator(ast.NodeTransformer):
    """AST transformer that randomly swaps Add↔Sub and flips comparison operators."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        if self.rng.random() < 0.3:
            if isinstance(node.op, ast.Add):
                node.op = ast.Sub()
            elif isinstance(node.op, ast.Sub):
                node.op = ast.Add()
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        if self.rng.random() < 0.3 and node.ops:
            new_ops = []
            for op in node.ops:
                if isinstance(op, ast.Lt):
                    new_ops.append(ast.Gt())
                elif isinstance(op, ast.Gt):
                    new_ops.append(ast.Lt())
                elif isinstance(op, ast.LtE):
                    new_ops.append(ast.GtE())
                elif isinstance(op, ast.GtE):
                    new_ops.append(ast.LtE())
                elif isinstance(op, ast.Eq):
                    new_ops.append(ast.NotEq())
                elif isinstance(op, ast.NotEq):
                    new_ops.append(ast.Eq())
                else:
                    new_ops.append(op)
            node.ops = new_ops
        return node


class _BinaryOperandSwapper(ast.NodeTransformer):
    """AST transformer that randomly swaps left/right operands of Add and Mult BinOps."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self._visited = set()

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        node_id = id(node)
        if node_id not in self._visited and isinstance(node.op, (ast.Add, ast.Mult)):
            self._visited.add(node_id)
            if self.rng.random() < 0.5:
                left = node.left
                right = node.right
                if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                    node.left, node.right = right, left
        return node


class _ConditionNegator(ast.NodeTransformer):
    """AST transformer that randomly wraps if-tests with not()."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def visit_If(self, node: ast.If) -> ast.AST:
        if self.rng.random() < 0.5:
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        return node
