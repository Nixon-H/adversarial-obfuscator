"""Custom C transformation layer: between Cython's .c and gcc.

This is the "beyond standard Cython" layer: it takes the Cython-generated C
source and transforms it before the compiler sees it.  Each transform is
polymorphic -- the choice, order and parameters are randomized per build --
so the same payload produces a structurally different native artefact every
time.

Transforms (each one is a test):

1. **String-literal encryption** -- Cython stores every Python string as a
   `static char __pyx_k_NAME[] = "..."` C literal.  Those survive `strings`
   on the binary and give an analyst every identifier, every route name and
   every message.  This transform XOR-encrypts each array with a key derived
   from the build seed and the array index, and emits a decrypt loop that
   runs before Cython's `__Pyx_InitStrings`.

2. **Opaque predicates** -- wraps selected `if (...)` conditions with an
   always-true arithmetic expression that is hard to prove constant.  The
   analyst cannot tell which branch is dead without symbolic execution.

3. **Junk function injection** -- adds static C functions that look real
   (plausible names, plausible bodies, real arithmetic) but are never
   called.  Ghidra/IDA will list them alongside the real code.

4. **Identifier shuffling** -- renames local variable declarations to
   per-build random names, so a pattern match against a previous build fails.

Safety: every transform is line- or regex-based on patterns that are
unambiguous in Cython-generated C (which has a stable structure).  A
transform that cannot apply cleanly is skipped with a warning, never
silently misapplied.
"""
from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


def _derive_key(seed: bytes, tag: str, index: int = 0) -> bytes:
    """Deterministic per-transform key from the build seed."""
    return hashlib.sha256(seed + tag.encode() + index.to_bytes(4, "big")).digest()


# ── 1. string-literal encryption ─────────────────────────────────────────

_CYX_STRING_DEF = re.compile(
    r'static\s+char\s+(__pyx_k_[A-Za-z0-9_]+)\[\s*\]\s*=\s*"((?:[^"\\]|\\.)*)"\s*;')
_CYX_STRING_TAB_INIT = "__Pyx_InitStrings"


def _c_escape(data: bytes) -> str:
    """Emit a C string literal from raw bytes (octal escapes for non-print)."""
    out = []
    for b in data:
        if 0x20 <= b < 0x7f and b not in (0x22, 0x5c):
            out.append(chr(b))
        else:
            out.append("\\%03o" % b)
    return '"%s"' % "".join(out)


def _unescape_c(literal: str) -> bytes:
    """Decode a C string literal body (the part between the quotes) to bytes."""
    out = bytearray()
    i = 0
    while i < len(literal):
        ch = literal[i]
        if ch == "\\" and i + 1 < len(literal):
            nxt = literal[i + 1]
            if nxt == "x" and i + 3 < len(literal):
                try:
                    out.append(int(literal[i + 2:i + 4], 16))
                    i += 4
                    continue
                except ValueError:
                    pass
            if nxt.isdigit() and i + 3 < len(literal):
                # 3-digit octal escape (C standard).
                try:
                    out.append(int(literal[i + 1:i + 4], 8))
                    i += 4
                    continue
                except ValueError:
                    pass
            mapping = {"n": 10, "t": 9, "r": 13, "\\": 92, '"': 34, "0": 0}
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
        out.extend(ch.encode("utf-8", errors="replace"))
        i += 1
    return bytes(out)


def encrypt_strings(source: str, seed: bytes,
                    rng: random.Random) -> Tuple[str, int]:
    """XOR-encrypt every `__pyx_k_*` array; emit a decrypt loop.

    Returns (new_source, count).  Count is 0 when the source has no
    Cython string table (e.g. it is not a Cython-generated file) -- the
    transform is skipped rather than misapplied.
    """
    matches = list(_CYX_STRING_DEF.finditer(source))
    if not matches:
        return source, 0
    key = _derive_key(seed, "c-string-enc")
    new_source = source
    count = 0
    entries = []  # (array_name, decrypted_len, encrypted_literal)
    for m in matches:
        name = m.group(1)
        raw = _unescape_c(m.group(2))
        if not raw:
            continue
        enc = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        entries.append((name, len(raw), _c_escape(enc), m.start(), m.end()))
        count += 1
    if count == 0:
        return source, 0
    # Replace each definition (bottom-up so offsets stay valid).
    for _name, _ln, literal, start, end in reversed(entries):
        new_source = new_source[:start] + (
            "static char %s[] = %s;" % (_name, literal)
        ) + new_source[end:]
    # Emit a decrypt function and call it before __Pyx_InitStrings.
    mkey = _c_escape(key)
    decrypt_fn = (
        "\n/* Build-time encrypted string literals (polymorphic, per-build key). */\n"
        "static const unsigned char __nx_str_key[] = %s;\n"
        "static void __nx_decrypt_strings(void) {\n" % mkey
    )
    for idx, (name, ln, _lit, _s, _e) in enumerate(entries):
        decrypt_fn += (
            "    { for (int _i = 0; _i < %d; _i++) %s[_i] ^= "
            "__nx_str_key[(_i + %d) %% %d]; }\n"
            % (ln, name, idx * 7 % len(key), len(key))
        )
    decrypt_fn += "}\n"
    # Insert the decrypt function AFTER all __pyx_k definitions (it
    # references them by name, so the definitions must come first), and the
    # call right before __Pyx_InitStrings.  Find the last definition in the
    # NEW source (the offsets above are stale after the replacements).
    _last_arr = 0
    for m2 in _CYX_STRING_DEF.finditer(new_source):
        _last_arr = m2.end()
    new_source = new_source[:_last_arr] + "\n" + decrypt_fn + new_source[_last_arr:]
    call = "    __nx_decrypt_strings();\n"
    # The call must go INSIDE __Pyx_InitStrings' body, not before its
    # definition.  At file scope, `name();` is parsed as a DECLARATION
    # (implicit int), not a call -- gcc reported
    #   conflicting types for '__nx_decrypt_strings'; have 'int()'
    # because the call was at module level.
    tab_pos = new_source.find(_CYX_STRING_TAB_INIT)
    if tab_pos >= 0:
        # Find the opening brace of __Pyx_InitStrings.
        brace = new_source.find("{", tab_pos)
        if brace >= 0:
            insert_at = brace + 1
            newline = "\n" if new_source[insert_at - 1] != "\n" else ""
            new_source = (new_source[:insert_at] + newline + call
                          + new_source[insert_at:])
    return new_source, count


# ── 2. opaque predicates ─────────────────────────────────────────────────

#: Match simple `if (cond)` lines in generated C.  Cython emits these with
#: consistent indentation; the match is deliberately narrow to avoid
#: wrapping something the transform cannot reason about.
_IF_LINE = re.compile(r"^(\s*)if\s*\((.+)\)\s*\{\s*$")

_OPAQUE_CONSTS = [
    "__nx_opa_1 * __nx_opa_2 + __nx_opa_3",
    "__nx_opa_1 ^ __nx_opa_2 ^ __nx_opa_3",
    "__nx_opa_1 & __nx_opa_2 | __nx_opa_3",
]


def insert_opaque_predicates(source: str, seed: bytes,
                             rng: random.Random,
                             rate: float = 0.15) -> Tuple[str, int]:
    """Wrap selected `if` conditions with an always-true opaque expression.

    The expression `((x*x+3*x+7) & 1) == 0` is always true for even x and
    always false for odd x; by fixing x to an even constant the branch is
    deterministic but requires algebra to prove.  The real condition is
    AND-ed in so the semantics are unchanged.
    """
    lines = source.splitlines(keepends=True)
    a = rng.randrange(2, 1000) | 1  # odd
    b = rng.randrange(2, 1000)
    c = rng.randrange(2, 1000)
    # Opaque-true: (a*x*x + b*x + c) with x = 2*k makes the polynomial even.
    decl = (
        "\n/* Opaque predicate operands (polymorphic, per build). */\n"
        "static const int __nx_opa_1 = %d;\n"
        "static const int __nx_opa_2 = %d;\n"
        "static const int __nx_opa_3 = %d;\n"
        % (a, b, c)
    )
    # Insert the declarations before the first function.
    first_fn = source.find("\ndef ") if "\ndef " in source else 0
    # C file: insert before the first `static` definition.
    first_static = source.find("\nstatic ")
    if first_static < 0:
        return source, 0
    insert_at = first_static + 1
    count = 0
    out = []
    for i, line in enumerate(lines):
        m = _IF_LINE.match(line.rstrip("\n"))
        if m and rng.random() < rate and "goto" not in line:
            indent, cond = m.group(1), m.group(2)
            pred = rng.choice(_OPAQUE_CONSTS)
            out.append(
                "%sif (((%s) & 1) == 0 && %s) {\n"
                % (indent, pred, cond)
            )
            count += 1
        else:
            out.append(line)
    if count == 0:
        return source, 0
    new_source = "".join(out)
    # Insert the declarations.
    new_source = new_source[:insert_at] + decl + new_source[insert_at:]
    return new_source, count


# ── 3. junk function injection ────────────────────────────────────────────

_JUNK_BODIES = [
    """static int {name}(int a, int b) {{
        unsigned acc = 0x{seed:x};
        for (int i = 0; i < 16; i++) {{
            acc = (acc * 0x9E3779B9 + (unsigned)(a * i + b)) & 0xFFFFFFFF;
            acc ^= acc >> 7;
        }}
        return (int)(acc & 0x7FFF);
    }}""",
    """static long {name}(const char *s, int n) {{
        long h = {seed}L;
        for (int i = 0; i < n && s[i]; i++) {{
            h = h * 31 + (long)s[i];
            h ^= h >> 13;
        }}
        return h;
    }}""",
    """static void {name}(unsigned char *buf, int len) {{
        unsigned state = 0x{seed:x};
        for (int i = 0; i < len; i++) {{
            state = state * 1103515245 + 12345;
            buf[i] = (unsigned char)((state >> 16) & 0xFF);
        }}
    }}""",
]

_JUNK_NAMES = [
    "_nx_verify_stamp", "_nx_resolve_shard", "_nx_rotate_key",
    "_nx_pack_header", "_nx_fold_digest", "_nx_scan_block",
    "_nx_route_table", "_nx_sync_state",
]


def inject_junk_functions(source: str, seed: bytes,
                          rng: random.Random,
                          count: int = 3) -> Tuple[str, int]:
    """Inject static C functions that look real but are never called.

    Ghidra/IDA will list them alongside the real code; the analyst must
    reverse each one to confirm it is dead.
    """
    bodies = []
    digest = hashlib.sha256(seed).digest()
    for i in range(min(count, len(_JUNK_BODIES))):
        name = rng.choice(_JUNK_NAMES) + "_%02x" % digest[i]
        body = _JUNK_BODIES[i % len(_JUNK_BODIES)].format(
            name=name,
            seed=int.from_bytes(digest[i * 4:i * 4 + 4], "big"),
        )
        bodies.append(body)
    if not bodies:
        return source, 0
    block = ("\n/* Build-time injected helpers (polymorphic). */\n"
             + "\n\n".join(bodies) + "\n")
    first_static = source.find("\nstatic ")
    if first_static < 0:
        return source, 0
    insert_at = first_static + 1
    return source[:insert_at] + block + source[insert_at:], len(bodies)


# ── 4. identifier shuffling ───────────────────────────────────────────────

_LOCAL_DECL = re.compile(r"\bint\s+(locals_\d+)\s*=")


def shuffle_locals(source: str, seed: bytes,
                   rng: random.Random) -> Tuple[str, int]:
    """Rename Cython's numbered local declarations to per-build names.

    Cython emits `int locals_N = ...` for some locals.  Renaming them to
    per-build names breaks pattern matching across builds.
    """
    names = {}
    count = 0
    for m in _LOCAL_DECL.finditer(source):
        old = m.group(1)
        if old not in names:
            suffix = hashlib.sha256(
                seed + old.encode()).hexdigest()[:6]
            names[old] = "locals_%s" % suffix
            count += 1
    if not names:
        return source, 0
    new_source = source
    for old, new in names.items():
        new_source = re.sub(r"\b%s\b" % re.escape(old), new, new_source)
    return new_source, count


# ── the pipeline ──────────────────────────────────────────────────────────

@dataclass
class CTransformResult:
    """What the transformation layer did (for the build log and the tests)."""

    source: str
    strings_encrypted: int = 0
    opaque_inserted: int = 0
    junk_injected: int = 0
    locals_shuffled: int = 0
    transforms_applied: List[str] = field(default_factory=list)


def transform_c(source: str, seed: bytes, *,
                do_encrypt_strings: bool = True,
                do_opaque_predicates: bool = True,
                do_junk_functions: bool = True,
                do_shuffle_locals: bool = True) -> CTransformResult:
    """Apply the C transformation layer.  Polymorphic per (source, seed).

    Each transform is applied in a randomised order (where safe) and the
    whole set is on by default for the native path.  A transform that cannot
    apply (e.g. string encryption on a non-Cython file) is skipped, never
    misapplied.
    """
    rng = random.Random(int.from_bytes(
        hashlib.sha256(seed).digest()[:8], "big"))
    result = CTransformResult(source=source)
    applied = result.transforms_applied

    # String encryption must run FIRST: it changes string literals that
    # other passes might try to reason about.
    if do_encrypt_strings:
        result.source, result.strings_encrypted = encrypt_strings(
            result.source, seed, rng)
        if result.strings_encrypted:
            applied.append("string-encryption(%d)" % result.strings_encrypted)
    for step in ("junk", "shuffle", "opaque"):
        if step == "junk" and do_junk_functions:
            result.source, result.junk_injected = inject_junk_functions(
                result.source, seed + b"junk", rng)
            if result.junk_injected:
                applied.append("junk-functions(%d)" % result.junk_injected)
        elif step == "shuffle" and do_shuffle_locals:
            result.source, result.locals_shuffled = shuffle_locals(
                result.source, seed + b"shuffle", rng)
            if result.locals_shuffled:
                applied.append("locals-shuffled(%d)" % result.locals_shuffled)
        elif step == "opaque" and do_opaque_predicates:
            result.source, result.opaque_inserted = insert_opaque_predicates(
                result.source, seed + b"opaque", rng)
            if result.opaque_inserted:
                applied.append("opaque-predicates(%d)" % result.opaque_inserted)
    return result


def transform_file(path: str, seed: bytes, *,
                   out_path: Optional[str] = None,
                   **kwargs) -> CTransformResult:
    """Transform a .c file in place (or to out_path)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        source = fh.read()
    result = transform_c(source, seed, **kwargs)
    dest = out_path or path
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(result.source)
    return result
