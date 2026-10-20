"""Re-add imports that the unused-import cleanup removed too eagerly.

The cleanup matched ruff's findings by qualified name (``os``), but the
same qualified name can be imported at two levels in one file -- once at
module scope where it IS used, and once inside a function where it is
not.  Ruff only flags the unused one; the cleanup then removed both.

This repair compares each modified file against HEAD: any name that is
still *used* in the file, is no longer bound by an import, and WAS bound
at HEAD gets its import statement back (rebuilt with just the missing
names, at its original position).
"""
import argparse
import ast
import os
import subprocess


def used_names(tree):
    """Every name the code actually reads."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            base = node
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                out.add(base.id)
    return out


def bound_names(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name != "*":
                    out.add(a.asname or a.name)
    return out


def import_statements(tree):
    """bound name -> (lineno, end_lineno, indent, text, alias list)."""
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for a in node.names:
            if a.name == "*":
                continue
            out.setdefault(a.asname or a.name.split(".")[0], []).append(node)
    return out


def alias_text(alias):
    return alias.name + (" as " + alias.asname if alias.asname else "")


def render(node, names):
    parts = []
    for a in node.names:
        bound = a.asname or a.name.split(".")[0]
        if bound in names:
            parts.append(alias_text(a))
    if not parts:
        return None
    if isinstance(node, ast.Import):
        return "import " + ", ".join(parts)
    module = ("." * node.level) + (node.module or "")
    return "from %s import %s" % (module, ", ".join(parts))


def first_use_line(tree, name):
    """Line of the first statement that reads *name* (1-indexed)."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            lineno = node.lineno
            if best is None or lineno < best:
                best = lineno
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    changed = subprocess.run(["git", "diff", "--name-only"], capture_output=True,
                             text=True).stdout.split()
    repaired = []
    for path in changed:
        if not path.endswith(".py") or not os.path.exists(path):
            continue
        head = subprocess.run(["git", "show", "HEAD:%s" % path],
                              capture_output=True, text=True).stdout
        if not head:
            continue
        try:
            head_tree = ast.parse(head)
            cur_src = open(path, encoding="utf-8").read()
            cur_tree = ast.parse(cur_src)
        except SyntaxError:
            continue
        used = used_names(cur_tree)
        bound_now = bound_names(cur_tree)
        missing = {n for n in used
                   if n not in bound_now
                   and n in bound_names(head_tree)}
        if not missing:
            continue
        # Rebuild the HEAD import statements with the missing names only.
        inserts = []
        for node in ast.walk(head_tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            names = {a.asname or a.name.split(".")[0] for a in node.names
                     if a.name != "*"} & missing
            if not names:
                continue
            text = render(node, names)
            if not text:
                continue
            # Place the import just before the statement that uses it, at
            # that statement's indentation, so it lands in the right scope
            # in the CURRENT file (HEAD's line numbers have shifted).
            target = min((first_use_line(cur_tree, n) for n in names
                          if first_use_line(cur_tree, n)), default=None)
            if target is None:
                continue
            lines_now = cur_src.split("\n")
            stmt_line = None
            for cand in ast.walk(cur_tree):
                if isinstance(cand, ast.stmt) and cand.lineno <= target <= (cand.end_lineno or 0):
                    if stmt_line is None or cand.lineno > stmt_line:
                        stmt_line = cand.lineno
            if stmt_line is None:
                continue
            raw = lines_now[stmt_line - 1]
            indent = " " * (len(raw) - len(raw.lstrip()))
            inserts.append((stmt_line, indent + text))
        if not inserts:
            continue
        lines = cur_src.split("\n")
        for lineno, text in sorted(inserts, reverse=True):
            lines.insert(lineno - 1, text)
        new_src = "\n".join(lines)
        repaired.append((path, sorted(missing)))
        if args.apply:
            open(path, "w", encoding="utf-8").write(new_src)
    print("files repaired: %d" % (len(repaired),))
    for path, names in repaired:
        print("  %s -> %s" % (path, ", ".join(names)))


if __name__ == "__main__":
    main()
