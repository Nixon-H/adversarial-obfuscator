"""Semantic lowering registry + AST pass + reference kernel (V10 headline).

Phase 1 (this module): pure-Python AST lowering. Call sites for covered
operations are rewritten to ``_nxk_<op>(...)`` calls against the reference
kernel in :mod:`obfuscator.lowering_shim`, so output still RUNS without any
native artifact. Phase 2 (later, --pytoc path): the shim import is swapped
for per-build-renamed Cython helpers with identical call shapes.

Families mirror V10: 14 default-ON (io, scalar, string, container, service,
protocol, function, import, fusion, list, dict, set, tuple, bytes) + 5
opt-in (arithmetic, truth, slice, format, augassign). ``--lowering`` CSV
selects families: "all", "none", "+arithmetic", "-io", or explicit lists.
Unknown names raise ValueError.

Method-call lowering: a call shaped ``recv.<meth>(args)`` where ``recv``
is a plain Name and ``<meth>`` matches a dotted registry op routes to the
kernel with the receiver prepended (``s.split(",")`` becomes
``_nxk_str_split(s, ",")``). Explicit dotted roots (``str.join(sep, it)``,
``dict.fromkeys("ab")``) keep their existing no-prepend rewrite.
"""

from __future__ import annotations

import ast

FAMILIES: dict[str, dict] = {
    # Default ON (V10 default set)
    "io": {"ops": ("print", "input", "open"), "default_on": True,
           "note": "print/input/open routed to kernel routines"},
    # Scalar family: original 12 entries UNTOUCHED (names/shapes identical).
    # NOTE: "str" also appears in protocol (legacy overlap in the ORIGINAL
    # registry — kept verbatim); totals below count UNIQUE op names.
    "scalar": {"ops": ("int", "float", "str", "bool", "chr", "ord", "hex",
                       "oct", "bin", "abs", "round", "len",
                       "int.bit_length", "int.to_bytes",
                       "float.hex",
                       "float.as_integer_ratio", "complex.conjugate"),
               "default_on": True, "note": "numeric conversions + basics"},
    "string": {"ops": ("str.join", "str.split", "str.format", "str.encode",
                       "str.decode", "str.upper", "str.lower",
                       "str.strip", "str.lstrip", "str.rstrip",
                       "str.replace", "str.find", "str.rfind", "str.index",
                       "str.count", "str.startswith", "str.endswith",
                       "str.partition", "str.rpartition", "str.splitlines",
                       "str.zfill", "str.ljust", "str.rjust", "str.center",
                       "str.swapcase",
                       "str.isalnum", "str.isspace",
                       "str.maketrans", "str.removeprefix",
                       "str.removesuffix"),
               "default_on": True, "note": "str method calls"},
    "container": {"ops": ("list", "tuple", "dict", "set", "frozenset",
                          "sorted", "reversed", "enumerate", "zip"),
                  "default_on": True, "note": "container constructors + iter"},
    # Protocol family: original 5 entries UNTOUCHED (names/shapes identical).
    # NOTE: "str" also appears in scalar (legacy overlap in the ORIGINAL
    # registry — kept verbatim); totals below count UNIQUE op names.
    "protocol": {"ops": ("iter", "next", "repr", "str", "bytes"),
                 "default_on": True, "note": "dunder-protocol builtins"},
    "service": {"ops": ("getattr", "setattr", "hasattr", "isinstance",
                        "issubclass", "callable", "id", "hash", "vars",
                        "dir", "globals", "locals", "compile",
                        "exec", "memoryview", "eval"),
                "default_on": True, "note": "introspection services"},
    # Range family: bare builtin needs atomicity protection (same fix as len/str).
    "range": {"ops": ("range", "aiter", "anext", "ascii", "format",
                      "slice"),
              "default_on": True, "note": "range + async iteration"},
    "function": {"ops": ("map", "filter", "any", "all", "sum", "min", "max",
                         "pow", "divmod", "complex"),
                 "default_on": True, "note": "higher-order builtins"},
    "import": {"ops": ("__import__", "breakpoint", "help",
                       "copyright", "credits", "license"),
               "default_on": True, "note": "kernel-resolved imports"},
    "fusion": {"ops": (),
               "default_on": True,
               "note": "collapses lowered-call chains into one dispatch"},
    # Container-method families (method-style ops: recv prepended).
    "list": {"ops": ("list.append", "list.extend", "list.insert",
                     "list.remove", "list.pop", "list.clear",
                     "list.index", "list.count", "list.sort",
                     "list.reverse", "list.copy"),
             "default_on": True, "note": "list method calls"},
    "dict": {"ops": ("dict.get", "dict.keys", "dict.values",
                     "dict.items", "dict.pop", "dict.popitem",
                     "dict.setdefault", "dict.update", "dict.clear",
                     "dict.copy", "dict.fromkeys"),
             "default_on": True, "note": "dict method calls"},
    "set": {"ops": ("set.add", "set.discard", "set.remove", "set.pop",
                    "set.clear", "set.union", "set.intersection",
                    "set.difference", "set.symmetric_difference",
                    "set.issubset", "set.issuperset", "set.copy"),
            "default_on": True, "note": "set method calls"},
    "tuple": {"ops": ("tuple.count", "tuple.index"),
              "default_on": True, "note": "tuple method calls"},
    "bytes": {"ops": ("bytes.decode", "bytes.hex", "bytes.fromhex"),
              "default_on": True, "note": "bytes method calls"},
    # Opt-in (V10 opt-in set)
    "arithmetic": {"ops": ("BinOp",), "default_on": False,
                   "note": "a+b etc become kernel calls (per-call cost)"},
    "truth": {"ops": ("Compare", "BoolOp", "Not"), "default_on": False,
              "note": "comparisons / boolean ops"},
    "slice": {"ops": ("Subscript",), "default_on": False,
              "note": "indexing/slicing"},
    "format": {"ops": ("JoinedStr", "FormattedValue"), "default_on": False,
               "note": "f-strings / .format"},
    "augassign": {"ops": ("AugAssign",), "default_on": False,
                  "note": "x += y etc"},
}

DEFAULT_ON = frozenset(n for n, f in FAMILIES.items() if f["default_on"])


def _op_token(op: str) -> str:
    return "_nxk_" + op.replace(".", "_").replace(" ", "_")


def _recv_class(name: str) -> "str | None":
    """Infer the kernel class for a receiver NAME (convention-based).

    Parity tests and the rewriter share this mapping so every routed
    method call binds the exact class implementation. Returns None for
    unknown receivers (never rewritten). Case-insensitive; longest
    prefix wins.
    """
    n = name.lower()
    for prefix, cls in (
        ("complex", "complex"), ("float", "float"), ("bytes", "bytes"),
        ("tuple", "tuple"), ("str", "str"), ("list", "list"),
        ("dict", "dict"), ("set", "set"), ("int", "int"),
        ("by", "bytes"), ("tpl", "tuple"), ("lst", "list"),
        ("num", "int"),
    ):
        if n.startswith(prefix):
            return cls
    if n in ("s", "sep", "txt", "text", "name", "msg", "word"):
        return "str"
    if n in ("xs", "ys", "zs", "items", "vals", "arr", "seq"):
        return "list"
    if n in ("d", "m", "mp", "mapping"):
        return "dict"
    if n in ("st", "ss"):
        return "set"
    if n in ("t", "tp"):
        return "tuple"
    if n in ("b", "buf", "data", "raw", "blob", "bs"):
        return "bytes"
    if n in ("n", "i", "j", "k", "x", "y", "z", "f", "c", "v", "num"):
        return "num"
    return None


def _op_class(op: str) -> "str | None":
    """Kernel class an op routes to (for dispatch + parity checks)."""
    if "." not in op:
        return None
    cls = op.split(".", 1)[0]
    if cls in ("str", "list", "dict", "set", "tuple", "bytes", "int",
               "float", "complex"):
        return cls
    return None


class _LoweringRewriter(ast.NodeTransformer):
    """Rewrite covered call sites to ``_nxk_*`` kernel calls.

    Bare-name builtins (``len(x)``) become ``_nxk_len(x)``.  Explicit
    dotted roots already in the registry (``str.join(sep, it)``,
    ``dict.fromkeys("ab")``) keep the receiver-agnostic rewrite.
    Object method calls (``s.split(",")``, ``xs.append(1)``,
    ``d.get("k")``) route through the matching dotted op by prepending
    the receiver: ``_nxk_str_split(s, ",")``.  Any other Attribute roots
    (``obj.len()``) are NEVER rewritten — matching is on the full
    dotted root for registry hits plus method-name dispatch for
    method-style ops, so unknown receivers keep their exact semantics.
    """

    # Method-style op lookup: method name -> set of dotted ops using it.
    # Filled lazily from the registry op set on first visit.

    def __init__(self, active: frozenset, op_set: frozenset) -> None:
        self.active = active
        self.op_set = op_set
        self.rewrites = 0

    def _dotted(self, node: ast.AST) -> "str | None":
        parts: "list[str]" = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return None

    def _meth_candidates(self, meth: str) -> "list[str]":
        """Dotted registry ops whose method segment equals ``meth``."""
        return sorted(o for o in self.op_set if "." in o
                      and o.rsplit(".", 1)[-1] == meth)

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        dotted = self._dotted(node.func)
        if dotted is None:
            return node
        # 1) Exact registry hit (bare builtins like len(x), or explicit
        #    dotted roots like str.join(sep, it) / dict.fromkeys(...)).
        #    No receiver is prepended: the source already names the root.
        if dotted in self.op_set:
            node.func = ast.Name(id=_op_token(dotted), ctx=ast.Load())
            self.rewrites += 1
            return node
        # 2) Object method call: recv.<meth>(...) with a plain-Name
        #    receiver. Rewritten ONLY when the (receiver-class, method)
        #    pair resolves to exactly one dotted registry op: the class
        #    is inferred from the receiver NAME prefix (``s``/``str*`` ->
        #    str, ``xs``/``lst``/``list*`` -> list, ``d``/``dict*`` ->
        #    dict, ``st``/``set*`` -> set, ``t``/``tpl``/``tuple*`` ->
        #    tuple, ``b``/``by*``/``bytes*`` -> bytes, ``n``/``i``/``f``/
        #    ``c``/``num*``/``int*``/``float*``/``complex*`` -> numeric).
        #    Same-named methods shared by several classes (clear/copy/
        #    count/decode/hex/index/pop/remove) resolve per receiver, and
        #    unknown receivers (``obj.len()``, ``foo.bar()``, ``s`` used
        #    for a set, ...) are NEVER rewritten. Receiver AST is
        #    prepended once, first — evaluation order preserved.
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            meth = node.func.attr
            cands = self._meth_candidates(meth)
            if not cands:
                return node
            cls = _recv_class(node.func.value.id)
            if cls == "num":
                matches = [o for o in cands
                           if o.split(".", 1)[0] in ("int", "float", "complex")]
            elif cls is None:
                return node
            else:
                matches = [o for o in cands if o.split(".", 1)[0] == cls]
            if len(matches) != 1:
                return node
            op = matches[0]
            recv = node.func.value
            node.func = ast.Name(id=_op_token(op), ctx=ast.Load())
            node.args = [recv] + list(node.args)
            self.rewrites += 1
            return node
        return node


def resolve_families(spec: str) -> frozenset:
    """Parse --lowering CSV into an active family set.

    "" (empty) -> no lowering. "all" -> all 14. "none" -> empty.
    "+arithmetic" adds, "-io" removes from defaults; bare names form an
    explicit list. Unknown names raise ValueError.
    """
    spec = (spec or "").strip()
    if not spec:
        return frozenset()
    active = set(DEFAULT_ON)
    if spec == "all":
        return frozenset(FAMILIES)
    if spec == "none":
        return frozenset()
    for raw in spec.split(","):
        part = raw.strip()
        if not part:
            continue
        if part.startswith("+"):
            name = part[1:]
            if name not in FAMILIES:
                raise ValueError(f"unknown lowering family: {name!r}")
            active.add(name)
        elif part.startswith("-"):
            name = part[1:]
            if name not in FAMILIES:
                raise ValueError(f"unknown lowering family: {name!r}")
            active.discard(name)
        else:
            if part not in FAMILIES:
                raise ValueError(f"unknown lowering family: {part!r}")
            active.add(part)
    return frozenset(active)


def _active_ops(active: frozenset) -> frozenset:
    ops: set[str] = set()
    for name in active:
        ops.update(FAMILIES[name]["ops"])
    return frozenset(ops)


def lower_source(source: str, families) -> tuple[str, int]:
    """Rewrite covered call sites; return (new_source, rewrite_count).

    Prepends ``from lowering_shim import ...``? No — the loader provides
    the ``_nxk_*`` names (shim import is emitted by the caller via
    emit_shim_import). Bare transform here for testability.
    """
    active = families if isinstance(families, frozenset) else resolve_families(families)
    # Node-kind families (BinOp/Compare/...) are Phase-2 (need fusion +
    # native perf story); Phase-1 covers CALLABLE ops only.
    call_ops = frozenset(
        o for o in _active_ops(active)
        if o not in ("BinOp", "Compare", "BoolOp", "Not", "Subscript",
                     "JoinedStr", "FormattedValue", "AugAssign")
    )
    tree = ast.parse(source)
    rw = _LoweringRewriter(active, call_ops)
    tree = rw.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), rw.rewrites


def emit_shim_import(active) -> str:
    """Import line binding every needed ``_nxk_*`` name from the shim."""
    active = active if isinstance(active, frozenset) else resolve_families(active)
    names = sorted(_op_token(o) for o in _active_ops(active)
                   if o not in ("BinOp", "Compare", "BoolOp", "Not", "Subscript",
                                "JoinedStr", "FormattedValue", "AugAssign"))
    if not names:
        return ""
    return "from lowering_shim import " + ", ".join(names) + "\n"
