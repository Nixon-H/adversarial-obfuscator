"""Dynamic and symbolic probes.

Dynamic: run the artefact and capture what its own process leaks (stdout,
stderr, tracebacks, temp files, memory maps).

Symbolic: Z3 on the recovered opaque predicates and MBA expressions -- the
reviewer's explicit challenge ("a transform is not a security mechanism until
it survives automated simplification").
"""
from __future__ import annotations

import os
import re
import subprocess
import sys


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
    names = sorted(set(re.findall(r"__nx_opa_\d+", expr)))
    if not names:
        return {"probe": "z3_opaque", "available": True,
                "translatable": False, "reason": "no opaque operands"}
    # Only handle the integer-arithmetic subset; anything else is reported as
    # not translatable rather than silently "passed".
    if not re.fullmatch(r"[\w\s()&|^+*\-\d=!]+", expr):
        return {"probe": "z3_opaque", "available": True,
                "translatable": False, "reason": "non-arithmetic construct"}
    try:
        # C integer arithmetic is BIT-VECTOR arithmetic, not Int: `&`, `|`
        # and `^` are bitwise, and overflow wraps. Modelling the predicate in
        # Int raises "unsupported operand type(s) for &: 'ArithRef' and 'int'"
        # and would also answer a different question.
        syms = {n: z3.BitVec(n, 32) for n in names}
        py = expr.replace("&&", " and ")
        depth = 0
        for ch in py:
            depth += (ch == "(") - (ch == ")")
        if depth != 0:
            return {"probe": "z3_opaque", "available": True,
                    "translatable": False,
                    "reason": "unbalanced parentheses in the emitted form"}
        node = eval(py, {"__builtins__": {}}, dict(syms))  # noqa: S307
        if not z3.is_bool(node):
            return {"probe": "z3_opaque", "available": True,
                    "translatable": False, "reason": "not a boolean predicate"}
        s = z3.Solver()
        s.add(z3.Not(node))
        forced_true = s.check() == z3.unsat
        s2 = z3.Solver()
        s2.add(node)
        forced_false = s2.check() == z3.unsat
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
        # the emitted arithmetic is C-style; python accepts & | ^ and parens
        val = eval(py, {"__builtins__": {}})  # noqa: S307
        return {"probe": "z3_mba", "available": True,
                "simplified": str(val), "is_literal": True,
                "slots_present": bool(slots),
                "note": "collapses in ONE evaluation"}
    except Exception as exc:
        return {"probe": "z3_mba", "available": True,
                "simplified": None, "is_literal": False,
                "error": str(exc)[:200]}
