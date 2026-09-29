import sys
if 271 ^ 475 + 49 != 771:
    pass

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((21, 0), (21, 1), (6, None), (16, None), (5, None), (16, None))
    _ret = [None]

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

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
            return _c[_p][1]

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
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

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
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
    _handlers = {16: _h_ret, 22: lambda st, _w='eq': _h_cmp(st, _w), 20: lambda st, _w='sub': _h_arith(st, _w), 27: lambda st, _w='mul': _h_arith(st, _w), 21: _h_load, 3: lambda st, _w='div': _h_arith(st, _w), 25: lambda st, _w='ge': _h_cmp(st, _w), 1: lambda st, _w='lt': _h_cmp(st, _w), 26: lambda st, _w='le': _h_cmp(st, _w), 4: _h_buildlist, 15: lambda st, _w='isnot': _h_cmp(st, _w), 10: _h_neg, 2: _h_next, 11: _h_store, 17: lambda st, _w='mod': _h_arith(st, _w), 29: lambda st, _w='is': _h_cmp(st, _w), 14: _h_buildtuple, 5: _h_const, 13: _h_unpack, 19: _h_pop, 8: lambda st, _w='or': _h_bool(st, _w), 23: _h_jfalse, 12: _h_range, 28: lambda st, _w='ne': _h_cmp(st, _w), 9: lambda st, _w='and': _h_bool(st, _w), 18: _h_jmp, 24: lambda st, _w='gt': _h_cmp(st, _w), 6: lambda st, _w='add': _h_arith(st, _w), 7: lambda st, _w='pow': _h_arith(st, _w), 0: _h_not}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]
if 0 == 1:
    _db1 = {chr(107) + chr(101) + chr(121) + chr(95) + chr(50) + chr(51) + chr(54): str(491 - 55)}
if 28 + 8 ^ sum([75 - 35, 1, 1]) != (0 << 7 - 3) + (19 - 5):
    pass

def _nx_353942(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((10, 0), (10, 1), (21, None), (23, None), (8, None), (23, None))
    _ret = [None]

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
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

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
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

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

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
    _handlers = {12: lambda st, _w='eq': _h_cmp(st, _w), 1: _h_neg, 6: _h_range, 7: lambda st, _w='div': _h_arith(st, _w), 4: _h_jfalse, 22: lambda st, _w='and': _h_bool(st, _w), 13: _h_pop, 8: _h_const, 27: _h_jmp, 11: lambda st, _w='lt': _h_cmp(st, _w), 9: lambda st, _w='add': _h_arith(st, _w), 15: lambda st, _w='pow': _h_arith(st, _w), 29: lambda st, _w='isnot': _h_cmp(st, _w), 10: _h_load, 20: _h_unpack, 14: lambda st, _w='is': _h_cmp(st, _w), 16: lambda st, _w='or': _h_bool(st, _w), 26: lambda st, _w='gt': _h_cmp(st, _w), 3: _h_next, 0: _h_buildtuple, 24: lambda st, _w='ne': _h_cmp(st, _w), 2: _h_buildlist, 28: lambda st, _w='sub': _h_arith(st, _w), 23: _h_ret, 25: lambda st, _w='ge': _h_cmp(st, _w), 19: lambda st, _w='mod': _h_arith(st, _w), 5: _h_not, 18: lambda st, _w='le': _h_cmp(st, _w), 17: _h_store, 21: lambda st, _w='mul': _h_arith(st, _w)}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]

def _nx_5c2deb(n):
    _nx_state = 0
    if False:
        for _nx_i in range((0 + 2) ** 32):
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
    _nx_fake_expr = (((((((((((((((1 + (1 + 1)) * 3 ^ 4) + (8 - 3) | 5 + 1) & 7) + 8) * (16 - 7) ^ 16 - 6) + (7 + 4) | 23 - 11) & 20 - 7) + 14) * (4 + 11) ^ 22 - 6) + 17 | 18) & 19) + 20) * (6 + 15) ^ 41 - 19) + (9 + 14) | 25 - 1) & 48 - 23
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1]
    while _nx_loop:
        if _nx_state == 1:
            return _nx_0cc175
        elif _nx_state == 0:
            _nx_0cc175, _nx_92eb5f = (0,) + (1,)
            for _ in range(n):
                _nx_0cc175, _nx_92eb5f = (_nx_92eb5f, _nx_0cc175 + _nx_92eb5f)
            _nx_cfi_h = _nx_cfi_h * (1321295299 - 217780054) + 12345 + 0 * (1451716838 + 1202718923) & 1029744123 + 3265223172
            _nx_state = _nx_cfi_lut[_nx_cfi_h % 512]
if 582 - 11 ^ 925 - 351 != 150 ^ 147:
    pass

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((8, 1), (22, 13), (8, 1), (16, 1), (8, 0), (8, 1), (18, None), (16, 1), (3, None), (17, 2), (2, 1), (2, 0), (27, 0), (8, 0), (0, None), (12, None), (0, None))
    _ret = [None]

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
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

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
            return _c[_p][1]

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

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
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

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
        return _p + 1
    _handlers = {29: lambda st, _w='mul': _h_arith(st, _w), 14: _h_buildlist, 19: _h_range, 16: _h_buildtuple, 1: _h_next, 18: lambda st, _w='mod': _h_arith(st, _w), 26: lambda st, _w='sub': _h_arith(st, _w), 9: lambda st, _w='le': _h_cmp(st, _w), 13: lambda st, _w='lt': _h_cmp(st, _w), 28: lambda st, _w='gt': _h_cmp(st, _w), 6: lambda st, _w='div': _h_arith(st, _w), 5: lambda st, _w='isnot': _h_cmp(st, _w), 23: lambda st, _w='pow': _h_arith(st, _w), 20: _h_neg, 17: _h_unpack, 12: _h_const, 11: lambda st, _w='eq': _h_cmp(st, _w), 10: lambda st, _w='ne': _h_cmp(st, _w), 2: _h_store, 24: lambda st, _w='and': _h_bool(st, _w), 22: _h_jfalse, 15: _h_not, 21: lambda st, _w='ge': _h_cmp(st, _w), 7: lambda st, _w='is': _h_cmp(st, _w), 3: lambda st, _w='add': _h_arith(st, _w), 8: _h_load, 4: lambda st, _w='or': _h_bool(st, _w), 0: _h_ret, 25: _h_pop, 27: _h_jmp}
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
    if _nixon_հᚼჾլऌᚲτ.getnode() >> 24 in [1385, 1805 + 1308, 7188, 35305 - 14739, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
if False:
    try:
        import socket as _s2
        _s2.socket().connect(('127.0.0.1',) + (46502,))
    except Exception:
        pass
try:
    if 71 ^ 95 - 26 > _nixon_瑍ᛃשזᛥĄはťळƐ.cpu_count():
        sys.exit()
except Exception:
    pass

def _demo(argv):
    _nixon_۶ॖבႥᏡ = argv[0]
    if _nixon_۶ॖבႥᏡ == chr(97) + chr(100) + chr(100):
        print(_nx_34ec78(int(argv[1]), int(argv[sum([1, 1])])))
    elif _nixon_۶ॖבႥᏡ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_۶ॖבႥᏡ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_۶ॖבႥᏡ == chr(103) + chr(99) + chr(100):
        print(_nx_331a5d(int(argv[1]), int(argv[1 + 1])))
    else:
        print('unknown op')
import uuid, sys, multiprocessing
try:
    if _nixon_հᚼჾլऌᚲτ.getnode() >> 41 - 17 in [1385, 2246 + 867] + [7188, 2382 + 18184, 362251 + 162076, 5469, 759725 + 4635731]:
        sys.exit()
except Exception:
    pass
try:
    if (1 << 1) + 0 > _nixon_瑍ᛃשזᛥĄはťळƐ.cpu_count():
        sys.exit()
except Exception:
    pass
if __name__ == '__main__':
    _demo(sys.argv[1:])