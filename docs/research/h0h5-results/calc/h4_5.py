import sys

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((6, 0), (6, 1), (17, None), (11, None), (26, None), (11, None))
    _ret = [None]

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

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
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

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
        return _c[_p][1]

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
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
    _handlers = {11: _h_ret, 26: _h_const, 15: _h_next, 14: lambda st, _w='eq': _h_cmp(st, _w), 13: _h_not, 6: _h_load, 3: _h_range, 17: lambda st, _w='add': _h_arith(st, _w), 24: _h_unpack, 2: lambda st, _w='or': _h_bool(st, _w), 18: lambda st, _w='isnot': _h_cmp(st, _w), 4: lambda st, _w='and': _h_bool(st, _w), 22: _h_neg, 19: lambda st, _w='is': _h_cmp(st, _w), 21: _h_buildlist, 5: lambda st, _w='lt': _h_cmp(st, _w), 28: lambda st, _w='ne': _h_cmp(st, _w), 25: lambda st, _w='le': _h_cmp(st, _w), 16: lambda st, _w='pow': _h_arith(st, _w), 9: lambda st, _w='ge': _h_cmp(st, _w), 23: _h_jfalse, 1: lambda st, _w='mul': _h_arith(st, _w), 10: lambda st, _w='sub': _h_arith(st, _w), 20: lambda st, _w='mod': _h_arith(st, _w), 8: lambda st, _w='gt': _h_cmp(st, _w), 27: _h_store, 0: lambda st, _w='div': _h_arith(st, _w), 29: _h_buildtuple, 7: _h_jmp, 12: _h_pop}
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
    _code = ((22, 0), (22, 1), (19, None), (15, None), (29, None), (15, None))
    _ret = [None]

    def _h_next(st):
        _s, _k, _c, _p, _r = st
        _it = _k[-1]
        try:
            _k.append(next(_it))
            return _p + 1
        except StopIteration:
            _k.pop()
            return _c[_p][1]

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
        return _p + 1

    def _h_jfalse(st):
        _s, _k, _c, _p, _r = st
        _v = _k.pop()
        return _c[_p][1] if not _v else _p + 1

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

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_store(st):
        _s, _k, _c, _p, _r = st
        _s[_c[_p][1]] = _k.pop()
        return _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
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

    def _h_buildlist(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(list(_vs))
        return _p + 1

    def _h_pop(st):
        _s, _k, _c, _p, _r = st
        _k.pop()
        return _p + 1

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1
    _handlers = {19: lambda st, _w='mul': _h_arith(st, _w), 6: lambda st, _w='gt': _h_cmp(st, _w), 14: _h_not, 3: _h_jfalse, 2: lambda st, _w='is': _h_cmp(st, _w), 4: _h_store, 26: lambda st, _w='lt': _h_cmp(st, _w), 24: lambda st, _w='eq': _h_cmp(st, _w), 15: _h_ret, 28: _h_buildlist, 25: lambda st, _w='ge': _h_cmp(st, _w), 20: lambda st, _w='and': _h_bool(st, _w), 13: _h_next, 11: lambda st, _w='mod': _h_arith(st, _w), 23: _h_range, 18: lambda st, _w='ne': _h_cmp(st, _w), 27: _h_jmp, 0: lambda st, _w='pow': _h_arith(st, _w), 21: lambda st, _w='div': _h_arith(st, _w), 1: lambda st, _w='le': _h_cmp(st, _w), 29: _h_const, 22: _h_load, 12: _h_neg, 9: _h_unpack, 7: _h_pop, 17: lambda st, _w='isnot': _h_cmp(st, _w), 10: lambda st, _w='add': _h_arith(st, _w), 8: _h_buildtuple, 5: lambda st, _w='or': _h_bool(st, _w), 16: lambda st, _w='sub': _h_arith(st, _w)}
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
    _code = ((13, 0), (13, 1), (20, 2), (7, 2), (6, 1), (6, 2), (13, 0), (18, 0), (13, 1), (17, None), (2, 21), (6, 3), (18, 1), (18, 2), (18, 1), (26, None), (20, 2), (7, 2), (6, 1), (6, 2), (14, 10), (18, 2), (8, None), (13, None), (8, None))
    _ret = [None]

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

    def _h_buildtuple(st):
        _s, _k, _c, _p, _r = st
        _n = _c[_p][1]
        _vs = [_k.pop() for _ in range(_n)]
        _vs.reverse()
        _k.append(tuple(_vs))
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

    def _h_bool(st, _w):
        _s, _k, _c, _p, _r = st
        _b = _k.pop()
        _a = _k.pop()
        _k.append(_a and _b if _w == 'and' else _a or _b)
        return _p + 1

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
        return _p + 1

    def _h_not(st):
        _s, _k, _c, _p, _r = st
        _k.append(not _k.pop())
        return _p + 1

    def _h_jmp(st):
        _s, _k, _c, _p, _r = st
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

    def _h_neg(st):
        _s, _k, _c, _p, _r = st
        _k.append(-_k.pop())
        return _p + 1

    def _h_ret(st):
        _s, _k, _c, _p, _r = st
        _r[0] = _k.pop()
        return len(_c)

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
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
    _handlers = {6: _h_store, 23: lambda st, _w='is': _h_cmp(st, _w), 11: lambda st, _w='ne': _h_cmp(st, _w), 0: lambda st, _w='lt': _h_cmp(st, _w), 26: lambda st, _w='add': _h_arith(st, _w), 7: _h_unpack, 3: lambda st, _w='div': _h_arith(st, _w), 9: lambda st, _w='mod': _h_arith(st, _w), 28: lambda st, _w='mul': _h_arith(st, _w), 4: lambda st, _w='or': _h_bool(st, _w), 25: _h_not, 14: _h_jmp, 15: lambda st, _w='and': _h_bool(st, _w), 27: lambda st, _w='le': _h_cmp(st, _w), 12: _h_pop, 19: lambda st, _w='gt': _h_cmp(st, _w), 18: _h_load, 16: _h_buildlist, 2: _h_next, 13: _h_const, 20: _h_buildtuple, 8: _h_ret, 29: _h_jfalse, 17: _h_range, 1: _h_neg, 5: lambda st, _w='isnot': _h_cmp(st, _w), 10: lambda st, _w='sub': _h_arith(st, _w), 21: lambda st, _w='ge': _h_cmp(st, _w), 22: lambda st, _w='pow': _h_arith(st, _w), 24: lambda st, _w='eq': _h_cmp(st, _w)}
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
    _code = ((0, 1), (1, 11), (0, 1), (0, 0), (0, 1), (13, None), (20, 2), (26, 2), (18, 1), (18, 0), (29, 0), (0, 0), (2, None), (6, None), (2, None))
    _ret = [None]

    def _h_load(st):
        _s, _k, _c, _p, _r = st
        _k.append(_s[_c[_p][1]])
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

    def _h_const(st):
        _s, _k, _c, _p, _r = st
        _k.append(_c[_p][1])
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

    def _h_range(st):
        _s, _k, _c, _p, _r = st
        _step = _k.pop()
        _end = _k.pop()
        _start = _k.pop()
        _k.append(iter(range(_start, _end, _step)))
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
    _handlers = {12: lambda st, _w='sub': _h_arith(st, _w), 17: lambda st, _w='le': _h_cmp(st, _w), 25: _h_next, 5: lambda st, _w='add': _h_arith(st, _w), 15: lambda st, _w='eq': _h_cmp(st, _w), 29: _h_jmp, 4: _h_range, 18: _h_store, 11: lambda st, _w='mul': _h_arith(st, _w), 19: lambda st, _w='div': _h_arith(st, _w), 22: lambda st, _w='and': _h_bool(st, _w), 14: lambda st, _w='ge': _h_cmp(st, _w), 10: lambda st, _w='pow': _h_arith(st, _w), 3: _h_buildlist, 21: _h_not, 13: lambda st, _w='mod': _h_arith(st, _w), 20: _h_buildtuple, 7: lambda st, _w='or': _h_bool(st, _w), 0: _h_load, 9: lambda st, _w='isnot': _h_cmp(st, _w), 16: lambda st, _w='ne': _h_cmp(st, _w), 26: _h_unpack, 2: _h_ret, 24: lambda st, _w='lt': _h_cmp(st, _w), 1: _h_jfalse, 28: _h_neg, 23: lambda st, _w='gt': _h_cmp(st, _w), 27: lambda st, _w='is': _h_cmp(st, _w), 6: _h_const, 8: _h_pop}
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
    _nixon_めļ椯ჵƝკѿᚤ = argv[0]
    if _nixon_めļ椯ჵƝკѿᚤ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_めļ椯ჵƝკѿᚤ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_めļ椯ჵƝკѿᚤ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_めļ椯ჵƝკѿᚤ == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[2])))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])