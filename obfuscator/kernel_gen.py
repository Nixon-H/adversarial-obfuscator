"""Native lowering kernel generator (V10 Phase 2).

Generates a Cython ``.pyx`` kernel module implementing the SAME call shapes
as :mod:`obfuscator.lowering_shim`, but compiled to machine code with
per-build renamed symbols. The lowered output's ``from lowering_shim
import ...`` line is swapped for the native module import — the call
sites (``_nxk_len(x)``) keep working because the native module exposes
aliases with IDENTICAL names; only the underlying *implementation*
symbols are renamed per build.

Design (matches lowering_DESIGN.md Phase 2):
- One ``def`` per lowered op, typed ``(*a, **k)`` passthrough to the real
  builtin (Cython compiles these to C; the obfuscation value is that the
  artifact contains no Python-level ``len(...)``/``print(...)`` call sites
  and the helper symbols are per-build unique).
- Per-build uniqueness: module name (``_nxk_<12hex>``) + an internal
  per-op salt prefix baked into a dispatch table, both derived from
  SHA-256(build_seed). Two builds of the same source share no stable
  kernel symbol names.
- Fusion dispatch: ``_nxk_fuse(*thunks)`` compiled natively (single
  dispatch, V10 fusion parity).
- Graceful degradation: Cython/setuptools/compiler missing ->
  (None, reason); never raises.

Public API:
  build_kernel(build_dir, seed, ops=None) -> (pyx_path, mod_name, op_map)
    Write the .pyx + return the module name and {public_name: impl_symbol}.
  cythonize_kernel(pyx_path, out_dir) -> (so_path | None, message)
    Compile via Cython.Build.cythonize + setuptools (isolated temp copy).
  emit_native_import(mod_name) -> str
    Import line the lowered output uses instead of the shim import.
"""

from __future__ import annotations

import glob
import hashlib
import os
import shutil as _shutil
import subprocess
import sys
import tempfile

# Ops the native kernel implements (must stay in sync with lowering_shim).
# Dotted ops (str.join) become method-style helpers (sep, it).
# 140 callable ops + the "fuse" dispatch = 141 total entries.
NATIVE_OPS: tuple[str, ...] = (
    # io
    "print", "input", "open",
    # scalar (bare builtins: original entries first, order untouched)
    "int", "float", "str", "bool", "chr", "ord", "hex", "oct", "bin",
    "abs", "round", "len",
    # scalar numeric methods
    "int.bit_length", "int.to_bytes",
    "float.hex", "float.as_integer_ratio",
    "complex.conjugate",
    # string (method-style)
    "str.join", "str.split", "str.format", "str.encode", "str.decode",
    "str.upper", "str.lower",
    "str.strip", "str.lstrip", "str.rstrip", "str.replace",
    "str.find", "str.rfind", "str.index", "str.count",
    "str.startswith", "str.endswith", "str.partition", "str.rpartition",
    "str.splitlines", "str.zfill", "str.ljust", "str.rjust", "str.center",
    "str.swapcase",
    "str.isalnum", "str.isspace", "str.maketrans",
    "str.removeprefix", "str.removesuffix",
    # container
    "list", "tuple", "dict", "set", "frozenset", "sorted", "reversed",
    "enumerate", "zip",
    # list methods
    "list.append", "list.extend", "list.insert", "list.remove",
    "list.pop", "list.clear", "list.index", "list.count", "list.sort",
    "list.reverse", "list.copy",
    # dict methods
    "dict.get", "dict.keys", "dict.values", "dict.items", "dict.pop",
    "dict.popitem", "dict.setdefault", "dict.update", "dict.clear",
    "dict.copy", "dict.fromkeys",
    # set methods
    "set.add", "set.discard", "set.remove", "set.pop", "set.clear",
    "set.union", "set.intersection", "set.difference",
    "set.symmetric_difference", "set.issubset", "set.issuperset",
    "set.copy",
    # tuple methods
    "tuple.count", "tuple.index",
    # bytes methods
    "bytes.decode", "bytes.hex", "bytes.fromhex",
    # service
    "getattr", "setattr", "hasattr", "isinstance", "issubclass",
    "callable", "id", "hash",
    # service extra
    "vars", "dir", "globals", "locals", "compile", "eval", "exec",
    "memoryview",
    # protocol
    "iter", "next", "repr", "bytes",
    # range family
    "range", "aiter", "anext", "ascii", "format", "slice",
    # function
    "map", "filter", "any", "all", "sum", "min", "max",
    # function extra
    "pow", "divmod", "complex",
    # import
    "__import__", "breakpoint", "help", "copyright", "credits",
    "license",
    # fusion
    "fuse",
)

_PYX_PREAMBLE = "# cython: language_level=3\n# cython: boundscheck=False\n# cython: wraparound=False\n"


def _token(op: str) -> str:
    return "_nxk_" + op.replace(".", "_")


def derive_symbols(seed: bytes, ops=None) -> tuple[str, dict[str, str]]:
    """Derive (module_name, {public_token: impl_symbol}) from seed.

    Deterministic: same seed -> same symbols (needed for reproducible
    tests); random seed per build -> per-build unique kernel (V10 parity).
    """
    ops = tuple(ops) if ops is not None else NATIVE_OPS
    mod_name = "_nxk_" + hashlib.sha256(b"mod:" + bytes(seed)).hexdigest()[:12]
    op_map: dict[str, str] = {}
    for op in ops:
        impl = "_k_" + hashlib.sha256(b"op:" + bytes(seed) + op.encode()).hexdigest()[:12]
        op_map[_token(op)] = impl
    return mod_name, op_map


def _impl_body(op: str, impl: str, fast: bool = False) -> str:
    """Cython body for one op: thin typed passthrough to the real builtin.

    When fast=True and the op has a hand-optimized body in
    obfuscator.kernel_fast, emit that instead (same impl symbol, same
    public token scheme). The kernel_fast import is lazy so a missing
    module never breaks the default path.
    """
    if fast:
        try:
            from obfuscator.kernel_fast import fast_body as _fb
            _body = _fb(op, impl)
            if _body is not None:
                return _body
        except Exception:
            pass
    if "." in op:
        recv, meth = op.split(".", 1)
        if op == "str.join":
            return f"def {impl}(sep, it):\n    return sep.join(it)\n"
        if op in ("str.maketrans", "dict.fromkeys", "bytes.fromhex",
                  "int.from_bytes"):
            return (
                f"def {impl}(*a, **k):\n"
                f"    import builtins as _bi\n"
                f"    return getattr(_bi.{recv}, {meth!r})(*a, **k)\n"
            )
        return f"def {impl}(s, *a, **k):\n    return s.{meth}(*a, **k)\n"
    if op == "fuse":
        return (
            f"def {impl}(*thunks):\n"
            "    _out = None\n"
            "    for _t in thunks:\n"
            "        _out = _t()\n"
            "    return _out\n"
        )
    if op == "__import__":
        return (
            f"def {impl}(*a, **k):\n"
            "    import builtins as _bi\n"
            "    return _bi.__import__(*a, **k)\n"
        )
    return f"def {impl}(*a, **k):\n    import builtins as _bi\n    return _bi.{op}(*a, **k)\n"


def render_pyx(seed: bytes, ops=None, fast=None) -> tuple[str, str, dict[str, str]]:
    """Render kernel source. Returns (pyx_text, mod_name, op_map).

    fast: None (default) -> byte-identical legacy output; any non-None
    set/list/tuple of op names -> those ops use the hand-optimized
    kernel_fast bodies (unknown names ignored). Public tokens and impl
    symbols are unchanged either way.
    """
    ops = tuple(ops) if ops is not None else NATIVE_OPS
    fast_set = set(fast) if fast is not None else set()
    mod_name, op_map = derive_symbols(seed, ops)
    parts = [_PYX_PREAMBLE,
             f'"""Native lowering kernel {mod_name} (per-build symbols)."""\n']
    if fast_set:
        try:
            from obfuscator.kernel_fast import _FAST_CIMPORTS as _fc
            parts.append(_fc)
        except Exception:
            pass
        parts.append("_nxk_fast_missing = object()\n")
    for op in ops:
        parts.append(_impl_body(op, op_map[_token(op)],
                               fast=(op in fast_set)))
    # Public aliases: IDENTICAL names to the shim so lowered call sites
    # keep working with a swapped import line.
    parts.append("\n# Public aliases (stable call shapes, swapped import)\n")
    for op in ops:
        parts.append(f"{_token(op)} = {op_map[_token(op)]}\n")
    return "".join(parts), mod_name, op_map


def build_kernel(build_dir: str, seed: bytes, ops=None, fast=None) -> tuple[str, str, dict[str, str]]:
    """Write ``<mod_name>.pyx`` into build_dir. Returns (pyx_path, mod, map).

    fast is passed through to render_pyx (None = legacy passthrough).
    """
    text, mod_name, op_map = render_pyx(seed, ops, fast=fast)
    os.makedirs(build_dir, exist_ok=True)
    pyx_path = os.path.join(build_dir, mod_name + ".pyx")
    with open(pyx_path, "w", encoding="utf-8") as f:
        f.write(text)
    return pyx_path, mod_name, op_map


def emit_native_import(mod_name: str, tokens) -> str:
    """Import line binding lowered call-site names from the native kernel."""
    names = sorted(set(tokens))
    if not names:
        return ""
    return f"from {mod_name} import " + ", ".join(names) + "\n"


def cythonize_kernel(pyx_path: str, out_dir: str) -> tuple[str | None, str]:
    """Compile the kernel .pyx to a native extension. Never raises."""
    if not os.path.isfile(pyx_path):
        return None, f"kernel skip: missing {pyx_path}"
    try:
        import Cython  # noqa: F401
    except Exception as e:
        return None, f"kernel skip: Cython not installed ({e})"
    try:
        import setuptools  # noqa: F401
    except Exception as e:
        return None, f"kernel skip: setuptools not installed ({e})"
    if _shutil.which("gcc") is None and _shutil.which("cc") is None:
        return None, "kernel skip: no C compiler found"
    tmp = tempfile.mkdtemp(prefix="nxk_")
    try:
        base = os.path.basename(pyx_path)
        _shutil.copy2(pyx_path, os.path.join(tmp, base))
        mod = os.path.splitext(base)[0]
        with open(os.path.join(tmp, "setup.py"), "w", encoding="utf-8") as f:
            f.write(
                "from setuptools import setup\n"
                "from Cython.Build import cythonize\n"
                f"setup(name={mod!r}, "
                f"ext_modules=cythonize({base!r}, "
                "compiler_directives={'language_level': 3}))\n"
            )
        res = subprocess.run(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=tmp, capture_output=True, text=True, timeout=600,
        )
        if res.returncode != 0:
            tail = (res.stderr or res.stdout or "")[-2000:]
            return None, f"kernel skip: cython build failed ({tail})"
        cands = sorted(
            glob.glob(os.path.join(tmp, mod + "*.so"))
            + glob.glob(os.path.join(tmp, mod + "*.pyd"))
        )
        if not cands:
            return None, "kernel skip: no extension artifact produced"
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, os.path.basename(cands[0]))
        _shutil.copy2(cands[0], dest)
        return dest, f"kernel built: {dest}"
    except Exception as e:
        return None, f"kernel skip: {e}"
    finally:
        _shutil.rmtree(tmp, ignore_errors=True)
