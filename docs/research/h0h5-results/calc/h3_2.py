import sys

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((10, 0), (10, 1), (7, None), (26, None), (2, None), (26, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 2:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 10:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 14:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 23:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 8:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 25:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 1:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 20:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 12:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 22:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 4:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 3:
            _pc = _code[_pc][1]
        elif _op == 18:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 11:
            _stack.pop()
            _pc += 1
        elif _op == 26:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 27:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 17:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 9:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 21:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 5:
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
    _code = ((16, 0), (16, 1), (15, None), (3, None), (22, None), (3, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 22:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 16:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 12:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 25:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 21:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 1:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 11:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 20:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 17:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 23:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 10:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 2:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 8:
            _pc = _code[_pc][1]
        elif _op == 27:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 14:
            _stack.pop()
            _pc += 1
        elif _op == 3:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 18:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 9:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 4:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 5:
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

def _nx_5c2deb(n):
    _slots = [None] * 4
    _slots[0] = n
    _stack = []
    _code = ((20, 0), (20, 1), (24, 2), (3, 2), (4, 1), (4, 2), (20, 0), (10, 0), (20, 1), (29, None), (12, 21), (4, 3), (10, 1), (10, 2), (10, 1), (13, None), (24, 2), (3, 2), (4, 1), (4, 2), (23, 10), (10, 2), (25, None), (20, None), (25, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 20:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 10:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 4:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 22:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 2:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 17:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 27:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 8:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 11:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 21:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 9:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 1:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 23:
            _pc = _code[_pc][1]
        elif _op == 5:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 14:
            _stack.pop()
            _pc += 1
        elif _op == 25:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 29:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 12:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 24:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 3:
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

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((20, 1), (7, 11), (20, 1), (20, 0), (20, 1), (24, None), (4, 2), (8, 2), (13, 1), (13, 0), (1, 0), (20, 0), (23, None), (19, None), (23, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 19:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 20:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 13:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 12:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 9:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 22:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 17:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 21:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 10:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 27:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 25:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 2:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 11:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 1:
            _pc = _code[_pc][1]
        elif _op == 7:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 0:
            _stack.pop()
            _pc += 1
        elif _op == 23:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 5:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 3:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 4:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 8:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 16:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _demo(argv):
    _nixon_湞ϔ๔贩ٌঋَ = argv[0]
    if _nixon_湞ϔ๔贩ٌঋَ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_湞ϔ๔贩ٌঋَ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_湞ϔ๔贩ٌঋَ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_湞ϔ๔贩ٌঋَ == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[2])))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])