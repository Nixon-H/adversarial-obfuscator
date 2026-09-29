import sys

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((13, 0), (13, 1), (9, None), (19, None), (3, None), (19, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 3:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 13:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 25:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 8:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 12:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 11:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 4:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 5:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 17:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 20:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 9:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 2:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 22:
            _pc = _code[_pc][1]
        elif _op == 1:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 23:
            _stack.pop()
            _pc += 1
        elif _op == 19:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 10:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 28:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 21:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 27:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 24:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _nx_353942(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((1, 0), (1, 1), (9, None), (2, None), (25, None), (2, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 25:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 1:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 27:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 7:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 10:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 3:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 4:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 8:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 20:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 9:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 23:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 17:
            _pc = _code[_pc][1]
        elif _op == 5:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 21:
            _stack.pop()
            _pc += 1
        elif _op == 2:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 22:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 11:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 12:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 29:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 6:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _nx_5c2deb(n):
    _slots = [None] * 4
    _slots[0] = n
    _stack = []
    _code = ((24, 0), (24, 1), (10, 2), (0, 2), (27, 1), (27, 2), (24, 0), (19, 0), (24, 1), (17, None), (8, 21), (27, 3), (19, 1), (19, 2), (19, 1), (15, None), (10, 2), (0, 2), (27, 1), (27, 2), (1, 10), (19, 2), (26, None), (24, None), (26, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 24:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 19:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 27:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 20:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 2:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 11:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 23:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 4:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 22:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 3:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 5:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 12:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 21:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 1:
            _pc = _code[_pc][1]
        elif _op == 25:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 18:
            _stack.pop()
            _pc += 1
        elif _op == 26:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 17:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 8:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 10:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 0:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 9:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((12, 1), (8, 11), (12, 1), (12, 0), (12, 1), (24, None), (1, 2), (22, 2), (5, 1), (5, 0), (11, 0), (12, 0), (20, None), (0, None), (20, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 0:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 12:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 5:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 2:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 17:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 9:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 10:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 26:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 3:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 23:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 25:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 4:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 27:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 11:
            _pc = _code[_pc][1]
        elif _op == 8:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 29:
            _stack.pop()
            _pc += 1
        elif _op == 20:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 19:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 21:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 1:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 22:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 6:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _demo(argv):
    _nixon_ЦծċͲぴʐΐ = argv[0]
    if _nixon_ЦծċͲぴʐΐ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_ЦծċͲぴʐΐ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_ЦծċͲぴʐΐ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_ЦծċͲぴʐΐ == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[2])))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])