"""Audit a commit for statements it removed.

The lint cleanup of 2026-10-19 removed hundreds of statements across the
tree.  Two classes turned out to be load-bearing:

* a call whose RESULT is unused but whose EXCEPTION is the test
  (``float(name)`` in a ``try:`` whose ``except`` returns True), and
* a method call on an unknown receiver (``hp.partition(ops)``,
  ``p.join(timeout=1)``) whose name happened to be on a "pure methods"
  list.

Both were caught by the test suite, not by inspection.  This tool makes
the inspection mechanical: it lists the statements a commit removed, so
each one can be classified as dead or load-bearing.

Usage::

    python3 scripts/lint/audit_commit_removals.py <rev> [<rev>...]
    python3 scripts/lint/audit_commit_removals.py --range 5     # last 5 commits

The comparison is structural (AST), not textual, so a quote-style change
does not show up as a removal.
"""
import argparse
import ast
import subprocess

COMPOUND = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
            ast.If, ast.For, ast.While, ast.With, ast.Try, ast.Module)


class _FoldFStrings(ast.NodeTransformer):
    """Fold an f-string with no placeholders into a plain constant.

    ``f"text"`` and ``"text"`` are the same statement; without this the
    tool would report every f-string prefix removal as a change.
    """

    def visit_JoinedStr(self, node):
        if not node.values:
            # f"" == "" — fold it, or every empty f-string looks removed.
            return ast.copy_location(ast.Constant(value=""), node)
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                return node
        return ast.copy_location(ast.Constant(value="".join(parts)), node)


def _statements(tree):
    """(structural key, source text) for statements without a nested body."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, COMPOUND) or not isinstance(node, ast.stmt):
            continue
        try:
            key = ast.dump(node, annotate_fields=False)
        except Exception:
            continue
        try:
            text = ast.unparse(node)
        except Exception:
            text = "<unparseable>"
        out.append((key, text))
    return out


def _normalise(text):
    """Structural key with f-strings folded."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    return ast.dump(tree, annotate_fields=False)


def _git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True,
                          text=True).stdout


def _changed_files(base, head):
    out = _git("diff", "--name-only", base, head)
    return [p for p in out.split() if p.endswith(".py")]


def _file_at(rev, path):
    return _git("show", "%s:%s" % (rev, path))


def _call_key(node):
    """Structural key of a call, with f-strings folded.

    The folding matters: ``ValueError(f"x")`` and ``ValueError("x")``
    are the same statement, and the F541 cleanup turns one into the
    other.  Without folding, every f-string prefix removal would be
    reported as a dropped call.
    """
    try:
        tree = ast.parse(ast.unparse(node))
    except Exception:
        try:
            return ast.dump(node, annotate_fields=False)
        except Exception:
            return None
    folded = _FoldFStrings().visit(tree)
    try:
        return ast.dump(folded, annotate_fields=False)
    except Exception:
        return None


def _calls(tree):
    """Structural keys of every call in the tree."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            key = _call_key(node)
            if key:
                out.add(key)
    return out


def audit(base, head):
    """Return (removed, dropped_calls) for *head* relative to *base*.

    ``removed`` is every statement that disappeared.  ``dropped_calls``
    is the subset that matters: a removed statement whose CALL is not
    present anywhere in the new file.  That call may have had a side
    effect (an exception raised on purpose, a process joined, an IR
    instruction emitted) -- those are the removals that broke code.
    """
    removed = []
    dropped_calls = []
    for path in _changed_files(base, head):
        old_src = _file_at(base, path)
        new_src = _file_at(head, path)
        if not old_src or not new_src:
            continue
        try:
            old_tree = ast.parse(old_src)
            new_tree = ast.parse(new_src)
        except SyntaxError:
            continue
        new_keys = set()
        for key, _text in _statements(new_tree):
            new_keys.add(key)
            norm = _normalise(_text)
            if norm:
                new_keys.add(norm)
        new_calls = _calls(new_tree)
        for key, text in _statements(old_tree):
            if key in new_keys:
                continue
            norm = _normalise(text)
            if norm and norm in new_keys:
                continue
            if text.startswith("import ") or text.startswith("from "):
                continue
            removed.append((path, text))
            try:
                stmt = ast.parse(text).body[0]
            except SyntaxError:
                continue
            for call in ast.walk(stmt):
                if isinstance(call, ast.Call):
                    ckey = _call_key(call)
                    if ckey is None:
                        continue
                    if ckey not in new_calls:
                        dropped_calls.append((path, text, ast.unparse(call)))
    return removed, dropped_calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("revs", nargs="*")
    ap.add_argument("--range", type=int, default=0,
                    help="audit the last N commits")
    ap.add_argument("--calls-only", action="store_true",
                    help="only list removals that dropped a call")
    args = ap.parse_args()

    pairs = []
    if args.range:
        log = _git("log", "--format=%H", "-n", str(args.range + 1)).split()
        for i in range(len(log) - 1):
            pairs.append((log[i + 1], log[i]))
    for rev in args.revs:
        base = _git("rev-parse", rev + "^").strip()
        pairs.append((base, _git("rev-parse", rev).strip()))

    if not pairs:
        ap.error("give one or more revisions, or --range N")

    total = 0
    dropped_total = 0
    for base, head in pairs:
        removed, dropped = audit(base, head)
        short = head[:8]
        print("=== %s..%s: %d statement(s) removed, %d of them dropped a call"
              % (base[:8], short, len(removed), len(dropped)))
        for path, text, call in dropped:
            print("  DROPPED CALL  %-40s %s" % (path, call[:80]))
        if not args.calls_only:
            for path, text in removed:
                print("  %-44s %s" % (path, text.replace("\n", " ")[:96]))
        total += len(removed)
        dropped_total += len(dropped)
    print("total: %d statement(s) removed, %d dropped a call"
          % (total, dropped_total))


if __name__ == "__main__":
    main()
