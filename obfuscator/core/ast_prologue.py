"""Safe insertion of module-level prologue nodes.

Several transforms prepend helpers or imports to a module.  A blind
``tree.body.insert(0, ...)`` is wrong twice over:

* a module docstring must stay the first statement or ``__doc__`` is lost;
* ``from __future__ import ...`` must stay before every other statement or
  the module raises ``SyntaxError: from __future__ imports must occur at the
  beginning of the file``.

These helpers compute the first legal insertion point once so every
transform uses the same rule.
"""
from __future__ import annotations

import ast


def module_prologue_index(tree: ast.Module) -> int:
    """Return the index after the docstring and any ``__future__`` imports."""
    at = 0
    if (tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        at = 1
    while (at < len(tree.body)
           and isinstance(tree.body[at], ast.ImportFrom)
           and tree.body[at].module == "__future__"):
        at += 1
    return at


def insert_module_prologue(tree: ast.Module, nodes: list[ast.AST]) -> None:
    """Insert ``nodes`` at the first legal module-level position."""
    if not nodes:
        return
    at = module_prologue_index(tree)
    tree.body[at:at] = nodes
