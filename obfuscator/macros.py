"""User macros + trial parsing (Phase-4 policy/product).

Build-time macros (expanded by :func:`apply_macros` without executing):
  - ``IS_OBFUSCATED`` -> ``True``
  - ``GET_HWID()`` -> string literal of ``hwid``

Runtime macros (left for runtime; implemented by :func:`emit_runtime_helpers`):
  - ``SELF_DELETE()``, ``SECURE_DELETE(...)``, ``CRASH()``,
    ``DETECT_FILE_TYPE(path)``
"""

import ast
import io
import re
import tokenize

MACROS = {
    "IS_OBFUSCATED",
    "GET_HWID",
    "SELF_DELETE",
    "SECURE_DELETE",
    "SELF_CORRUPT",
    "CRASH",
    "DETECT_FILE_TYPE",
    "__all__",
}

_MACRO_NAMES = MACROS - {"__all__"}


def collect_macros(source: str) -> set[str]:
    """AST scan returning which macros appear as Names/Calls/comparisons.

    Never executes anything.
    """
    found: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in _MACRO_NAMES:
            found.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in _MACRO_NAMES:
            # e.g. module.GET_HWID — still counts as a reference.
            found.add(node.attr)
    return found


def _replace_is_obfuscated_tokens(source: str) -> str:
    """Replace bare IS_OBFUSCATED Name tokens with True (string-level)."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except Exception:
        return source
    out = []
    for tok in toks:
        if tok.type == tokenize.NAME and tok.string == "IS_OBFUSCATED":
            out.append((tokenize.NAME, "True"))
        else:
            out.append((tok.type, tok.string))
    try:
        return tokenize.untokenize(out)
    except Exception:
        return source


_GET_HWID_RE = re.compile(r"(?<![A-Za-z0-9_.])GET_HWID\s*\(\s*\)")


def apply_macros(source: str, *, hwid: str = "", trial: str = "") -> str:
    """String-level transform for build-time macros.

    - bare ``IS_OBFUSCATED`` Name -> ``True``
    - ``GET_HWID()`` call -> string literal of ``hwid``
    - other macros (SELF_DELETE, SECURE_DELETE, SELF_CORRUPT, CRASH,
      DETECT_FILE_TYPE) are runtime-only and left untouched.

    ``trial`` is accepted for API symmetry but does not rewrite source
    (trial enforcement is a runtime concern).
    """
    _ = trial  # reserved; runtime-enforced, no source rewrite.
    try:
        ast.parse(source)
    except SyntaxError:
        return source
    out = _replace_is_obfuscated_tokens(source)
    out = _GET_HWID_RE.sub(repr(hwid), out)
    return out


_UNIT_SECONDS = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "w": 7 * 86400,
    "week": 7 * 86400,
    "weeks": 7 * 86400,
    "mo": 30 * 86400,
    "month": 30 * 86400,
    "months": 30 * 86400,
}

_TRIAL_RE = re.compile(r"(\d+)\s*([A-Za-z]+)")


def parse_trial(spec: str | None) -> int | None:
    """Parse '1s/1m/1h/1d/1w/1mo' combos into total seconds.

    Examples: '90s', '1w2d', '1mo1hr'. Returns None for ''/None.
    Raises ValueError on garbage.

    Note: 'm' = minute (not month); month is 'mo'.
    """
    if spec is None:
        return None
    if not isinstance(spec, str):
        raise ValueError(f"bad trial spec: {spec!r}")
    s = spec.strip().lower().replace(" ", "")
    if s == "":
        return None
    matches = _TRIAL_RE.findall(s)
    if not matches:
        raise ValueError(f"bad trial spec: {spec!r}")
    # Ensure the whole string is consumed by number+unit pairs.
    consumed = "".join(n + u for n, u in matches)
    if consumed != s:
        raise ValueError(f"bad trial spec: {spec!r}")
    total = 0
    for num, unit in matches:
        if unit not in _UNIT_SECONDS:
            raise ValueError(f"bad trial unit {unit!r} in {spec!r}")
        total += int(num) * _UNIT_SECONDS[unit]
    if total <= 0:
        raise ValueError(f"bad trial spec: {spec!r}")
    return total


def emit_runtime_helpers() -> str:
    """Return Python source with runtime macro implementations. Must compile()."""
    src = '''import os as _os
import sys as _sys


def SELF_DELETE():
    """Best-effort unlink of sys.argv[0]. Returns True on success."""
    try:
        _p = _sys.argv[0] if _sys.argv else None
        if not _p:
            return False
        _os.unlink(_p)
        return True
    except Exception:
        return False


def SECURE_DELETE(path, passes=3):
    """Overwrite file with random/zero bytes then unlink. Returns True on success."""
    import secrets as _secrets
    try:
        _passes = int(passes) if passes is not None else 3
    except Exception:
        _passes = 3
    if _passes < 1:
        _passes = 1
    try:
        _size = _os.path.getsize(path)
    except Exception:
        return False
    try:
        with open(path, "r+b") as _f:
            for _i in range(_passes):
                _f.seek(0)
                _chunk = 65536
                _left = _size
                while _left > 0:
                    _n = _chunk if _left > _chunk else _left
                    if _i == _passes - 1:
                        _f.write(b"\\x00" * _n)
                    else:
                        _f.write(_secrets.token_bytes(_n))
                    _left -= _n
                _f.flush()
                try:
                    _os.fsync(_f.fileno())
                except Exception:
                    pass
        _os.unlink(path)
        return True
    except Exception:
        try:
            _os.unlink(path)
            return True
        except Exception:
            return False


def SELF_CORRUPT(path=None, passes=1):
    """On-tamper self-corruption (V10 adopt, opt-in).

    Overwrites the artifact with SAME-LENGTH garbage (so size-based
    tripwires don't notice) then unlinks it. Runs synchronously when
    called; the DETACHED-child pattern (wait-for-parent-exit, then
    corrupt) lives in the loader template — this helper is the payload
    half, callable from a tamper branch as ``SELF_CORRUPT()``.
    Defaults to sys.argv[0]; returns True on success.
    """
    import secrets as _sc
    try:
        _p = path or (_sys.argv[0] if _sys.argv else None)
        if not _p:
            return False
        _size = _os.path.getsize(_p)
    except Exception:
        return False
    try:
        with open(_p, "r+b") as _f:
            _f.seek(0)
            _left = _size
            while _left > 0:
                _n = 65536 if _left > 65536 else _left
                _f.write(_sc.token_bytes(_n))
                _left -= _n
            _f.flush()
            try:
                _os.fsync(_f.fileno())
            except Exception:
                pass
        _os.unlink(_p)
        return True
    except Exception:
        return False


def CRASH():
    """Terminate immediately."""
    _os._exit(1)


def DETECT_FILE_TYPE(path):
    """Magic-byte classifier: binary_executable/python_script/shell_script/text_file/unknown."""
    try:
        with open(path, "rb") as _f:
            _head = _f.read(4096)
    except Exception:
        return "unknown"
    if _head[:4] == b"\\x7fELF" or _head[:2] == b"MZ":
        return "binary_executable"
    # Mach-O / fat binary magics
    if _head[:4] in (b"\\xfe\\xed\\xfa\\xce", b"\\xfe\\xed\\xfa\\xcf", b"\\xce\\xfa\\xed\\xfe", b"\\xcf\\xfa\\xed\\xfe", b"\\xca\\xfe\\xba\\xbe"):
        return "binary_executable"
    _text = None
    try:
        _text = _head.decode("utf-8", errors="strict")
    except Exception:
        _text = None
    if _text is not None:
        _lines = _text.splitlines()
        _first = _lines[0] if _lines else ""
        if _first.startswith("#!"):
            _low = _first.lower()
            if "python" in _low:
                return "python_script"
            if "sh" in _low or "bash" in _low or "zsh" in _low:
                return "shell_script"
        # Extension-agnostic content sniffing
        _stripped = _text.lstrip()
        if _stripped.startswith("import ") or _stripped.startswith("from ") or "def " in _text or "print(" in _text:
            # Only claim python if it looks like code, else generic text
            try:
                compile(_text, "<detect>", "exec")
                return "python_script"
            except Exception:
                pass
        # printable ASCII/UTF-8 without NULs -> text
        if b"\\x00" not in _head:
            return "text_file"
        return "unknown"
    if b"\\x00" in _head:
        return "unknown"
    return "text_file"
'''
    compile(src, "<nx_macro_helpers>", "exec")
    return src
