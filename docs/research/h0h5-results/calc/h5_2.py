import sys

def _nx_34ec78(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((17, 0), (17, 1), (11, None), (14, None), (28, None), (14, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 28:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 17:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 21:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 7:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 15:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 8:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 20:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 11:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 1:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 5:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 3:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 26:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 25:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 12:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 4:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 27:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 22:
            _pc = _code[_pc][1]
        elif _op == 23:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 16:
            _stack.pop()
            _pc += 1
        elif _op == 14:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 10:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 29:
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
        elif _op == 2:
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
if (0 << 3) + 3 ^ 172 + 37 != 210:
    pass

def _nx_353942(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((7, 0), (7, 1), (8, None), (15, None), (23, None), (15, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 23:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 7:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 16:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 5:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 1:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 9:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 2:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 17:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 20:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 26:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 27:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 12:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 4:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 22:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 8:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 21:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 6:
            _pc = _code[_pc][1]
        elif _op == 28:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 10:
            _stack.pop()
            _pc += 1
        elif _op == 15:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 25:
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
        elif _op == 13:
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
        elif _op == 3:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _nx_5c2deb(n):
    _nx_state = 0
    if False:
        for _nx_i in range(2 ** (3 + 29)):
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
    _nx_fake_expr = (((((((((((((((1 + 2) * (1 + 2) ^ 4) + 5 | 6) & 7) + (6 + 2)) * 9 ^ 10) + 11 | 12) & 13) + (22 - 8)) * (5 + 10) ^ 16 - 0) + 17 | 35 - 17) & 19) + 20) * (0 + 21) ^ 22) + (42 - 19) | 24) & 14 + 11
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0]
    while _nx_loop:
        if _nx_state == 0:
            _nx_0cc175, _nx_92eb5f = (0,) + (1,)
            for _ in range(n):
                _nx_0cc175, _nx_92eb5f = (_nx_92eb5f, _nx_0cc175 + _nx_92eb5f)
            _nx_cfi_h = _nx_cfi_h * (1409470593 - 305955348) + 12345 + (((115 * 0 + 0 * (1781331093 + (1282746974 - 409642421))) * (7596 - (2434 - 776)) // (11515 - 5577) | 699160 - 200912) & ((115 * 0 + 0 * (1781331093 + (1282746974 - 409642421))) * (7596 - (2434 - 776)) // (11515 - 5577) | ~(377640 + 120608))) & 5656286685 - 1361319390
            _nx_state = _nx_cfi_lut[_nx_cfi_h % (528 ^ 16)]
        elif _nx_state == 1:
            return _nx_0cc175
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1', 59356))
    except Exception:
        pass
if sum([356, 33, 55 - 27, 81, 2, 11, 12, 2 + 1]) ^ 26 + 74 != 517 + 101:
    pass
if 0 == 1:
    _db2 = {'key_106': str(523)}

def _nx_331a5d(a, b):
    _slots = [None] * 2
    _slots[0] = a
    _slots[1] = b
    _stack = []
    _code = ((11, 1), (5, 11), (11, 1), (11, 0), (11, 1), (14, None), (15, 2), (21, 2), (12, 1), (12, 0), (23, 0), (11, 0), (7, None), (20, None), (7, None))
    _n = len(_code)
    _pc = 0
    _ret = None
    while _pc < _n:
        _op = _code[_pc][0]
        if _op == 20:
            _stack.append(_code[_pc][1])
            _pc += 1
        elif _op == 11:
            _stack.append(_slots[_code[_pc][1]])
            _pc += 1
        elif _op == 12:
            _slots[_code[_pc][1]] = _stack.pop()
            _pc += 1
        elif _op == 2:
            _stack.append(-_stack.pop())
            _pc += 1
        elif _op == 14:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a % _b)
            _pc += 1
        elif _op == 16:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a != _b)
            _pc += 1
        elif _op == 6:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is not _b)
            _pc += 1
        elif _op == 19:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a ** _b)
            _pc += 1
        elif _op == 17:
            _stack.append(not _stack.pop())
            _pc += 1
        elif _op == 0:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a > _b)
            _pc += 1
        elif _op == 24:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a + _b)
            _pc += 1
        elif _op == 18:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a < _b)
            _pc += 1
        elif _op == 3:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a is _b)
            _pc += 1
        elif _op == 1:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a == _b)
            _pc += 1
        elif _op == 13:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a * _b)
            _pc += 1
        elif _op == 4:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a - _b)
            _pc += 1
        elif _op == 29:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a and _b)
            _pc += 1
        elif _op == 8:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a <= _b)
            _pc += 1
        elif _op == 25:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a >= _b)
            _pc += 1
        elif _op == 28:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a / _b)
            _pc += 1
        elif _op == 9:
            _b = _stack.pop()
            _a = _stack.pop()
            _stack.append(_a or _b)
            _pc += 1
        elif _op == 23:
            _pc = _code[_pc][1]
        elif _op == 5:
            _c = _stack.pop()
            _pc = _code[_pc][1] if not _c else _pc + 1
        elif _op == 26:
            _stack.pop()
            _pc += 1
        elif _op == 7:
            _ret = _stack.pop()
            _pc = _n
        elif _op == 10:
            _s = _stack.pop()
            _e = _stack.pop()
            _t = _stack.pop()
            _stack.append(iter(range(_t, _e, _s)))
            _pc += 1
        elif _op == 22:
            _it = _stack[-1]
            try:
                _v = next(_it)
                _stack.append(_v)
                _pc += 1
            except StopIteration:
                _stack.pop()
                _pc = _code[_pc][1]
        elif _op == 15:
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
        elif _op == 27:
            _m = _code[_pc][1]
            _vs = [_stack.pop() for _ in range(_m)]
            _vs.reverse()
            _stack.append(list(_vs))
            _pc += 1
        else:
            raise RuntimeError('bad opcode')
    return _ret

def _demo(argv):
    _nixon_מ涎ץᚻӟъьॎโহ = argv[0]
    if _nixon_מ涎ץᚻӟъьॎโহ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_מ涎ץᚻӟъьॎโহ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[212 + 21 ^ 235])))
    elif _nixon_מ涎ץᚻӟъьॎโহ == ''.join(['f', 'i', 'b']):
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_מ涎ץᚻӟъьॎโহ == ''.join(['g', 'c', 'd']):
        print(_nx_331a5d(int(argv[1]), int(argv[1 + 1])))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])