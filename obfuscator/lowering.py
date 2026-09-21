"""Semantic lowering registry + AST pass + reference kernel (V10 headline).

Phase 1 (this module): pure-Python AST lowering. Call sites for covered
operations are rewritten to ``_nxk_<op>(...)`` calls against the reference
kernel in :mod:`obfuscator.lowering_shim`, so output still RUNS without any
native artifact. Phase 2 (later, --pytoc path): the shim import is swapped
for per-build-renamed Cython helpers with identical call shapes.

Families mirror V10: 9 default-ON (io, scalar, string, container, service,
protocol, function, import, fusion) + 5 opt-in (arithmetic, truth, slice,
format, augassign). ``--lowering`` CSV selects families: "all", "none",
"+arithmetic", "-io", or explicit lists. Unknown names raise ValueError.
"""

from __future__ import annotations

import ast

FAMILIES: dict[str, dict] = {
    # Default ON (V10 default set)
    "io": {"ops": ("print", "input", "open"), "default_on": True,
           "note": "print/input/open routed to kernel routines"},
    "scalar": {"ops": ("int", "float", "str", "bool", "chr", "ord", "hex",
                       "oct", "bin", "abs", "round", "len"),
               "default_on": True, "note": "numeric conversions + basics"},
    "string": {"ops": ("str.join", "str.split", "str.format", "str.encode",
                       "str.decode", "str.upper", "str.lower"),
               "default_on": True, "note": "str method calls"},
    "container": {"ops": ("list", "tuple", "dict", "set", "frozenset",
                          "len", "sorted", "reversed", "enumerate", "zip"),
                  "default_on": True, "note": "container constructors + iter"},
    "service": {"ops": ("getattr", "setattr", "hasattr", "isinstance",
                        "issubclass", "callable", "id", "hash"),
                "default_on": True, "note": "introspection services"},
    "protocol": {"ops": ("iter", "next", "repr", "str", "bytes"),
                 "default_on": True, "note": "dunder-protocol builtins"},
    "function": {"ops": ("map", "filter", "any", "all", "sum", "min", "max"),
                 "default_on": True, "note": "higher-order builtins"},
    "import": {"ops": ("__import__",),
               "default_on": True, "note": "kernel-resolved imports"},
    "fusion": {"ops": (),
               "default_on": True,
               "note": "collapses lowered-call chains into one dispatch"},
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


class _LoweringRewriter(ast.NodeTransformer):
    """Rewrite covered call sites to ``_nxk_*`` kernel calls."""

    def __init__(self, active: frozenset, op_set: frozenset) -> None:
        self.active = active
        self.op_set = op_set
        self.rewrites = 0

    def _dotted(self, node: ast.AST) -> str | None:
        parts: list[str] = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return None

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        dotted = self._dotted(node.func)
        if dotted is None:
            return node
        # Bare-name builtins (print(x)) and dotted (str.join) both match.
        hit = dotted in self.op_set or dotted.split(".")[-1] in self.op_set
        if not hit:
            return node
        node.func = ast.Name(id=_op_token(dotted), ctx=ast.Load())
        self.rewrites += 1
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
