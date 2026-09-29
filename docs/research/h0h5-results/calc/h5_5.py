import sys

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((21, 0), (21, 1), (7, None), (11, None), (15, None), (11, None))
    _ret = [None]

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
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

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

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

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
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
    _handlers = {23: lambda st, _w='le': _h_cmp(st, _w), 14: lambda st, _w='ne': _h_cmp(st, _w), 24: _h_jfalse, 0: lambda st, _w='isnot': _h_cmp(st, _w), 21: _h_load, 3: _h_pop, 18: lambda st, _w='is': _h_cmp(st, _w), 8: _h_range, 19: lambda st, _w='mod': _h_arith(st, _w), 25: lambda st, _w='sub': _h_arith(st, _w), 11: _h_ret, 20: _h_buildlist, 12: _h_jmp, 9: lambda st, _w='eq': _h_cmp(st, _w), 27: _h_neg, 22: _h_next, 13: lambda st, _w='mul': _h_arith(st, _w), 7: lambda st, _w='add': _h_arith(st, _w), 26: lambda st, _w='div': _h_arith(st, _w), 10: _h_buildtuple, 5: lambda st, _w='or': _h_bool(st, _w), 1: lambda st, _w='and': _h_bool(st, _w), 6: _h_unpack, 29: lambda st, _w='gt': _h_cmp(st, _w), 2: _h_store, 16: lambda st, _w='ge': _h_cmp(st, _w), 4: lambda st, _w='pow': _h_arith(st, _w), 28: _h_not, 17: lambda st, _w='lt': _h_cmp(st, _w), 15: _h_const}
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
    if uuid.getnode() >> 24 in [1748 - 363, 761 + 2352, 1511 + 5677, 20135 + 431, 67891 + 456436, 8689 - 3220, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if 0 + 2 > multiprocessing.cpu_count():
        sys.exit()
except Exception:
    pass

def _nx_353942(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((6, 0), (6, 1), (20, None), (15, None), (9, None), (15, None))
    _ret = [None]

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

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

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

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

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
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

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1
    _handlers = {11: lambda st, _w='isnot': _h_cmp(st, _w), 25: lambda st, _w='gt': _h_cmp(st, _w), 1: _h_store, 27: _h_not, 14: lambda st, _w='eq': _h_cmp(st, _w), 15: _h_ret, 6: _h_load, 2: lambda st, _w='div': _h_arith(st, _w), 22: _h_neg, 5: lambda st, _w='ne': _h_cmp(st, _w), 24: lambda st, _w='and': _h_bool(st, _w), 19: _h_next, 12: _h_pop, 28: lambda st, _w='pow': _h_arith(st, _w), 29: lambda st, _w='lt': _h_cmp(st, _w), 26: lambda st, _w='mod': _h_arith(st, _w), 23: lambda st, _w='ge': _h_cmp(st, _w), 8: lambda st, _w='add': _h_arith(st, _w), 3: _h_buildlist, 13: _h_jmp, 7: _h_unpack, 4: lambda st, _w='or': _h_bool(st, _w), 20: lambda st, _w='mul': _h_arith(st, _w), 16: lambda st, _w='is': _h_cmp(st, _w), 9: _h_const, 17: lambda st, _w='le': _h_cmp(st, _w), 10: _h_jfalse, 21: _h_buildtuple, 0: lambda st, _w='sub': _h_arith(st, _w), 18: _h_range}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]
if (60 - 12 << 2) + 0 ^ 843 != 907:
    pass

def _nx_5c2deb(n):
    _nx_state = 0
    if False:
        for _nx_i in range(2 ** 32):
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
    _nx_fake_expr = (((((((((((((((1 + (2 - 0)) * (1 + 2) ^ 4) + 5 | 5 + 1) & 0 + 7) + 8) * 9 ^ 20 - 10) + 11 | 21 - 9) & 13) + 14) * 15 ^ 13 + 3) + 17 | 21 - 3) & 19) + 20) * 21 ^ 22) + 23 | 24) & 25
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1]
    while _nx_loop:
        if _nx_state == 1:
            return _nx_0cc175
        elif _nx_state == 0:
            _nx_0cc175, _nx_92eb5f = (0,) + (1,)
            for _ in range(n):
                _nx_0cc175, _nx_92eb5f = (_nx_92eb5f, _nx_0cc175 + _nx_92eb5f)
            _nx_cfi_h = _nx_cfi_h * (1192748641 - 89233396) + 12345 + 0 * (2077939569 + 576496192) & 2612702709 + 1682264586
            _nx_state = _nx_cfi_lut[_nx_cfi_h % (799 - 146 ^ 141)]

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((17, 1), (15, 11), (17, 1), (17, 0), (17, 1), (1, None), (12, 2), (6, 2), (8, 1), (8, 0), (2, 0), (17, 0), (21, None), (29, None), (21, None))
    _ret = [None]

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

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
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

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

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

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1
    _handlers = {3: lambda st, _w='gt': _h_cmp(st, _w), 27: _h_not, 11: _h_buildlist, 28: _h_range, 10: lambda st, _w='lt': _h_cmp(st, _w), 29: _h_const, 9: _h_neg, 6: _h_unpack, 5: lambda st, _w='isnot': _h_cmp(st, _w), 18: lambda st, _w='add': _h_arith(st, _w), 23: lambda st, _w='pow': _h_arith(st, _w), 2: _h_jmp, 7: _h_next, 12: _h_buildtuple, 16: lambda st, _w='is': _h_cmp(st, _w), 20: lambda st, _w='ne': _h_cmp(st, _w), 13: lambda st, _w='or': _h_bool(st, _w), 14: lambda st, _w='div': _h_arith(st, _w), 15: _h_jfalse, 4: lambda st, _w='eq': _h_cmp(st, _w), 8: _h_store, 19: _h_pop, 24: lambda st, _w='sub': _h_arith(st, _w), 26: lambda st, _w='mul': _h_arith(st, _w), 22: lambda st, _w='and': _h_bool(st, _w), 21: _h_ret, 0: lambda st, _w='ge': _h_cmp(st, _w), 17: _h_load, 25: lambda st, _w='le': _h_cmp(st, _w), 1: lambda st, _w='mod': _h_arith(st, _w)}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]
if 2 ^ 709 != sum([604, 33, 64, 10]):
    pass

def _demo(argv):
    _nixon_ᛄŧ輌侀ضۺสĐ = argv[0]
    if _nixon_ᛄŧ輌侀ضۺสĐ == chr(97) + chr(100) + chr(100):
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_ᛄŧ輌侀ضۺสĐ == chr(109) + chr(117) + chr(108):
        print(_nx_353942(int(argv[1]), int(argv[(1 << 1) + 0])))
    elif _nixon_ᛄŧ輌侀ضۺสĐ == ''.join(['f', 'i', 'b']):
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_ᛄŧ輌侀ضۺสĐ == chr(103) + chr(99) + chr(100):
        print(_nx_331a5d(int(argv[1]), int(argv[2 - 0])))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if 638 ^ 29 != sum([194, 1 + 255, 166 - 75, 67, 1, 1, 1]):
    pass
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])
_nx_j0 = bytes([x ^ 109 for x in str(959).encode()])