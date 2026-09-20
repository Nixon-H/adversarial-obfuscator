"""pyinstaller_spec.py — best-effort PyInstaller .spec generation.

collect_hidden_imports(source): AST import scan (Import + ImportFrom,
top-level package only), stdlib-filtered via sys.stdlib_module_names when
available else a small hardcoded set.

generate_spec(...): renders a valid one-file .spec text.
"""

from __future__ import annotations

import ast as _ast
import sys as _sys

# Fallback stdlib set used only when sys.stdlib_module_names is unavailable
# (Python < 3.10). Kept intentionally small.
_FALLBACK_STDLIB = frozenset(
    {
        "os", "sys", "re", "json", "ast", "io", "math", "time", "base64",
        "hashlib", "zlib", "struct", "argparse", "subprocess", "tempfile",
        "shutil", "platform", "threading", "multiprocessing", "collections",
        "itertools", "functools", "typing", "pathlib", "logging", "unittest",
        "http", "urllib", "email", "xml", "csv", "sqlite3", "inspect",
        "importlib", "pkgutil", "traceback", "warnings", "contextlib",
        "dataclasses", "enum", "abc", "copy", "pickle", "marshal", "ctypes",
        "socket", "ssl", "select", "signal", "atexit", "gc", "dis",
        "tokenize", "codecs", "string", "random", "secrets", "uuid",
        "datetime", "calendar", "locale", "gettext", "bz2", "lzma",
        "zipfile", "tarfile", "gzip", "builtins",
    }
)


def _stdlib_names() -> frozenset:
    names = getattr(_sys, "stdlib_module_names", None)
    if names:
        return frozenset(names)
    return _FALLBACK_STDLIB


def collect_hidden_imports(source: str) -> list[str]:
    """Scan *source* for imports; return sorted third-party top-level names."""
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return []
    stdlib = _stdlib_names()
    found: set[str] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                top = (alias.name or "").split(".")[0].strip()
                if top:
                    found.add(top)
        elif isinstance(node, _ast.ImportFrom):
            if node.level:  # relative import — local package, skip
                continue
            if node.module:
                top = node.module.split(".")[0].strip()
                if top:
                    found.add(top)
    return sorted(n for n in found if n and n not in stdlib)


def generate_spec(
    name: str,
    entry: str,
    hiddenimports: list[str] | None = None,
    datas: list[tuple[str, str]] | None = None,
    onefile: bool = True,
) -> str:
    """Render a valid PyInstaller .spec text (best-effort)."""
    his = list(hiddenimports or [])
    ds = list(datas or [])
    hi_repr = "[" + ", ".join(repr(h) for h in his) + "]"
    datas_repr = "[" + ", ".join(f"({s!r}, {d!r})" for s, d in ds) + "]"
    exe_kwargs = "console=True"
    lines = [
        "# -*- mode: python ; coding: utf-8 -*-",
        f"# Auto-generated PyInstaller spec for {name} (best-effort).",
        "",
        "block_cipher = None",
        "",
        "a = Analysis(",
        f"    [{entry!r}],",
        "    pathex=[],",
        "    binaries=[],",
        f"    datas={datas_repr},",
        f"    hiddenimports={hi_repr},",
        "    hookspath=[],",
        "    runtime_hooks=[],",
        "    excludes=[],",
        "    cipher=block_cipher,",
        "    noarchive=False,",
        ")",
        "",
        "pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)",
        "",
    ]
    if onefile:
        lines += [
            f"exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name={name!r}, {exe_kwargs})",
            "",
        ]
    else:
        lines += [
            f"exe = EXE(pyz, a.scripts, name={name!r}, {exe_kwargs})",
            f"coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name={name!r})",
            "",
        ]
    return "\n".join(lines)
