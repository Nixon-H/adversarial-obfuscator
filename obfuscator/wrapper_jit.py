"""Per-wrapper JIT compile+eval emit convention (batch 4).

The Rust side already compiles *per wrapper*: see
``runtime/src/jit.rs::specialize_template_with_class(class_id)`` — each
distinct ``class_id`` gets its own machine-code variant (``class_id`` is
injected as the first ``mov imm32`` so no two wrappers share a build).

What was missing was the *emit-side* convention: how the Python emitter
assigns a stable, distinct ``class_id`` to every wrapper and how the
generated loader invokes the per-wrapper specialization. That is what
this module provides:

Loader convention (documented here, implemented by the emitter):
  1. ``assign_class_ids(source)`` maps each ``FunctionDef`` qualified name
     to a stable ``u32`` class id (SHA-256, deterministic, no randomness).
  2. Instead of one central ``compile(template)`` call, the loader emits
     one call per wrapper::
         specialize_template_with_class(class_id, runtime_values)
     (see :func:`emit_wrapper_call` for the exact snippet shape) so each
     wrapper is specialized/compiled with its own ``class_id``.

This module is convention + mapping only; actual compilation stays in Rust.
"""

import ast
import hashlib

#: Mask to keep ids in u32 range.
_U32_MASK = 0xFFFFFFFF


class _ClassIdVisitor(ast.NodeVisitor):
    """Collect qualified FunctionDef names (classes + nesting aware)."""

    def __init__(self):
        self.stack: list[str] = []
        self.names: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def _record(self, node):
        self.stack.append(node.name)
        self.names.append(".".join(self.stack))
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._record(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):  # type: ignore[override]
        self._record(node)


def class_id_for_name(qualified_name: str) -> int:
    """Stable u32 class id for one qualified function name."""
    digest = hashlib.sha256(qualified_name.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little") & _U32_MASK


def assign_class_ids(source: str) -> dict[str, int]:
    """Map each FunctionDef qualified name in ``source`` to a stable u32 id.

    Qualified names include enclosing classes and functions, e.g.
    ``{"f": ..., "C.m": ..., "outer.inner": ...}``. Deterministic: no
    randomness, same source always yields the same mapping.
    """
    tree = ast.parse(source)
    visitor = _ClassIdVisitor()
    visitor.visit(tree)
    return {name: class_id_for_name(name) for name in visitor.names}


def emit_wrapper_call(func_name: str, class_id: int) -> str:
    """Emit the loader snippet for one wrapper.

    Documents the loader convention: the loader calls
    ``specialize_template_with_class(class_id, runtime_values)`` per
    wrapper instead of one central compile, so each wrapper gets its own
    specialized machine-code variant keyed by ``class_id``.
    """
    cid = int(class_id) & _U32_MASK
    return (
        f"# wrapper '{func_name}': per-wrapper specialization "
        f"(distinct class_id per wrapper)\n"
        f"specialize_template_with_class({cid}, runtime_values)  # {func_name}"
    )
