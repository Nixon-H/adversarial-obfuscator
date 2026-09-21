"""Runtime API name gate (V10 adopt, small).

Privileged runtime call names are resolved through a per-build mapping
instead of appearing as literals at call sites, so they cannot be found
by a static string scan of the call sites.

Honest limitation: the mapping table itself (token -> dotted path) IS
recoverable from the artifact — what this defeats is grepping CALL SITES
for names like ``marshal.loads`` or ``os.system``. Matches Nyami's
"cannot be found by a static scan" claim for call sites, not the registry.
"""

from __future__ import annotations

import ast
import hashlib

PRIVILEGED = (
    "marshal.loads",
    "marshal.dumps",
    "builtins.exec",
    "builtins.eval",
    "builtins.compile",
    "builtins.__import__",
    "ctypes.CDLL",
    "ctypes.pythonapi",
    "os.system",
    "os.popen",
    "subprocess.Popen",
    "subprocess.run",
    "subprocess.call",
    "sys.settrace",
    "sys.gettrace",
    "sys.setprofile",
    "sys.getprofile",
    "sys.addaudithook",
    "gc.get_objects",
    "importlib.import_module",
    "importlib.util.spec_from_file_location",
    "open",
    "eval",
    "exec",
)


def build_mapping(seed: bytes, names=None) -> dict[str, str]:
    """Map privileged dotted name -> token ``_nxg_<12 hex>``.

    Deterministic for the same seed (SHA-256(seed + name)); distinct
    names always yield distinct tokens for a fixed seed in practice
    (12 hex chars = 48 bits; collisions would need ~2^24 names).
    """
    wanted = tuple(names) if names is not None else PRIVILEGED
    mapping: dict[str, str] = {}
    for name in wanted:
        digest = hashlib.sha256(bytes(seed) + name.encode("utf-8")).hexdigest()
        mapping[name] = "_nxg_" + digest[:12]
    return mapping


def emit_gate_snippet(mapping: dict[str, str]) -> str:
    """Return Python source defining the runtime resolver.

    Defines ``_NXG_MAP`` (token -> dotted path) plus ``_nx_get(token)``
    which splits the dotted path and walks ``__import__``/``getattr``.
    Call sites use ``_nx_get('<token>')(args)`` — no privileged dotted
    name appears at any rewritten call site.
    """
    lines = [
        "from functools import lru_cache as _nxg_lru",
        "_NXG_MAP = {",
    ]
    for dotted in sorted(mapping, key=mapping.get):  # type: ignore[arg-type]
        lines.append(f"    {mapping[dotted]!r}: {dotted!r},")
    lines.append("}")
    lines.append("@_nxg_lru(maxsize=None)")
    lines.append("def _nx_get(_token):")
    lines.append("    _dotted = _NXG_MAP[_token]")
    lines.append("    _parts = _dotted.split('.')")
    lines.append("    if len(_parts) == 1:")
    lines.append("        import builtins as _bi")
    lines.append("        return getattr(_bi, _parts[0])")
    lines.append("    _mod = __import__(_parts[0])")
    lines.append("    _obj = _mod")
    lines.append("    for _p in _parts[1:-1]:")
    lines.append("        _obj = getattr(_obj, _p)")
    lines.append("    return getattr(_obj, _parts[-1])")
    return "\n".join(lines) + "\n"


def _dotted_of(node: ast.AST) -> str | None:
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


class _GateRewriter(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping
        self.rewrites = 0

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        dotted = _dotted_of(node.func)
        if dotted is not None and dotted in self.mapping:
            token = self.mapping[dotted]
            node.func = ast.Call(
                func=ast.Name(id="_nx_get", ctx=ast.Load()),
                args=[ast.Constant(value=token)],
                keywords=[],
            )
            self.rewrites += 1
        return node


def rewrite_calls(source: str, mapping: dict[str, str]) -> str:
    """Rewrite privileged call sites to ``_nx_get('<token>')(...)``.

    Only exact dotted matches are rewritten; everything else is left
    alone (modulo ast.unparse reformatting — semantics preserved).
    """
    tree = ast.parse(source)
    tree = _GateRewriter(mapping).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)
