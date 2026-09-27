"""Hand-optimized C fast tier for the native lowering kernel.

The default kernel (obfuscator/kernel_gen.py::_impl_body) renders thin
Cython passthroughs::

    def impl(*a, **k):
        import builtins as _bi
        return _bi.op(*a, **k)

which compile to one thin frame + a full Python call (tuple pack for
``*a``, dict for ``**k``, generic CALL dispatch). Measured native
geomean is ~2.95x of plain CPython — far above the vendor 0.19x-1.56x
band, because the passthrough does no REAL C work.

This module is the opt-in fast tier: for a curated set of hot PURE-
COMPUTE ops it emits Cython bodies with REAL specialization:

- fixed-arity signatures (``def impl(object o, /, *a, **k)``) so the
  COMMON 1-arg path avoids tuple/dict packing on the hot branch, while
  the ``*a, **k`` tail preserves EXACT builtin call-shape behavior
  (extra args, kwargs, missing args all produce the builtin's own
  TypeError via a generic fallback).
- direct CPython C-API calls on the hot path (``PyObject_Length``,
  ``PyNumber_Absolute``, ``PyObject_Str``, ``PySequence_List``, ...),
  which hit the sq_length/nb_absolute/tp_str slots directly instead
  of going through a Python-level CALL.
- EXACT semantic fallback: every fast body checks its preconditions
  and delegates to the real builtin on ANY deviation, including
  exception-forcing paths. Fast tier is never wrong; on exotic types
  it is just the passthrough again.

Only pure-compute ops are eligible. ``print`` is deliberately
EXCLUDED (I/O side effects must keep exact passthrough semantics);
``getattr``/``setattr`` keep passthrough (descriptor protocol subtleties
make specialization risky for zero gain).

Python 3.10 compatible: plain string building, no X|Y annotations in
evaluated positions, no match statements, no PEP-695 syntax.

Per-op "why faster" notes live in _FAST_BODIES docstrings below.

Call-shape contract (verified against CPython builtins):
- single-arg builtins that reject kwargs (len/abs/ord/chr/repr/hash/
  callable/id/bool/float/list/tuple/hex/oct/bin): the hot branch fires
  only when ``not a and not k and o is present``; everything else goes
  through ``_bi.op(*args, **k)`` which raises the builtin's OWN
  TypeError (identical message, identical type).
- multi-arity builtins (int/str): fixed positional params plus the
  ``*a, **k`` tail; only the exact covered arities take the C fast
  path, all other shapes delegate wholesale.
"""

from __future__ import annotations

# Ops with hand-optimized bodies. Keep this list conservative: an op is
# here only if (a) it wins measured headroom on the benchmark (same
# machine, same N, fast/pass < 1.0 on the geometric-mean signal), and
# (b) the fallback covers everything else exactly.
# 16 ops: len/abs/repr/hash/callable/id/bool/hex/float/list/
# tuple/str/int/isinstance/issubclass/hasattr.
# Deliberately NOT fast-tier (measured neutral-or-negative, or risky):
# chr/oct/ord/bin (guard chain costs MORE than the passthrough's single
# CALL on this host — chr +50-70%, oct +56-109%, ord/bin neutral-to-
# negative in same-process isolation: the branch + type() check exceed
# the arity-1 CALL saving), set/frozenset/dict/sorted (kwarg-valid shapes; win
# marginal vs TypeError-drift risk), getattr (2/3-arg overloads +
# descriptor subtleties; C call saves nothing measurable).
FAST_OPS: tuple[str, ...] = (
    "len",        # 1-arg, PyObject_Length -> sq_length slot
    "abs",        # 1-arg, PyNumber_Absolute -> nb_absolute slot
    "repr",       # 1-arg, PyObject_Repr -> tp_repr slot
    "hash",       # 1-arg, PyObject_Hash -> tp_hash slot
    "callable",   # 1-arg, PyCallable_Check (no call at all)
    "id",         # 1-arg, PyLong_FromVoidPtr on the pointer
    "bool",       # 1-arg, PyObject_IsTrue -> nb_bool fast path
    "hex",        # 1-arg, exact-int path without tuple pack
    "str",        # 0-3 args, 1-arg PyObject_Str fast path
    "int",        # 0-2 args, exact-arity fast paths
    "float",      # 1-arg, PyNumber_Float fast path
    "list",       # 0-1 args, PySequence_List fast path
    "tuple",      # 0-1 args, PySequence_Tuple fast path
    "isinstance",  # 2-arg, PyObject_IsInstance C call
    "issubclass",  # 2-arg, PyObject_IsSubclass C call
    "hasattr",     # 2-arg, str-name PyObject_HasAttr fast path
)

# Module-level cimports shared by all fast bodies. Cython only allows
# cimport at module level, so render_pyx must emit these ONCE when any
# fast op is present (see _FAST_CIMPORTS).
_FAST_CIMPORTS = (
    "from cpython.object cimport (\n"
    "    PyObject_Hash, PyObject_IsInstance, PyObject_IsSubclass,\n"
    "    PyObject_IsTrue, PyObject_Length, PyObject_Repr, PyObject_Str,\n"
    "    PyCallable_Check, PyObject_HasAttr,\n"
    ")\n"
    "from cpython.number cimport PyNumber_Absolute, PyNumber_Float\n"
    "from cpython.sequence cimport PySequence_List, PySequence_Tuple\n"
    "from cpython.long cimport PyLong_FromVoidPtr\n"
)

_FAST_BODIES: dict[str, str] = {}


def _t(name: str, body_lines: "list[str]") -> str:
    """Join body lines into a template with {impl} placeholder."""
    _FAST_BODIES[name] = "\n".join(body_lines)
    return _FAST_BODIES[name]


# --- 1-arg slot-call ops: C-API direct hit on the hot branch,
# --- *a/**k tail preserves the builtin's own TypeErrors otherwise.

_t("len", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyObject_Length direct to the',
    '    sq_length slot (no *args tuple pack, no **kwargs dict, no',
    '    generic CALL). Any other shape (0/2+ args, kwargs) rebuilds',
    '    the call for the REAL builtin, which raises its OWN TypeError.',
    '    Identical results AND identical errors."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return PyObject_Length(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.len(*_args + tuple(a), **k)',
    '',
])

_t("abs", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyNumber_Absolute direct to',
    '    nb_absolute. Other shapes -> real builtin (own TypeError)."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return PyNumber_Absolute(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.abs(*_args + tuple(a), **k)',
    '',
])

_t("repr", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyObject_Repr direct to the',
    '    tp_repr slot, skipping the generic builtin CALL frame.',
    '    Other shapes -> real builtin (own TypeError)."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return PyObject_Repr(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.repr(*_args + tuple(a), **k)',
    '',
])

_t("hash", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyObject_Hash direct to the',
    '    tp_hash slot. Unhashable types raise the SAME TypeError via',
    '    the C API. Other shapes -> real builtin."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return PyObject_Hash(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.hash(*_args + tuple(a), **k)',
    '',
])

_t("callable", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyCallable_Check — no CALL at',
    '    all, just a tp_call slot probe (wrapped in bool() so the hot',
    '    path returns a real bool like the builtin). Other shapes ->',
    '    real builtin."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return bool(PyCallable_Check(o))',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.callable(*_args + tuple(a), **k)',
    '',
])

_t("id", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyLong_FromVoidPtr on the',
    '    object pointer — no builtin dispatch frame. Same value as',
    '    builtin id(). Other shapes -> real builtin."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return PyLong_FromVoidPtr(<void *>o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.id(*_args + tuple(a), **k)',
    '',
])

_t("bool", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyObject_IsTrue — nb_bool /',
    '    sq_length fast path in C. bool() with no args returns False',
    '    via the real builtin (same object). Other shapes -> builtin."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return bool(PyObject_IsTrue(o))',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.bool(*_args + tuple(a), **k)',
    '',
])

# ord body removed from fast tier (see FAST_OPS note).
# Kept as doc-only reference; NOT registered in _FAST_BODIES.
# _ORD_BODY_DOC = [
#     'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
#     '    """Fast: 1-arg 1-char exact-str path calls the builtin WITHOUT',
#     '    tuple pack (single METH-style arg). Subclasses/bytes/',
#     '    wrong-length/other types fall through to the real builtin',
#     '    with EXACT semantics. Other shapes -> builtin."""',
#     '    import builtins as _bi',
#     '    if not a and not k and o is not _nxk_fast_missing:',
#     '        if type(o) is str and len(o) == 1:',
#     '            return _bi.ord(o)',
#     '    _args = () if o is _nxk_fast_missing else (o,)',
#     '    return _bi.ord(*_args + tuple(a), **k)',
#     '',
# ]
# 

# chr/oct bodies removed (measured slower than passthrough; see
# FAST_OPS + _CHR_BODY/_OCT_BODY doc notes below). Kept out of
# _FAST_BODIES so is_fast()/fast_body() report them as passthrough.

_t("hex", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: exact-int path calls the builtin WITHOUT tuple pack',
    '    (single METH-style arg). Full formatting stays in the C',
    '    builtin (no Python "%" emulation). __index__/bool-subclass/',
    '    exotic -> same builtin via fallback, exact errors."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        if type(o) is int:',
    '            return _bi.hex(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.hex(*_args + tuple(a), **k)',
    '',
])

# bin body removed from fast tier (see FAST_OPS note).
# Kept as doc-only reference; NOT registered in _FAST_BODIES.
# _BIN_BODY_DOC = [
#     'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
#     '    """Fast: exact-int path calls the builtin WITHOUT tuple pack',
#     '    (single METH-style arg). Exotic -> same builtin via fallback.',
#     '    Other shapes -> builtin (own TypeError)."""',
#     '    import builtins as _bi',
#     '    if not a and not k and o is not _nxk_fast_missing:',
#     '        if type(o) is int:',
#     '            return _bi.bin(o)',
#     '    _args = () if o is _nxk_fast_missing else (o,)',
#     '    return _bi.bin(*_args + tuple(a), **k)',
#     '',
# ]
# 

_t("float", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyNumber_Float (float()/',
    '    nb_float in C). float() no-arg and exotic shapes go to the',
    '    real builtin (float() == 0.0; kwargs rejected by builtin)."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        return PyNumber_Float(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.float(*_args + tuple(a), **k)',
    '',
])

_t("list", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PySequence_List in C (handles',
    '    lists/tuples/strings/generators/dicts — same as list(it)).',
    '    list() no-arg returns []. Non-iterables raise the SAME',
    '    TypeError via the C API. Other shapes -> real builtin."""',
    '    import builtins as _bi',
    '    if not a and not k:',
    '        if o is _nxk_fast_missing:',
    '            return []',
    '        return PySequence_List(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.list(*_args + tuple(a), **k)',
    '',
])

_t("tuple", [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PySequence_Tuple in C.',
    '    tuple() no-arg returns (). Same errors as the builtin via',
    '    the C API. Other shapes -> real builtin."""',
    '    import builtins as _bi',
    '    if not a and not k:',
    '        if o is _nxk_fast_missing:',
    '            return ()',
    '        return PySequence_Tuple(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.tuple(*_args + tuple(a), **k)',
    '',
])

# --- multi-arity ops: fixed positional params + *a/**k tail ---

_t("int", [
    'def {impl}(object o=_nxk_fast_missing, object base=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: fixed-arity FASTCALL (common 0/1/2-arg shapes skip',
    '    the *args tuple AND **kwargs dict on the hot branch). int()/',
    '    int(x)/int(s, base) delegate to the real builtin with EXACT',
    '    errors; excess args/kwargs rebuilt for the builtin\'s OWN',
    '    TypeError (e.g. "int expected at most 2 arguments")."""',
    '    import builtins as _bi',
    '    if not a and not k:',
    '        if base is not _nxk_fast_missing:',
    '            if o is _nxk_fast_missing:',
    '                return _bi.int()',
    '            return _bi.int(o, base)',
    '        if o is _nxk_fast_missing:',
    '            return 0',
    '        return _bi.int(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    if base is not _nxk_fast_missing:',
    '        _args = _args + (base,)',
    '    return _bi.int(*_args + tuple(a), **k)',
    '',
])

_t("str", [
    'def {impl}(object o=_nxk_fast_missing, object e=_nxk_fast_missing, object r=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: 1-arg hot branch calls PyObject_Str (tp_str in C).',
    '    str() no-arg returns \'\'. 2/3-arg decode shapes and every',
    '    other shape delegate to the real builtin with EXACT errors',
    '    ("str expected at most 3 arguments", decoding errors)."""',
    '    import builtins as _bi',
    '    if not a and not k:',
    '        if e is _nxk_fast_missing and r is _nxk_fast_missing:',
    '            if o is _nxk_fast_missing:',
    "                return ''",
    '            return PyObject_Str(o)',
    '        if r is _nxk_fast_missing:',
    '            if o is _nxk_fast_missing or e is _nxk_fast_missing:',
    '                return _bi.str()',
    '            return _bi.str(o, e)',
    '        if o is _nxk_fast_missing or e is _nxk_fast_missing or r is _nxk_fast_missing:',
    '            return _bi.str()',
    '        return _bi.str(o, e, r)',
    '    _args = ()',
    '    if o is not _nxk_fast_missing:',
    '        _args = (o,)',
    '        if e is not _nxk_fast_missing:',
    '            _args = (o, e)',
    '            if r is not _nxk_fast_missing:',
    '                _args = (o, e, r)',
    '    return _bi.str(*_args + tuple(a), **k)',
    '',
])

_t("isinstance", [
    'def {impl}(object o=_nxk_fast_missing, object c=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: exact-2-arg hot branch calls PyObject_IsInstance in',
    '    C (no tuple pack, no kwargs dict — the builtin rejects kwargs',
    '    anyway). Every other shape -> real builtin (own TypeError)."""',
    '    import builtins as _bi',
    '    if not a and not k:',
    '        if o is not _nxk_fast_missing and c is not _nxk_fast_missing:',
    '            return bool(PyObject_IsInstance(o, c))',
    '    _args = ()',
    '    if o is not _nxk_fast_missing:',
    '        _args = (o,)',
    '        if c is not _nxk_fast_missing:',
    '            _args = (o, c)',
    '    return _bi.isinstance(*_args + tuple(a), **k)',
    '',
])

_t("issubclass", [
    'def {impl}(object d=_nxk_fast_missing, object c=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: exact-2-arg hot branch calls PyObject_IsSubclass in',
    '    C. Other shapes -> real builtin (own TypeError)."""',
    '    import builtins as _bi',
    '    if not a and not k:',
    '        if d is not _nxk_fast_missing and c is not _nxk_fast_missing:',
    '            return bool(PyObject_IsSubclass(d, c))',
    '    _args = ()',
    '    if d is not _nxk_fast_missing:',
    '        _args = (d,)',
    '        if c is not _nxk_fast_missing:',
    '            _args = (d, c)',
    '    return _bi.issubclass(*_args + tuple(a), **k)',
    '',
])

_t("hasattr", [
    'def {impl}(object o=_nxk_fast_missing, object n=_nxk_fast_missing, /, *a, **k):',
    '    """Fast: exact-2-arg str-name hot branch calls',
    '    PyObject_HasAttr (C-level getattr + exception swallow, no',
    '    CALL). Non-str names fall to the builtin for EXACT TypeError',
    '    parity. Other shapes -> real builtin."""',
    '    import builtins as _bi',
    '    if not a and not k:',
    '        if o is not _nxk_fast_missing and n is not _nxk_fast_missing:',
    '            if isinstance(n, str):',
    '                return bool(PyObject_HasAttr(o, n))',
    '            return _bi.hasattr(o, n)',
    '    _args = ()',
    '    if o is not _nxk_fast_missing:',
    '        _args = (o,)',
    '        if n is not _nxk_fast_missing:',
    '            _args = (o, n)',
    '    return _bi.hasattr(*_args + tuple(a), **k)',
    '',
])

# chr/oct deliberately NOT fast-tier (measured slower than passthrough;
# see FAST_OPS note). Their templates are kept for documentation but are
# NOT registered in _FAST_BODIES, so is_fast()/fast_body() ignore them
# and render_pyx emits the exact passthrough for them.
_CHR_BODY = [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Kept as documentation only: the range-guard chain costs',
    '    MORE than the passthrough CALL on the benchmark host (+70%).',
    '    NOT registered — chr stays passthrough."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        if type(o) is int and 0 <= o < 0x110000:',
    '            return _bi.chr(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.chr(*_args + tuple(a), **k)',
    '',
]

_OCT_BODY = [
    'def {impl}(object o=_nxk_fast_missing, /, *a, **k):',
    '    """Kept as documentation only: the exact-int guard costs MORE',
    '    than the passthrough CALL on the benchmark host (+109%).',
    '    NOT registered — oct stays passthrough."""',
    '    import builtins as _bi',
    '    if not a and not k and o is not _nxk_fast_missing:',
    '        if type(o) is int:',
    '            return _bi.oct(o)',
    '    _args = () if o is _nxk_fast_missing else (o,)',
    '    return _bi.oct(*_args + tuple(a), **k)',
    '',
]

# set/frozenset/dict/sorted/getattr deliberately NOT fast-tier:
# - set()/frozenset()/dict()/sorted() have kwarg-valid call shapes
#   (sorted key=/reverse=; dict **kw) where specialization wins little
#   and risks TypeError drift; getattr has 2/3-arg overloads plus
#   descriptor subtleties where the C call saves nothing measurable.
# - print/input/open/eval/exec/compile have I/O or code-object side
#   effects; they MUST stay exact passthroughs.


def fast_body(op: str, impl: str) -> "str | None":
    """Return the C-optimized Cython ``def`` for op, or None.

    The returned text uses the SAME impl symbol name as the passthrough
    path, so per-build uniqueness and the public token->impl scheme are
    unaffected. Never raises: unknown ops return None.
    """
    tmpl = _FAST_BODIES.get(op)
    if tmpl is None:
        return None
    return tmpl.format(impl=impl)


def is_fast(op: str) -> bool:
    """True if op has a hand-optimized fast-tier body."""
    return op in _FAST_BODIES
