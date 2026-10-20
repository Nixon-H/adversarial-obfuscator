"""
lowering_perf.py

Purpose:
    Real benchmark measuring Phase-1 lowering-shim call overhead versus
    plain CPython, per lowering family. For each covered op it times
    N iterations of (a) the natural plain call spelling and (b) the
    shim-routed ``_nxk_*`` call shape, using time.perf_counter with
    best-of-R repeats, and reports ratio shim/plain per family
    (geometric mean of op ratios) plus per-op detail.

Architectural Role:
    Supplies the missing V10 perf-numbers evidence for
    obfuscator/lowering_DESIGN.md: the vendor claim (0.19x-1.56x of
    CPython, native kernel) is contrasted here with measured Phase-1
    pure-Python shim overhead on the current host. Numbers vary by
    machine; this script is the reproduction procedure.

Dependencies:
    ast (not needed at runtime), time, argparse, json, math,
    platform, contextlib, os, sys; obfuscator.lowering (family list),
    obfuscator.lowering_shim (kernels under test).

Security Relevance:
    Quantifies the per-call cost of semantic lowering so family
    opt-outs (--lowering) can be traded against protection depth
    with measured data instead of vendor claims.

Usage:
    NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py
    NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py \
        --iterations 20000 --repeats 5 --json /tmp/lowering_perf.json
    NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py \
        --families scalar,container --iterations 5000

Notes:
    - Interactive ops (input/open) and site-interactive helpers
      (breakpoint/help/copyright/credits/license) are NOT timed.
    - Async builtins (aiter/anext) are NOT timed (need an event loop).
    - Opt-in node-kind families (arithmetic/truth/slice/format/
      augassign) have no runtime functions yet (Phase-2) — not timed.
    - print is timed with stdout redirected to devnull in both arms.
    - Mutating-receiver ops build a fresh receiver inside each thunk
      in BOTH arms, so construction cost is symmetric.

Python 3.10 compatible: stdlib only, no match statements, no X|Y
annotations in evaluated positions.
"""

from __future__ import annotations

import argparse
import contextlib
import io as _io
import json
import math
import os
import platform
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from obfuscator import lowering  # noqa: E402
from obfuscator import lowering_shim as shim  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixtures (module level so thunks stay tiny)
# ---------------------------------------------------------------------------

_XS = [1, 2, 3]
_XD = [1, 2, 2]
_S = "hello world, hello"
_SEP = "-"
_IT = ["a", "b"]
_FMT = "{a}-{b}"
_MLS = "a\nb\n"
_ALNUM = "ab1"
_SP = "  "
_PRE = "pre_hi"
_SUF = "hi_suf"
_B = b"hi there"
_T = (1, 2, 2)
_D = {"k": 1, "j": 2}
_ST = {1, 2, 3}
_N = 255
_N2 = 256
_F = 1.5
_C = complex(1, 2)
_MF = [1, 2, 3]


class _Fresh(object):
    pass


class _WithAttr(object):
    def __init__(self):
        self.x = 1


def _do_exec_plain():
    ns = {}  # type: Dict[str, Any]
    exec("z = 41", ns)
    return ns.get("z")


def _do_exec_shim():
    ns = {}  # type: Dict[str, Any]
    shim._nxk_exec("z = 41", ns)
    return ns.get("z")


def _fuse_k1():
    return 1


def _fuse_k2():
    return 2


def _do_fuse_plain():
    _fuse_k1()
    return _fuse_k2()


def _do_fuse_shim():
    return shim._nxk_fuse(_fuse_k1, _fuse_k2)


def _eq(a, b):
    # type: (Any, Any) -> bool
    if isinstance(a, float) and isinstance(b, float):
        return a == b
    if isinstance(a, complex) and isinstance(b, complex):
        return a == b
    if isinstance(a, range) and isinstance(b, range):
        return list(a) == list(b)
    if isinstance(a, type) and isinstance(b, type):
        return a is b
    return a == b and type(a) is type(b)


def _isinstance_check(a, b):
    # type: (Any, Any) -> bool
    return isinstance(a, type(b)) or isinstance(b, type(a))


def _dict_check(a, b):
    # type: (Any, Any) -> bool
    return isinstance(a, dict) and isinstance(b, dict)


def _bytes_check(a, b):
    # type: (Any, Any) -> bool
    return bytes(a) == bytes(b)


def _list_check(a, b):
    # type: (Any, Any) -> bool
    return list(a) == list(b)


# ---------------------------------------------------------------------------
# Case table: one pure-compute (plain, shim) thunk pair per op.
# Fields: family, op, plain, shim, check, slow, quiet.
# ---------------------------------------------------------------------------

def _cases():
    # type: () -> List[Dict[str, Any]]
    nx = shim
    C = []  # type: List[Dict[str, Any]]

    def add(family, op, plain, shimed, check=None, slow=False,
            quiet=False, nativargs=None, nativkwargs=None):
        # type: (str, str, Callable, Callable, Any, bool, bool, Any, Any) -> None
        # nativargs/nativkwargs: explicit (args, kwargs) for the --native
        # arm (same call shape as the shim for bare builtins). Only set on
        # bare-builtin cases; method-style ops leave them None (skipped).
        C.append({"family": family, "op": op, "plain": plain,
                  "shim": shimed,
                  "check": check if check is not None else _eq,
                  "slow": slow, "quiet": quiet, "nativargs": nativargs,
                  "nativkwargs": nativkwargs})

    # io (print only; stdout suppressed in both arms)
    add("io", "print", lambda: print("hi"),
        lambda: nx._nxk_print("hi"), quiet=True)

    # scalar bare builtins
    add("scalar", "int", lambda: int("42"), lambda: nx._nxk_int("42"), nativargs=("42",))
    add("scalar", "float", lambda: float("1.5"),
        lambda: nx._nxk_float("1.5"), nativargs=("1.5",))
    add("scalar", "str", lambda: str(42), lambda: nx._nxk_str(42), nativargs=(42,))
    add("scalar", "bool", lambda: bool(1), lambda: nx._nxk_bool(1), nativargs=(1,))
    add("scalar", "chr", lambda: chr(65), lambda: nx._nxk_chr(65), nativargs=(65,))
    add("scalar", "ord", lambda: ord("A"), lambda: nx._nxk_ord("A"), nativargs=("A",))
    add("scalar", "hex", lambda: hex(255), lambda: nx._nxk_hex(255), nativargs=(255,))
    add("scalar", "oct", lambda: oct(8), lambda: nx._nxk_oct(8), nativargs=(8,))
    add("scalar", "bin", lambda: bin(5), lambda: nx._nxk_bin(5), nativargs=(5,))
    add("scalar", "abs", lambda: abs(-3), lambda: nx._nxk_abs(-3), nativargs=(-3,))
    add("scalar", "round", lambda: round(1.567, 2),
        lambda: nx._nxk_round(1.567, 2), nativargs=(1.567, 2,))
    add("scalar", "len", lambda: len(_XS), lambda: nx._nxk_len(_XS), nativargs=(_XS,))
    # scalar numeric methods
    add("scalar", "int.bit_length", lambda: _N.bit_length(),
        lambda: nx._nxk_int_bit_length(_N))
    add("scalar", "int.to_bytes", lambda: _N2.to_bytes(2, "big"),
        lambda: nx._nxk_int_to_bytes(_N2, 2, "big"))
    add("scalar", "float.hex", lambda: _F.hex(),
        lambda: nx._nxk_float_hex(_F))
    add("scalar", "float.as_integer_ratio",
        lambda: _F.as_integer_ratio(),
        lambda: nx._nxk_float_as_integer_ratio(_F))
    add("scalar", "complex.conjugate", lambda: _C.conjugate(),
        lambda: nx._nxk_complex_conjugate(_C))

    # string methods
    add("string", "str.join", lambda: _SEP.join(_IT),
        lambda: nx._nxk_str_join(_SEP, _IT))
    add("string", "str.split", lambda: _S.split(","),
        lambda: nx._nxk_str_split(_S, ","))
    add("string", "str.format", lambda: _FMT.format(a=1, b=2),
        lambda: nx._nxk_str_format(_FMT, a=1, b=2))
    add("string", "str.encode", lambda: _S.encode(),
        lambda: nx._nxk_str_encode(_S))
    add("string", "bytes.decode", lambda: b"hi".decode(),
        lambda: nx._nxk_bytes_decode(b"hi"))
    add("string", "str.upper", lambda: _S.upper(),
        lambda: nx._nxk_str_upper(_S))
    add("string", "str.lower", lambda: _S.lower(),
        lambda: nx._nxk_str_lower(_S))
    add("string", "str.strip", lambda: _SP.strip() or "  hi  ".strip(),
        lambda: nx._nxk_str_strip("  hi  "))
    add("string", "str.lstrip", lambda: "  hi".lstrip(),
        lambda: nx._nxk_str_lstrip("  hi"))
    add("string", "str.rstrip", lambda: "hi  ".rstrip(),
        lambda: nx._nxk_str_rstrip("hi  "))
    add("string", "str.replace", lambda: _S.replace("l", "L"),
        lambda: nx._nxk_str_replace(_S, "l", "L"))
    add("string", "str.find", lambda: _S.find("o"),
        lambda: nx._nxk_str_find(_S, "o"))
    add("string", "str.rfind", lambda: _S.rfind("o"),
        lambda: nx._nxk_str_rfind(_S, "o"))
    add("string", "str.index", lambda: _S.index("o"),
        lambda: nx._nxk_str_index(_S, "o"))
    add("string", "str.count", lambda: _S.count("l"),
        lambda: nx._nxk_str_count(_S, "l"))
    add("string", "str.startswith", lambda: _S.startswith("he"),
        lambda: nx._nxk_str_startswith(_S, "he"))
    add("string", "str.endswith", lambda: _S.endswith("lo"),
        lambda: nx._nxk_str_endswith(_S, "lo"))
    add("string", "str.partition", lambda: _S.partition(","),
        lambda: nx._nxk_str_partition(_S, ","))
    add("string", "str.rpartition", lambda: _S.rpartition(","),
        lambda: nx._nxk_str_rpartition(_S, ","))
    add("string", "str.splitlines", lambda: _MLS.splitlines(),
        lambda: nx._nxk_str_splitlines(_MLS))
    add("string", "str.zfill", lambda: _S.zfill(20),
        lambda: nx._nxk_str_zfill(_S, 20))
    add("string", "str.ljust", lambda: _S.ljust(20, "-"),
        lambda: nx._nxk_str_ljust(_S, 20, "-"))
    add("string", "str.rjust", lambda: _S.rjust(20, "-"),
        lambda: nx._nxk_str_rjust(_S, 20, "-"))
    add("string", "str.center", lambda: _S.center(20, "-"),
        lambda: nx._nxk_str_center(_S, 20, "-"))
    add("string", "str.swapcase", lambda: _S.swapcase(),
        lambda: nx._nxk_str_swapcase(_S))
    add("string", "str.isalnum", lambda: _ALNUM.isalnum(),
        lambda: nx._nxk_str_isalnum(_ALNUM))
    add("string", "str.isspace", lambda: _SP.isspace(),
        lambda: nx._nxk_str_isspace(_SP))
    add("string", "str.maketrans",
        lambda: str.maketrans("a", "X"),
        lambda: nx._nxk_str_maketrans("a", "X"))
    add("string", "str.removeprefix", lambda: _PRE.removeprefix("pre_"),
        lambda: nx._nxk_str_removeprefix(_PRE, "pre_"))
    add("string", "str.removesuffix", lambda: _SUF.removesuffix("_suf"),
        lambda: nx._nxk_str_removesuffix(_SUF, "_suf"))

    # container bare builtins
    add("container", "list", lambda: list((1, 2)),
        lambda: nx._nxk_list((1, 2)), nativargs=((1, 2),))
    add("container", "tuple", lambda: tuple([1, 2]),
        lambda: nx._nxk_tuple([1, 2]), nativargs=([1, 2],))
    add("container", "dict", lambda: dict(a=1),
        lambda: nx._nxk_dict(a=1), nativkwargs={'a': 1})
    add("container", "set", lambda: set([1, 2, 2]),
        lambda: nx._nxk_set([1, 2, 2]), nativargs=([1, 2, 2],))
    add("container", "frozenset", lambda: frozenset([1, 2]),
        lambda: nx._nxk_frozenset([1, 2]), nativargs=([1, 2],))
    add("container", "sorted", lambda: sorted([3, 1, 2]),
        lambda: nx._nxk_sorted([3, 1, 2]), nativargs=([3, 1, 2],))
    add("container", "reversed", lambda: reversed([1, 2, 3]),
        lambda: nx._nxk_reversed([1, 2, 3]), check=_list_check, nativargs=([1, 2, 3],))
    add("container", "enumerate", lambda: enumerate(["a", "b"]),
        lambda: nx._nxk_enumerate(["a", "b"]), check=_list_check, nativargs=(["a", "b"],))
    add("container", "zip", lambda: zip([1, 2], [3, 4]),
        lambda: nx._nxk_zip([1, 2], [3, 4]), check=_list_check, nativargs=([1, 2], [3, 4],))

    # protocol
    add("protocol", "iter", lambda: iter(_XS),
        lambda: nx._nxk_iter(_XS), check=_list_check, nativargs=(_XS,))
    add("protocol", "next", lambda: next(iter([1])),
        lambda: nx._nxk_next(iter([1])), nativargs=(iter([1]),))
    add("protocol", "repr", lambda: repr(_S),
        lambda: nx._nxk_repr(_S), nativargs=(_S,))
    add("protocol", "bytes", lambda: bytes("hi", "utf-8"),
        lambda: nx._nxk_bytes("hi", "utf-8"), nativargs=("hi", "utf-8",))

    # service
    add("service", "getattr", lambda: getattr(_S, "upper")(),
        lambda: nx._nxk_getattr(_S, "upper")())
    add("service", "setattr", lambda: setattr(_Fresh(), "x", 1),
        lambda: nx._nxk_setattr(_Fresh(), "x", 1), nativargs=(_Fresh(), "x", 1,))
    add("service", "hasattr", lambda: hasattr(_S, "upper"),
        lambda: nx._nxk_hasattr(_S, "upper"), nativargs=(_S, "upper",))
    add("service", "isinstance", lambda: isinstance(_S, str),
        lambda: nx._nxk_isinstance(_S, str), nativargs=(_S, str,))
    add("service", "issubclass", lambda: issubclass(bool, int),
        lambda: nx._nxk_issubclass(bool, int), nativargs=(bool, int,))
    add("service", "callable", lambda: callable(len),
        lambda: nx._nxk_callable(len), nativargs=(len,))
    add("service", "id", lambda: id(_S), lambda: nx._nxk_id(_S),
        check=_isinstance_check, nativargs=(_S,))
    add("service", "hash", lambda: hash(_S),
        lambda: nx._nxk_hash(_S), nativargs=(_S,))
    add("service", "vars", lambda: sorted(vars(_WithAttr())),
        lambda: sorted(nx._nxk_vars(_WithAttr())))
    add("service", "dir", lambda: dir([]), lambda: nx._nxk_dir([]), nativargs=([],))
    add("service", "globals", lambda: isinstance(globals(), dict),
        lambda: nx._nxk_globals() is not None and
        isinstance(nx._nxk_globals(), dict))
    add("service", "locals", lambda: locals(),
        lambda: nx._nxk_locals(), check=_dict_check)
    add("service", "compile",
        lambda: compile("40 + 2", "<bench>", "eval"),
        lambda: nx._nxk_compile("40 + 2", "<bench>", "eval"),
        check=_isinstance_check, slow=True, nativargs=("40 + 2", "<bench>", "eval",))
    add("service", "eval", lambda: eval("40 + 2"),
        lambda: nx._nxk_eval("40 + 2"), nativargs=("40 + 2",))
    add("service", "exec", _do_exec_plain, _do_exec_shim, slow=True)
    add("service", "memoryview", lambda: memoryview(_B),
        lambda: nx._nxk_memoryview(_B), check=_bytes_check, nativargs=(_B,))

    # range family (range + async-iteration leftovers living here)
    add("range", "range", lambda: range(3), lambda: nx._nxk_range(3), nativargs=(3,))
    add("range", "ascii", lambda: ascii("hé"),
        lambda: nx._nxk_ascii("hé"), nativargs=("hé",))
    add("range", "format", lambda: format(3.14159, ".2f"),
        lambda: nx._nxk_format(3.14159, ".2f"), nativargs=(3.14159, ".2f",))
    add("range", "slice", lambda: slice(1, 10, 2),
        lambda: nx._nxk_slice(1, 10, 2), nativargs=(1, 10, 2,))

    # function family (lazy iterators compared via list())
    add("function", "map", lambda: map(str, _MF),
        lambda: nx._nxk_map(str, _MF), check=_list_check, nativargs=(str, _MF,))
    add("function", "filter", lambda: filter(bool, [0, 1, 2]),
        lambda: nx._nxk_filter(bool, [0, 1, 2]), check=_list_check, nativargs=(bool, [0, 1, 2],))
    add("function", "any", lambda: any([0, 1]),
        lambda: nx._nxk_any([0, 1]), nativargs=([0, 1],))
    add("function", "all", lambda: all([1, 2]),
        lambda: nx._nxk_all([1, 2]), nativargs=([1, 2],))
    add("function", "sum", lambda: sum([1, 2, 3]),
        lambda: nx._nxk_sum([1, 2, 3]), nativargs=([1, 2, 3],))
    add("function", "min", lambda: min([3, 1, 2]),
        lambda: nx._nxk_min([3, 1, 2]), nativargs=([3, 1, 2],))
    add("function", "max", lambda: max([3, 1, 2]),
        lambda: nx._nxk_max([3, 1, 2]), nativargs=([3, 1, 2],))
    add("function", "pow", lambda: pow(2, 10),
        lambda: nx._nxk_pow(2, 10), nativargs=(2, 10,))
    add("function", "divmod", lambda: divmod(7, 3),
        lambda: nx._nxk_divmod(7, 3), nativargs=(7, 3,))
    add("function", "complex", lambda: complex(1, 2),
        lambda: nx._nxk_complex(1, 2), nativargs=(1, 2,))

    # import family (only the non-interactive op)
    add("import", "__import__", lambda: __import__("math").pi,
        lambda: nx._nxk___import__("math").pi)

    # fusion dispatch
    add("fusion", "fuse", _do_fuse_plain, _do_fuse_shim)

    # list methods
    add("list", "list.append", lambda: [1].append(2),
        lambda: nx._nxk_list_append([1], 2))
    add("list", "list.extend", lambda: [1].extend([2, 3]),
        lambda: nx._nxk_list_extend([1], [2, 3]))
    add("list", "list.insert", lambda: [1, 3].insert(1, 2),
        lambda: nx._nxk_list_insert([1, 3], 1, 2))
    add("list", "list.remove", lambda: [1, 2].remove(1),
        lambda: nx._nxk_list_remove([1, 2], 1))
    add("list", "list.pop", lambda: [1, 2].pop(),
        lambda: nx._nxk_list_pop([1, 2]))
    add("list", "list.clear", lambda: [1, 2].clear(),
        lambda: nx._nxk_list_clear([1, 2]))
    add("list", "list.index", lambda: _XS.index(2),
        lambda: nx._nxk_list_index(_XS, 2))
    add("list", "list.count", lambda: _XD.count(2),
        lambda: nx._nxk_list_count(_XD, 2))
    add("list", "list.sort", lambda: [3, 1, 2].sort(),
        lambda: nx._nxk_list_sort([3, 1, 2]))
    add("list", "list.reverse", lambda: [1, 2, 3].reverse(),
        lambda: nx._nxk_list_reverse([1, 2, 3]))
    add("list", "list.copy", lambda: _XS.copy(),
        lambda: nx._nxk_list_copy(_XS))

    # dict methods
    add("dict", "dict.get", lambda: _D.get("k"),
        lambda: nx._nxk_dict_get(_D, "k"))
    add("dict", "dict.keys", lambda: sorted(_D.keys()),
        lambda: sorted(nx._nxk_dict_keys(_D)))
    add("dict", "dict.values", lambda: sorted(_D.values()),
        lambda: sorted(nx._nxk_dict_values(_D)))
    add("dict", "dict.items", lambda: sorted(_D.items()),
        lambda: sorted(nx._nxk_dict_items(_D)))
    add("dict", "dict.pop", lambda: {"k": 1}.pop("k"),
        lambda: nx._nxk_dict_pop({"k": 1}, "k"))
    add("dict", "dict.popitem", lambda: {"k": 1}.popitem(),
        lambda: nx._nxk_dict_popitem({"k": 1}))
    add("dict", "dict.setdefault", lambda: {}.setdefault("k", 5),
        lambda: nx._nxk_dict_setdefault({}, "k", 5))
    add("dict", "dict.update", lambda: {}.update({"k": 1}),
        lambda: nx._nxk_dict_update({}, {"k": 1}))
    add("dict", "dict.clear", lambda: {"k": 1}.clear(),
        lambda: nx._nxk_dict_clear({"k": 1}))
    add("dict", "dict.copy", lambda: _D.copy(),
        lambda: nx._nxk_dict_copy(_D))
    add("dict", "dict.fromkeys", lambda: dict.fromkeys("ab"),
        lambda: nx._nxk_dict_fromkeys("ab"))

    # set methods
    add("set", "set.add", lambda: set().add(1),
        lambda: nx._nxk_set_add(set(), 1))
    add("set", "set.discard", lambda: {1}.discard(1),
        lambda: nx._nxk_set_discard({1}, 1))
    add("set", "set.remove", lambda: {1}.remove(1),
        lambda: nx._nxk_set_remove({1}, 1))
    add("set", "set.pop", lambda: {1}.pop(),
        lambda: nx._nxk_set_pop({1}))
    add("set", "set.clear", lambda: {1}.clear(),
        lambda: nx._nxk_set_clear({1}))
    add("set", "set.union", lambda: sorted(_ST.union({4})),
        lambda: sorted(nx._nxk_set_union(_ST, {4})))
    add("set", "set.intersection",
        lambda: sorted(_ST.intersection({2, 4})),
        lambda: sorted(nx._nxk_set_intersection(_ST, {2, 4})))
    add("set", "set.difference",
        lambda: sorted(_ST.difference({2})),
        lambda: sorted(nx._nxk_set_difference(_ST, {2})))
    add("set", "set.symmetric_difference",
        lambda: sorted(_ST.symmetric_difference({2, 4})),
        lambda: sorted(nx._nxk_set_symmetric_difference(_ST, {2, 4})))
    add("set", "set.issubset", lambda: {1}.issubset({1, 2}),
        lambda: nx._nxk_set_issubset({1}, {1, 2}))
    add("set", "set.issuperset", lambda: _ST.issuperset({1}),
        lambda: nx._nxk_set_issuperset(_ST, {1}))
    add("set", "set.copy", lambda: _ST.copy(),
        lambda: nx._nxk_set_copy(_ST))

    # tuple methods
    add("tuple", "tuple.count", lambda: _T.count(2),
        lambda: nx._nxk_tuple_count(_T, 2))
    add("tuple", "tuple.index", lambda: _T.index(2),
        lambda: nx._nxk_tuple_index(_T, 2))

    # bytes methods
    add("bytes", "bytes.decode", lambda: b"hi".decode(),
        lambda: nx._nxk_bytes_decode(b"hi"))
    add("bytes", "bytes.hex", lambda: b"ab".hex(),
        lambda: nx._nxk_bytes_hex(b"ab"))
    add("bytes", "bytes.fromhex", lambda: bytes.fromhex("4142"),
        lambda: nx._nxk_bytes_fromhex("4142"))

    return C


CASES = _cases()


def _load_native_module(spec):
    # type: (str) -> Any
    """Build or load a native kernel module for the --native arm.

    spec == "build": render a fresh per-build-symbols kernel and cythonize
    it into a temp dir. A .pyx path: cythonize it. A .so/.pyd path: load
    it directly. Returns the loaded module or None (with a stderr note).
    """
    import importlib.util as _ilu
    import tempfile as _tf
    try:
        from obfuscator.kernel_gen import (
            cythonize_kernel as _kc,
            render_pyx as _kr,
        )
    except Exception as _e:
        sys.stderr.write("native arm unavailable (kernel_gen: %s)\n" % (_e,))
        return None
    try:
        if spec == "build":
            import secrets as _sec
            _seed = _sec.token_bytes(16)
            _text, _mod, _omap = _kr(_seed)
            _d = _tf.mkdtemp(prefix="nxknative_")
            _pyx = os.path.join(_d, _mod + ".pyx")
            with open(_pyx, "w", encoding="utf-8") as _f:
                _f.write(_text)
            _so, _msg = _kc(_pyx, _d)
            if _so is None:
                sys.stderr.write("native arm skipped: %s\n" % (_msg,))
                return None
            _spec = _ilu.spec_from_file_location(_mod, _so)
            _m = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_m)
            return _m
        if spec.endswith(".pyx") and os.path.isfile(spec):
            _base = os.path.splitext(os.path.basename(spec))[0]
            _d = _tf.mkdtemp(prefix="nxknative_")
            _so, _msg = _kc(spec, _d)
            if _so is None:
                sys.stderr.write("native arm skipped: %s\n" % (_msg,))
                return None
            _spec = _ilu.spec_from_file_location(_base, _so)
            _m = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_m)
            return _m
        if (spec.endswith(".so") or spec.endswith(".pyd")) and \
                os.path.isfile(spec):
            _base = os.path.splitext(os.path.basename(spec))[0]
            _spec = _ilu.spec_from_file_location(_base, spec)
            _m = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_m)
            return _m
        sys.stderr.write("native arm skipped: unknown spec %r "
                         "(use 'build', a .pyx path, or a .so path)\n"
                         % (spec,))
        return None
    except Exception as _e:
        sys.stderr.write("native arm skipped: %s\n" % (_e,))
        return None

# Timing defaults
DEFAULT_N = 20000
DEFAULT_REPEATS = 5
SLOW_DIVISOR = 10  # slow ops (compile/exec) run at N // 10
MIN_N = 20


def _devnull():
    # type: () -> Any
    return open(os.devnull, "w")


def _best(fn, n, repeats, quiet=False):
    # type: (Callable, int, int, bool) -> float
    # Warmup (untimed) so first-run effects don't pollute best-of.
    warm = n if n < 1000 else 1000
    if quiet:
        with contextlib.redirect_stdout(_io.StringIO()):
            for _ in range(warm):
                fn()
    else:
        for _ in range(warm):
            fn()
    best = float("inf")
    for _ in range(repeats):
        if quiet:
            with contextlib.redirect_stdout(_io.StringIO()):
                t0 = time.perf_counter()
                for _ in range(n):
                    fn()
                dt = time.perf_counter() - t0
        else:
            t0 = time.perf_counter()
            for _ in range(n):
                fn()
            dt = time.perf_counter() - t0
        if dt < best:
            best = dt
    return best


def time_case(case, n, repeats, native_module=None):
    # type: (Dict[str, Any], int, int, Any) -> Dict[str, Any]
    nn = max(MIN_N, n // SLOW_DIVISOR) if case["slow"] else n
    plain_s = _best(case["plain"], nn, repeats, case["quiet"])
    shim_s = _best(case["shim"], nn, repeats, case["quiet"])
    native_s = None
    native_ok = None
    if native_module is not None and case.get("nativargs") is not None \
            or (native_module is not None
                and case.get("nativkwargs") is not None):
        try:
            from obfuscator.kernel_gen import _token as _kg_token
            _tok = _kg_token(case["op"])
            _native_fn = getattr(native_module, _tok, None)
            if _native_fn is not None:
                _na = tuple(case.get("nativargs") or ())
                _nk = dict(case.get("nativkwargs") or {})

                def _nthunk():
                    return _native_fn(*_na, **_nk)

                native_s = _best(_nthunk, nn, repeats, case["quiet"])
                try:
                    if case["quiet"]:
                        with contextlib.redirect_stdout(_io.StringIO()):
                            _nres = _nthunk()
                            _pres2 = case["plain"]()
                    else:
                        _nres = _nthunk()
                        _pres2 = case["plain"]()
                    native_ok = bool(case["check"](_pres2, _nres))
                except Exception:
                    native_ok = False
        except Exception:
            native_s = None
    if case["quiet"]:
        with contextlib.redirect_stdout(_io.StringIO()):
            pres = case["plain"]()
            sres = case["shim"]()
    else:
        pres = case["plain"]()
        sres = case["shim"]()
    ok = bool(case["check"](pres, sres))
    ratio = (shim_s / plain_s) if plain_s > 0 else float("inf")
    out = {"family": case["family"], "op": case["op"], "n": nn,
           "repeats": repeats,
           "plain_s": plain_s, "shim_s": shim_s,
           "plain_us": plain_s / nn * 1e6, "shim_us": shim_s / nn * 1e6,
           "ratio": ratio, "ok": ok}
    if native_s is not None:
        out["native_s"] = native_s
        out["native_us"] = native_s / nn * 1e6
        out["native_ratio"] = (native_s / plain_s) \
            if plain_s > 0 else float("inf")
        out["native_ok"] = native_ok
    return out


def _geomean(xs):
    # type: (List[float]) -> float
    logs = [math.log(x) for x in xs if x > 0 and math.isfinite(x)]
    if not logs:
        return float("nan")
    return math.exp(sum(logs) / len(logs))


def run_benchmark(n=DEFAULT_N, repeats=DEFAULT_REPEATS,
                   families=None, native_module=None):
    # type: (int, int, Optional[List[str]], Any) -> Dict[str, Any]
    if families:
        wanted = set(families)
        unknown = wanted - set(lowering.FAMILIES)
        if unknown:
            raise ValueError("unknown lowering family: %s"
                             % sorted(unknown))
        todo = [c for c in CASES if c["family"] in wanted]
    else:
        todo = list(CASES)
    results = [time_case(c, n, repeats, native_module=native_module)
               for c in todo]
    fams = {}  # type: Dict[str, Dict[str, Any]]
    for r in results:
        fams.setdefault(r["family"], []).append(r)
    summary = {}
    for fam, rows in fams.items():
        ratios = [r["ratio"] for r in rows]
        summary[fam] = {"ops": len(rows),
                        "geomean": _geomean(ratios),
                        "min": min(ratios), "max": max(ratios),
                        "all_ok": all(r["ok"] for r in rows)}
    meta = {"python": platform.python_version(),
            "platform": platform.platform(),
            "host": platform.node(),
            "date": time.strftime("%Y-%m-%d"),
            "iterations": n, "repeats": repeats,
            "timer": "time.perf_counter best-of-%d" % repeats,
            "families": sorted(fams)}
    return {"meta": meta, "results": results, "summary": summary}


def format_markdown(bundle):
    # type: (Dict[str, Any]) -> str
    meta = bundle["meta"]
    summary = bundle["summary"]
    results = bundle["results"]
    L = []  # type: List[str]
    L.append("# Lowering-shim overhead vs plain CPython (measured)")
    L.append("")
    L.append("host=%s platform=%s python=%s date=%s N=%d repeats=%s" % (
        meta["host"], meta["platform"], meta["python"], meta["date"],
        meta["iterations"], meta["repeats"]))
    L.append("")
    L.append("Ratio = shim_time / plain_time (best-of-%d "
             "time.perf_counter; <1.0 means the shim timed faster, "
             "i.e. noise/faster dispatch on that op)." % meta["repeats"])
    _has_native = any("native_us" in r for r in results)
    if _has_native:
        L.append("native_ratio = native_time / plain_time (same machine, "
                 "fresh per-build-symbols Cython kernel via --native build).")
    L.append("")
    L.append("## Per-family summary (geometric mean of op ratios)")
    L.append("")
    if _has_native:
        L.append("| family | ops | geomean shim/plain | min | max | parity | "
                 "native ops | geomean native/plain | native parity |")
        L.append("|---|---|---|---|---|---|---|---|---|")
    else:
        L.append("| family | ops | geomean shim/plain | min | max | parity |")
        L.append("|---|---|---|---|---|---|")
    for fam in sorted(summary):
        s = summary[fam]
        if _has_native:
            _nratios = [r["native_ratio"] for r in results
                        if r["family"] == fam and "native_ratio" in r
                        and isinstance(r["native_ratio"], float)
                        and math.isfinite(r["native_ratio"])
                        and r["native_ratio"] > 0]
            _nok = [r for r in results if r["family"] == fam
                    and "native_ok" in r]
            _ng = _geomean(_nratios) if _nratios else float("nan")
            _npar = ("ok" if all(r["native_ok"] for r in _nok)
                     else ("MISMATCH" if _nok else "n/a"))
            L.append("| %s | %d | %.3f | %.3f | %.3f | %s | %d | %.3f | %s |"
                     % (fam, s["ops"], s["geomean"], s["min"], s["max"],
                        "ok" if s["all_ok"] else "MISMATCH",
                        len(_nratios), _ng, _npar))
        else:
            L.append("| %s | %d | %.3f | %.3f | %.3f | %s |" % (
                fam, s["ops"], s["geomean"], s["min"], s["max"],
                "ok" if s["all_ok"] else "MISMATCH"))
    L.append("")
    L.append("## Per-op detail (µs per call)")
    L.append("")
    if _has_native:
        L.append("| family | op | plain µs | shim µs | ratio | parity | "
                 "native µs | native ratio | native parity |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
    else:
        L.append("| family | op | plain µs | shim µs | ratio | parity |")
        L.append("|---|---|---|---|---|---|")
    for r in results:
        if _has_native:
            if "native_us" in r:
                L.append("| %s | %s | %.4f | %.4f | %.3f | %s | %.4f | "
                         "%.3f | %s |" % (
                             r["family"], r["op"], r["plain_us"],
                             r["shim_us"], r["ratio"],
                             "ok" if r["ok"] else "MISMATCH",
                             r["native_us"], r["native_ratio"],
                             "ok" if r.get("native_ok") else "MISMATCH"))
            else:
                L.append("| %s | %s | %.4f | %.4f | %.3f | %s | n/a | "
                         "n/a | n/a |" % (
                             r["family"], r["op"], r["plain_us"],
                             r["shim_us"], r["ratio"],
                             "ok" if r["ok"] else "MISMATCH"))
        else:
            L.append("| %s | %s | %.4f | %.4f | %.3f | %s |" % (
                r["family"], r["op"], r["plain_us"], r["shim_us"],
                r["ratio"], "ok" if r["ok"] else "MISMATCH"))
    L.append("")
    return "\n".join(L)


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    ap = argparse.ArgumentParser(
        description="Time lowering-shim calls vs plain CPython "
                    "per family (best-of-R, markdown table + JSON).")
    ap.add_argument("--iterations", type=int, default=DEFAULT_N,
                    help="timed iterations per op per arm (default %d)"
                    % DEFAULT_N)
    ap.add_argument("--repeats", type=int, default=DEFAULT_REPEATS,
                    help="best-of-R repeats (default %d)"
                    % DEFAULT_REPEATS)
    ap.add_argument("--families", default="",
                    help="CSV family subset (default: all benchmarked)")
    ap.add_argument("--json", default="",
                    help="optional path to write full JSON results")
    ap.add_argument("--native", default="",
                    help="also time the NATIVE Cython kernel: 'build' (fresh "
                         "per-build-symbols kernel), a .pyx path, or a .so "
                         "path. Adds native_us/native_ratio/native_ok. "
                         "Bare builtins auto-covered via recorded args; "
                         "method-style ops report n/a (shape differs).")
    args = ap.parse_args(argv)
    fams = [f.strip() for f in args.families.split(",") if f.strip()]
    native_mod = _load_native_module(args.native) if args.native else None
    bundle = run_benchmark(n=args.iterations, repeats=args.repeats,
                           families=fams or None,
                           native_module=native_mod)
    print(format_markdown(bundle))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2, sort_keys=True)
        print("wrote %s" % args.json)
    bad = [r for r in bundle["results"] if not r["ok"]]
    if bad:
        print("PARITY MISMATCHES: %s"
              % [r["op"] for r in bad])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
