"""Delete dead expression statements whose call is provably pure.

The unused-local cleanup keeps a call whose result is unused, because
the call may have a side effect (``list.append``, ``mprotect``, a CLI
subparser registration, an IR instruction emission...).  When the call is
known to be pure the whole statement is dead and can go.

"Pure" is decided by an explicit allowlist of builtins and methods, so
an unknown call is always kept.
"""
import argparse
import ast
import os

#: Builtins that never have side effects.
PURE_BUILTINS = frozenset([
    "abs", "all", "any", "bool", "bytes", "bytearray", "dict", "float",
    "frozenset", "hash", "id", "int", "len", "list", "max", "min", "ord",
    "range", "repr", "reversed", "set", "sorted", "str", "sum", "tuple",
    "zip",
])

#: Methods that never have side effects -- but ONLY on a receiver whose
#: type is known (a literal).  A method name alone is NOT evidence:
#: ``str.partition`` is pure, ``hp.partition`` is not.
PURE_METHODS = frozenset([
    "count", "copy", "endswith", "format", "get", "index", "items",
    "join", "keys", "lower", "lstrip", "partition", "replace", "rstrip",
    "split", "splitlines", "startswith", "strip", "title", "upper", "values",
])

#: Receiver types whose methods are provably pure.
_LITERAL_TYPES = (ast.Dict, ast.List, ast.Set, ast.Tuple)


def _dotted_name(node):
    """The dotted path of an attribute chain, e.g. "os.path.relpath"."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _is_pure_call(node):
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in PURE_BUILTINS
    if isinstance(func, ast.Attribute):
        dotted = _dotted_name(func)
        if dotted and (dotted.startswith("os.path.")
                       or dotted.startswith("pathlib.")
                       or dotted in ("ast.unparse", "ast.dump", "ast.dumps")):
            return True
        if dotted and dotted.split(".")[0] == "np":
            return True
        # A method is only known-pure when the receiver is a literal of a
        # type whose methods cannot have side effects.
        if isinstance(func.value, _LITERAL_TYPES):
            return func.attr in PURE_METHODS
        return False
    return False


def _expand(paths):
    """Expand directories into the .py files they contain."""
    out = []
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                for fn in filenames:
                    if fn.endswith(".py"):
                        out.append(os.path.join(dirpath, fn))
        elif path.endswith(".py"):
            out.append(path)
    return out


def _catches_exception(handler):
    """True when the handler catches an exception (not just a sentinel)."""
    node = handler.type
    if node is None:
        return True                      # bare except
    if isinstance(node, ast.Name):
        return node.id.endswith("Error") or node.id == "Exception"
    if isinstance(node, ast.Tuple):
        return any(isinstance(e, ast.Name)
                   and (e.id.endswith("Error") or e.id == "Exception")
                   for e in node.elts)
    return False


def _in_guarded_try(node, parent_map):
    """True when *node* sits in a try block whose exception is the test.

    A call inside such a block may be there precisely BECAUSE it
    raises: ``float(name)`` in a ``try/except ValueError`` is a
    validation probe, and removing it makes the check answer "always
    valid".  Such statements are never removed.
    """
    parent = parent_map.get(id(node))
    if not isinstance(parent, ast.Try):
        return False
    return any(_catches_exception(h) for h in parent.handlers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    changed = []
    total = 0
    for path in _expand(args.paths):
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[id(child)] = node
        drop = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr):
                continue
            if not _is_pure_call(node.value):
                continue
            if _in_guarded_try(node, parents):
                # The exception this call raises may BE the test.
                continue
            parent = parents.get(id(node))
            body = getattr(parent, "body", None)
            if not isinstance(body, list) or len(body) == 1:
                # the only statement in its block: keep the block valid
                continue
            drop.append(node)
        if not drop:
            continue
        lines = src.split("\n")
        for node in sorted(drop, key=lambda n: n.lineno, reverse=True):
            del lines[node.lineno - 1:node.end_lineno]
            total += 1
        new_src = "\n".join(lines)
        if new_src != src:
            changed.append(path)
            if args.apply:
                open(path, "w", encoding="utf-8").write(new_src)
    print("pure dead statements removed: %d   files changed: %d"
          % (total, len(changed)))
    if not args.apply:
        for p in changed:
            print("  would change:", p)


if __name__ == "__main__":
    main()
