"""Proven-internal method/attribute analysis (V10 gap, opt-in).

A ``(class_name, method_name)`` pair is *proven internal* iff all of:

(a) the method is defined in a class body (``class C: def m(...)``,
    including ``async def``);
(b) the name does NOT start with ``__`` (dunder exempt: ``__init__``,
    ``__class__`` cells, zero-arg ``super()``, operator protocol);
(c) every *use* of that attribute name resolves inside the same class
    body — i.e. no ``obj.m`` / ``instance.m`` access outside the class,
    no ``getattr(obj, "m")`` / ``setattr`` / ``hasattr`` / ``delattr``
    string reference, no export via module-level ``__all__``, and no
    decorator implying an external contract (anything other than a
    plain ``@staticmethod`` / ``@classmethod`` used internally blocks
    the rename — ``@property``, ``@override``, custom decorators,
    ``@functools.*``, etc. block it).

Conservative by design: fewer renames, never break. Any doubt -> the
method is NOT internal (stays preserved). Whole-module analysis only:
no cross-file reasoning (an external module importing the class and
calling ``obj.m()`` cannot be seen, so the proof is necessarily
within one compilation unit).

Wiring: ``apply_ast_mutation(..., {"rename_internal": True})``
(default OFF) runs :func:`find_internal_methods` first and hands the
result to ``SymbolRenamer`` / ``UnicodeIdentifierEncoder`` so only
proven-internal names are renamed; every other public method stays
preserved (default = safe: external API preserved).

Python 3.10 compatible: no match statements, no X|Y annotations.
"""

from __future__ import annotations

import ast


# Decorators that do NOT imply an external contract. Only these (used
# alone) keep a method eligible; any other decorator blocks the rename.
_PLAIN_DECOS = frozenset(["staticmethod", "classmethod"])

# Builtin names that take a string attribute reference:
# getattr(obj, "m") / setattr(obj, "m", v) / hasattr(obj, "m") /
# delattr(obj, "m") / vars(obj)["m"]-style via string constants.
_DYNAMIC_REF_FUNCS = frozenset(["getattr", "setattr", "hasattr", "delattr"])

# Special first-arg names whose ``self.m`` / ``cls.m`` receivers count
# as same-class access. Anything else (``obj.m`` where obj is not
# self/cls) is treated as potentially external.
_SELF_NAMES = frozenset(["self", "cls", "mcs"])


def _decorator_names(node):
    # type: (ast.FunctionDef) -> Optional[List[str]]
    """Return dotted decorator names, or None if any is unresolvable."""
    names = []  # type: List[str]
    for deco in node.decorator_list:
        if isinstance(deco, ast.Name):
            names.append(deco.id)
        elif isinstance(deco, ast.Attribute):
            parts = []  # type: List[str]
            cur = deco  # type: ast.AST
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
                parts.reverse()
                names.append(".".join(parts))
            else:
                return None
        elif isinstance(deco, ast.Call):
            func = deco.func
            if isinstance(func, ast.Name):
                names.append(func.id)
            elif isinstance(func, ast.Attribute):
                parts2 = []  # type: List[str]
                cur2 = func  # type: ast.AST
                while isinstance(cur2, ast.Attribute):
                    parts2.append(cur2.attr)
                    cur2 = cur2.value
                if isinstance(cur2, ast.Name):
                    parts2.append(cur2.id)
                    parts2.reverse()
                    names.append(".".join(parts2))
                else:
                    return None
            else:
                return None
        else:
            return None
    return names


def _is_eligible_definition(node):
    # type: (ast.AST) -> bool
    """Check rule (b) + decorator rule for one FunctionDef/AsyncFunctionDef."""
    name = getattr(node, "name", "")
    if not isinstance(name, str) or not name:
        return False
    if name.startswith("__"):
        return False
    decos = _decorator_names(node)
    if decos is None:
        return False
    for deco in decos:
        base = deco.split(".")[-1]
        if deco in _PLAIN_DECOS or base in _PLAIN_DECOS:
            continue
        return False
    return True


class _MethodCollector(ast.NodeVisitor):
    """Collect per-class method definitions: class -> {name: node}."""

    def __init__(self):
        # type: () -> None
        self.class_stack = []  # type: List[str]
        self.methods = {}  # type: Dict[str, Dict[str, ast.AST]]
        self.class_nodes = {}  # type: Dict[str, ast.AST]

    def visit_ClassDef(self, node):
        # type: (ast.ClassDef) -> None
        self.class_stack.append(node.name)
        if node.name not in self.methods:
            self.methods[node.name] = {}
            self.class_nodes[node.name] = node
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if stmt.name not in self.methods[node.name]:
                    self.methods[node.name][stmt.name] = stmt
        self.generic_visit(node)
        self.class_stack.pop()


class _UsageScanner(ast.NodeVisitor):
    """Scan every *use* of attribute names and dynamic string refs.

    Records, per attribute name:
    - external attribute access: ANY ``x.name`` / ``self.name`` use
      occurring OUTSIDE the owning class body (module level, another
      class, a free function). NOTE: ``self.name`` uses inside the
      owning class body do NOT count (they are the internal pattern).
      Rationale: external ``obj.name`` proves external reachability;
      internal-only ``self.name`` proves nothing either way — the
      method is internal iff no use exists anywhere else.
    - dynamic string references (getattr/setattr/hasattr/delattr with a
      string-literal name argument);
    - bare ``Name`` loads of the method name outside the class body
      (e.g. ``handler = obj.method`` passed around, or a module-level
      function aliasing it).
    """

    def __init__(self, defined):
        # type: (Dict[str, Dict[str, ast.AST]]) -> None
        self.defined = defined
        self.name_to_classes = {}  # type: Dict[str, Set[str]]
        for cls_name, meths in defined.items():
            for meth_name in meths:
                self.name_to_classes.setdefault(meth_name, set()).add(cls_name)
        self.class_stack = []  # type: List[str]
        # Per attribute name: set of class names whose body the use is
        # "inside of" is tracked at visit time; external uses recorded:
        self.external_attr = set()  # type: Set[str]
        self.dynamic_refs = set()  # type: Set[str]
        self.external_name_load = set()  # type: Set[str]
        self._in_attr_value = 0

    def visit_ClassDef(self, node):
        # type: (ast.ClassDef) -> None
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_Attribute(self, node):
        # type: (ast.Attribute) -> None
        attr = node.attr
        if attr in self.name_to_classes:
            owners = self.name_to_classes[attr]
            if not (set(self.class_stack) & owners):
                # Use outside every owning class body: external.
                # (self.m inside the owner is the internal pattern and
                # does not taint; obj.m outside does.)
                self.external_attr.add(attr)
        self._in_attr_value += 1
        self.visit(node.value)
        self._in_attr_value -= 1
        # Do not generic_visit (would revisit value); ctx/keywds hold
        # no further attribute uses beyond value already visited, but
        # visit child ctx safely:
        for child in ast.iter_child_nodes(node):
            if child is not node.value:
                self.visit(child)

    def visit_Name(self, node):
        # type: (ast.Name) -> None
        if isinstance(node.ctx, ast.Load) and node.id in self.name_to_classes:
            if self._in_attr_value > 0:
                # Receiver of an attribute access (obj in obj.m) — not
                # a use of the method name itself.
                return
            owners = self.name_to_classes[node.id]
            if not (set(self.class_stack) & owners):
                self.external_name_load.add(node.id)
        # No children to visit for Name.

    def visit_Call(self, node):
        # type: (ast.Call) -> None
        func = node.func
        func_name = None  # type: Optional[str]
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute):
            func_name = func.attr
        if func_name in _DYNAMIC_REF_FUNCS and len(node.args) >= 2:
            str_arg = node.args[1]
            if isinstance(str_arg, ast.Constant) and isinstance(str_arg.value, str):
                if str_arg.value in self.name_to_classes:
                    self.dynamic_refs.add(str_arg.value)
            else:
                # Non-literal name argument (variable / f-string / ...):
                # cannot prove which attribute is referenced -> every
                # candidate method name is tainted (conservative).
                self.dynamic_refs.update(self.name_to_classes.keys())
        self.generic_visit(node)


def find_internal_methods(tree, all_names=None):
    # type: (ast.Module, Optional[List[str]]) -> Set[Tuple[str, str]]
    """Return ``{(class_name, method_name)}`` proven internal to one file.

    ``all_names``: module-level ``__all__`` export names (see
    ``obfuscator.all_preserve.extract_all_names``); any method whose
    name appears there is never internal.
    """
    exported = set(all_names or [])
    collector = _MethodCollector()
    try:
        collector.visit(tree)
    except Exception:
        return set()
    defined = collector.methods
    if not defined:
        return set()
    scanner = _UsageScanner(defined)
    try:
        scanner.visit(tree)
    except Exception:
        return set()
    blocked = (
        set(scanner.external_attr)
        | set(scanner.dynamic_refs)
        | set(scanner.external_name_load)
    )
    result = set()  # type: Set[Tuple[str, str]]
    for cls_name, meths in defined.items():
        for meth_name, meth_node in meths.items():
            if meth_name in exported:
                continue
            if meth_name in blocked:
                continue
            try:
                if not _is_eligible_definition(meth_node):
                    continue
            except Exception:
                continue
            result.add((cls_name, meth_name))
    return result
