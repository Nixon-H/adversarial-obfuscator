"""Remove unused imports, safely.

Two rules:

* A name that appears inside a STRING LITERAL in the same file is not
  removed -- this repo embeds generated code (loader templates, emitted
  snippets) as string constants, and those templates are executed or
  rendered later.  A name that only exists inside such a template is
  invisible to the linter but still needed.
* Everything else is removed surgically: the import statement is
  rebuilt from its AST, so multi-name and multi-line imports are handled
  without touching the rest of the file.

Names kept for template use get a ``# noqa: F401`` with the reason, so
the gate stays clean and the decision stays visible.
"""
import argparse
import ast
import os
import re
import subprocess

IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
NOQA = "  # noqa: F401 (this line binds a name used by an embedded template)"


def _docstring_nodes(tree):
    """ids of the Constant nodes that are docstrings."""
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            out.add(id(first.value))
    return out


def string_identifiers(tree):
    """Identifiers mentioned inside a string literal in the file.

    Docstrings are excluded: a module docstring that lists a class name
    is documentation, not a template that needs the import to survive.
    """
    docstrings = _docstring_nodes(tree)
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            out.update(IDENT.findall(node.value))
    return out


def collect_findings(paths):
    """Map path -> {(lineno, col): qualified name ruff reported}.

    The position matters: the same qualified name can be imported twice
    in one file -- once at module scope where it IS used, once inside a
    function where it is not.  Ruff reports only the unused one, so
    matching by name alone would remove both.
    """
    out = subprocess.run(
        ["ruff", "check", "--no-cache", "--select", "F401",
         "--output-format=concise"] + paths,
        capture_output=True, text=True).stdout
    findings = {}
    for line in out.splitlines():
        if " F401 " not in line:
            continue
        path, lineno, col, rest = line.split(":", 3)
        m = re.search(r"`([^`]+)` imported but unused", rest)
        if m:
            findings.setdefault(path, {})[(int(lineno), int(col))] = m.group(1)
    return findings


def alias_text(alias):
    return alias.name + (" as " + alias.asname if alias.asname else "")


def bound_name(alias):
    if alias.name == "*":
        return None
    if alias.asname:
        return alias.asname
    return alias.name.split(".")[0]


def qualified_name(node, alias):
    """The name ruff reports for this alias.

    ``import a.b`` is reported as ``a.b`` but binds ``a``;
    ``from x import y`` is reported as ``x.y`` and binds ``y``.
    """
    if isinstance(node, ast.Import):
        return alias.name
    module = ("." * node.level) + (node.module or "")
    return ("%s.%s" % (module, alias.name)) if module else alias.name


def alias_key(alias):
    """(lineno, column) of an alias, in ruff's 1-based column numbering.

    AST ``col_offset`` is 0-based; ruff reports 1-based columns.
    """
    return (alias.lineno, alias.col_offset + 1)


def _only_statement_in_guarded_try(node, parent_map):
    """True when *node* is the only statement in a try/except ImportError.

    Such an import IS the test: removing it leaves the ``except``
    branch unreachable and turns an availability probe into a lie.  It
    happened once (``_check_aes_ctr``) -- the probe then always reported
    AES-CTR as available.
    """
    parent = parent_map.get(id(node))
    if not isinstance(parent, ast.Try):
        return False
    body = getattr(parent, "body", None)
    if not isinstance(body, list) or len(body) != 1 or body[0] is not node:
        return False
    for handler in parent.handlers:
        exc = handler.type
        if exc is None:
            return True
        names = []
        if isinstance(exc, ast.Name):
            names = [exc.id]
        elif isinstance(exc, ast.Tuple):
            names = [e.id for e in exc.elts
                     if isinstance(e, ast.Name)]
        if "ImportError" in names:
            return True
    return False


def plan_node(node, unused, in_strings):
    """Return (new_text, marked) for one import node.

    *unused* maps (lineno, col) -> qualified name, so only the exact
    import ruff flagged is dropped.
    """
    kept = []
    marked = False
    for alias in node.names:
        bound = bound_name(alias)
        if bound is None:
            kept.append(alias)
            continue
        key = alias_key(alias)
        qualified = unused.get(key)
        if qualified is None:
            kept.append(alias)
            continue
        if bound in in_strings:
            kept.append(alias)
            marked = True
    if len(kept) == len(node.names) and not marked:
        return None, False
    if not kept:
        return "", False
    if isinstance(node, ast.Import):
        text = "import " + ", ".join(alias_text(a) for a in kept)
    else:
        module = ("." * node.level) + (node.module or "")
        text = "from %s import %s" % (module, ", ".join(alias_text(a) for a in kept))
    return text, marked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    findings = collect_findings(args.paths)
    dropped = kept = 0
    changed = []
    for path in sorted(findings):
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            print("SKIP (syntax):", path)
            continue
        in_strings = string_identifiers(tree)
        parent_map = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent_map[id(child)] = node
        unused = findings[path]
        lines = src.split("\n")
        edits = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if not any(alias_key(a) in unused for a in node.names):
                continue
            if _only_statement_in_guarded_try(node, parent_map):
                # The import is an availability probe: keep it.
                continue
            text, marked = plan_node(node, unused, in_strings)
            if text is None:
                continue
            indent = " " * node.col_offset
            body = indent + text if text else None
            edits.append((node.lineno, node.end_lineno, body, marked))
            for alias in node.names:
                b = bound_name(alias)
                if alias_key(alias) not in unused:
                    continue
                if b in in_strings:
                    kept += 1
                else:
                    dropped += 1
        if not edits:
            continue
        for start, end, body, marked in sorted(edits, reverse=True):
            if body is None:
                del lines[start - 1:end]
            else:
                if marked:
                    body += NOQA
                lines[start - 1:end] = [body]
        new_src = "\n".join(lines)
        if new_src != src:
            changed.append(path)
            if args.apply:
                open(path, "w", encoding="utf-8").write(new_src)
    print("dropped: %d   kept-for-template: %d   files changed: %d"
          % (dropped, kept, len(changed)))
    if not args.apply:
        for p in changed:
            print("  would change:", p)


if __name__ == "__main__":
    main()
