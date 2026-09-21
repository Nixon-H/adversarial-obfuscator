"""Reference kernel for semantic lowering (Phase-1 pure-Python shim).

Every ``_nxk_*`` name the AST pass can emit is defined here with IDENTICAL
call shapes to the future native kernel, so lowered output runs today and
the --pytoc swap is import-only. Each shim documents which V10 family it
belongs to. Shim functions delegate to the real builtins (no behavior
change by design — obfuscation comes from the call-shape change, native
helpers come in Phase 2).
"""

from __future__ import annotations

import builtins as _bi


# I/O family
def _nxk_print(*a, **k):
    return _bi.print(*a, **k)


def _nxk_input(*a, **k):
    return _bi.input(*a, **k)


def _nxk_open(*a, **k):
    return _bi.open(*a, **k)


# scalar family
def _nxk_int(*a, **k):
    return _bi.int(*a, **k)


def _nxk_float(*a, **k):
    return _bi.float(*a, **k)


def _nxk_str(*a, **k):
    return _bi.str(*a, **k)


def _nxk_bool(*a, **k):
    return _bi.bool(*a, **k)


def _nxk_chr(*a, **k):
    return _bi.chr(*a, **k)


def _nxk_ord(*a, **k):
    return _bi.ord(*a, **k)


def _nxk_hex(*a, **k):
    return _bi.hex(*a, **k)


def _nxk_oct(*a, **k):
    return _bi.oct(*a, **k)


def _nxk_bin(*a, **k):
    return _bi.bin(*a, **k)


def _nxk_abs(*a, **k):
    return _bi.abs(*a, **k)


def _nxk_round(*a, **k):
    return _bi.round(*a, **k)


def _nxk_len(*a, **k):
    return _bi.len(*a, **k)


# string family (method-style: _nxk_str_join(sep, it))
def _nxk_str_join(sep, it):
    return sep.join(it)


def _nxk_str_split(s, *a, **k):
    return s.split(*a, **k)


def _nxk_str_format(s, *a, **k):
    return s.format(*a, **k)


def _nxk_str_encode(s, *a, **k):
    return s.encode(*a, **k)


def _nxk_str_decode(s, *a, **k):
    return s.decode(*a, **k)


def _nxk_str_upper(s):
    return s.upper()


def _nxk_str_lower(s):
    return s.lower()


# container family
def _nxk_list(*a, **k):
    return _bi.list(*a, **k)


def _nxk_tuple(*a, **k):
    return _bi.tuple(*a, **k)


def _nxk_dict(*a, **k):
    return _bi.dict(*a, **k)


def _nxk_set(*a, **k):
    return _bi.set(*a, **k)


def _nxk_frozenset(*a, **k):
    return _bi.frozenset(*a, **k)


def _nxk_sorted(*a, **k):
    return _bi.sorted(*a, **k)


def _nxk_reversed(*a, **k):
    return _bi.reversed(*a, **k)


def _nxk_enumerate(*a, **k):
    return _bi.enumerate(*a, **k)


def _nxk_zip(*a, **k):
    return _bi.zip(*a, **k)


# service family
def _nxk_getattr(*a, **k):
    return _bi.getattr(*a, **k)


def _nxk_setattr(*a, **k):
    return _bi.setattr(*a, **k)


def _nxk_hasattr(*a, **k):
    return _bi.hasattr(*a, **k)


def _nxk_isinstance(*a, **k):
    return _bi.isinstance(*a, **k)


def _nxk_issubclass(*a, **k):
    return _bi.issubclass(*a, **k)


def _nxk_callable(*a, **k):
    return _bi.callable(*a, **k)


def _nxk_id(*a, **k):
    return _bi.id(*a, **k)


def _nxk_hash(*a, **k):
    return _bi.hash(*a, **k)


# protocol family
def _nxk_iter(*a, **k):
    return _bi.iter(*a, **k)


def _nxk_next(*a, **k):
    return _bi.next(*a, **k)


def _nxk_repr(*a, **k):
    return _bi.repr(*a, **k)


def _nxk_bytes(*a, **k):
    return _bi.bytes(*a, **k)


# function family
def _nxk_map(*a, **k):
    return _bi.map(*a, **k)


def _nxk_filter(*a, **k):
    return _bi.filter(*a, **k)


def _nxk_any(*a, **k):
    return _bi.any(*a, **k)


def _nxk_all(*a, **k):
    return _bi.all(*a, **k)


def _nxk_sum(*a, **k):
    return _bi.sum(*a, **k)


def _nxk_min(*a, **k):
    return _bi.min(*a, **k)


def _nxk_max(*a, **k):
    return _bi.max(*a, **k)


# import family
def _nxk___import__(*a, **k):
    return _bi.__import__(*a, **k)


# fusion family: collapse a lowered chain into one dispatch.
def _nxk_fuse(*thunks):
    """Call each zero-arg thunk in order; return the last result."""
    _out = None
    for _t in thunks:
        _out = _t()
    return _out
