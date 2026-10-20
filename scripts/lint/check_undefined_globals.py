"""Find names that a module references but never binds.

The lint gate ignores F403/F405 (the package imports its own modules with
``from .mod import *``), and the consequence of that is that a name
arriving through a star import is not existence-checked: a typo or a
removed definition stays invisible until that code path runs.

The static approximation is not good enough, so this checks the real
thing at runtime: for every module in the live tree, every name its code
objects LOAD from the global scope must resolve -- to a binding in the
module's own namespace, to a builtin, to a name the module declares
``global`` and assigns, or to an optional dependency imported inside a
``try: ... except ImportError`` (the guard makes those safe).

That is what catches the case the static check misses:
``_platform_src_migrate`` and ``tempfile_name`` were both referenced but
never defined anywhere in the tree.

Run it directly::

    python3 scripts/lint/check_undefined_globals.py [package ...]

Exits 0 when every name resolves, 1 otherwise (and prints the
offenders).
"""
import argparse
import ast
import builtins
import dis
import importlib
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

#: Packages that make up the live tree.
DEFAULT_PACKAGES = ("obfuscator", "scripts", "irgen", "vm", "llvmgen",
                    "encrypt")


def _module_names(package):
    """Every importable module name under *package*."""
    root = os.path.join(REPO_ROOT, package)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", "tests", "test_data",
                                    "fixtures", "node_modules")]
        rel = os.path.relpath(dirpath, REPO_ROOT)
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            if fn == "__init__.py":
                out.append(rel.replace(os.sep, "."))
            else:
                out.append("%s.%s" % (rel.replace(os.sep, "."), fn[:-3]))
    return sorted(set(out))


def _module_ast(module):
    """The module's source AST, or None."""
    path = getattr(module, "__file__", None)
    if not path:
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return ast.parse(fh.read())
    except Exception:
        return None


def _declared_globals(tree):
    """Names a function declares ``global`` (and therefore binds)."""
    out = set()
    if tree is None:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            out.update(node.names)
    return out


def _guarded_optional_names(tree):
    """Names bound by an import inside a ``try: ... except ImportError``.

    An optional dependency (``gmpy2``, ``pyopencl``) is bound only when
    it is installed; the code that uses it is guarded by the flag the
    same ``try`` sets.  Such a name is not undefined -- it is
    conditional, and the guard is what makes it safe.
    """
    guarded = set()
    if tree is None:
        return guarded

    def catches_import_error(handler):
        node = handler.type
        if isinstance(node, ast.Name):
            return node.id == "ImportError"
        if isinstance(node, ast.Tuple):
            return any(isinstance(e, ast.Name) and e.id == "ImportError"
                       for e in node.elts)
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not any(catches_import_error(h) for h in node.handlers):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    guarded.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    guarded.add(alias.asname or alias.name)
    return guarded


_ALLOWED_CACHE = {}


def _allowed_for_file(path):
    """Names that count as bound in the module at *path*."""
    if path not in _ALLOWED_CACHE:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                tree = ast.parse(fh.read())
        except Exception:
            tree = None
        _ALLOWED_CACHE[path] = (_declared_globals(tree)
                                | _guarded_optional_names(tree))
    return _ALLOWED_CACHE[path]


def _allowed_for_namespace(namespace):
    """Allowed names of the module that owns *namespace*."""
    path = namespace.get("__file__")
    if not path:
        return frozenset()
    return _allowed_for_file(path)


def _problems_for(module):
    """Undefined-global problems in *module*."""
    problems = []
    seen = set()

    def check_code(code, namespace, origin):
        allowed = _allowed_for_namespace(namespace)
        if id(code) in seen:
            return
        seen.add(id(code))
        for instr in dis.get_instructions(code):
            # Only a READ of an unbound name is a defect: a STORE_GLOBAL
            # creates the binding, so it is not undefined.
            if instr.opname != "LOAD_GLOBAL":
                continue
            name = instr.argval
            if name.startswith("__"):
                continue
            if name in namespace or hasattr(builtins, name):
                continue
            if name in allowed:
                continue
            problems.append("%s: undefined global %r" % (origin, name))
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                check_code(const, namespace, origin)

    own = module.__name__
    # Nested classes and functions are not in vars(module): their code
    # is still ours, and it is still ours to check.  (A nested
    # ConsoleArgumentParser referenced an undefined _console this way.)
    nested = []
    for value in list(vars(module).values()):
        if not isinstance(value, types.FunctionType):
            continue
        # Only code DEFINED in this tree: an imported decorator such as
        # dataclasses.dataclass carries the internals of ITS module.
        owner = getattr(value, "__module__", own)
        if owner not in (own, None) and not owner.startswith(own + "."):
            continue
        for const in value.__code__.co_consts:
            if isinstance(const, types.CodeType):
                nested.append((const, value.__globals__))
    for code, namespace in nested:
        check_code(code, namespace, "%s.<nested>" % own)

    for name, value in list(vars(module).items()):
        if isinstance(value, types.ModuleType):
            continue
        # Only code DEFINED in this tree is checked: an imported stdlib
        # class may reference names that only exist on another platform
        # (e.g. multiprocessing's _winapi on Windows).
        owner = getattr(value, "__module__", own)
        if owner not in (own, None) and not owner.startswith(own + "."):
            continue
        func = value
        if isinstance(func, types.FunctionType):
            code = getattr(func, "__code__", None)
            if code is not None:
                check_code(code, getattr(func, "__globals__", {}),
                           "%s.%s" % (own, name))
        elif isinstance(func, type):
            for attr_name, attr in list(vars(func).items()):
                inner = attr
                if isinstance(inner, (staticmethod, classmethod)):
                    inner = getattr(inner, "__func__", None)
                inner_code = getattr(inner, "__code__", None)
                if inner_code is not None:
                    check_code(inner_code, getattr(inner, "__globals__", {}),
                               "%s.%s.%s" % (own, name, attr_name))
    return problems


def check(packages):
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    problems = []
    import_errors = []
    # Several modules run argparse at import time (they are CLI wrappers).
    # Give them an empty argv so they do not consume this script's, and
    # treat their SystemExit as "not importable as a library".
    saved_argv = list(sys.argv)
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    sys.argv = [saved_argv[0]]
    # A CLI wrapper module may print its usage while being imported.
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")
    try:
        for package in packages:
            for name in _module_names(package):
                try:
                    module = importlib.import_module(name)
                except SystemExit:
                    continue
                except Exception as exc:
                    if isinstance(exc, ImportError) and "not a package" in str(exc):
                        # A standalone program in a directory that is not a
                        # package: it is a script, not a library module.
                        continue
                    import_errors.append("%s: %s: %s"
                                        % (name, type(exc).__name__, exc))
                    continue
                problems.extend(_problems_for(module))
    finally:
        sys.argv = saved_argv
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
    return problems, import_errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("packages", nargs="*", default=list(DEFAULT_PACKAGES))
    args = ap.parse_args()
    packages = tuple(args.packages) or DEFAULT_PACKAGES
    problems, import_errors = check(packages)
    for line in import_errors:
        print("IMPORT ERROR  " + line)
    for line in problems:
        print("UNDEFINED     " + line)
    print("checked %d package(s): %d undefined global(s), %d import error(s)"
          % (len(packages), len(problems), len(import_errors)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
