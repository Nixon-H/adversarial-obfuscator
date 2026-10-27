"""Function-level virtualization with two dispatcher organizations (G2-H3/H4).

Compiles eligible Python functions to a stack-VM bytecode executed by an
emitted interpreter. Two materially different families:

  VM-A (switch dispatcher): one while loop over an if/elif opcode chain.
  VM-B (threaded dispatcher): table of per-opcode handler closures
      invoked indirectly (handlers[op](state)).

Per-build diversification: opcode numbers shuffled per seed; VM-A elif
order shuffled; VM-B handler definition/table order shuffled; VM-B routes
all six comparisons through one parametrized helper while VM-A inlines
each comparison (different handler layouts).

Eligibility (conservative allowlist; everything else untouched):
- posonly + pos-or-kw params (with or without defaults); no *args,
  **kwargs, kwonly.
- No decorators, no nested def/class/lambda, no global/nonlocal,
  no yield/await, no try, no import.
- No Call nodes except range() inside For headers (executed by the
  real range() builtin at runtime via RANGE/ITER_NEXT).
- No Attribute/Subscript (object model out of scope for v1).
- No starred assignment targets.
- Body: Assign (single Name), AugAssign (+,-,*,/,%,** on locals; // unsupported),
  If, While, For-over-range (real range() iterator: exact bounds,
  int-validation, and zero-step errors come from CPython itself),
  Return, docstring Expr.

Soundness conditions (each enforced by construction + tests):
- Desugared For-range is exactly equivalent (init/end/step temps).
- AND/OR evaluate both sides: operands are pure (no calls possible
  after eligibility filter), so eager == short-circuit observably.
- Division/modulo/power use the identical Python operators.
- Docstring preserved as wrapper docstring.
- Signature (name, params, defaults) preserved exactly.

Python 3.10 compatible. Deterministic per seed (no global random).
"""
import sys

import ast
import random

# Canonical op names. Per-build numeric encoding is shuffled.
OPS = ("CONST", "LOAD", "STORE", "ADD", "SUB", "MUL", "DIV", "MOD",
       "POW", "NEG", "NOT", "EQ", "NE", "LT", "LE", "GT", "GE",
       "IS", "ISNOT", "AND", "OR", "JMP", "JMP_FALSE", "POP", "RETURN",
       "RANGE", "ITER_NEXT", "BUILD_TUPLE", "UNPACK", "BUILD_LIST")


class _Unsupported(Exception):
    pass


def _for_range_parts(node):
    """If node is `for x in range(...)`, return (target, start, end, step)
    name-ASTs, else None. Only Name target, range() call only."""
    if not isinstance(node, ast.For):
        return None
    if not (isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Call)):
        return None
    fn = node.iter.func
    if not (isinstance(fn, ast.Name) and fn.id == "range"):
        return None
    args = node.iter.args
    if node.iter.keywords or not (1 <= len(args) <= 3):
        return None
    if len(args) == 1:
        start, end, step = ast.Constant(value=0), args[0], ast.Constant(value=1)
    elif len(args) == 2:
        start, end, step = args[0], args[1], ast.Constant(value=1)
    else:
        start, end, step = args
    return node.target.id, start, end, step


#: Nodes the VM cannot compile.  ``ast.TryStar`` (except*, PEP 654) only
#: exists on 3.11+, so it is appended when available: referencing it
#: directly raised AttributeError on 3.10, every call to _eligible()
#: swallowed that as "ineligible", and the whole VM corpus reported zero
#: eligible functions there.
_BANNED_NODES = (
    ast.Yield, ast.YieldFrom, ast.Await, ast.Try, ast.Break, ast.Continue,
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Lambda,
    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Starred,
    ast.Delete,
)
if hasattr(ast, "TryStar"):
    _BANNED_NODES = _BANNED_NODES + (ast.TryStar,)


def _check_supported(tree):
    """Raise _Unsupported unless every FunctionDef body is VM-compilable."""
    # range() calls that are direct For headers execute natively via
    # RANGE/ITER_NEXT (never slot-loaded): exempt those exact Call nodes.
    # Anything else callable (including range() used as a VALUE, whose
    # result object would need a slot type the VM does not model) is out.
    # Calls inside range bounds are also out (bound exprs must be pure).
    allowed_calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and _for_range_parts(node) is not None:
            allowed_calls.add(id(node.iter))
            for arg in node.iter.args:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Call):
                        raise _Unsupported("call in range bound")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            raise _Unsupported("object model")
        if isinstance(node, ast.Call):
            if id(node) not in allowed_calls:
                raise _Unsupported("call")
        if isinstance(node, _BANNED_NODES):
            # FunctionDef/ClassDef handled at top level; nested ones banned.
            # (Top-level scan below exempts the root function itself.)
            raise _Unsupported(type(node).__name__)
        if isinstance(node, ast.arguments):
            if (node.vararg is not None or node.kwarg is not None
                    or node.kwonlyargs):
                raise _Unsupported("var/kwonly args")


class _Compiler:
    """Function body -> (slots, code) with jump fixups."""

    def __init__(self, encoding, mask_rng=None):
        self.enc = encoding  # opname -> number
        self.slots = {}      # var name -> slot index
        self.code = []       # (number, arg) list
        # Hardening A4: masks INT CONST args as (v^m, m) pairs so table
        # literals never carry original integers in clear. Bools excluded
        # (True/1 identity semantics under `is`); Nones/floats/strings
        # pass through (strings are sealed upstream; floats documented).
        self.mask_rng = mask_rng

    def slot(self, name):
        if name not in self.slots:
            self.slots[name] = len(self.slots)
        return self.slots[name]

    def emit(self, op, arg=None):
        self.code.append((self.enc[op], arg))
        return len(self.code) - 1

    def patch(self, pos, target):
        op, _ = self.code[pos]
        self.code[pos] = (op, target)

    def compile_expr(self, node):
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, tuple):
                raise _Unsupported("tuple constant passthrough")
            if (isinstance(v, int) and not isinstance(v, bool)
                    and self.mask_rng is not None):
                m = self.mask_rng.randrange(1 << 30) or 1
                self.emit("CONST", (v ^ m, m))
            else:
                self.emit("CONST", v)
        elif isinstance(node, ast.Name):
            if not isinstance(node.ctx, ast.Load):
                raise _Unsupported("non-load name in expr")
            self.emit("LOAD", self.slot(node.id))
        elif isinstance(node, ast.BinOp):
            _bop = {"Add": "ADD", "Sub": "SUB", "Mult": "MUL",
                    "Div": "DIV", "Mod": "MOD", "Pow": "POW"}.get(
                        type(node.op).__name__)
            if _bop is None:
                # Bitwise/shift/floor-div operators: explicit skip, never
                # silent miscompilation (KeyError would also skip via the
                # eligibility guard, but this states intent).
                raise _Unsupported("binop %s" % type(node.op).__name__)
            self.compile_expr(node.left)
            self.compile_expr(node.right)
            self.emit(_bop)
        elif isinstance(node, ast.UnaryOp):
            self.compile_expr(node.operand)
            if isinstance(node.op, ast.USub):
                self.emit("NEG")
            elif isinstance(node.op, ast.Not):
                self.emit("NOT")
            else:
                # UAdd/Invert intentionally unsupported (explicit skip,
                # never silent miscompilation).
                raise _Unsupported("unary %s" % type(node.op).__name__)
        elif isinstance(node, ast.BoolOp):
            for v in node.values:
                self.compile_expr(v)
            for _ in node.values[1:]:
                self.emit("AND" if isinstance(node.op, ast.And) else "OR")
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            _cop = {"Eq": "EQ", "NotEq": "NE", "Lt": "LT", "LtE": "LE",
                    "Gt": "GT", "GtE": "GE", "Is": "IS",
                    "IsNot": "ISNOT"}.get(type(node.ops[0]).__name__)
            if _cop is None:
                # In/NotIn and chained comparisons: explicit skip.
                raise _Unsupported("compare %s" % type(node.ops[0]).__name__)
            self.compile_expr(node.left)
            self.compile_expr(node.comparators[0])
            self.emit(_cop)
        elif isinstance(node, ast.IfExp):
            self.compile_expr(node.test)
            jfalse = self.emit("JMP_FALSE", None)
            self.compile_expr(node.body)
            jend = self.emit("JMP", None)
            self.patch(jfalse, len(self.code))
            self.compile_expr(node.orelse)
            self.patch(jend, len(self.code))
        elif isinstance(node, ast.Tuple):
            # Tuple display: evaluate left-to-right, pack. Exact
            # (evaluation order and packing match CPython display).
            for elt in node.elts:
                if isinstance(elt, ast.Starred):
                    raise _Unsupported("starred display")
                self.compile_expr(elt)
            self.emit("BUILD_TUPLE", len(node.elts))
        elif isinstance(node, ast.List):
            for elt in node.elts:
                if isinstance(elt, ast.Starred):
                    raise _Unsupported("starred display")
                self.compile_expr(elt)
            self.emit("BUILD_LIST", len(node.elts))
        else:
            raise _Unsupported("expr %s" % type(node).__name__)

    def compile_stmt(self, node):
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise _Unsupported("multi-target assign")
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name):
                self.compile_expr(node.value)
                self.emit("STORE", self.slot(tgt.id))
            elif isinstance(tgt, ast.Tuple):
                # Destructuring: all elements plain Names (Starred banned
                # by _check_supported). UNPACK replicates CPython exactly:
                # tuple(value), length check with identical messages.
                for elt in tgt.elts:
                    if not isinstance(elt, ast.Name):
                        raise _Unsupported("non-name unpack target")
                self.compile_expr(node.value)
                self.emit("UNPACK", len(tgt.elts))
                for elt in reversed(tgt.elts):
                    self.emit("STORE", self.slot(elt.id))
            else:
                raise _Unsupported("assign target")
        elif isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name):
                raise _Unsupported("augassign target")
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult,
                                        ast.Div, ast.Mod, ast.Pow)):
                raise _Unsupported("augassign op")
            self.emit("LOAD", self.slot(node.target.id))
            self.compile_expr(node.value)
            self.emit({"Add": "ADD", "Sub": "SUB", "Mult": "MUL",
                       "Div": "DIV", "Mod": "MOD",
                       "Pow": "POW"}[type(node.op).__name__])
            self.emit("STORE", self.slot(node.target.id))
        elif isinstance(node, ast.Return):
            if node.value is not None:
                self.compile_expr(node.value)
            else:
                self.emit("CONST", None)
            self.emit("RETURN")
        elif isinstance(node, ast.If):
            self.compile_expr(node.test)
            jfalse = self.emit("JMP_FALSE", None)
            for s in node.body:
                self.compile_stmt(s)
            jend = self.emit("JMP", None)
            self.patch(jfalse, len(self.code))
            for s in node.orelse:
                self.compile_stmt(s)
            self.patch(jend, len(self.code))
        elif isinstance(node, ast.While):
            top = len(self.code)
            self.compile_expr(node.test)
            jfalse = self.emit("JMP_FALSE", None)
            for s in node.body:
                self.compile_stmt(s)
            self.emit("JMP", top)
            self.patch(jfalse, len(self.code))
            for s in node.orelse:
                self.compile_stmt(s)
        elif isinstance(node, ast.For):
            parts = _for_range_parts(node)
            if parts is None:
                raise _Unsupported("non-range for")
            tname, start, end, step = parts
            # Exact range() semantics via the REAL range object: bounds,
            # int validation, zero-step ValueError all come from CPython
            # itself. RANGE pops (start, end, step), pushes an iterator;
            # ITER_NEXT advances it (StopIteration -> jump out).
            self.compile_expr(start)
            self.compile_expr(end)
            self.compile_expr(step)
            self.emit("RANGE")
            top = len(self.code)
            jout = self.emit("ITER_NEXT", None)
            self.emit("STORE", self.slot(tname))
            for s in node.body:
                self.compile_stmt(s)
            self.emit("JMP", top)
            self.patch(jout, len(self.code))
            # NOTE: no POP here — ITER_NEXT already popped the exhausted
            # iterator on the exit path; an extra POP would unbalance
            # the stack (was IndexError on every counted loop).
            for s in node.orelse:
                self.compile_stmt(s)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            self.compile_expr(node.value)
            self.emit("POP")
        elif isinstance(node, ast.Pass):
            pass
        elif isinstance(node, (ast.Break, ast.Continue)):
            raise _Unsupported("break/continue")
        else:
            raise _Unsupported("stmt %s" % type(node).__name__)



def _eligible(func):
    """Conservative eligibility: decorated/bizarre functions untouched."""
    if func.decorator_list:
        return False
    a = func.args
    if a.vararg is not None or a.kwarg is not None or a.kwonlyargs:
        return False
    try:
        probe = ast.parse(ast.unparse(func))
        # Scan the BODY only: the root def itself is not a nested def.
        body_mod = ast.Module(body=list(probe.body[0].body), type_ignores=[])
        _check_supported(body_mod)
        _check_loads_resolve(probe.body[0])
    except _Unsupported:
        return False
    except Exception:
        return False
    return True


def _check_loads_resolve(func):
    """Every Name Load must resolve to a param or a function-local Store.

    Otherwise the VM slot would read None where the original read a
    module global / closure cell / builtin value — silent miscompilation.
    range() in For headers is exempt (executed by the real builtin via
    RANGE/ITER_NEXT, never slot-loaded).
    """
    assigned = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(
                node.ctx, (ast.Store, ast.Del)):
            assigned.add(node.id)
        if isinstance(node, ast.arg):
            assigned.add(node.arg)
    # For-target names are assigned by the loop itself.
    for node in ast.walk(func):
        if isinstance(node, ast.For):
            parts = _for_range_parts(node)
            if parts is not None:
                assigned.add(parts[0])
    params = {a.arg for a in list(func.args.posonlyargs) + list(func.args.args)}
    allowed = set(assigned) | set(params)
    range_callees = set()
    for fnode in ast.walk(func):
        if isinstance(fnode, ast.For) and _for_range_parts(fnode) is not None:
            callee = fnode.iter.func
            if isinstance(callee, ast.Name):
                range_callees.add(id(callee))
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in allowed or node.id in ("True", "False", "None"):
                continue
            # range() callees of valid For headers execute natively
            # (RANGE op), never through slots: exempt those exact nodes.
            if node.id == "range" and id(node) in range_callees:
                continue
            raise _Unsupported("unresolved load %s" % node.id)


def compile_function(func, encoding, mask_rng=None):
    """Compile one FunctionDef -> (slots, code, params, defaults, n_posonly)."""
    comp = _Compiler(encoding, mask_rng)
    params = [a.arg for a in list(func.args.posonlyargs) + list(func.args.args)]
    for p in params:
        comp.slot(p)
    for stmt in func.body:
        if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str) and stmt is func.body[0]):
            continue  # docstring: preserved on wrapper, not compiled
        comp.compile_stmt(stmt)
    comp.emit("CONST", None)
    comp.emit("RETURN")
    defaults = [ast.unparse(d) for d in func.args.defaults]
    n_posonly = len(func.args.posonlyargs)
    return comp.slots, comp.code, params, defaults, n_posonly


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------

def _encoding(seed, family):
    """Per-build opcode-number permutation. Deterministic (sha256 seed)."""
    import hashlib
    key = hashlib.sha256(("%s:%s" % (seed, family)).encode()).digest()
    nums = list(range(len(OPS)))
    rng = random.Random(int.from_bytes(key[:8], "little"))
    rng.shuffle(nums)
    return {op: nums[i] for i, op in enumerate(OPS)}


def _code_table(code):
    """Render code as a Python literal tuple ((opnum, arg), ...)."""
    parts = []
    for num, arg in code:
        parts.append("(%d, %r)" % (num, arg))
    return "(%s,)" % ", ".join(parts)


def _signature(params, defaults, n_posonly):
    """Rebuild the exact def-line signature (names + defaults + /)."""
    out = list(params)
    if n_posonly and n_posonly < len(params):
        out.insert(n_posonly, "/")
    elif n_posonly and n_posonly == len(params):
        out.append("/")
    sig = ", ".join(out)
    if defaults:
        parts = sig.split(", ")
        for i, d in enumerate(defaults):
            parts[len(parts) - len(defaults) + i] += "=" + d
        sig = ", ".join(parts)
    return sig


def _match_unpack_text(source):
    """Match CPython 3.14's unpack error wording.

    3.14 added the count -- "too many values to unpack (expected 2, got
    3)" -- so a snippet generated on 3.14 with the 3.13 text made the VM
    and native runs disagree on the message (only the message).  The
    snippet is generated per build and runs on the same interpreter, so
    emit that interpreter's wording.
    """
    if sys.version_info >= (3, 14):
        source = source.replace(
            "raise ValueError('too many values to unpack (expected %d)' % _m)",
            "raise ValueError('too many values to unpack (expected %d, got %d)' % (_m, _l))",
        )
        source = source.replace(
            "raise ValueError('too many values to unpack (expected %d)' % _n)",
            "raise ValueError('too many values to unpack (expected %d, got %d)' % (_n, _l))",
        )
    return source


def emit_vm_a(func_name, params, defaults, n_posonly, slots, code,
              encoding, seed, doc=None):
    """VM-A: switch/table dispatcher (if/elif opcode chain).

    Elif-branch order shuffled per seed (handler-layout diversification).
    """
    rng = random.Random(int.from_bytes(
        __import__("hashlib").sha256(
            ("%s:vm-a-order" % seed).encode()).digest()[:8], "little"))
    nslots = len(slots)
    inits = "\n".join("    _slots[%d] = %s" % (slots[p], p) for p in params)
    branches = [
        ("ADD", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a+_b)"),
        ("SUB", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a-_b)"),
        ("MUL", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a*_b)"),
        ("DIV", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a/_b)"),
        ("MOD", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a%_b)"),
        ("POW", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a**_b)"),
        ("NEG", "_stack.append(-_stack.pop())"),
        ("NOT", "_stack.append(not _stack.pop())"),
        ("EQ", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a==_b)"),
        ("NE", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a!=_b)"),
        ("LT", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a<_b)"),
        ("LE", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a<=_b)"),
        ("GT", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a>_b)"),
        ("GE", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a>=_b)"),
        ("IS", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a is _b)"),
        ("ISNOT", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a is not _b)"),
        ("AND", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a and _b)"),
        ("OR", "_b=_stack.pop();_a=_stack.pop();_stack.append(_a or _b)"),
    ]
    rng.shuffle(branches)
    shuffled = ["        elif _op == %d: %s; _pc+=1" % (encoding[op], stmt)
                for op, stmt in branches]
    body = "\n".join([
        "        if _op == %d: _t=_code[_pc][1];_stack.append(_t[0]^_t[1] if type(_t) is tuple and len(_t)==2 and type(_t[0]) is int and type(_t[1]) is int else _t);_pc+=1  # CONST" % encoding["CONST"],
        "        elif _op == %d: _stack.append(_slots[_code[_pc][1]]); _pc+=1  # LOAD" % encoding["LOAD"],
        "        elif _op == %d: _slots[_code[_pc][1]]=_stack.pop(); _pc+=1  # STORE" % encoding["STORE"],
    ] + shuffled + [
        "        elif _op == %d: _pc=_code[_pc][1]  # JMP" % encoding["JMP"],
        "        elif _op == %d: _c=_stack.pop();_pc=_code[_pc][1] if not _c else _pc+1  # JMP_FALSE" % encoding["JMP_FALSE"],
        "        elif _op == %d: pass  # POP" % encoding["POP"],
        "        elif _op == %d: _ret=_stack.pop();_pc=_n  # RETURN" % encoding["RETURN"],
        "        elif _op == %d: _s=_stack.pop();_e=_stack.pop();_t=_stack.pop();_stack.append(iter(range(_t,_e,_s)));_pc+=1  # RANGE" % encoding["RANGE"],
        "        elif _op == %d:" % encoding["ITER_NEXT"],
        "            _it=_stack[-1]",
        "            try: _v=next(_it);_stack.append(_v);_pc+=1",
        "            except StopIteration: _stack.pop();_pc=_code[_pc][1]",
        "        elif _op == %d: _m=_code[_pc][1];_vs=[_stack.pop() for _ in range(_m)];_vs.reverse();_stack.append(tuple(_vs));_pc+=1  # BUILD_TUPLE" % encoding["BUILD_TUPLE"],
        "        elif _op == %d:" % encoding["UNPACK"],
        "            _m=_code[_pc][1];_t=tuple(_stack.pop());_l=len(_t)",
        "            if _l>_m: raise ValueError('too many values to unpack (expected %d)' % _m)",
        "            if _l<_m: raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))",
        "            _stack.extend(_t);_pc+=1",
        "        elif _op == %d: _m=_code[_pc][1];_vs=[_stack.pop() for _ in range(_m)];_vs.reverse();_stack.append(list(_vs));_pc+=1  # BUILD_LIST" % encoding["BUILD_LIST"],
        "        else: raise RuntimeError('bad opcode')",
    ])
    # POP must drop: fix the placeholder above into a real pop.
    body = body.replace(
        "elif _op == %d: pass  # POP" % encoding["POP"],
        "elif _op == %d: _stack.pop();_pc+=1  # POP" % encoding["POP"])
    doc_line = '    """%s"""\n' % doc.replace('"""', '"') if doc else ""
    _vm_src = (
        "def %s(%s):\n%s"
        "    _slots=[None]*%d\n%s\n"
        "    _stack=[]\n    _code=%s\n    _n=len(_code)\n    _pc=0\n    _ret=None\n"
        "    while _pc<_n:\n        _op=_code[_pc][0]\n%s\n    return _ret\n"
    ) % (func_name, _signature(params, defaults, n_posonly), doc_line,
         nslots, inits, _code_table(code), body)
    return _match_unpack_text(_vm_src)


def emit_vm_b(func_name, params, defaults, n_posonly, slots, code,
              encoding, seed, doc=None):
    """VM-B: threaded/indirect dispatcher (handler table + shared workers).

    Handlers are closures invoked as handlers[op](st); definition and
    table order shuffled per seed. All six comparisons (+IS/ISNOT) route
    through ONE parametrized worker (vs VM-A inline branches): genuinely
    different handler layout, identical semantics.
    """
    import hashlib as _hl
    rng = random.Random(int.from_bytes(
        _hl.sha256(("%s:vm-b-order" % seed).encode()).digest()[:8], "little"))
    nslots = len(slots)
    inits = "\n".join("    _slots[%d] = %s" % (slots[p], p) for p in params)
    defs = [
        "    def _h_const(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _t=_c[_p][1]\n"
        "        _k.append(_t[0]^_t[1] if type(_t) is tuple and len(_t)==2 and type(_t[0]) is int and type(_t[1]) is int else _t)\n        return _p+1",
        "    def _h_load(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _k.append(_s[_c[_p][1]])\n        return _p+1",
        "    def _h_store(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _s[_c[_p][1]]=_k.pop()\n        return _p+1",
        "    def _h_neg(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _k.append(-_k.pop())\n        return _p+1",
        "    def _h_not(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _k.append(not _k.pop())\n        return _p+1",
        "    def _h_arith(st, _w):\n        _s,_k,_c,_p,_r=st\n"
        "        _b=_k.pop();_a=_k.pop()\n"
        "        if _w=='add': _k.append(_a+_b)\n"
        "        elif _w=='sub': _k.append(_a-_b)\n"
        "        elif _w=='mul': _k.append(_a*_b)\n"
        "        elif _w=='div': _k.append(_a/_b)\n"
        "        elif _w=='mod': _k.append(_a%_b)\n"
        "        else: _k.append(_a**_b)\n"
        "        return _p+1",
        "    def _h_cmp(st, _w):\n        _s,_k,_c,_p,_r=st\n"
        "        _b=_k.pop();_a=_k.pop()\n"
        "        _k.append({'eq':_a==_b,'ne':_a!=_b,'lt':_a<_b,'le':_a<=_b,"
        "'gt':_a>_b,'ge':_a>=_b,'is':_a is _b,'isnot':_a is not _b}[_w])\n"
        "        return _p+1",
        "    def _h_bool(st, _w):\n        _s,_k,_c,_p,_r=st\n"
        "        _b=_k.pop();_a=_k.pop()\n"
        "        _k.append((_a and _b) if _w=='and' else (_a or _b))\n"
        "        return _p+1",
        "    def _h_jmp(st):\n        _s,_k,_c,_p,_r=st\n        return _c[_p][1]",
        "    def _h_jfalse(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _v=_k.pop()\n        return _c[_p][1] if not _v else _p+1",
        "    def _h_pop(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _k.pop()\n        return _p+1",
        "    def _h_ret(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _r[0]=_k.pop()\n        return len(_c)",
        "    def _h_range(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _step=_k.pop();_end=_k.pop();_start=_k.pop()\n"
        "        _k.append(iter(range(_start,_end,_step)))\n        return _p+1",
        "    def _h_next(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _it=_k[-1]\n"
        "        try:\n            _k.append(next(_it))\n            return _p+1\n"
        "        except StopIteration:\n            _k.pop()\n            return _c[_p][1]",
        "    def _h_buildtuple(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _n=_c[_p][1]\n"
        "        _vs=[_k.pop() for _ in range(_n)];_vs.reverse()\n"
        "        _k.append(tuple(_vs))\n        return _p+1",
        "    def _h_unpack(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _n=_c[_p][1];_t=tuple(_k.pop());_l=len(_t)\n"
        "        if _l>_n: raise ValueError('too many values to unpack (expected %d)' % _n)\n"
        "        if _l<_n: raise ValueError('not enough values to unpack (expected %d, got %d)' % (_n, _l))\n"
        "        _k.extend(_t)\n        return _p+1",
        "    def _h_buildlist(st):\n        _s,_k,_c,_p,_r=st\n"
        "        _n=_c[_p][1]\n"
        "        _vs=[_k.pop() for _ in range(_n)];_vs.reverse()\n"
        "        _k.append(list(_vs))\n        return _p+1",
    ]
    rng.shuffle(defs)
    cmp_ops = ["EQ", "NE", "LT", "LE", "GT", "GE", "IS", "ISNOT"]
    cmp_which = {"EQ": "eq", "NE": "ne", "LT": "lt", "LE": "le",
                 "GT": "gt", "GE": "ge", "IS": "is", "ISNOT": "isnot"}
    table = [
        ("CONST", "_h_const"), ("LOAD", "_h_load"), ("STORE", "_h_store"),
        ("NEG", "_h_neg"), ("NOT", "_h_not"),
        ("JMP", "_h_jmp"), ("JMP_FALSE", "_h_jfalse"), ("POP", "_h_pop"),
        ("RETURN", "_h_ret"), ("RANGE", "_h_range"), ("ITER_NEXT", "_h_next"),
        ("BUILD_TUPLE", "_h_buildtuple"), ("UNPACK", "_h_unpack"),
        ("BUILD_LIST", "_h_buildlist"),
    ]
    for op in ("ADD", "SUB", "MUL", "DIV", "MOD", "POW"):
        table.append((op, None))  # per-op closures below
    for op in cmp_ops:
        table.append((op, None))
    table.append(("AND", None))
    table.append(("OR", None))
    rng.shuffle(table)
    tlines = []
    for op, fn in table:
        if fn is not None:
            tlines.append("        %d: %s," % (encoding[op], fn))
        elif op in ("ADD", "SUB", "MUL", "DIV", "MOD", "POW"):
            w = {"ADD": "add", "SUB": "sub", "MUL": "mul", "DIV": "div",
                 "MOD": "mod", "POW": "pow"}[op]
            tlines.append("        %d: (lambda st,_w=%r: _h_arith(st,_w)),"
                          % (encoding[op], w))
        elif op in cmp_which:
            tlines.append("        %d: (lambda st,_w=%r: _h_cmp(st,_w)),"
                          % (encoding[op], cmp_which[op]))
        else:
            w = "and" if op == "AND" else "or"
            tlines.append("        %d: (lambda st,_w=%r: _h_bool(st,_w)),"
                          % (encoding[op], w))
    doc_line = '    """%s"""\n' % doc.replace('"""', '"') if doc else ""
    _vm_src = (
        "def %s(%s):\n%s"
        "    _slots=[None]*%d\n%s\n"
        "    _stack=[]\n    _code=%s\n    _ret=[None]\n"
        "%s\n"
        "    _handlers={\n%s\n    }\n"
        "    _st=[_slots,_stack,_code,0,_ret]\n"
        "    _n=len(_code)\n"
        "    while _st[3]<_n:\n"
        "        _op=_code[_st[3]][0]\n"
        "        _h=_handlers.get(_op)\n"
        "        if _h is None: raise RuntimeError('bad opcode')\n"
        "        _st[3]=_h(_st)\n"
        "    return _ret[0]\n"
    ) % (func_name, _signature(params, defaults, n_posonly), doc_line,
         nslots, inits, _code_table(code), "\n".join(defs),
         "\n".join(tlines))
    return _match_unpack_text(_vm_src)


# ---------------------------------------------------------------------------
# Transformer (selective, opt-in, default OFF)
# ---------------------------------------------------------------------------

class VMDispatchTransformer(ast.NodeTransformer):
    """Rewrite eligible module-level functions into VM-A/VM-B dispatchers.

    family: "a" (switch) or "b" (threaded). seed: per-build diversification
    (opcode encoding + handler layout). probability: fraction of eligible
    functions to transform (seeded; default 1.0 = all eligible).
    Ineligible functions pass through untouched. Never raises: compile
    failures leave the original node in place.
    """

    def __init__(self, seed=None, family="a", probability=1.0):
        import hashlib as _hl
        self.rng = random.Random(int.from_bytes(
            _hl.sha256(("%s:vm-%s-pick" % (seed, family)).encode()
                       ).digest()[:8], "little"))
        self.seed = seed
        self.family = family if family in ("a", "b") else "a"
        self.probability = probability
        self.stats = {"virtualized": 0, "skipped": 0}

    def visit_Module(self, node):
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        # Module-level only: nested defs are skipped by eligibility
        # (closure cells unsupported), and generic_visit still descends
        # so nested eligible defs... do NOT transform nested defs either:
        # only rewrite when parent is the module. Track via flag.
        in_func = getattr(self, "_in_func", False)
        if in_func:
            return node
        self._in_func = True
        try:
            self.generic_visit(node)
        finally:
            self._in_func = False
        if not _eligible(node):
            self.stats["skipped"] += 1
            return node
        if self.rng.random() > self.probability:
            self.stats["skipped"] += 1
            return node
        try:
            return self._rewrite(node)
        except _Unsupported:
            self.stats["skipped"] += 1
            return node
        except Exception:
            self.stats["skipped"] += 1
            return node

    def visit_AsyncFunctionDef(self, node):
        # Never virtualize async functions (the VM cannot suspend).
        # Nested defs are left untouched too (conservative; load
        # resolution would guard them anyway).
        prev = getattr(self, "_in_func", False)
        self._in_func = True
        try:
            self.generic_visit(node)
        finally:
            self._in_func = prev
        return node

    def _rewrite(self, node):
        import hashlib as _hl
        enc_seed = "%s:%s:%s" % (self.seed, self.family, node.name)
        encoding = _encoding(enc_seed, self.family)
        mask_rng = random.Random(int.from_bytes(
            _hl.sha256(("%s:constmask" % enc_seed).encode()).digest()[:8],
            "little"))
        slots, code, params, defaults, n_posonly = compile_function(
            node, encoding, mask_rng)
        doc = ast.get_docstring(node)
        if self.family == "b":
            src = emit_vm_b(node.name, params, defaults, n_posonly,
                            slots, code, encoding, enc_seed, doc)
        else:
            src = emit_vm_a(node.name, params, defaults, n_posonly,
                            slots, code, encoding, enc_seed, doc)
        new_tree = ast.parse(src)
        ast.fix_missing_locations(new_tree)
        self.stats["virtualized"] += 1
        return new_tree.body[0]


def virtualize_source(source, seed=None, family="a", probability=1.0):
    """Virtualize eligible functions; returns (code, stats)."""
    tree = ast.parse(source)
    tr = VMDispatchTransformer(seed=seed, family=family,
                               probability=probability)
    tree = tr.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), dict(tr.stats)
