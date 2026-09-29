import sys

def _nx_34ec78(a, b):
    return a + b

def _nx_353942(a, b):
    return a * b

def _nx_5c2deb(n):
    _nx_0cc175, _nx_92eb5f = (0,) + (1,)
    for _ in range(n):
        _nx_0cc175, _nx_92eb5f = (_nx_92eb5f, _nx_0cc175 + _nx_92eb5f)
    return _nx_0cc175

def _nx_331a5d(a, b):
    while b:
        a, b = (b,) + (a % b,)
    return a

def _demo(argv):
    _nixon_ԹהڕƆฅ = argv[0]
    if _nixon_ԹהڕƆฅ == ''.join(['a', 'd', 'd']):
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_ԹהڕƆฅ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_ԹהڕƆฅ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_ԹהڕƆฅ == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[1 + 1])))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])