"""Remove unused local variables, safely.

Two shapes are handled:

* ``except X as e:`` where *e* is never read -- the binding is dropped.
* an assignment whose value is never read -- the statement is removed,
  EXCEPT when the right-hand side is a call, which may have side
  effects; in that case the call is kept as a bare expression statement
  so the behaviour (including any RNG consumption) is unchanged.
"""
import argparse
import ast
import os
import re
import subprocess


def collect(paths):
    out = subprocess.run(
        ["ruff", "check", "--no-cache", "--select", "F841",
         "--output-format=concise"] + paths,
        capture_output=True, text=True).stdout
    found = {}
    for line in out.splitlines():
        if " F841 " not in line:
            continue
        path, lineno, _col, rest = line.split(":", 3)
        m = re.search(r"Local variable `([^`]+)` is assigned to but never used", rest)
        if m:
            found.setdefault(path, set()).add((int(lineno), m.group(1)))
    return found


def is_call(node):
    return isinstance(node, (ast.Call, ast.Await, ast.Yield, ast.YieldFrom))


def sole_statement(node, parent_map):
    """True when *node* is the only statement in its parent block."""
    parent = parent_map.get(id(node))
    if parent is None:
        return False
    body = getattr(parent, "body", None)
    if not isinstance(body, list):
        return False
    return len(body) == 1 and body[0] is node


def build_parent_map(tree):
    out = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            out[id(child)] = node
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    found = collect(args.paths)
    changed = []
    for path in sorted(found):
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        targets = found[path]
        edits = []
        parent_map = build_parent_map(tree)
        for node in ast.walk(tree):
            # except-handler binding
            if isinstance(node, ast.ExceptHandler) and node.name:
                if (node.lineno, node.name) in targets:
                    edits.append((node.lineno, node.end_lineno, "except", node))
                    continue
            # plain assignment
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                names = []
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            names.append(t.id)
                elif isinstance(node.target, ast.Name):
                    names.append(node.target.id)
                if not names:
                    continue
                if not any((node.lineno, n) in targets for n in names):
                    continue
                if is_call(node.value):
                    # keep the call, drop the binding
                    text = ast.unparse(node.value)
                    edits.append((node.lineno, node.end_lineno, "call", text))
                elif sole_statement(node, parent_map):
                    # the only statement in its block: keep the block valid
                    edits.append((node.lineno, node.end_lineno, "pass", None))
                else:
                    edits.append((node.lineno, node.end_lineno, "drop", None))
        if not edits:
            continue
        lines = src.split("\n")
        # handler edits need a regex on the except line
        for start, end, kind, payload in sorted(edits, reverse=True):
            if kind == "except":
                for i in range(start - 1, end):
                    if " as " in lines[i] and "except" in lines[i]:
                        lines[i] = re.sub(r"\s+as\s+\w+\s*:", ":", lines[i], count=1)
                        break
            elif kind == "call":
                indent = " " * (len(lines[start - 1]) - len(lines[start - 1].lstrip()))
                lines[start - 1:end] = [indent + payload]
            elif kind == "pass":
                indent = " " * (len(lines[start - 1]) - len(lines[start - 1].lstrip()))
                lines[start - 1:end] = [indent + "pass"]
            else:
                del lines[start - 1:end]
        new_src = "\n".join(lines)
        if new_src != src:
            changed.append(path)
            if args.apply:
                open(path, "w", encoding="utf-8").write(new_src)
    print("files changed: %d" % (len(changed),))
    if not args.apply:
        for p in changed:
            print("  would change:", p)


if __name__ == "__main__":
    main()
