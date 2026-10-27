"""Constant-literal attack (Experiment v2.0, T_const_split).

Registered instrument -- see ``docs/research/protocol-v2.md`` amendment 1,
corrected by amendment 2 (flatten folded sequences; pre-amendment numbers
are disclosed next to the corrected ones). The arm and the scoring rule
were frozen before any const-arm number was taken; this module implements
the frozen rule and nothing else.

Level: Python BYTECODE. Source is compiled with builtin ``compile()``
(never executed) and the constant pool is walked recursively through the
nested code objects. No AST, so nothing about the transform's source
shape leaks in: the measure sees exactly the literals a signature matcher
would see.

Amendment 2: CPython folds a constant sequence display (list/tuple/set
literal, dict keys) into a single tuple in ``co_consts``. Those nested
elements are flattened, because the searchable literal is the element,
not the container. Pass ``flatten=False`` to reproduce the amendment-1
extractor for the disclosed pre-amendment table.

Development ``P_i``: the distinct literal constants of build ``i``,
tagged by type so ``1`` and ``1.0`` cannot collapse into one another in a
Python set (they compare equal and hash equal).

Apply: the same extraction on ``B_j``.

``S(B_j | P_i) = |P_i & B_j| / |P_i|`` over distinct values, i.e. the
hit rate of a plain literal search.

``S(B_j | P_j)`` is 1.00 by construction (the extractor is deterministic
and complete for a build against itself), so the frozen denominator gate
is satisfied everywhere. The informative gate is C0->C0, which must stay
>= 0.80; if renaming-only builds stop transferring constants, the
instrument is broken and the arm is void.

Scope: this measures literal *search*. It does not measure value
recovery -- ``C`` split as ``C ^ m`` and ``m`` is algebraically
recoverable by an analyst who models the rule. A positive T here
supports "hides literals from search", never "hides values".
"""
import types

#: Type tags keep equal-comparing values of different types apart.
_TAG_FOR = ((bool, None), (int, "i"), (float, "f"), (bytes, "b"), (str, "s"))

#: Minimum string/bytes length worth calling a literal. One-character
#: strings are structural glue (separators, format chars) and are noise
#: in every build; the rule is fixed here, before measurement.
MIN_TEXT_LEN = 2

#: Amendment 2: flatten tuple/frozenset constants into their elements.
#: Fixed before the corrected number; ``flatten=False`` reproduces the
#: amendment-1 instrument for disclosure.
FLATTEN_SEQUENCES = True


def _tag(value):
    """Return the type tag for *value*, or None when it is not a literal."""
    if isinstance(value, bool):
        return None          # True/False are syntax, not obfuscated literals
    if isinstance(value, int):
        return "i"
    if isinstance(value, float):
        return "f"
    if isinstance(value, bytes):
        return "b" if len(value) >= MIN_TEXT_LEN else None
    if isinstance(value, str):
        if len(value) < MIN_TEXT_LEN:
            return None
        if value.startswith("_"):
            # Sentinel/dunder-ish names are emitted by the toolchain and
            # would measure the toolchain, not the program's literals.
            return None
        return "s"
    return None


def _flatten(seq, flatten):
    """Yield scalars inside a folded sequence constant, recursively."""
    for item in seq:
        if isinstance(item, types.CodeType):
            continue
        if flatten and isinstance(item, (tuple, frozenset)):
            for inner in _flatten(item, flatten):
                yield inner
        else:
            yield item


def _walk(code, flatten=FLATTEN_SEQUENCES):
    """Yield every non-code constant in *code*, recursing into nested codes.

    On 3.10 the compiler stores a def's qualname as a plain string
    constant right after the code object (``<code values>, 'values',
    ...``); 3.11+ moved it to ``co_qualname``.  Emitting it as a literal
    made the string pool -- and every S() denominator -- version
    dependent, so the qualname slot is skipped by position: a string that
    directly follows a code object and repeats its ``co_name`` is the
    compiler's qualname, not a literal.
    """
    consts = code.co_consts
    for index, const in enumerate(consts):
        if isinstance(const, types.CodeType):
            for inner in _walk(const, flatten):
                yield inner
        elif isinstance(const, str) and index:
            prev = consts[index - 1]
            if isinstance(prev, types.CodeType) and const == prev.co_name:
                continue
            yield const
        elif flatten and isinstance(const, (tuple, frozenset)):
            for inner in _flatten(const, flatten):
                yield inner
        else:
            yield const


def _inline_small_ints(code):
    """Yield ints 3.14 keeps in the instruction stream, not in co_consts.

    Python 3.14 encodes 0..255 as ``LOAD_SMALL_INT`` operands, so a
    literal search over ``co_consts`` alone sees a *subset* of the pool
    on that interpreter -- measured here as {7} instead of {7, 11} for
    ``[[[7, 11]]]``.  The value is still a literal in the program, so it
    belongs in the profile; without this the S() denominator shrinks on
    3.14 and the arm is not comparable across the matrix.
    """
    try:
        import dis as _dis
        instructions = _dis.get_instructions(code)
    except Exception:
        return
    for ins in instructions:
        if ins.opname == "LOAD_SMALL_INT" and isinstance(ins.arg, int):
            yield ins.arg


def _inline_or_const_walk(code, flatten):
    for value in _walk(code, flatten):
        yield value
    # Inline operands live per code object, so walk the nested ones too.
    stack = [code]
    while stack:
        current = stack.pop()
        for value in _inline_small_ints(current):
            yield value
        stack.extend(c for c in current.co_consts
                     if isinstance(c, types.CodeType))


def extract(source, flatten=None):
    """Extract the literal-constant profile of one build.

    ``flatten`` defaults to :data:`FLATTEN_SEQUENCES` (amendment 2).
    Returns ``{"ok": True, "values": set[(tag, value)], "by_tag": {...},
    "n": int}`` or ``{"ok": False, "reason": str}``.
    """
    if flatten is None:
        flatten = FLATTEN_SEQUENCES
    if not isinstance(source, str):
        return {"ok": False, "reason": "not-source"}
    try:
        top = compile(source, "<nxk-const>", "exec")
    except SyntaxError as exc:
        return {"ok": False, "reason": "uncompilable: %s" % (exc,)}
    except Exception as exc:                                  # pragma: no cover
        return {"ok": False, "reason": "compile-error: %s" % (exc,)}
    values = set()
    by_tag = {"i": set(), "f": set(), "b": set(), "s": set()}
    for const in _inline_or_const_walk(top, flatten):
        tag = _tag(const)
        if tag is None:
            continue
        try:
            values.add((tag, const))
        except TypeError:                                     # pragma: no cover
            continue
        by_tag[tag].add(const)
    return {"ok": True, "values": values, "by_tag": by_tag, "n": len(values)}


def score(p_i, b_j, tag=None):
    """Hit rate of ``P_i``'s literals inside build ``B_j``.

    ``tag`` restricts both sides to one type class (``"i"`` for the
    integer subset, ``"s"`` for the string specificity control).

    Returns ``(S, n_total, n_hit)``; ``S`` is ``None`` when ``P_i`` holds
    nothing of that class (nothing to measure, caller excludes).
    """
    if not p_i.get("ok") or not b_j.get("ok"):
        return None, 0, 0
    if tag is None:
        wanted, found = p_i["values"], b_j["values"]
    else:
        wanted = {(tag, v) for v in p_i["by_tag"].get(tag, ())}
        found = {(tag, v) for v in b_j["by_tag"].get(tag, ())}
    total = len(wanted)
    if total == 0:
        return None, 0, 0
    hits = len(wanted & found)
    return hits / total, total, hits


def self_score(source, flatten=None):
    """``S(B_j | P_j)``: must be 1.00 (denominator-gate sanity)."""
    prof = extract(source, flatten=flatten)
    if not prof["ok"]:
        return None, 0, 0, prof["reason"]
    s, total, hits = score(prof, prof)
    return s, total, hits, "ok"


def transfer(p_i_source, b_j_source, tag=None, flatten=None):
    """Convenience: extract both sides and score in one call."""
    p_i = extract(p_i_source, flatten=flatten)
    b_j = extract(b_j_source, flatten=flatten)
    if not p_i.get("ok") or not b_j.get("ok"):
        return None, 0, 0, (p_i.get("reason") or b_j.get("reason") or "")
    s, total, hits = score(p_i, b_j, tag=tag)
    return s, total, hits, "ok"
