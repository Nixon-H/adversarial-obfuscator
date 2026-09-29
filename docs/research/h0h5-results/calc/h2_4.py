import sys

def _nx_34ec78(a, b):
    return a + b

def _nx_353942(a, b):
    return a * b

def _nx_5c2deb(n):
    _nx_0cc175, _nx_92eb5f = (0, 1)
    for _ in range(n):
        _nx_0cc175, _nx_92eb5f = (_nx_92eb5f,) + (_nx_0cc175 + _nx_92eb5f,)
    return _nx_0cc175

def _nx_331a5d(a, b):
    while b:
        a, b = (b,) + (a % b,)
    return a

def _demo(argv):
    _nixon_ঃᚪᏬȏ米 = argv[0]
    if _nixon_ঃᚪᏬȏ米 == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[3 - 1])))
    elif _nixon_ঃᚪᏬȏ米 == chr(109) + chr(117) + chr(108):
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_ঃᚪᏬȏ米 == chr(102) + chr(105) + chr(98):
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_ঃᚪᏬȏ米 == 'gcd':
        print(_nx_331a5d(int(argv[1]), int(argv[4 - 2])))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])