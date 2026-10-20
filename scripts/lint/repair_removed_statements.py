"""Restore statements that the pure-dead-statement pass removed by mistake.

The first version of that pass treated any method whose NAME was on a
"pure methods" list as side-effect free.  That is wrong: ``str.partition``
is pure, ``hp.partition`` is not.  It removed real calls such as
``hp.partition(ops)``.

This repair compares each file against HEAD: a statement that HEAD had,
that the current file lost, and that the CORRECTED purity predicate
considers pure, is put back.  (Statements the corrected predicate
considers impure were never removed, so they need no repair.)
"""
import argparse
import ast
import importlib.util
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "rpd", os.path.join(HERE, "remove_pure_dead_statements.py"))
rpd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rpd)


def _stmt_texts(tree):
    """Every statement in the tree, as (unparsed, index-in-body) items."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        try:
            out.append((ast.unparse(node), node))
        except Exception:
            continue
    return out


def _legacy_pure(node):
    """The FIRST version of the predicate (the buggy one).

    It treated any method whose name was on the "pure methods" list as
    side-effect free, regardless of the receiver's type.  That is what
    removed statements like ``hp.partition(ops)``.
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in rpd.PURE_BUILTINS
    if isinstance(func, ast.Attribute):
        dotted = rpd._dotted_name(func)
        if dotted and (dotted.startswith("os.path.")
                       or dotted.startswith("pathlib.")
                       or dotted in ("ast.unparse", "ast.dump", "ast.dumps")):
            return True
        if dotted and dotted.split(".")[0] == "np":
            return True
        return func.attr in rpd.PURE_METHODS
    return False


def _pure_expr_statements(tree):
    """The Expr(Call) statements the BUGGY predicate called pure."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and _legacy_pure(node.value):
            try:
                out.append(ast.unparse(node))
            except Exception:
                pass
    return out


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
        lost = _pure_expr_statements(head_tree)
        if not lost:
            continue
        cur_texts = {t for t, _ in _stmt_texts(cur_tree)}
        missing = []
        for text in lost:
            if text in cur_texts:
                continue
            if text not in head:
                continue
            missing.append(text)
        if not missing:
            continue
        # Re-insert each missing statement before the statement that
        # followed it in HEAD.
        head_stmts = _stmt_texts(head_tree)
        cur_lines = cur_src.split("\n")
        inserts = []
        for text in missing:
            anchor = None
            for i, (t, node) in enumerate(head_stmts):
                if t == text:
                    for t2, _n2 in head_stmts[i + 1:]:
                        anchor = t2
                        break
                    break
            if anchor is None:
                continue
            for node in ast.walk(cur_tree):
                if isinstance(node, ast.stmt):
                    try:
                        if ast.unparse(node) == anchor:
                            indent = " " * node.col_offset
                            inserts.append((node.lineno, indent + text))
                            break
                    except Exception:
                        continue
        if not inserts:
            continue
        for lineno, text in sorted(inserts, reverse=True):
            cur_lines.insert(lineno - 1, text)
        new_src = "\n".join(cur_lines)
        repaired.append((path, missing))
        if args.apply:
            open(path, "w", encoding="utf-8").write(new_src)
    print("files repaired: %d" % (len(repaired),))
    for path, missing in repaired:
        print("  %s -> %r" % (path, missing))


if __name__ == "__main__":
    main()
