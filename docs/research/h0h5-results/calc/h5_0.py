import sys
if sum([139, 111 - 19, 289] + [0 + 3, 1]) ^ sum([12 + 37, 0 + 2, 2, 2, 1]) != sum([261 - 80, 334 - 148, 119, 34, 8, 13, 19, 3 - 1, 2]):
    pass

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((12, 0), (12, 1), (2, None), (16, None), (26, None), (16, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 26:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 12:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 8:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 3:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 21:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 1:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 25:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 2:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 9:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 11:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 10:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 27:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 17:
            _pc = _code[_pc][1]
        elif _op == 20:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 15:
            _stack.pop()
            _pc += 1
        elif _op == 16:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 0:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 4:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 22:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 23:
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
if sum([768 - 312, 78 - 37, 15, 3, 4, 2 + 1] + [2, 1]) ^ 766 - 233 != 35 - 11:
    pass

def _nx_353942(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((19, 0), (19, 1), (13, None), (14, None), (11, None), (14, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 11:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 19:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 1:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 5:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 3:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 4:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 23:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 22:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 2:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 12:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 10:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 21:
            _pc = _code[_pc][1]
        elif _op == 16:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 17:
            _stack.pop()
            _pc += 1
        elif _op == 14:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 9:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 20:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 8:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 25:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 27:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret
if 0 + 4 ^ sum([119, 108 + 164, 217, 96, 118, 26 - 5, 3, 1]) != 85 + 758:
    pass

def _nx_5c2deb(n):
    _nx_state = 0
    if False:
        for _nx_i in range((4 - 2) ** (35 - 3)):
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
    _nx_fake_expr = (((((((((((((((1 + 2) * 3 ^ 8 - 4) + 5 | 5 + 1) & 7) + 8) * (16 - 7) ^ 8 + 2) + (10 + 1) | 23 - 11) & 4 + 9) + (14 - 0)) * 15 ^ 16) + (16 + 1) | 17 + 1) & 27 - 8) + 20) * 21 ^ 22) + (17 + 6) | 24) & 25
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0]
    while _nx_loop:
        if _nx_state == 0:
            _nx_0cc175, _nx_92eb5f = (0, 1)
            for _ in range(n):
                _nx_0cc175, _nx_92eb5f = (_nx_92eb5f, _nx_0cc175 + _nx_92eb5f)
            _nx_cfi_h = _nx_cfi_h * 1103515245 + 12345 + ((~~((234 - 52 ^ 106 - 39 + (61 + 87)) * 0 + 0 * (4800899482 - (539658901 + 1606804917))) | 584389) & (~~((234 - 52 ^ 106 - 39 + (61 + 87)) * 0 + 0 * (4800899482 - (539658901 + 1606804917))) | ~(596723 - 12334)) & 683783 | (~~((234 - 52 ^ 106 - 39 + (61 + 87)) * 0 + 0 * (4800899482 - (539658901 + 1606804917))) | 584389) & (~~((234 - 52 ^ 106 - 39 + (61 + 87)) * 0 + 0 * (4800899482 - (539658901 + 1606804917))) | ~(596723 - 12334)) & ~(1301948 - 618165)) & 4294967295
            _nx_state = _nx_cfi_lut[_nx_cfi_h % (526 ^ 14)]
        elif _nx_state == 1:
            return _nx_0cc175

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((23, 1), (12, 13), (23, 1), (22, 1), (23, 0), (23, 1), (26, None), (22, 1), (17, None), (25, 2), (21, 1), (21, 0), (27, 0), (23, 0), (19, None), (20, None), (19, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 20:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 23:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 21:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 4:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 3:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 11:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 8:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 17:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 10:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 2:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 0:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 27:
            _pc = _code[_pc][1]
        elif _op == 12:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 9:
            _stack.pop()
            _pc += 1
        elif _op == 19:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 5:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 1:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 22:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(tuple(_vs))
            _pc += 1
        elif _op == 25:
            _m = _code[_pc][1]
            _t = tuple(_stack.pop())
            _l = len(_t)
            if _l > _m:
                raise ValueError('too many values to unpack (expected %d)' % _m)
            if _l < _m:
                raise ValueError('not enough values to unpack (expected %d, got %d)' % (_m, _l))
            _stack.extend(_t)
            _pc += 1
        elif _op == 29:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _demo(argv):
    _nixon_ืĹūķţȎ = argv[0]
    if _nixon_ืĹūķţȎ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[sum([1, 1])])))
    elif _nixon_ืĹūķţȎ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[(1 << 1) + 0])))
    elif _nixon_ืĹūķţȎ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_ืĹūķţȎ == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[4 - 2])))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])