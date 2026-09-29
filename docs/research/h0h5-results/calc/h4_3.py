import sys

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((6, 0), (6, 1), (23, None), (12, None), (0, None), (12, None))
    _ret = [None]

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

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

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

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

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
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

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _t = _c[_p][1]
        _k.append(_t[0] ^ _t[1] if type(_t) is tuple and len(_t) == 2 and (type(_t[0]) is int) and (type(_t[1]) is int) else _t)
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1
    _handlers = {5: lambda st, _w='ge': _h_cmp(st, _w), 8: _h_buildtuple, 21: lambda st, _w='div': _h_arith(st, _w), 2: lambda st, _w='mod': _h_arith(st, _w), 7: _h_jmp, 28: _h_buildlist, 0: _h_const, 26: _h_jfalse, 17: lambda st, _w='mul': _h_arith(st, _w), 16: lambda st, _w='gt': _h_cmp(st, _w), 10: lambda st, _w='or': _h_bool(st, _w), 19: lambda st, _w='is': _h_cmp(st, _w), 20: _h_next, 4: lambda st, _w='sub': _h_arith(st, _w), 3: lambda st, _w='and': _h_bool(st, _w), 9: _h_store, 23: lambda st, _w='add': _h_arith(st, _w), 6: _h_load, 15: _h_neg, 12: _h_ret, 22: lambda st, _w='eq': _h_cmp(st, _w), 29: _h_pop, 25: lambda st, _w='isnot': _h_cmp(st, _w), 11: _h_unpack, 1: lambda st, _w='pow': _h_arith(st, _w), 13: lambda st, _w='lt': _h_cmp(st, _w), 18: lambda st, _w='le': _h_cmp(st, _w), 24: _h_range, 14: lambda st, _w='ne': _h_cmp(st, _w), 27: _h_not}
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
    _code = ((17, 0), (17, 1), (3, None), (25, None), (13, None), (25, None))
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

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
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

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
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

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _t = _c[_p][1]
        _k.append(_t[0] ^ _t[1] if type(_t) is tuple and len(_t) == 2 and (type(_t[0]) is int) and (type(_t[1]) is int) else _t)
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

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
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

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1
    _handlers = {16: _h_range, 28: _h_jmp, 20: lambda st, _w='isnot': _h_cmp(st, _w), 22: lambda st, _w='gt': _h_cmp(st, _w), 27: _h_unpack, 21: lambda st, _w='is': _h_cmp(st, _w), 19: lambda st, _w='mod': _h_arith(st, _w), 3: lambda st, _w='mul': _h_arith(st, _w), 24: lambda st, _w='ge': _h_cmp(st, _w), 1: lambda st, _w='and': _h_bool(st, _w), 12: _h_store, 8: _h_not, 18: _h_buildtuple, 4: _h_pop, 17: _h_load, 10: _h_neg, 0: lambda st, _w='le': _h_cmp(st, _w), 14: lambda st, _w='sub': _h_arith(st, _w), 7: _h_jfalse, 13: _h_const, 5: _h_buildlist, 25: _h_ret, 2: lambda st, _w='lt': _h_cmp(st, _w), 29: lambda st, _w='or': _h_bool(st, _w), 23: lambda st, _w='eq': _h_cmp(st, _w), 26: _h_next, 11: lambda st, _w='div': _h_arith(st, _w), 15: lambda st, _w='add': _h_arith(st, _w), 9: lambda st, _w='pow': _h_arith(st, _w), 6: lambda st, _w='ne': _h_cmp(st, _w)}
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
    _slots = [None] * 4
    _slots[0] = n
    _stack = []
    _code = ((10, (1052521172, 1052521172)), (10, (281054242, 281054243)), (15, 2), (4, 2), (14, 1), (14, 2), (10, (702411742, 702411742)), (28, 0), (10, (280799230, 280799231)), (12, None), (11, 21), (14, 3), (28, 1), (28, 2), (28, 1), (9, None), (15, 2), (4, 2), (14, 1), (14, 2), (21, 10), (28, 2), (26, None), (10, None), (26, None))
    _ret = [None]

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

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

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _t = _c[_p][1]
        _k.append(_t[0] ^ _t[1] if type(_t) is tuple and len(_t) == 2 and (type(_t[0]) is int) and (type(_t[1]) is int) else _t)
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

    def _h_cmp(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append({'eq': _a == _b, 'ne': _a != _b, 'lt': _a < _b, 'le': _a <= _b, 'gt': _a > _b, 'ge': _a >= _b, 'is': _a is _b, 'isnot': _a is not _b}[_w])
        return _p + 1

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

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
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

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
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
    _handlers = {5: lambda st, _w='ne': _h_cmp(st, _w), 10: _h_const, 11: _h_next, 29: lambda st, _w='isnot': _h_cmp(st, _w), 9: lambda st, _w='add': _h_arith(st, _w), 8: lambda st, _w='mul': _h_arith(st, _w), 12: _h_range, 14: _h_store, 6: _h_pop, 2: lambda st, _w='gt': _h_cmp(st, _w), 18: _h_neg, 22: lambda st, _w='and': _h_bool(st, _w), 15: _h_buildtuple, 19: lambda st, _w='ge': _h_cmp(st, _w), 17: lambda st, _w='mod': _h_arith(st, _w), 1: lambda st, _w='eq': _h_cmp(st, _w), 28: _h_load, 3: _h_not, 13: _h_buildlist, 20: lambda st, _w='le': _h_cmp(st, _w), 27: lambda st, _w='is': _h_cmp(st, _w), 21: _h_jmp, 16: _h_jfalse, 4: _h_unpack, 7: lambda st, _w='lt': _h_cmp(st, _w), 23: lambda st, _w='sub': _h_arith(st, _w), 26: _h_ret, 0: lambda st, _w='div': _h_arith(st, _w), 24: lambda st, _w='or': _h_bool(st, _w), 25: lambda st, _w='pow': _h_arith(st, _w)}
    _st = [_slots, _stack, _code, 0, _ret]
    _n = len(_code)
    while _st[3] < _n:
        _op = _code[_st[3]][0]
        _h = _handlers.get(_op)
        if _h is None:
            raise RuntimeError('bad opcode')
        _st[3] = _h(_st)
    return _ret[0]

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((4, 1), (6, 11), (4, 1), (4, 0), (4, 1), (20, None), (7, 2), (2, 2), (19, 1), (19, 0), (10, 0), (4, 0), (12, None), (29, None), (12, None))
    _ret = [None]

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

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

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

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _t = _c[_p][1]
        _k.append(_t[0] ^ _t[1] if type(_t) is tuple and len(_t) == 2 and (type(_t[0]) is int) and (type(_t[1]) is int) else _t)
        return _p + 1

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

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

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

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

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
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
    _handlers = {11: lambda st, _w='lt': _h_cmp(st, _w), 5: _h_range, 2: _h_unpack, 15: lambda st, _w='ne': _h_cmp(st, _w), 27: lambda st, _w='mul': _h_arith(st, _w), 7: _h_buildtuple, 23: lambda st, _w='isnot': _h_cmp(st, _w), 28: lambda st, _w='ge': _h_cmp(st, _w), 13: _h_next, 8: lambda st, _w='eq': _h_cmp(st, _w), 1: lambda st, _w='sub': _h_arith(st, _w), 26: lambda st, _w='div': _h_arith(st, _w), 29: _h_const, 12: _h_ret, 21: _h_pop, 17: lambda st, _w='and': _h_bool(st, _w), 19: _h_store, 24: _h_buildlist, 0: lambda st, _w='pow': _h_arith(st, _w), 9: _h_neg, 25: lambda st, _w='gt': _h_cmp(st, _w), 14: lambda st, _w='is': _h_cmp(st, _w), 18: _h_not, 22: lambda st, _w='le': _h_cmp(st, _w), 6: _h_jfalse, 3: lambda st, _w='add': _h_arith(st, _w), 4: _h_load, 16: lambda st, _w='or': _h_bool(st, _w), 10: _h_jmp, 20: lambda st, _w='mod': _h_arith(st, _w)}
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
    _nixon_ᛛĐেҹʘ黿ฒҤɹΆ = argv[0]
    if _nixon_ᛛĐেҹʘ黿ฒҤɹΆ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_ᛛĐেҹʘ黿ฒҤɹΆ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_ᛛĐেҹʘ黿ฒҤɹΆ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_ᛛĐেҹʘ黿ฒҤɹΆ == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[2])))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])