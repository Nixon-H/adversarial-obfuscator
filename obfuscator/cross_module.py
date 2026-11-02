"""Find module-level names a sibling module imports.

Defect 13 of the research programme: the renamer renames module-level public names
in a module that has no ``__all__``, while the modules that import those names are
transformed separately and are not rewritten. The result is a package that cannot
import itself::

    pkg/_mod.py      def cmp_using(...): ...        # public, no __all__
    pkg/__init__.py  from ._mod import cmp_using   # ImportError after obfuscation

A single-module transform cannot see the sibling that imports the name, so the caller
supplies the result of this scan via ``options={"imported_names": ...}``. That keeps
the documented contract (public names are renamed when there is no ``__all__``) while
making the cross-module case work.

This is a *narrowing* of what gets renamed, never an expansion.
"""
import ast
import os


def _names_imported_from(tree, module_stem):
    """Module-level names ``tree`` imports from a module whose stem is ``module_stem``."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            level = getattr(node, "level", 0) or 0
            mod = node.module or ""
            # `from ._mod import x` (level 1, module "_mod") or
            # `from pkg._mod import x` (module "pkg._mod")
            if not (mod == module_stem or mod.endswith("." + module_stem)):
                continue
            if level == 0 and mod != module_stem:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.name)
    return names


def sibling_imports(module_path):
    """Names that other ``.py`` files in the same directory import from ``module_path``.

    Returns an empty set rather than raising when the directory cannot be read, so a
    caller can pass the result straight into ``options["imported_names"]``.
    """
    try:
        directory = os.path.dirname(os.path.abspath(module_path))
        stem = os.path.splitext(os.path.basename(module_path))[0]
    except Exception:
        return set()
    found = set()
    try:
        entries = os.listdir(directory)
    except OSError:
        return found
    for entry in entries:
        if not entry.endswith(".py"):
            continue
        other = os.path.join(directory, entry)
        if os.path.abspath(other) == os.path.abspath(module_path):
            continue
        try:
            with open(other, encoding="utf-8", errors="replace") as handle:
                tree = ast.parse(handle.read())
        except (OSError, SyntaxError, ValueError):
            continue
        found |= _names_imported_from(tree, stem)
    return found
