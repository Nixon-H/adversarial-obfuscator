"""VM-dispatcher recovery attack (Experiment v2.0, T_VM_table).

Develop on B_i: parse B_i's VM functions, recovering the emission-number
-> canonical-op map M_i (per-build opcode permutation) plus code tables.
Apply on B_j: decode B_j's tables with frozen M_i; S = position-wise
op-match rate against B_j's true ops (evaluator-extracted with the same
parser). No execution involved: failures are decoding mismatches
(misalignment / wrong handler mapping), never crashes.

Pre-registered predictions (docs/research/protocol-v2.md): self ~= 1.00
(extraction soundness, gate S >= 0.80); cross-seed ~= 0.00 (permuted
state space); cross-family ~= chance. Builds without VM tables yield
S undefined and are EXCLUDED (denominator rule), not scored as wins.

Canonical op space mirrors obfuscator/vm_dispatch.py::OPS. The parser
matches emitted template shapes (branch bodies / handler-table values);
if emission templates change, self-decode drops below the gate and the
run stops instead of producing numbers -- the gate is load-bearing.
"""
import ast

OPS = ("CONST", "LOAD", "STORE", "ADD", "SUB", "MUL", "DIV", "MOD",
       "POW", "NEG", "NOT", "EQ", "NE", "LT", "LE", "GT", "GE",
       "IS", "ISNOT", "AND", "OR", "JMP", "JMP_FALSE", "POP", "RETURN",
       "RANGE", "ITER_NEXT", "BUILD_TUPLE", "UNPACK", "BUILD_LIST")

_BINOP = {ast.Add: "ADD", ast.Sub: "SUB", ast.Mult: "MUL",
            ast.Div: "DIV", ast.Mod: "MOD", ast.Pow: "POW",
            ast.Eq: "EQ", ast.NotEq: "NE", ast.Lt: "LT", ast.LtE: "LE",
            ast.Gt: "GT", ast.GtE: "GE", ast.Is: "IS", ast.IsNot: "ISNOT"}
_BOOLOP = {ast.And: "AND", ast.Or: "OR"}


def _is_pop(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "pop")


def _is_append(node):
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "_stack"
            and node.value.func.attr == "append")


def _match_a(stmts):
    """Match VM-A branch bodies by semantic roles, not exact shape.

    Composed legacy passes (junk insertion, MBA) add statements inside
    VM branches, so matching must find roles (store / jump / append-arg
    shape / distinctive calls) anywhere in the body instead of assuming
    the isolated-emission statement count.
    """
    if not stmts:
        return None
    for sub in stmts:
        # STORE: _slots[...] = _stack.pop()
        if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                and isinstance(sub.targets[0], ast.Subscript)
                and isinstance(sub.targets[0].value, ast.Name)
                and sub.targets[0].value.id == "_slots"):
            return "STORE"
        # JMP_FALSE before JMP: _pc = (... if ... else ...)
        if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                and isinstance(sub.targets[0], ast.Name)
                and sub.targets[0].id == "_pc"
                and isinstance(sub.value, ast.IfExp)):
            return "JMP_FALSE"
        # JMP: _pc = _code[_pc][1]
        if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                and isinstance(sub.targets[0], ast.Name)
                and sub.targets[0].id == "_pc"
                and isinstance(sub.value, ast.Subscript)):
            return "JMP"
        # RETURN: _ret = _stack.pop()
        if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                and isinstance(sub.targets[0], ast.Name)
                and sub.targets[0].id == "_ret"):
            return "RETURN"
    for sub in stmts:
        if _is_append(sub):
            args = sub.value.args
            if not args:
                continue
            arg = args[0]
            if isinstance(arg, ast.Subscript):
                # LOAD indexes _slots[...] (value is the Name); CONST
                # indexes _code[_pc][1] (value is a Subscript).
                if (isinstance(arg.value, ast.Name)
                        and arg.value.id == "_slots"):
                    return "LOAD"
                return "CONST"
            if isinstance(arg, ast.UnaryOp):
                if isinstance(arg.op, ast.Not):
                    return "NOT"
                if isinstance(arg.op, ast.USub):
                    return "NEG"
            if isinstance(arg, ast.BinOp) and type(arg.op) in _BINOP:
                return _BINOP[type(arg.op)]
            if isinstance(arg, ast.BoolOp) and type(arg.op) in _BOOLOP:
                return _BOOLOP[type(arg.op)]
    blob_stmts = list(stmts)
    for sub in blob_stmts:
        for node in ast.walk(sub):
            if isinstance(node, ast.Try):
                return "ITER_NEXT"
    blob = ast.dump(ast.Module(body=blob_stmts, type_ignores=[]))
    if "too many values to unpack" in blob:
        return "UNPACK"
    for node in ast.walk(ast.Module(body=blob_stmts, type_ignores=[])):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "range":
                return "RANGE"
            if node.func.id == "tuple":
                return "BUILD_TUPLE"
            if node.func.id == "list":
                return "BUILD_LIST"
    for sub in blob_stmts:
        for node in ast.walk(sub):
            if isinstance(node, ast.Call) and _is_pop(node):
                return "POP"
    return None


# VM-B handler-table values -> canonical op.
_B_DIRECT = {
    "_h_const": "CONST", "_h_load": "LOAD", "_h_store": "STORE",
    "_h_neg": "NEG", "_h_not": "NOT", "_h_jmp": "JMP",
    "_h_jfalse": "JMP_FALSE", "_h_pop": "POP", "_h_ret": "RETURN",
    "_h_range": "RANGE", "_h_next": "ITER_NEXT",
    "_h_buildtuple": "BUILD_TUPLE", "_h_unpack": "UNPACK",
    "_h_buildlist": "BUILD_LIST",
}
_B_WORKER = {
    "_h_arith": {"add": "ADD", "sub": "SUB", "mul": "MUL", "div": "DIV",
                 "mod": "MOD", "pow": "POW"},
    "_h_cmp": {"eq": "EQ", "ne": "NE", "lt": "LT", "le": "LE",
               "gt": "GT", "ge": "GE", "is": "IS", "isnot": "ISNOT"},
    "_h_bool": {"and": "AND", "or": "OR"},
}

_VM_A_MARKS = ("while _pc", "elif _op")
_VM_B_MARKS = ("_handlers",)


def _op_test_number(test):
    """If test is `_op == <int>` return the int, else None."""
    if (isinstance(test, ast.Compare) and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and isinstance(test.left, ast.Name) and test.left.id == "_op"
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and isinstance(test.comparators[0].value, int)):
        return test.comparators[0].value
    return None


def _code_table_of(func_node):
    """Emission-number sequence of the function's _code table, or None."""
    for sub in ast.walk(func_node):
        if (isinstance(sub, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id in ("_code", "_c")
                        for t in sub.targets)
                and isinstance(sub.value, ast.Tuple)):
            nums = []
            for elt in sub.value.elts:
                if (isinstance(elt, ast.Tuple) and len(elt.elts) == 2
                        and isinstance(elt.elts[0], ast.Constant)
                        and isinstance(elt.elts[0].value, int)):
                    nums.append(elt.elts[0].value)
                else:
                    return None
            if nums:
                return nums
    return None


def _parse_a(func_node, source):
    """VM-A function -> (emit_numbers, num2op, unmatched)."""
    branches = []  # (number, body_stmt_list)
    for sub in ast.walk(func_node):
        if not isinstance(sub, ast.If):
            continue
        num = _op_test_number(sub.test)
        if num is None:
            continue
        branches.append((num, list(sub.body)))
    table = _code_table_of(func_node)
    if table is None or not branches:
        return None
    num2op, unmatched = {}, 0
    for num, body in branches:
        # Strip trailing `_pc += 1` bookkeeping before matching.
        while (body and isinstance(body[-1], ast.Expr)
               and isinstance(body[-1].value, ast.BinOp)):
            last = body[-1].value
            if (isinstance(last.left, ast.Name) and last.left.id == "_pc"
                    and isinstance(last.op, ast.Add)
                    and isinstance(last.right, ast.Constant)
                    and last.right.value == 1):
                body = body[:-1]
            else:
                break
        op = _match_a(body)
        if op is None:
            unmatched += 1
        elif num in num2op and num2op[num] != op:
            return None  # conflicting map: unparseable, fail loud
        else:
            num2op[num] = op
    return table, num2op, unmatched


def _lambda_target(elt):
    """Map a _handlers dict value to a canonical op, or None."""
    if isinstance(elt, ast.Name):
        return _B_DIRECT.get(elt.id)
    if (isinstance(elt, ast.Lambda) and elt.args.defaults
            and isinstance(elt.body, ast.Call)
            and isinstance(elt.body.func, ast.Name)):
        worker = _B_WORKER.get(elt.body.func.id)
        w = elt.args.defaults[0]
        if worker is not None and isinstance(w, ast.Constant):
            return worker.get(w.value)
    return None


def _parse_b(func_node, source):
    """VM-B function -> (emit_numbers, num2op, unmatched)."""
    del source
    table = _code_table_of(func_node)
    num2op, unmatched, found = {}, 0, False
    for sub in ast.walk(func_node):
        if (isinstance(sub, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "_handlers"
                        for t in sub.targets)
                and isinstance(sub.value, ast.Dict)):
            found = True
            for k, v in zip(sub.value.keys, sub.value.values):
                if not (isinstance(k, ast.Constant)
                        and isinstance(k.value, int)):
                    return None
                op = _lambda_target(v)
                if op is None:
                    unmatched += 1
                elif k.value in num2op and num2op[k.value] != op:
                    return None
                else:
                    num2op[k.value] = op
    if table is None or not found or not num2op:
        return None
    return table, num2op, unmatched


def detect_family(func_seg):
    has_a = all(m in func_seg for m in _VM_A_MARKS)
    has_b = all(m in func_seg for m in _VM_B_MARKS)
    if has_a:
        return "a"
    if has_b:
        return "b"
    return None


def extract(source):
    """Parse all VM functions.

    Maps are PER FUNCTION: the pipeline derives the opcode permutation
    from (vm_seed, family, function name), so each virtualized function
    has its own encoding. There is no build-level map; merging maps
    across functions is a category error (caught during development as
    phantom `cross-func-map-conflict`s).

    Returns {"ok": True, "functions": {name: {"numbers", "true_ops",
    "map", "family"}}} or {"ok": False, "reason": ...}.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"ok": False, "reason": "unparseable: %s" % e}
    funcs = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        try:
            seg = ast.get_source_segment(source, node) or ""
        except Exception:
            continue
        fam = detect_family(seg)
        if fam is None:
            continue
        parsed = _parse_a(node, source) if fam == "a" else _parse_b(
            node, source)
        if parsed is None:
            return {"ok": False,
                    "reason": "unparseable-vm-func: %s" % node.name}
        table, num2op, unmatched = parsed
        true_ops = []
        for num in table:
            if num not in num2op:
                return {"ok": False,
                        "reason": "table-op-missing-from-map: %s" % node.name}
            true_ops.append(num2op[num])
        funcs[node.name] = {"numbers": list(table), "true_ops": true_ops,
                            "map": dict(num2op), "family": fam,
                            "unmatched": unmatched}
    if not funcs:
        return {"ok": False, "reason": "no-vm-functions"}
    return {"ok": True, "functions": funcs}


def align(ext_i, ext_j):
    """Align B_j functions to B_i functions by true-op sequence.

    The same original function compiles to the same true-op sequence
    under any permutation, so equality aligns same-function pairs
    exactly. Alignment is evaluator scaffolding (like the static arm's
    use of original-source features): the modeled attacker capability
    is table extraction + frozen-map decoding, not function matching.
    Returns {j_name: i_name}; ambiguous/unmatched j functions are
    omitted (caller reports the alignment rate).
    """
    by_seq_i = {}
    for name, f in ext_i["functions"].items():
        by_seq_i.setdefault(tuple(f["true_ops"]), []).append(name)
    pairs = {}
    for jname, jf in ext_j["functions"].items():
        cands = by_seq_i.get(tuple(jf["true_ops"]), [])
        if len(cands) == 1:
            pairs[jname] = cands[0]
    return pairs


def decode_score(target_source, ext_i):
    """S(B_j | P_i): mean position-wise op-match rate over aligned pairs.

    Decodes each aligned B_j function with the frozen per-function map
    from B_i and compares against B_j's true ops. Returns
    (S, n_aligned, n_total, n_positions) or (None, 0, n, 0) when
    nothing aligns / no VM tables (caller excludes under the
    denominator rule).
    """
    ext_j = extract(target_source)
    if not ext_j["ok"]:
        return None, 0, 0, 0
    n_total = len(ext_j["functions"])
    pairs = align(ext_i, ext_j)
    hits, total = 0, 0
    for jname, iname in pairs.items():
        fj = ext_j["functions"][jname]
        mi = ext_i["functions"][iname]["map"]
        for num, true_op in zip(fj["numbers"], fj["true_ops"]):
            total += 1
            if mi.get(num) == true_op:
                hits += 1
    if total == 0:
        return None, 0, n_total, 0
    return hits / total, len(pairs), n_total, total


def self_score(source):
    """S(B_j | P_j): decode with the build's own maps. Gate: >= 0.80."""
    ext = extract(source)
    if not ext["ok"]:
        return None, 0, 0, ext["reason"]
    s, n_al, n_tot, npos = decode_score(source, ext)
    if s is None:
        return None, 0, n_tot, "no-aligned-pairs"
    return s, npos, n_tot, "ok"
