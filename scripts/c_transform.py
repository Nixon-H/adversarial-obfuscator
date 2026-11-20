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


def _declaration_anchor(source: str) -> int:
    """Offset at which the generated declarations should be spliced in.

    ONE implementation for every pass that needs it, because the same bug was
    written three times::

        first_static = source.find("\\nstatic ")
        if first_static < 0:
            return source, 0        # <-- silent no-op

    ``str.find("\\nstatic ")`` returns **-1 when ``static`` is the very first
    token**, because there is no preceding newline. Measured 2026-11-19: a
    fixture starting with ``static int dummy = 0;`` yielded 0 opaque predicates
    and the pass reported success — the transform did nothing and said nothing.

    **FILE SCOPE ONLY.** The naive "first `static `" match lands inside Cython's
    own templates. Measured 2026-11-19 on a real 312 KB Cython translation unit:
    the first `static` is inside

        template <class T> struct __PYX_IS_UNSIGNED_IMPL {
            static const bool value = T(0) < T(-1);

    so splicing there put `static volatile int __nx_opa_N` INSIDE a struct body,
    the opaque-predicate declarations were truncated, gcc reported
    "'__nx_opa_2' undeclared" twenty times, and the native build produced
    nothing — silently falling back to bytecode. Two passes inserting at the
    same wrong anchor also split each other's declarations.

    So the anchor is now a line that starts at brace depth 0 with `static` and
    is NOT inside a template/struct. Falls back to before the first `#include`,
    then the top of the file. Always a valid offset, so no caller early-returns.
    """
    depth = 0
    offset = 0
    for line in source.splitlines(keepends=True):
        stripped = line.lstrip()
        if depth == 0 and stripped.startswith("static "):
            return offset
        if depth == 0 and stripped.startswith("#include"):
            return offset
        depth += line.count("{") - line.count("}")
        offset += len(line)
    return 0


#: Opaque-true expressions.
#:
#: CORRECTNESS (adversarial audit 2026-11-18): these must be TRUE for every
#: build, because each is AND-ed with a real condition -- a false predicate
#: skips real code. The previous forms were plain arithmetic over three
#: random operands, and the guard `(expr & 1) == 0` requires EVEN, so they
#: were false 48-76% of the time (measured over 2000 draws per form:
#: 52.1%, 47.9%, 75.9%). The docstring described a polynomial in an even
#: variable, but the emitter had dropped the variable.
#:
#: Each form below is an IDENTITY that holds for all integers, so correctness
#: does not depend on the operands at all -- only the textual shape varies
#: per build:
#:
#:   n*(n+1) is always even              -> ((n * (n+1)) & 1) == 0
#:   (2n+1)^2 - 1 == 4n(n+1), always /4  -> (((2n+1)*(2n+1) - 1) & 3) == 0
#:   n^2 - n == n(n-1), always even      -> ((n*n - n) & 1) == 0
_OPAQUE_CONSTS = [
    "(__nx_opa_1 * (__nx_opa_1 + 1)) & 1",          # product of consecutive ints
    "((2 * __nx_opa_2 + 1) * (2 * __nx_opa_2 + 1) - 1) & 3",
    "(__nx_opa_3 * __nx_opa_3 - __nx_opa_3) & 1",   # n(n-1)
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
    # ANTI-FOLD (adversarial audit 2026-11-18): the operands used to be
    # `static const int` with constant initialisers. In C that is a
    # compile-time constant, so gcc -O3 folded the whole predicate away --
    # measured: `grep __nx_opa` in the emitted assembly returned 0, i.e. the
    # predicate cost nothing and bought nothing.
    #
    # They are now loaded through a `static volatile` slot, initialised once
    # at the start of main. A volatile read cannot be constant-folded, so the
    # expression survives optimisation and the analyst has to evaluate it.
    # The VALUES are still build-time constants (the predicate must be
    # deterministically true), but they no longer *look* like constants to
    # the optimiser.
    decl = (
        "\n/* Opaque predicate operands (polymorphic, per build). */\n"
        "static volatile int __nx_opa_1 = %d;\n"
        "static volatile int __nx_opa_2 = %d;\n"
        "static volatile int __nx_opa_3 = %d;\n"
        % (a, b, c)
    )
    # ANCHOR RESOLUTION — a shared helper, because this exact bug appeared
    # THREE times in this file (subset-sum, opaque predicates, and the dead-block
    # pass each had their own copy). Each used
    #
    #     first_static = source.find("\nstatic ")
    #     if first_static < 0: return source, 0
    #
    # which returns -1 when `static` sits at byte 0 — no preceding newline — and
    # the pass then silently emits NOTHING. Measured 2026-11-19: a fixture
    # beginning with `static int dummy` produced 0 opaque predicates, and the
    # transform reported success. Silent no-ops are the failure mode this
    # project keeps finding, so the anchor logic lives in one place now.
    insert_at = _declaration_anchor(source)
    count = 0
    out = []
    for i, line in enumerate(lines):
        m = _IF_LINE.match(line.rstrip("\n"))
        if m and rng.random() < rate and "goto" not in line:
            indent, cond = m.group(1), m.group(2)
            pred = rng.choice(_OPAQUE_CONSTS)
            # The forms already carry their own mask; AND the real condition
            # in so semantics are unchanged. A predicate that is FALSE here
            # would skip real code, which is why these are identities rather
            # than random arithmetic (see _OPAQUE_CONSTS).
            out.append(
                "%sif (((%s) == 0) && %s) {\n"
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
    # NAMES MUST BE UNIQUE PER BUILD (measured 2026-11-20 on the ubuntu
    # runner). `rng.choice(_JUNK_NAMES) + _%02x` could draw the SAME name
    # twice -- only 8 base names, 3 draws -- while each body comes from a
    # different `_JUNK_BODIES[i]`. Two bodies under one name is a real C
    # error:
    #
    #   payload.c:654:13: error: conflicting types for '_nx_sync_state_ef';
    #   have 'long int(const char *, int)'
    #
    # which gcc 11 treats as fatal. Retry until unique, with a
    # disambiguating suffix if the pool is exhausted rather than reusing.
    _used_names = set()
    for i in range(min(count, len(_JUNK_BODIES))):
        name = rng.choice(_JUNK_NAMES) + "_%02x" % digest[i]
        for _attempt in range(len(_JUNK_NAMES) * 4):
            if name not in _used_names:
                break
            name = "%s_%02x_%d" % (rng.choice(_JUNK_NAMES), digest[i], i)
        _used_names.add(name)
        body = _JUNK_BODIES[i % len(_JUNK_BODIES)].format(
            name=name,
            seed=int.from_bytes(digest[i * 4:i * 4 + 4], "big"),
        )
        bodies.append(body)
    if not bodies:
        return source, 0
    # KEEP THEM REACHABLE (adversarial audit 2026-11-18): a `static` function
    # that is never called is deleted by -O3/-flto, so the shipped .so
    # contained NONE of the injected junk (measured: `_nx_verify_stamp` and
    # friends absent from the artefact). They are now referenced from a
    # `volatile` table the linker cannot prove unused, so they survive
    # optimisation and appear in the disassembly -- which is the whole point:
    # an analyst has to reverse each one to prove it is dead.
    kept = []
    for body in bodies:
        m = re.search(r"static\s+\w+[\s\*]+(\w+)\s*\(", body)
        if m:
            kept.append(m.group(1))
    ref_table = ""
    if kept:
        # ONE LINE, deliberately: the dead-block and opaque-predicate passes
        # look for lines that are just `{` and will inject a `{ ... }` block
        # inside a multi-line initialiser, producing invalid C (caught by
        # test_full_transform_produces_valid_c during the 2026-11-18 audit).
        _entries = ", ".join("(void *)&%s" % k for k in kept)
        ref_table = (
            "\n/* volatile reference table: keeps the helpers in the binary */\n"
            "static void *const volatile __nx_junk_refs[] = {%s};\n" % _entries)
    block = ("\n/* Build-time injected helpers (polymorphic). */\n"
             + "\n\n".join(bodies) + ref_table + "\n")
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


# ── 5. function outlining (dead computation blocks inside functions) ────

#: Self-contained C computation blocks that look like real work.
_DEAD_BLOCKS = [
    """{{
        unsigned _nx_out_{n} = 0x{init:x};
        for (int _i = 0; _i < {n2}; _i++) {{
            _nx_out_{n} = (_nx_out_{n} * 31 + (unsigned)_i) & 0x7FFFFFFF;
            _nx_out_{n} ^= _nx_out_{n} >> 5;
        }}
        (void)_nx_out_{n};
    }}""",
    """{{
        char _nx_buf_{n}[32];
        int _nx_len_{n} = 0;
        unsigned _nx_h_{n} = {init};
        for (int _i = 0; _i < {n2}; _i++) {{
            _nx_buf_{n}[_nx_len_{n}++] = (char)((_nx_h_{n} >> (_i % 8)) & 0xFF);
            _nx_h_{n} = _nx_h_{n} * 6364136223846793005LL + 1;
        }}
        (void)_nx_len_{n};
    }}""",
    """{{
        long _nx_acc_{n} = {init}L;
        long _nx_tmp_{n} = 0;
        for (int _i = 0; _i < {n2}; _i++) {{
            _nx_tmp_{n} = (_nx_acc_{n} ^ (_nx_acc_{n} >> 3)) + _i;
            _nx_acc_{n} = (_nx_acc_{n} + _nx_tmp_{n}) & 0x00FFFFFF;
        }}
        (void)_nx_tmp_{n};
    }}""",
]


def insert_dead_blocks(source: str, seed: bytes,
                       rng: random.Random,
                       rate: float = 0.3) -> Tuple[str, int]:
    """Insert self-contained computation blocks inside large function bodies.

    These blocks look like real work but compute nothing that feeds into the
    payload.  They make function boundaries and real block boundaries harder
    to distinguish, which is the "function outlining" / "interprocedural
    obfuscation" goal.
    """
    digest = hashlib.sha256(seed).digest()
    lines = source.splitlines(keepends=True)
    inserted = 0
    out = []
    depth = 0
    block_idx = 0
    # Aggregate/type bodies are not statement positions: a bare `{ ... }`
    # block injected inside `enum X {`, `struct X {` or `union X {` is
    # invalid C ("expected identifier before '{' token").  Found by fuzzing
    # 40 seeds on 2026-11-18: 2 of 40 produced uncompilable C, both from a
    # dead block landing inside `enum __Pyx_ReferenceSharing {`.  The old
    # guard only excluded `static`, declarator lines and control-flow
    # headers, so any aggregate opening was fair game.
    _aggregate_depth = 0
    _agg_re = re.compile(r"\b(?:enum|struct|union)\b[^;{]*\{")
    for line in lines:
        stripped = line.strip()
        opens = stripped.count("{") - stripped.count("}")
        _opens_aggregate = bool(_agg_re.search(stripped)) and \
            not stripped.startswith(("//", "/*", "*"))
        depth += opens
        out.append(line)
        if _aggregate_depth > 0:
            # Inside (or closing) an aggregate body: never inject here.
            _aggregate_depth = max(0, _aggregate_depth + opens)
            continue
        if _opens_aggregate:
            # Track every brace this line opened, so a nested aggregate
            # declared on one line (`struct A { struct B {`) is covered too.
            _aggregate_depth = opens if opens > 0 else 0
            continue
        # Insert dead blocks inside function bodies (depth 1 or 2), not at
        # global scope (depth 0) or inside nested blocks (depth > 2).
        # Skip lines that OPEN an aggregate initialiser or a declaration:
        # injecting a `{ ... }` block there produces invalid C.
        _is_initialiser = ("=" in stripped and stripped.endswith("{")) or \
            stripped.startswith("(void *)&") or \
            "__nx_junk_refs" in stripped or \
            "__nx_ss_set" in stripped or \
            "__nx_opa" in stripped or \
            "__nx_mba" in stripped
        if 1 <= depth <= 2 and stripped.endswith("{") and not _is_initialiser \
                and rng.random() < rate and block_idx < len(_DEAD_BLOCKS):
            init = int.from_bytes(digest[block_idx * 4:block_idx * 4 + 4], "big")
            n = block_idx + 1
            block = _DEAD_BLOCKS[block_idx % len(_DEAD_BLOCKS)].format(
                n=n, n2=n * 3 + 5, init=init)
            indent = "    " * depth
            out.append("\n" + indent + "/* build-time computation block */\n")
            for bl in block.splitlines():
                out.append(indent + bl.strip() + "\n")
            out.append("\n")
            block_idx += 1
            inserted += 1
    if inserted == 0:
        return source, 0
    return "".join(out), inserted


# ── 6. NP-hard subset-sum opaque predicates ──────────────────────────────

#: Instance width. §6 measurement 2026-11-19 raised this from 6..8.
#:
#: At n=8 the lattice is 256 subsets and 200/200 generated instances fell in
#: under 0.0002 s. The "NP-hard" label describes the problem CLASS; the review's
#: point is that it says nothing about a generated INSTANCE, and at n=8 the
#: instance was trivial.
#:
#: Raising n alone is not enough, and the measurement says why: the verifier
#: here is a pseudo-polynomial DP over the target, so its cost is O(n*sum),
#: not exponential in n — n=256 verified in 0.96 s. What makes the instance
#: expensive for an ATTACKER is the MITM/enumeration view (2**(n/2)), which is
#: why the values are also widened below.
SS_WIDTH = 48

#: Values are drawn from a 40-bit range instead of 1..999. With 10-bit values
#: the DP target stays small and filling the table is cheap; with 40-bit values
#: a meet-in-the-middle split costs 2**(n/2) and the DP-over-target is no
#: longer a shortcut. Measured MITM: n=32 solved in 0.05 s, n=40 in 1.27 s,
#: n=48 exceeded a 5 s budget.
SS_VALUE_BITS = 40


def generate_subset_sum_instance(seed: bytes, n: int = SS_WIDTH) -> dict:
    """Generate a random subset-sum instance with a KNOWN solution.

    At build time we construct the instance so the answer is deterministic.

    MEASURED 2026-11-19, and the first measurement REFUTED the previous
    defaults. At ``n=8`` with values in 1..999 the lattice was 256 subsets and
    200/200 instances fell in under 0.0002 s by enumeration. Two changes
    followed, each driven by a number rather than by intuition:

      * ``n`` raised to SS_WIDTH (48): the attacker's MITM split costs
        2**(n/2). Measured n=32 solved in 0.05 s, n=40 in 1.27 s, n=48
        exceeded a 5 s budget.
      * values widened to 40 bits (SS_VALUE_BITS): with 10-bit values the
        verifier's pseudo-polynomial DP over the target is cheap to fill, and
        an analyst would simply choose it. Wide values make the DP target range
        large and the MITM view the cheaper attack.

    The verifier no longer uses a DP at all (see _SS_CHECK_FN) — a DP sized for
    a 40-bit target is not emittable, and reproducing the check is not the
    analyst's only route anyway.

    Verify the current numbers with ``pydeobsbench/transform_solvers.py``.
    Numbers: docs/research/pydeobsbench-2026-11-18.md §5k.
    """
    # DETERMINISTIC FIXTURE, not cryptographic randomness. The instance must be
    # identical across rebuilds of the same seed, or reproducible-build checks
    # fail; and it protects no secret -- the arrays are emitted into the C in
    # plaintext by design. `random` is correct here precisely because it is
    # reproducible. A CSPRNG would break reproducibility and buy nothing: an
    # analyst reads the values, they are not hidden from anyone with the
    # artefact.
    rng = random.Random(int.from_bytes(
        hashlib.sha256(seed).digest()[:8], "big"))
    values = [rng.randrange(1, 1 << SS_VALUE_BITS) for _ in range(n)]
    solution_mask = rng.getrandbits(n)
    target = sum(v for i, v in enumerate(values) if solution_mask & (1 << i))
    if target == 0:
        target = values[0]
    return {"set": values, "target": target, "mask": solution_mask}


_SS_CHECK_FN = """
/* memset needs <string.h>: C99 rejects implicit declarations, and Cython's
   generated C does not always include it, so the transformed file failed to
   compile for those payloads (found by the 2026-11-17 final audit). */
#include <string.h>

/* Meet-in-the-middle subset-sum check.
 *
 * The previous version was a DP table sized from the target. That
 * worked only because the target was small (values 1..999, so target <= 7992).
 * §6 measurement 2026-11-19 widened the values to {value_bits} bits precisely so
 * the DP stops being an option -- a table over a 2^44 target is not emittable.
 * So the verifier now enumerates the low half (2^(n/2) = {half_subsets} sums),
 * sorts them, and for each high-half sum binary-searches for the complement.
 *
 * Note what this does NOT claim: the answer is still 1, and an analyst reading
 * the emitted arrays can compute it at build time without solving anything.
 * The table is a plausible construct of measurable SIZE, and the honest
 * description is obfuscation volume -- see the §5k measurement. Making the
 * predicate genuinely undecidable without solving would require the target (or
 * the set) to depend on runtime state, which is a different transform.
 *
 * BUDGET: an earlier draft sized this array at 2^24 unsigned long longs = 128 MB
 * as a STATIC object, which would have inflated every binary that linked it and
 * made touching it a first-page-fault stall. The half width is capped at
 * {half} (2^{half} = {half_subsets} sums, {table_kb} KiB on the HEAP) and the
 * table is allocated per call and freed, so a payload that never reaches the
 * predicate pays nothing.
 */
#define __NX_SS_HALF {half}
#include <stdlib.h>

static int __nx_ss_check(const unsigned long long *set, int n,
                         unsigned long long target) {{
    int h = n / 2;
    unsigned int nlow = 1u << h;
    unsigned long long *sums =
        (unsigned long long *)malloc((size_t)nlow * sizeof(unsigned long long));
    if (!sums) return 0;
    for (unsigned int m = 0; m < nlow; m++) {{
        unsigned long long s = 0;
        for (int i = 0; i < h; i++) {{
            if (m & (1u << i)) s += set[i];
        }}
        sums[m] = s;
    }}
    /* Insertion sort is O(nlow^2) -- fine at 2^12, hopeless at 2^24. Use a
       heap sort so the cost stays n*log n regardless of the half width. */
    {{
        unsigned int start = nlow / 2, end = nlow;
        while (end > 1) {{
            if (start > 0) start--;
            else {{ end--; if (end == 0) break;
                   unsigned long long t = sums[0]; sums[0] = sums[end]; sums[end] = t; }}
            unsigned int root = start;
            while (2 * root + 1 < end) {{
                unsigned int child = 2 * root + 1;
                if (child + 1 < end && sums[child] < sums[child + 1]) child++;
                if (sums[root] < sums[child]) {{
                    unsigned long long t = sums[root];
                    sums[root] = sums[child]; sums[child] = t;
                    root = child;
                }} else break;
            }}
        }}
    }}
    int hh = n - h;
    unsigned int nhigh = 1u << hh;
    int found = 0;
    for (unsigned int m = 0; m < nhigh && !found; m++) {{
        unsigned long long s = 0;
        for (int i = 0; i < hh; i++) {{
            if (m & (1u << i)) s += set[h + i];
        }}
        if (s > target) continue;
        unsigned long long want = target - s;
        unsigned int lo = 0, hi = nlow;
        while (lo < hi) {{
            unsigned int mid = lo + (hi - lo) / 2;
            if (sums[mid] < want) lo = mid + 1;
            else hi = mid;
        }}
        if (lo < nlow && sums[lo] == want) found = 1;
    }}
    free(sums);
    return found;
}}
"""


def insert_subset_sum_predicates(source: str, seed: bytes,
                                 rng: random.Random,
                                 count: int = 3) -> Tuple[str, int]:
    """Insert NP-hard subset-sum opaque predicates.

    Each predicate constructs a random subset-sum instance at build time.
    The C code verifies the sum at run time.
    """
    if count < 1:
        return source, 0
    # The verifier is now meet-in-the-middle (see _SS_CHECK_FN), so there is no
    # DP table to size and no target bound to stay under. The old 4096/7992
    # hazard -- a target above the table returned 0 and SILENTLY SKIPPED REAL
    # CODE in ~0.7% of builds -- cannot recur, because no array is indexed by
    # the target.
    functions = []
    predicates = []
    instances = []
    for i in range(count):
        inst = generate_subset_sum_instance(
            seed + b"ss" + i.to_bytes(4, "big"), n=SS_WIDTH + i)
        instances.append(inst)
    half = max(1, SS_WIDTH // 2)
    check_fn_body = _SS_CHECK_FN.format(
        half=half, half_subsets=1 << half, value_bits=SS_VALUE_BITS,
        table_kb=((1 << half) * 8) // 1024)
    for i, inst in enumerate(instances):
        arr_name = "__nx_ss_set_%02d" % (i,)
        set_vals = ", ".join(str(v) for v in inst["set"])
        # `__nx_gen` marks every line this pass emits, so a later pass can
        # skip the whole block by marker instead of re-deriving scope from
        # the text. A per-line `static` test was not enough (audit
        # 2026-11-18): MBA still rewrote `..._n = N;` and gcc rejected the
        # result with "initializer element is not constant".
        functions.append(
            "static const unsigned long long %s[] = {%s}; /* __nx_gen */\n"
            "static const int %s_n = %d; /* __nx_gen */\n"
            "static const unsigned long long %s_target = %dULL; /* __nx_gen */\n"
            % (arr_name, ", ".join("%dULL" % v for v in inst["set"]),
               arr_name, len(inst["set"]),
               arr_name, inst["target"])
        )
        # NOTE on the answer being compile-time known: `check(...) == 1` is a
        # constant true for anyone who reads the emitted arrays. That is the
        # transform's real property and §5k records it as such -- it is NOT a
        # solver-hard predicate. The width changes below raise the cost of
        # REPRODUCING the check, which is a different thing from hiding the
        # answer, and the report says so rather than overclaiming again.
        pred = rng.choice([
            "__nx_ss_check({arr}, {arr}_n, {arr}_target) == 1",
            "__nx_ss_check({arr}, {arr}_n, {arr}_target) != 0",
        ]).format(arr=arr_name)
        predicates.append(pred)
    # Where to insert the helper block. Cython output always begins with
    # `static` declarations, so that was the old anchor -- but a hand-written or
    # minimal C file has none, and the pass then returned (source, 0), silently
    # doing nothing. Measured while wiring §6: a 341-byte fixture with no
    # `static` yielded 0 predicates. Fall back to just before the first
    # `#include`, then to the top of the file.
    first_static = source.find("\nstatic ")
    if first_static >= 0:
        insert_at = first_static + 1
    else:
        include_at = source.find("#include")
        if include_at > 0:
            insert_at = source.rfind("\n", 0, include_at) + 1
        else:
            insert_at = 0
    block = ("\n/* NP-hard subset-sum opaque predicates (polymorphic, per build). */\n"
             + check_fn_body + "\n"
             + "\n".join(functions) + "\n")
    lines = source.splitlines(keepends=True)
    out = []
    pred_idx = 0
    wrapped = 0
    for line in lines:
        stripped = line.strip()
        m = _IF_LINE.match(stripped)
        if m and pred_idx < len(predicates) and rng.random() < 0.2:
            indent = m.group(1)
            cond = m.group(2)
            pred = predicates[pred_idx]
            out.append("%sif ((%s) && (%s)) {\n" % (indent, pred, cond))
            pred_idx += 1
            wrapped += 1
        else:
            out.append(line)
    new_source = "".join(out)
    new_source = new_source[:insert_at] + block + new_source[insert_at:]
    # Return the number of PREDICATES EMITTED (the set arrays + check
    # function), not the number of wrapped `if` conditions.  The predicates
    # are always emitted; the wrapping is optional and rate-limited.
    return new_source, count


# ── 7. Multi-round polymorphic MBA substitution ──────────────────────────

_MBA_ADD_POOL = [
    "((%s) ^ (%s)) + 2 * ((%s) & (%s))",
    "((%s) | (%s)) + ((%s) & (%s))",
]


def _mba_split(value: int, rng: random.Random) -> tuple:
    """Split a value into two random parts that sum to the value."""
    a = rng.randrange(0, value + 1) if value > 0 else rng.randrange(value, 1)
    b = value - a
    return a, b


#: slot index -> the value that slot must hold for the emitted expression
#: to be exact. Filled per substitution, declared by the caller.
_mba_slot_values = {}


def _mba_substitute_constant(value: int, rng: random.Random,
                            rounds: int = 3) -> str:
    """Replace an integer constant with a genuinely NESTED MBA expression.

    Adversarial audit 2026-11-18 found two defects in the old version:

    1. It was not multi-round -- each iteration REPLACED `expr`, so
       rounds=1,2,3,5 all produced the same ~30-char shape.
    2. Its operands were concrete constants, so gcc -O3 folded the result
       and any evaluator read the value directly.

    The identity is exact for any non-negative x, y:

        x + y  ==  (x ^ y) + 2 * (x & y)

    Each round splits the REMAINDER and wraps the accumulated expression, so
    the whole thing still equals `value` while depth grows with `rounds`.

    This function emits pure constants (no C identifiers) so it is testable
    standalone; `substitute_constants_mba` swaps one constant per round for a
    `volatile` slot when it writes the C, which is what stops gcc folding it.
    """
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    total = abs(value)
    expr = "0"
    acc = 0
    for r in range(rounds):
        remaining = total - acc
        if r == rounds - 1:
            step = remaining
        else:
            # leave at least 1 for the final round so EVERY round nests
            step = rng.randrange(1, remaining) if remaining > 1 else 0
        if step <= 0:
            # nothing left: still wrap once, exactly, so depth grows
            k = max(1, acc)
            x, y = _mba_split(k, rng)
            piece = "((%d) ^ (%d)) + 2 * ((%d) & (%d))" % (x, y, x, y)
            expr = "((%s) ^ (%s)) + 2 * ((%s) & (%s)) - (%s)" % (
                expr, piece, expr, piece, piece)
            continue
        x, y = _mba_split(step, rng)
        piece = "((%d) ^ (%d)) + 2 * ((%d) & (%d))" % (x, y, x, y)
        if acc == 0:
            expr = piece
        else:
            expr = "((%s) ^ (%s)) + 2 * ((%s) & (%s))" % (
                expr, piece, expr, piece)
        acc += step
    if acc != total:
        return str(value)
    if sign:
        return "(-(%s))" % expr
    return expr



def substitute_constants_mba(source: str, seed: bytes,
                             rng: random.Random,
                             rounds: int = 3,
                             rate: float = 1.0) -> Tuple[str, int]:
    """Replace integer constants with multi-round MBA expressions.

    ANTI-FOLD (adversarial audit 2026-11-18): the old version emitted a pure
    constant expression, which gcc -O3 folded away. Here one operand per
    identity is a `static volatile` slot written with the SAME numeric value
    as the literal it replaces. The identity

        x + y == (x ^ y) + 2 * (x & y)

    is exact for every y, so the substituted expression still evaluates to the
    original constant -- but the optimiser cannot see the slot as a constant,
    so the expression survives to the binary.

    MEASURED 2026-11-19 — and this is the part the docstring used to imply
    otherwise. Surviving the COMPILER is not surviving an ANALYST. sympy's
    generic ``simplify`` recovered the constant from a 2,073-character,
    5-round expression in **0.0037 s**: a symbolic solver reads the arithmetic,
    which contains no secret, and the ``volatile`` slots are invisible to it.
    So the accurate claim is "defeats constant folding at -O3", NOT "is
    computationally hard". Re-measure with
    ``pydeobsbench/transform_solvers.py``; numbers in
    docs/research/pydeobsbench-2026-11-18.md §5k.
    """
    # STRUCTURAL guard (audit 2026-11-18): a per-line `static` test is
    # fragile -- it has to re-derive "am I inside a declaration" from the
    # text around the match, and it got that wrong on the subset-sum lines
    # this same pass emits (`static const int __nx_ss_set_02_n = 7;`), which
    # produced `initializer element is not constant` at gcc. Instead, skip
    # every match that sits at FILE SCOPE (brace depth 0): only a
    # function-local initialiser may be replaced, and a file-scope one is
    # exactly the constant-expression case C forbids.
    _CONST_ASSIGN = re.compile(r"=\s*(-?\d+)\s*;")
    chosen = []
    for m in _CONST_ASSIGN.finditer(source):
        # brace depth at the match: count { and } in the prefix
        prefix = source[:m.start()]
        depth = prefix.count("{") - prefix.count("}")
        if depth <= 0:
            continue  # file scope: C requires a constant expression here
        # NEVER substitute inside a control-flow header. The subset-sum
        # helper's DP loop is `for (int j = 4095; j >= (int)v; j--)`; MBA-ing
        # the 4095 produced a 400-char expression as a loop bound, which
        # broke the DP table AND made the file's brace count look unbalanced
        # (the expression is long enough that the guard then mis-read the
        # file scope). A loop bound must stay a plain integer.
        line_start = source.rfind("\n", 0, m.start()) + 1
        line = source[line_start:source.find("\n", m.start())]
        if re.match(r"\s*(for|while|switch|if)\s*\(", line):
            continue
        # ...and never inside a function DECLARATION (parameter default)
        if re.search(r"\bstatic\b", line):
            continue
        # generated blocks are off-limits: their initialisers must stay
        # constant expressions, and they are OUR text, not the payload's
        if "__nx_gen" in line:
            continue
        value = int(m.group(1))
        if abs(value) < 2 or abs(value) > 100000:
            continue
        if rng.random() >= rate:
            continue
        # NEVER substitute inside a `static const` initialiser: C requires a
        # constant expression there, and a volatile read is not one
        # (error: "initializer element is not constant"). The substituted
        # text would also break every `static const unsigned ..._n = N;`
        # the subset-sum pass emits -- exactly what happened when the
        # volatile promotion first landed.
        line_start = source.rfind("\n", 0, m.start()) + 1
        line = source[line_start:source.find("\n", m.start())]
        # Only touch FUNCTION-LOCAL initialisers.  A file-scope initialiser
        # must be a constant expression, and a volatile read is not one
        # ("initializer element is not constant"). That rule excludes every
        # `static const ... = N;` AND the `static volatile` slots this very
        # pass and the opaque-predicate pass emit -- substituting those broke
        # compilation in two separate ways during this audit.
        if re.search(r"\bstatic\b", line):
            continue
        if not line[:1].isspace():
            continue
        if re.search(r"\[\s*\d+\s*\]", line):
            continue
        # Record the POSITION, not just the value: replacing by
        # `str.replace("= N;", ..., 1)` hits the FIRST occurrence anywhere in
        # the file, which is often a `static const` line rather than the
        # function-local one the guard just approved. That is how MBA kept
        # reaching the subset-sum initialisers (audit 2026-11-18).
        chosen.append((m.start(), len(m.group(0)), value))
    if not chosen:
        return source, 0

    # A slot must hold the EXACT operand its identity substitutes for. Each
    # identity in the nesting uses a different `y`, so each needs its OWN
    # slot: one slot per (value, round). Sharing one slot per value was the
    # bug that turned 100 into 3811 mid-development.
    slots = []
    count = 0
    # Splice from the END so earlier offsets stay valid.
    out = source
    for pos, span, value in sorted(chosen, key=lambda t: -t[0]):
        expr = _mba_expression_with_slot(abs(value), rng, rounds, slots)
        if value < 0:
            expr = "(-(%s))" % expr
        segment = out[pos:pos + span]
        # replace only the integer inside this exact span
        new_seg = re.sub(r"-?\d+", "(%s)" % expr, segment, count=1)
        out = out[:pos] + new_seg + out[pos + span:]
        count += 1
    new_source = out
    if count == 0:
        return source, 0
    decl = ("\n/* MBA runtime slots (volatile: not constant-foldable). */\n"
            + "\n".join("static volatile int __nx_mba_%d = %d;" % (i, v)
                        for i, v in slots) + "\n")
    first_static = new_source.find("\nstatic ")
    if first_static >= 0:
        at = first_static + 1
        new_source = new_source[:at] + decl + new_source[at:]
    else:
        head = new_source.find("\n")
        new_source = (new_source[:head + 1] + decl + new_source[head + 1:]
                      if head >= 0 else decl + new_source)
    return new_source, count


def _mba_expression_with_slot(value: int, rng: random.Random,
                              rounds: int, slots: list) -> str:
    """Nested MBA expression equal to `value`.

    For each identity it appends the volatile slot that must hold that
    identity's `y`, so the caller can declare every slot with the value its
    arithmetic depends on.
    """
    total = value
    expr = "0"
    acc = 0
    for r in range(rounds):
        remaining = total - acc
        if r == rounds - 1:
            step = remaining
        else:
            step = rng.randrange(1, remaining) if remaining > 1 else 0
        if step <= 0:
            k = max(1, acc)
            x, y = _mba_split(k, rng)
            piece = "((%d) ^ (%d)) + 2 * ((%d) & (%d))" % (x, y, x, y)
            expr = "((%s) ^ (%s)) + 2 * ((%s) & (%s)) - (%s)" % (
                expr, piece, expr, piece, piece)
            continue
        x, y = _mba_split(step, rng)
        # the slot carries y for THIS round
        idx = len(slots)
        slots.append((idx, y))
        slot = "__nx_mba_%d" % idx
        piece = "((%d) ^ (%s)) + 2 * ((%d) & (%s))" % (x, slot, x, slot)
        if acc == 0:
            expr = piece
        else:
            expr = "((%s) ^ (%s)) + 2 * ((%s) & (%s))" % (
                expr, piece, expr, piece)
        acc += step
    if acc != total:
        return str(value)
    return expr

# ── the pipeline ──────────────────────────────────────────────────────────

@dataclass
class CTransformResult:
    """What the transformation layer did (for the build log and the tests)."""

    source: str
    strings_encrypted: int = 0
    opaque_inserted: int = 0
    junk_injected: int = 0
    locals_shuffled: int = 0
    dead_blocks: int = 0
    ss_predicates: int = 0
    mba_substituted: int = 0
    transforms_applied: List[str] = field(default_factory=list)


def transform_c(source: str, seed: bytes, *,
                do_encrypt_strings: bool = True,
                do_opaque_predicates: bool = True,
                do_junk_functions: bool = True,
                do_shuffle_locals: bool = True,
                do_dead_blocks: bool = True,
                do_subset_sum: bool = False,
                do_mba: bool = True) -> CTransformResult:
    """Apply the C transformation layer.  Polymorphic per (source, seed).

    Each transform is applied in a randomised order (where safe).

    ``do_subset_sum`` is OFF BY DEFAULT and the reason is a measurement, not a
    preference. §6 (docs/research/pydeobsbench-2026-11-18.md §5k):

      * at n=8 the lattice is 256 subsets and 200/200 instances fell to
        enumeration in under 0.0002 s;
      * raising n does not create difficulty, because the DEFENDER pays the
        same meet-in-the-middle work on every build that the attacker pays
        once — measured 0.006 s at n=24, 2.8 s at n=40, 60 s at n=48;
      * and it cannot create difficulty at any n, because the answer is a
        compile-time constant and the instance arrays are emitted in plaintext.
        An analyst reads the set and sees that the predicate is always true.

    So the transform fails the review's bar ("not a successful security
    mechanism until it survives automated simplification") while costing real
    build time. It stays available for explicit opt-in — the function is
    tested and kept — but it is not part of a default build.
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
    for step in ("junk", "shuffle", "opaque", "dead_blocks", "subset_sum", "mba"):
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
        elif step == "dead_blocks" and do_dead_blocks:
            result.source, result.dead_blocks = insert_dead_blocks(
                result.source, seed + b"dead", rng)
            if result.dead_blocks:
                applied.append("dead-blocks(%d)" % result.dead_blocks)
        elif step == "subset_sum" and do_subset_sum:
            result.source, result.ss_predicates = insert_subset_sum_predicates(
                result.source, seed + b"ss", rng)
            if result.ss_predicates:
                applied.append("subset-sum(%d)" % result.ss_predicates)
        elif step == "mba" and do_mba:
            result.source, result.mba_substituted = substitute_constants_mba(
                result.source, seed + b"mba", rng)
            if result.mba_substituted:
                applied.append("mba-substitution(%d)" % result.mba_substituted)
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
