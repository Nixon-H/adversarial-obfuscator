"""Dynamic and symbolic probes.

Dynamic: run the artefact and capture what its own process leaks (stdout,
stderr, tracebacks, temp files, memory maps).

Symbolic: Z3 on the recovered opaque predicates and MBA expressions -- the
reviewer's explicit challenge ("a transform is not a security mechanism until
it survives automated simplification").
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys

from .transform_solvers import (
    MAX_EXPRESSION_DEPTH,
    MAX_EXPRESSION_LENGTH,
    MAX_EXPRESSION_NODES,
    _check_expression_budget,
    _integer_literal_value,
)

#: Per-solver ceilings. z3.unknown is reported as a timeout, never as proof of
#: constancy. timeout is milliseconds; max_memory is MiB, matching Z3's options.
Z3_SOLVER_TIMEOUT_MS = 5000
Z3_SOLVER_RLIMIT = 1_000_000
Z3_SOLVER_MAX_MEMORY = 512


def probe_runtime_output(artefact_path, timeout=180):
    """Run the artefact and record everything it prints.

    A payload that prints its own identifiers/constants is leaking them; the
    build already warns about this, so measure it.
    """
    env = dict(os.environ, NIXON_LOG_REDIRECT="0")
    d = os.path.dirname(os.path.abspath(artefact_path))
    try:
        p = subprocess.run([sys.executable, artefact_path], cwd=d,
                           capture_output=True, text=True, timeout=timeout,
                           env=env)
        out, err, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        return {"probe": "runtime_output", "timed_out": True}
    return {
        "probe": "runtime_output",
        "returncode": rc,
        "stdout": out[-4000:],
        "stderr": err[-4000:],
        "timed_out": False,
    }


def probe_temp_files(artefact_path, timeout=180):
    """Does the run leave plaintext on disk?"""
    env = dict(os.environ, NIXON_LOG_REDIRECT="0")
    d = os.path.dirname(os.path.abspath(artefact_path))
    before = set(os.listdir(d))
    try:
        subprocess.run([sys.executable, artefact_path], cwd=d,
                       capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"probe": "temp_files", "timed_out": True, "new_files": []}
    after = set(os.listdir(d))
    return {"probe": "temp_files", "new_files": sorted(after - before)}


def probe_memory_maps(artefact_path, timeout=180):
    """Can a debugger-adjacent read of the process see plaintext?

    Approximates a memory dump: start the artefact, read /proc/<pid>/maps and
    look for executable mappings created at run time (RWX or private exec),
    which is where a JIT-style decryptor would live.
    """
    env = dict(os.environ, NIXON_LOG_REDIRECT="0")
    d = os.path.dirname(os.path.abspath(artefact_path))
    proc = subprocess.Popen([sys.executable, artefact_path], cwd=d,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env)
    import time
    rwx = 0
    maps_seen = 0
    try:
        for _ in range(40):
            if proc.poll() is not None:
                break
            try:
                with open("/proc/%d/maps" % proc.pid) as fh:
                    rows = fh.readlines()
                maps_seen = max(maps_seen, len(rows))
                for row in rows:
                    perms = row.split()[1] if len(row.split()) > 1 else ""
                    if "x" in perms and "w" in perms:
                        rwx += 1
            except OSError:
                break
            time.sleep(0.02)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    return {"probe": "memory_maps", "max_maps": maps_seen, "rwx_mappings": rwx}


def _z3_from_ast(text, syms, z3):
    """Translate a C-style arithmetic predicate to a Z3 expression by AST
    walk. Returns None for anything outside the allowed grammar (names must
    be known operands; no calls, attributes, subscripts, or ** )."""
    try:
        if len(text) > MAX_EXPRESSION_LENGTH:
            return None
        tree = ast.parse(text, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > MAX_EXPRESSION_NODES:
            return None
    except SyntaxError:
        return None
    _BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
            ast.Mult: lambda a, b: a * b, ast.BitAnd: lambda a, b: a & b,
            ast.BitOr: lambda a, b: a | b, ast.BitXor: lambda a, b: a ^ b,
            ast.LShift: lambda a, b: a << b, ast.RShift: lambda a, b: a >> b}
    _CMP = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
            ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
            ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}

    def walk(node, depth=0):
        if depth > MAX_EXPRESSION_DEPTH:
            raise ValueError("expression too deep")
        literal = _integer_literal_value(node, text)
        if literal is not None:
            # The operands are signed 32-bit bit-vectors. Silently truncating a
            # wider literal would answer a different question than the
            # artefact's C arithmetic, so refuse it instead.
            if not (-(1 << 31) <= literal <= (1 << 31) - 1):
                return None
            return z3.BitVecVal(literal, 32)
        if isinstance(node, ast.Expression):
            return walk(node.body, depth + 1)
        if isinstance(node, ast.Constant):
            return None
        if isinstance(node, ast.Name):
            return syms.get(node.id)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            l, r = walk(node.left, depth + 1), walk(node.right, depth + 1)
            if l is None or r is None:
                return None
            return _BIN[type(node.op)](l, r)
        if isinstance(node, ast.UnaryOp):
            v = walk(node.operand, depth + 1)
            if v is None:
                return None
            if isinstance(node.op, ast.Not):
                return z3.Not(v)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.Invert):
                return ~v
            return None
        if isinstance(node, ast.BoolOp):
            vals = [walk(v, depth + 1) for v in node.values]
            if any(v is None for v in vals):
                return None
            # C's && / || take integer operands; coerce bit-vectors to bool.
            vals = [v if z3.is_bool(v) else (v != 0) for v in vals]
            if isinstance(node.op, ast.And):
                return z3.And(*vals)
            return z3.Or(*vals)
        if isinstance(node, ast.Compare):
            l = walk(node.left, depth + 1)
            if l is None or len(node.ops) != 1 or type(node.ops[0]) not in _CMP:
                return None
            r = walk(node.comparators[0], depth + 1)
            if r is None:
                return None
            return _CMP[type(node.ops[0])](l, r)
        return None

    try:
        return walk(tree)
    except (ValueError, RecursionError):
        return None
    except Exception:
        # z3 sort/type errors on unexpected shapes: not translatable, not a crash
        return None


def probe_z3_opaque(predicate_c_expr):
    """Can an SMT solver decide an opaque predicate without modelling it?

    The reviewer's challenge was "whether the compiler can constant-fold it".
    Measured directly: translate the arithmetic to Z3 and ask whether the
    predicate's value is FORCED (i.e. a constant) across all operand values.
    A volatile operand still leaves the predicate provable -- measuring that
    is the point.
    """
    try:
        import z3
    except ImportError:
        return {"probe": "z3_opaque", "available": False}

    expr = predicate_c_expr
    if len(expr) > MAX_EXPRESSION_LENGTH:
        return {"probe": "z3_opaque", "available": True,
                "translatable": False,
                "reason": "expression length budget exceeded"}
    names = sorted(set(re.findall(r"__nx_opa_\d+", expr)))
    if not names:
        return {"probe": "z3_opaque", "available": True,
                "translatable": False, "reason": "no opaque operands"}
    # Only handle the integer-arithmetic subset; anything else is reported as
    # not translatable rather than silently "passed". The old charset omitted
    # < > / ~, so every real comparison predicate was rejected before the
    # translator ever saw it. '%' stays out: Z3's signed modulo differs from C
    # and its zero-divisor behavior is not the artefact's C behavior. The AST
    # walk below is the real gate; this is just a cheap pre-filter.
    if not re.fullmatch(r"[\w\s()&|^+*\-/~<>=!,]+", expr):
        return {"probe": "z3_opaque", "available": True,
                "translatable": False, "reason": "non-arithmetic construct"}
    try:
        # C integer arithmetic is BIT-VECTOR arithmetic, not Int: `&`, `|`
        # and `^` are bitwise, and overflow wraps. Modelling the predicate in
        # Int raises "unsupported operand type(s) for &: 'ArithRef' and 'int'"
        # and would also answer a different question.
        syms = {n: z3.BitVec(n, 32) for n in names}
        py = expr.replace("&&", " and ").replace("||", " or ")
        depth = 0
        for ch in py:
            depth += (ch == "(") - (ch == ")")
        if depth != 0:
            return {"probe": "z3_opaque", "available": True,
                    "translatable": False,
                    "reason": "unbalanced parentheses in the emitted form"}
        # Build the Z3 expression by walking the AST -- never eval(). The
        # predicate text comes from an artefact (trust boundary); eval() here
        # was a code-execution sink, and a charset regex still let `9**9**9`
        # through as a CPU/memory DoS.
        node = _z3_from_ast(py, syms, z3)
        if node is None:
            return {"probe": "z3_opaque", "available": True,
                    "translatable": False,
                    "reason": "expression outside the supported arithmetic subset"}
        if not z3.is_bool(node):
            return {"probe": "z3_opaque", "available": True,
                    "translatable": False, "reason": "not a boolean predicate"}
        s = z3.Solver()
        s.set(timeout=Z3_SOLVER_TIMEOUT_MS,
              rlimit=Z3_SOLVER_RLIMIT,
              max_memory=Z3_SOLVER_MAX_MEMORY)
        s.add(z3.Not(node))
        check_true = s.check()
        s2 = z3.Solver()
        s2.set(timeout=Z3_SOLVER_TIMEOUT_MS,
               rlimit=Z3_SOLVER_RLIMIT,
               max_memory=Z3_SOLVER_MAX_MEMORY)
        s2.add(node)
        check_false = s2.check()
        if check_true == z3.unknown or check_false == z3.unknown:
            # An undecided query proves nothing. Treating unknown as "not
            # forced true" previously reported it as a measured result.
            return {"probe": "z3_opaque", "available": True,
                    "translatable": False, "timed_out": True}
        forced_true = check_true == z3.unsat
        forced_false = check_false == z3.unsat
        return {
            "probe": "z3_opaque", "available": True, "translatable": True,
            "forced_true": forced_true, "forced_false": forced_false,
            "constant": forced_true or forced_false,
            "note": ("the solver decides the predicate over %d free 32-bit "
                     "operands -- so it is obscured, not opaque" % len(names)),
        }
    except Exception as exc:
        return {"probe": "z3_opaque", "available": True,
                "translatable": False, "error": str(exc)[:200]}


def probe_z3_mba(expression, slot_values=None):
    """Can a solver collapse an MBA expression to a constant?

    The documented claim was "exponential to simplify". Measured: evaluate it
    symbolically. If the result is a literal, any evaluator recovers it.
    """
    try:
        import z3  # noqa: F401
    except ImportError:
        return {"probe": "z3_mba", "available": False}

    expr = expression
    if len(expr) > MAX_EXPRESSION_LENGTH:
        return {"probe": "z3_mba", "available": True,
                "simplified": None, "is_literal": False,
                "reason": "expression length budget exceeded"}
    try:
        _check_expression_budget(expr)
    except (ValueError, SyntaxError) as exc:
        return {"probe": "z3_mba", "available": True,
                "simplified": None, "is_literal": False,
                "reason": str(exc) or "expression outside the supported grammar"}
    slots = sorted(set(re.findall(r"__nx_mba_\d+", expr)))
    try:
        py = expr
        if slots:
            if not slot_values:
                return {"probe": "z3_mba", "available": True,
                        "simplified": None, "is_literal": False,
                        "reason": "references runtime slots; needs their values"}
            for n in slots:
                py = py.replace(n, str(slot_values.get(n, 0)))
        # the emitted arithmetic is C-style; python accepts & | ^ and parens.
        # Evaluate WITHOUT eval(): the expression text is artefact-derived
        # (trust boundary). The AST-walk evaluator rejects any name/call.
        from .transform_solvers import evaluate_integer_expression
        try:
            val = evaluate_integer_expression(py)
        except ValueError as exc:
            # Preserve the specific budget failure (length, node count or
            # integer width) instead of collapsing it to a generic message.
            reason = str(exc) or "expression outside the constant-arithmetic grammar"
            return {"probe": "z3_mba", "available": True,
                    "simplified": None, "is_literal": False,
                    "reason": reason}
        return {"probe": "z3_mba", "available": True,
                "simplified": str(val), "is_literal": True,
                "slots_present": bool(slots),
                "note": "collapses in ONE evaluation"}
    except Exception as exc:
        return {"probe": "z3_mba", "available": True,
                "simplified": None, "is_literal": False,
                "error": str(exc)[:200]}
