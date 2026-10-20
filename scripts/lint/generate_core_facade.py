#!/usr/bin/env python3
"""Regenerate ``obfuscator/core/__init__.py``.

The package facade used to be four star imports.  That made the
linter unable to check the names it re-exported (F403/F405 had to be
ignored), and it made the surface incidental: a name could disappear
from a module and vanish from every consumer without a word.

The facade is now explicit, and therefore it has to be kept in sync
with the four modules it re-exports.  This script does that
mechanically, so the sync is a command rather than a chore.

Usage::

    python3 scripts/lint/generate_core_facade.py            # rewrite the file
    python3 scripts/lint/generate_core_facade.py --check    # fail if stale

The exported set is exactly what ``from .mod import *`` produced:
every public module-level name of the four modules, with the later
modules shadowing the earlier ones (utils, transforms, sources,
pipeline).  A name that only exists conditionally -- ``np``, which
utils binds only when numpy is installed -- is therefore NOT exported:
re-exporting it would make the package unimportable without numpy.
"""
import argparse
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
CORE = os.path.join(REPO_ROOT, "obfuscator", "core")
FACADE = os.path.join(CORE, "__init__.py")

#: The order the star imports ran in.  Later modules shadow earlier
#: ones, so this order defines the surface.
ORDER = ("utils", "transforms", "sources", "pipeline")

HEADER = '''"""The obfuscation pipeline's public surface.

This package re-exports the public names of its four modules.  It used
to do that with ``from .mod import *``, which meant the linter could
not check that a name arriving through a star import actually existed
-- and the conversion to explicit imports immediately found a dead
``return`` in ``sources.generate_poly_vm`` that referenced two names
nobody had ever defined.

The surface is spelled out here, and in ``__all__``, so that:

* the lint gate can check it (F401/F403/F405 are all enforced),
* the compatibility surface is explicit rather than incidental, and
* a name that disappears from a module fails loudly here instead of
  silently vanishing from every consumer.

GENERATED FILE -- do not edit by hand.  Regenerate with:

    python3 scripts/lint/generate_core_facade.py

and check it with:

    python3 scripts/lint/generate_core_facade.py --check

Submodules remain importable as ``obfuscator.core.utils`` and so on.
"""'''


def _catches_import_error(handler):
    node = handler.type
    if node is None:
        return True
    if isinstance(node, ast.Name):
        return node.id == "ImportError"
    if isinstance(node, ast.Tuple):
        return any(isinstance(e, ast.Name) and e.id == "ImportError"
                   for e in node.elts)
    return False


def public_names(path):
    """The public module-level names of *path*.

    Mirrors what ``from module import *`` exports: every name bound at
    module level that does not start with an underscore.

    Names bound only INSIDE a ``try: ... except ImportError`` are
    excluded.  They are conditional: ``np`` exists in ``utils`` only
    when numpy is installed, and re-exporting it unconditionally would
    make the whole package unimportable on an interpreter without
    numpy.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = set()

    def add(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                out.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                out.add(alias.asname or alias.name.split(".")[0])

    for node in tree.body:
        add(node)
        if isinstance(node, ast.Try):
            if any(_catches_import_error(h) for h in node.handlers):
                # Conditional binding: not part of the unconditional
                # surface.
                continue
            for sub in (node.body
                        + [n for h in node.handlers for n in h.body]
                        + list(node.orelse) + list(node.finalbody)):
                add(sub)
    return {n for n in out if not n.startswith("_")}


def surface():
    """(owner module -> names) and the flattened ordered surface."""
    owner = {}
    for module in ORDER:
        for name in public_names(os.path.join(CORE, "%s.py" % module)):
            owner[name] = module          # later modules shadow earlier
    buckets = {m: [] for m in ORDER}
    for name in sorted(owner):
        buckets[owner[name]].append(name)
    return buckets, sorted(owner)


def render():
    buckets, allnames = surface()
    lines = [HEADER, ""]
    for module in ORDER:
        names = buckets[module]
        if not names:
            continue
        lines.append("from .%s import (" % module)
        for name in names:
            lines.append("    %s," % name)
        lines.append(")")
        lines.append("")
    lines.append("__all__ = [")
    for name in allnames:
        lines.append("    %r," % name)
    lines.append("]")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit nonzero if the facade is out of date")
    args = ap.parse_args()
    rendered = render()
    if args.check:
        current = open(FACADE, encoding="utf-8").read()
        if current != rendered:
            print("obfuscator/core/__init__.py is out of date; run "
                  "scripts/lint/generate_core_facade.py")
            return 1
        print("obfuscator/core/__init__.py is up to date")
        return 0
    with open(FACADE, "w", encoding="utf-8") as fh:
        fh.write(rendered)
    _buckets, allnames = surface()
    print("wrote %s (%d names)" % (FACADE, len(allnames)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
