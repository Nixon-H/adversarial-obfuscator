import sys
if False:
    try:
        import socket as _s1
        _s1.socket().connect((chr(49) + chr(50) + chr(55) + chr(46) + chr(48) + chr(46) + chr(48) + chr(46) + chr(49), 33889 + 13852))
    except Exception:
        pass

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((10, 0), (10, 1), (0, None), (11, None), (4, None), (11, None))
    _ret = [None]

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
            return _c[_p][1]

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_unpack(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _t = tuple(_k.pop())
        _l = len(_t)
        if _l > _n:
            raise ValueError('too many values to unpack (expected %d)' % _n)
        if _l < _n:
            raise ValueError('not enough values to unpack (expected %d, got %d)' % (_n, _l))
        _k.extend(_t)
        return _p + 1

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_arith(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        if _w == 'add':
            _k.append(_a + _b)
        elif _w == 'sub':
            _k.append(_a - _b)
        elif _w == 'mul':
            _k.append(_a * _b)
        elif _w == 'div':
            _k.append(_a / _b)
        elif _w == 'mod':
            _k.append(_a % _b)
        else:
            _k.append(_a ** _b)
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1
    _handlers = {29: lambda st, _w='mul': _h_arith(st, _w), 18: lambda st, _w='ne': _h_cmp(st, _w), 23: lambda st, _w='and': _h_bool(st, _w), 7: lambda st, _w='gt': _h_cmp(st, _w), 0: lambda st, _w='add': _h_arith(st, _w), 25: _h_unpack, 14: lambda st, _w='pow': _h_arith(st, _w), 6: _h_pop, 3: lambda st, _w='is': _h_cmp(st, _w), 15: _h_store, 26: lambda st, _w='lt': _h_cmp(st, _w), 27: lambda st, _w='sub': _h_arith(st, _w), 24: lambda st, _w='isnot': _h_cmp(st, _w), 17: lambda st, _w='div': _h_arith(st, _w), 28: _h_neg, 22: _h_jfalse, 4: _h_const, 2: _h_buildlist, 16: lambda st, _w='le': _h_cmp(st, _w), 12: lambda st, _w='mod': _h_arith(st, _w), 21: _h_buildtuple, 9: lambda st, _w='eq': _h_cmp(st, _w), 1: _h_next, 13: _h_range, 10: _h_load, 5: _h_not, 19: lambda st, _w='or': _h_bool(st, _w), 8: lambda st, _w='ge': _h_cmp(st, _w), 11: _h_ret, 20: _h_jmp}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]
import uuid, sys, multiprocessing
try:
    if _nixon_תʋᛔんϓघתәჱ.getnode() >> 24 in [1385] + [97 + 3016, 7188, 20566, 524327, 6268 - 799, 4718411 + 677045]:
        sys.exit()
except Exception:
    pass
try:
    if _nixon_ϴقだזტРႬᏳ๘ɐ.cpu_count() < 2 - 0:
        sys.exit()
except Exception:
    pass
if 0 == 1:
    _db2 = {'key_478': str(662)}

def _nx_353942(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((29, 0), (29, 1), (15, None), (4, None), (13, None), (4, None))
    _ret = [None]

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1

    def _h_arith(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        if _w == 'add':
            _k.append(_a + _b)
        elif _w == 'sub':
            _k.append(_a - _b)
        elif _w == 'mul':
            _k.append(_a * _b)
        elif _w == 'div':
            _k.append(_a / _b)
        elif _w == 'mod':
            _k.append(_a % _b)
        else:
            _k.append(_a ** _b)
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_unpack(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _t = tuple(_k.pop())
        _l = len(_t)
        if _l > _n:
            raise ValueError('too many values to unpack (expected %d)' % _n)
        if _l < _n:
            raise ValueError('not enough values to unpack (expected %d, got %d)' % (_n, _l))
        _k.extend(_t)
        return _p + 1

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
            return _c[_p][1]

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1
    _handlers = {23: lambda st, _w='lt': _h_cmp(st, _w), 24: _h_pop, 29: _h_load, 10: lambda st, _w='gt': _h_cmp(st, _w), 19: _h_buildtuple, 13: _h_const, 21: _h_not, 0: lambda st, _w='ne': _h_cmp(st, _w), 11: lambda st, _w='div': _h_arith(st, _w), 12: lambda st, _w='is': _h_cmp(st, _w), 4: _h_ret, 9: _h_jfalse, 25: lambda st, _w='pow': _h_arith(st, _w), 8: _h_range, 3: lambda st, _w='sub': _h_arith(st, _w), 5: lambda st, _w='mod': _h_arith(st, _w), 20: lambda st, _w='le': _h_cmp(st, _w), 7: lambda st, _w='and': _h_bool(st, _w), 1: _h_buildlist, 22: lambda st, _w='ge': _h_cmp(st, _w), 27: lambda st, _w='or': _h_bool(st, _w), 6: lambda st, _w='add': _h_arith(st, _w), 2: _h_neg, 14: _h_store, 26: lambda st, _w='isnot': _h_cmp(st, _w), 28: _h_next, 15: lambda st, _w='mul': _h_arith(st, _w), 18: lambda st, _w='eq': _h_cmp(st, _w), 17: _h_unpack, 16: _h_jmp}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]
_nx_j2 = bytes([x ^ 2 for x in str(395).encode()])
import uuid, sys, multiprocessing
if False:
    try:
        import socket as _s4
        _s4.socket().connect(('127.0.0.1', 18370 + 8278))
    except Exception:
        pass
try:
    if _nixon_תʋᛔんϓघתәჱ.getnode() >> 24 in [1385, 3113, 11730 - 4542, 20566, 974173 - 449846] + [4676 + 793, 10047061 - 4651605]:
        sys.exit()
except Exception:
    pass
try:
    if _nixon_ϴقだזტРႬᏳ๘ɐ.cpu_count() < 2:
        sys.exit()
except Exception:
    pass

def _nx_5c2deb(n):
    _nx_state = 0
    if False:
        for _nx_i in range(2 ** (57 - 25)):
            pass
    if False:
        try:
            if 0 == 1:
                1
        except Exception:
            pass
        finally:
            if False:
                pass
    _nx_fake_expr = (((((((((((((((1 + (0 + 2)) * (4 - 1) ^ 4) + 5 | 6) & 7) + (12 - 4)) * 9 ^ 10 + 0) + 11 | 11 + 1) & 13) + 14) * 15 ^ 32 - 16) + 17 | 18) & 21 - 2) + (35 - 15)) * (27 - 6) ^ 22) + (43 - 20) | 24) & 8 + 17
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1]
    while _nx_loop:
        if _nx_state == 1:
            return _nx_0cc175
        elif _nx_state == 0:
            _nx_0cc175, _nx_92eb5f = (0, 1)
            for _ in range(n):
                _nx_0cc175, _nx_92eb5f = (_nx_92eb5f, _nx_0cc175 + _nx_92eb5f)
            _nx_cfi_h = _nx_cfi_h * (1788384662 - 684869417) + (7294 + 5051) + (740 * 0 + 0 * (4292755914 - 1638320893) ^ 301811 - 114671 ^ 244737 - 57597) & 1516757479 + 2778209816
            _nx_state = _nx_cfi_lut[_nx_cfi_h % (585 ^ 12 + 61)]
if sum([186] + [349 - 130, 172, 36, 12 - 5, 60 - 21, 8, 4 - 2, 1, 7, 7, 1]) ^ 79 + 98 != 1228 - 590 ^ 98:
    pass
if False:
    try:
        import socket as _s5
        _s5.socket().connect(('127.0.0.1',) + (38468,))
    except Exception:
        pass

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((9, 1), (20, 11), (9, 1), (9, 0), (9, 1), (23, None), (11, 2), (4, 2), (15, 1), (15, 0), (29, 0), (9, 0), (19, None), (22, None), (19, None))
    _ret = [None]

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
        return _p + 1

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_unpack(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _t = tuple(_k.pop())
        _l = len(_t)
        if _l > _n:
            raise ValueError('too many values to unpack (expected %d)' % _n)
        if _l < _n:
            raise ValueError('not enough values to unpack (expected %d, got %d)' % (_n, _l))
        _k.extend(_t)
        return _p + 1

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
            return _c[_p][1]

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1

    def _h_arith(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        if _w == 'add':
            _k.append(_a + _b)
        elif _w == 'sub':
            _k.append(_a - _b)
        elif _w == 'mul':
            _k.append(_a * _b)
        elif _w == 'div':
            _k.append(_a / _b)
        elif _w == 'mod':
            _k.append(_a % _b)
        else:
            _k.append(_a ** _b)
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1
    _handlers = {1: lambda st, _w='mul': _h_arith(st, _w), 19: _h_ret, 10: _h_buildlist, 6: lambda st, _w='eq': _h_cmp(st, _w), 25: lambda st, _w='le': _h_cmp(st, _w), 12: lambda st, _w='isnot': _h_cmp(st, _w), 15: _h_store, 27: _h_not, 5: lambda st, _w='add': _h_arith(st, _w), 2: lambda st, _w='is': _h_cmp(st, _w), 26: lambda st, _w='div': _h_arith(st, _w), 29: _h_jmp, 4: _h_unpack, 14: _h_range, 7: lambda st, _w='sub': _h_arith(st, _w), 24: lambda st, _w='lt': _h_cmp(st, _w), 28: _h_pop, 0: lambda st, _w='ge': _h_cmp(st, _w), 3: _h_next, 20: _h_jfalse, 8: _h_neg, 9: _h_load, 18: lambda st, _w='pow': _h_arith(st, _w), 13: lambda st, _w='gt': _h_cmp(st, _w), 17: lambda st, _w='ne': _h_cmp(st, _w), 11: _h_buildtuple, 23: lambda st, _w='mod': _h_arith(st, _w), 16: lambda st, _w='or': _h_bool(st, _w), 22: _h_const, 21: lambda st, _w='and': _h_bool(st, _w)}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]
if 321 + 392 ^ 402 - 190 != (58 - 25 << 4) + (26 - 13):
    pass

def _demo(argv):
    _nixon_ՠԴ鲞ॉへा = argv[0]
    if _nixon_ՠԴ鲞ॉへा == chr(97) + chr(100) + chr(100):
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_ՠԴ鲞ॉへा == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_ՠԴ鲞ॉへा == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_ՠԴ鲞ॉへा == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[3 - 1])))
    else:
        print('unknown op')
import uuid, sys, multiprocessing
try:
    if _nixon_תʋᛔんϓघתәჱ.getnode() >> sum([3 - 0, 4] + [21 - 4]) in [274 + 1111, 3113, 7188, 20566] + [457724 + 66603, 10101 - 4632, 4132526 + 1262930]:
        sys.exit()
except Exception:
    pass
try:
    if sum([2]) > _nixon_ϴقだזტРႬᏳ๘ɐ.cpu_count():
        sys.exit()
except Exception:
    pass
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])