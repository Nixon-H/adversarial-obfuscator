import sys
if 968 ^ (747 ^ 69 + 183) != 869 - 390:
    pass

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((27, 0), (27, 1), (18, None), (9, None), (8, None), (9, None))
    _ret = [None]

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
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

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _t = _c[_p][1]
        _k.append(_t[0] ^ _t[1] if type(_t) is tuple and len(_t) == 2 and (type(_t[0]) is int) and (type(_t[1]) is int) else _t)
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
    _handlers = {5: _h_store, 11: lambda st, _w='pow': _h_arith(st, _w), 25: _h_buildlist, 2: lambda st, _w='mod': _h_arith(st, _w), 4: lambda st, _w='gt': _h_cmp(st, _w), 16: _h_jfalse, 19: lambda st, _w='div': _h_arith(st, _w), 18: lambda st, _w='add': _h_arith(st, _w), 20: lambda st, _w='lt': _h_cmp(st, _w), 1: _h_neg, 15: lambda st, _w='sub': _h_arith(st, _w), 23: _h_next, 29: lambda st, _w='isnot': _h_cmp(st, _w), 8: _h_const, 9: _h_ret, 27: _h_load, 10: lambda st, _w='ge': _h_cmp(st, _w), 7: lambda st, _w='le': _h_cmp(st, _w), 28: _h_unpack, 14: _h_jmp, 26: lambda st, _w='mul': _h_arith(st, _w), 3: _h_pop, 21: lambda st, _w='and': _h_bool(st, _w), 12: _h_buildtuple, 0: lambda st, _w='eq': _h_cmp(st, _w), 17: _h_not, 24: lambda st, _w='ne': _h_cmp(st, _w), 22: lambda st, _w='is': _h_cmp(st, _w), 6: _h_range, 13: lambda st, _w='or': _h_bool(st, _w)}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]

def _nx_353942(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((5, 0), (5, 1), (25, None), (2, None), (11, None), (2, None))
    _ret = [None]

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
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

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

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

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _t = _c[_p][1]
        _k.append(_t[0] ^ _t[1] if type(_t) is tuple and len(_t) == 2 and (type(_t[0]) is int) and (type(_t[1]) is int) else _t)
        return _p + 1

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
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

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

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
    _handlers = {24: _h_buildlist, 18: _h_buildtuple, 9: lambda st, _w='or': _h_bool(st, _w), 2: _h_ret, 20: lambda st, _w='eq': _h_cmp(st, _w), 19: _h_jfalse, 13: _h_jmp, 0: _h_next, 12: lambda st, _w='is': _h_cmp(st, _w), 4: lambda st, _w='le': _h_cmp(st, _w), 17: lambda st, _w='pow': _h_arith(st, _w), 3: lambda st, _w='and': _h_bool(st, _w), 28: lambda st, _w='div': _h_arith(st, _w), 16: _h_store, 21: lambda st, _w='lt': _h_cmp(st, _w), 22: _h_not, 1: lambda st, _w='ge': _h_cmp(st, _w), 8: lambda st, _w='mod': _h_arith(st, _w), 25: lambda st, _w='mul': _h_arith(st, _w), 15: lambda st, _w='ne': _h_cmp(st, _w), 5: _h_load, 6: lambda st, _w='sub': _h_arith(st, _w), 14: lambda st, _w='add': _h_arith(st, _w), 23: _h_neg, 27: lambda st, _w='isnot': _h_cmp(st, _w), 7: _h_range, 29: _h_unpack, 10: lambda st, _w='gt': _h_cmp(st, _w), 11: _h_const, 26: _h_pop}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]
if 170 - 52 ^ 220 + 240 != 425 ^ 22 - 3:
    pass

def _nx_5c2deb(n):
    _nx_state = 0
    if False:
        for _nx_i in range((2 - 0) ** (46 - 14)):
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
    _nx_fake_expr = (((((((((((((((1 + (1 + 1)) * (3 - 0) ^ 4) + 5 | 7 - 1) & 7) + (16 - 8)) * 9 ^ 17 - 7) + (11 + 0) | 12) & 13 + 0) + (17 - 3)) * 15 ^ 27 - 11) + 17 | 18) & 19) + 20) * 21 ^ 22) + 23 | 24) & 16 + 9
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1]
    while _nx_loop:
        if _nx_state == 0:
            _nx_0cc175, _nx_92eb5f = (0, 1)
            for _ in range(n):
                _nx_0cc175, _nx_92eb5f = (_nx_92eb5f,) + (_nx_0cc175 + _nx_92eb5f,)
            _nx_cfi_h = _nx_cfi_h * 1103515245 + 12345 + 0 * (1183457409 + 1470978352) & 2364571761 + 1930395534
            _nx_state = _nx_cfi_lut[_nx_cfi_h % 512]
        elif _nx_state == 1:
            return _nx_0cc175
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 795 + 2318, 7188, 30812 - 10246, 524327, 10581 - 5112, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if 2 > multiprocessing.cpu_count():
        sys.exit()
except Exception:
    pass

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((7, 1), (2, 13), (7, 1), (19, 1), (7, 0), (7, 1), (15, None), (19, 1), (0, None), (3, 2), (16, 1), (16, 0), (25, 0), (7, 0), (1, None), (6, None), (1, None))
    _ret = [None]

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

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
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

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
            return _c[_p][1]

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

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _t = _c[_p][1]
        _k.append(_t[0] ^ _t[1] if type(_t) is tuple and len(_t) == 2 and (type(_t[0]) is int) and (type(_t[1]) is int) else _t)
        return _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1
    _handlers = {23: lambda st, _w='is': _h_cmp(st, _w), 24: _h_buildlist, 20: _h_not, 9: _h_next, 15: lambda st, _w='mod': _h_arith(st, _w), 12: _h_pop, 29: lambda st, _w='div': _h_arith(st, _w), 5: lambda st, _w='pow': _h_arith(st, _w), 19: _h_buildtuple, 10: lambda st, _w='eq': _h_cmp(st, _w), 6: _h_const, 28: lambda st, _w='mul': _h_arith(st, _w), 11: lambda st, _w='le': _h_cmp(st, _w), 8: lambda st, _w='lt': _h_cmp(st, _w), 1: _h_ret, 18: lambda st, _w='gt': _h_cmp(st, _w), 27: lambda st, _w='ge': _h_cmp(st, _w), 4: lambda st, _w='ne': _h_cmp(st, _w), 3: _h_unpack, 25: _h_jmp, 22: lambda st, _w='or': _h_bool(st, _w), 13: lambda st, _w='sub': _h_arith(st, _w), 21: lambda st, _w='and': _h_bool(st, _w), 26: _h_range, 2: _h_jfalse, 0: lambda st, _w='add': _h_arith(st, _w), 17: _h_neg, 7: _h_load, 16: _h_store, 14: lambda st, _w='isnot': _h_cmp(st, _w)}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]

def _demo(argv):
    _nixon_יৣᛟᏂήのऐփႭȥ = argv[0]
    if _nixon_יৣᛟᏂήのऐփႭȥ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[1 + 1])))
    elif _nixon_יৣᛟᏂήのऐփႭȥ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[44 ^ 86 - 40])))
    elif _nixon_יৣᛟᏂήのऐփႭȥ == chr(102) + chr(105) + chr(98):
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_יৣᛟᏂήのऐփႭȥ == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[2])))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])