"""Module-level ``__all__`` preservation pass (AUDIT GAP #64, C11).

Public exports listed in a statically determinable module-level
``__all__`` (a list/tuple of string literals)::

    __all__ = ["foo", "Bar"]

must survive obfuscation so the built module stays importable with a
correct public API.  This module only *reads* the AST — it never
rewrites it::

    names, dynamic = extract_all_names(tree)

- ``names``: the statically known export names (possibly empty).
- ``dynamic``: True when a module-level ``__all__`` assignment exists
  but is *computed* (call, comprehension, concat, star-unpack, ...) and
  therefore cannot be resolved without executing code.  Callers leave
  the source untouched and emit a warning comment/log.

Wiring: ``obfuscator/core/sources.py::apply_ast_mutation`` reads
``__all__`` from the AST *before* SymbolRenamer/UnicodeIdentifierEncoder
run and adds the names to each pass's ``reserved`` set (additive: no
``__all__`` or empty static list changes nothing).

``__all__`` itself is already in the renamer-reserved macro-adjacent set
(see ``obfuscator/macros.py:25``) via the SymbolRenamer defaults; the
names *inside* it are what this pass protects.

Python 3.10 compatible: no match statements, no X|Y annotations.
"""

import ast
from typing import List, Tuple


def _static_string_list(node):
    # type: (ast.AST) -> List[str]
    """Return the string list if ``node`` is a static list/tuple of str.

    Raises ValueError for anything computed (calls, names, comprehensions,
    starred elements, non-string elements, JoinedStr, ...).
    """
    if isinstance(node, (ast.List, ast.Tuple)):
        out = []  # type: List[str]
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                out.append(elt.value)
            else:
                raise ValueError("non-literal __all__ element")
        return out
    raise ValueError("non-static __all__ value")


def extract_all_names(tree):
    # type: (ast.Module) -> Tuple[List[str], bool]
    """Read module-level ``__all__`` from an AST.

    Returns ``(names, dynamic)`` where ``names`` is the statically
    determinable export list and ``dynamic`` flags a computed
    ``__all__`` the caller should warn about (but not rewrite).

    - no module-level ``__all__`` assignment -> ``([], False)``.
    - ``__all__ = [...]`` / ``__all__ = (...)`` of string literals ->
      ``(names, False)`` (last static assignment wins).
    - ``__all__ += [...]`` with static elements extends the list.
    - anything else assigned/appended/computed -> ``([], True)`` when
      no static names were found, else ``(names, True)`` (partially
      static: keep what is known, still warn).
    """
    names = []  # type: List[str]
    dynamic = False
    if not isinstance(tree, ast.Module):
        return ([], False)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets
                       if isinstance(t, ast.Name) and t.id == "__all__"]
            if not targets:
                continue
            try:
                names = _static_string_list(node.value)
            except ValueError:
                dynamic = True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                if node.value is None:
                    dynamic = True
                    continue
                try:
                    names = _static_string_list(node.value)
                except ValueError:
                    dynamic = True
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                try:
                    names.extend(_static_string_list(node.value))
                except ValueError:
                    dynamic = True
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            # __all__.append("x") / __all__.extend(["x"]) — computed
            # unless the argument is a static string / string list.
            func = node.value.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id == "__all__" and func.attr in ("append", "extend"):
                    try:
                        if func.attr == "append":
                            arg = node.value.args[0]
                            if (isinstance(arg, ast.Constant)
                                    and isinstance(arg.value, str)):
                                names.append(arg.value)
                            else:
                                raise ValueError("non-literal append")
                        else:
                            names.extend(
                                _static_string_list(node.value.args[0]))
                    except (ValueError, IndexError):
                        dynamic = True
    # Deduplicate, preserving order.
    seen = set()
    unique = []  # type: List[str]
    for name in names:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return (unique, dynamic)


def warning_comment(names, dynamic=False):
    # type: (List[str], bool) -> str
    """Build-time warning comment for a dynamic ``__all__`` (no rewrite)."""
    _ = names
    if dynamic:
        return ("# NIXON: dynamic __all__ detected (computed, not a static "
                "list/tuple of string literals); public exports left "
                "untouched, no renames reserved from __all__")
    return ""
