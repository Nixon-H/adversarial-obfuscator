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


# scalar family — numeric method ops (receiver first, like str methods)
def _nxk_int_bit_length(n):
    return n.bit_length()


def _nxk_int_to_bytes(n, *a, **k):
    return n.to_bytes(*a, **k)


def _nxk_float_hex(f):
    return f.hex()


def _nxk_float_as_integer_ratio(f):
    return f.as_integer_ratio()


def _nxk_complex_conjugate(c):
    return c.conjugate()


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


def _nxk_str_strip(s, *a, **k):
    return s.strip(*a, **k)


def _nxk_str_lstrip(s, *a, **k):
    return s.lstrip(*a, **k)


def _nxk_str_rstrip(s, *a, **k):
    return s.rstrip(*a, **k)


def _nxk_str_replace(s, *a, **k):
    return s.replace(*a, **k)


def _nxk_str_find(s, *a, **k):
    return s.find(*a, **k)


def _nxk_str_rfind(s, *a, **k):
    return s.rfind(*a, **k)


def _nxk_str_index(s, *a, **k):
    return s.index(*a, **k)


def _nxk_str_count(s, *a, **k):
    return s.count(*a, **k)


def _nxk_str_startswith(s, *a, **k):
    return s.startswith(*a, **k)


def _nxk_str_endswith(s, *a, **k):
    return s.endswith(*a, **k)


def _nxk_str_partition(s, *a, **k):
    return s.partition(*a, **k)


def _nxk_str_rpartition(s, *a, **k):
    return s.rpartition(*a, **k)


def _nxk_str_splitlines(s, *a, **k):
    return s.splitlines(*a, **k)


def _nxk_str_zfill(s, *a, **k):
    return s.zfill(*a, **k)


def _nxk_str_ljust(s, *a, **k):
    return s.ljust(*a, **k)


def _nxk_str_rjust(s, *a, **k):
    return s.rjust(*a, **k)


def _nxk_str_center(s, *a, **k):
    return s.center(*a, **k)


def _nxk_str_swapcase(s):
    return s.swapcase()


def _nxk_str_isalnum(s):
    return s.isalnum()


def _nxk_str_isspace(s):
    return s.isspace()


def _nxk_str_maketrans(*a, **k):
    return _bi.str.maketrans(*a, **k)


def _nxk_str_removeprefix(s, *a, **k):
    return s.removeprefix(*a, **k)


def _nxk_str_removesuffix(s, *a, **k):
    return s.removesuffix(*a, **k)


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


# list family (method-style: receiver first)
def _nxk_list_append(xs, *a, **k):
    return xs.append(*a, **k)


def _nxk_list_extend(xs, *a, **k):
    return xs.extend(*a, **k)


def _nxk_list_insert(xs, *a, **k):
    return xs.insert(*a, **k)


def _nxk_list_remove(xs, *a, **k):
    return xs.remove(*a, **k)


def _nxk_list_pop(xs, *a, **k):
    return xs.pop(*a, **k)


def _nxk_list_clear(xs):
    return xs.clear()


def _nxk_list_index(xs, *a, **k):
    return xs.index(*a, **k)


def _nxk_list_count(xs, *a, **k):
    return xs.count(*a, **k)


def _nxk_list_sort(xs, *a, **k):
    return xs.sort(*a, **k)


def _nxk_list_reverse(xs):
    return xs.reverse()


def _nxk_list_copy(xs):
    return xs.copy()


# dict family (method-style: receiver first; fromkeys is a classmethod)
def _nxk_dict_get(d, *a, **k):
    return d.get(*a, **k)


def _nxk_dict_keys(d):
    return d.keys()


def _nxk_dict_values(d):
    return d.values()


def _nxk_dict_items(d):
    return d.items()


def _nxk_dict_pop(d, *a, **k):
    return d.pop(*a, **k)


def _nxk_dict_popitem(d):
    return d.popitem()


def _nxk_dict_setdefault(d, *a, **k):
    return d.setdefault(*a, **k)


def _nxk_dict_update(d, *a, **k):
    return d.update(*a, **k)


def _nxk_dict_clear(d):
    return d.clear()


def _nxk_dict_copy(d):
    return d.copy()


def _nxk_dict_fromkeys(*a, **k):
    return _bi.dict.fromkeys(*a, **k)


# set family (method-style: receiver first)
def _nxk_set_add(st, *a, **k):
    return st.add(*a, **k)


def _nxk_set_discard(st, *a, **k):
    return st.discard(*a, **k)


def _nxk_set_remove(st, *a, **k):
    return st.remove(*a, **k)


def _nxk_set_pop(st):
    return st.pop()


def _nxk_set_clear(st):
    return st.clear()


def _nxk_set_union(st, *a, **k):
    return st.union(*a, **k)


def _nxk_set_intersection(st, *a, **k):
    return st.intersection(*a, **k)


def _nxk_set_difference(st, *a, **k):
    return st.difference(*a, **k)


def _nxk_set_symmetric_difference(st, *a, **k):
    return st.symmetric_difference(*a, **k)


def _nxk_set_issubset(st, *a, **k):
    return st.issubset(*a, **k)


def _nxk_set_issuperset(st, *a, **k):
    return st.issuperset(*a, **k)


def _nxk_set_copy(st):
    return st.copy()


# tuple family (method-style: receiver first)
def _nxk_tuple_count(t, *a, **k):
    return t.count(*a, **k)


def _nxk_tuple_index(t, *a, **k):
    return t.index(*a, **k)


# bytes family (method-style: receiver first; fromhex is a classmethod)
def _nxk_bytes_decode(b, *a, **k):
    return b.decode(*a, **k)


def _nxk_bytes_hex(b):
    return b.hex()


def _nxk_bytes_fromhex(*a, **k):
    return _bi.bytes.fromhex(*a, **k)


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


def _nxk_vars(*a, **k):
    return _bi.vars(*a, **k)


def _nxk_dir(*a, **k):
    return _bi.dir(*a, **k)


def _nxk_globals(*a, **k):
    return _bi.globals(*a, **k)


def _nxk_locals(*a, **k):
    return _bi.locals(*a, **k)


def _nxk_compile(*a, **k):
    return _bi.compile(*a, **k)


def _nxk_eval(*a, **k):
    return _bi.eval(*a, **k)


def _nxk_exec(*a, **k):
    return _bi.exec(*a, **k)


def _nxk_memoryview(*a, **k):
    return _bi.memoryview(*a, **k)


def _nxk_ascii(*a, **k):
    return _bi.ascii(*a, **k)


def _nxk_format(*a, **k):
    return _bi.format(*a, **k)


def _nxk_slice(*a, **k):
    return _bi.slice(*a, **k)


# protocol family
def _nxk_iter(*a, **k):
    return _bi.iter(*a, **k)


def _nxk_next(*a, **k):
    return _bi.next(*a, **k)


def _nxk_repr(*a, **k):
    return _bi.repr(*a, **k)


def _nxk_bytes(*a, **k):
    return _bi.bytes(*a, **k)


# range family
def _nxk_range(*a, **k):
    return _bi.range(*a, **k)


def _nxk_aiter(*a, **k):
    return _bi.aiter(*a, **k)


def _nxk_anext(*a, **k):
    return _bi.anext(*a, **k)


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


def _nxk_pow(*a, **k):
    return _bi.pow(*a, **k)


def _nxk_divmod(*a, **k):
    return _bi.divmod(*a, **k)


def _nxk_complex(*a, **k):
    return _bi.complex(*a, **k)


# import family
def _nxk___import__(*a, **k):
    return _bi.__import__(*a, **k)


def _nxk_breakpoint(*a, **k):
    return _bi.breakpoint(*a, **k)


def _nxk_help(*a, **k):
    return _bi.help(*a, **k)


def _nxk_copyright(*a, **k):
    return _bi.copyright(*a, **k)


def _nxk_credits(*a, **k):
    return _bi.credits(*a, **k)


def _nxk_license(*a, **k):
    return _bi.license(*a, **k)


# fusion family: collapse a lowered chain into one dispatch.
def _nxk_fuse(*thunks):
    """Call each zero-arg thunk in order; return the last result."""
    _out = None
    for _t in thunks:
        _out = _t()
    return _out
