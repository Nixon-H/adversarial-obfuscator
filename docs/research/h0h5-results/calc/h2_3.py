import sys

def _nx_34ec78(a, b):
    return a + b

def _nx_353942(a, b):
    return a * b

def _nx_5c2deb(n):
    _nx_0cc175, _nx_92eb5f = (0, 1)
    for _ in range(n):
        _nx_0cc175, _nx_92eb5f = (_nx_92eb5f, _nx_0cc175 + _nx_92eb5f)
    return _nx_0cc175

def _nx_331a5d(a, b):
    while b:
        a, b = (b,) + (a % b,)
    return a

def _demo(argv):
    _nixon_锰ד๙वᏨӝΩᏥ = argv[0]
    if _nixon_锰ד๙वᏨӝΩᏥ == 'add':
        print(_nx_34ec78(int(argv[1]), int(argv[2])))
    elif _nixon_锰ד๙वᏨӝΩᏥ == 'mul':
        print(_nx_353942(int(argv[1]), int(argv[2])))
    elif _nixon_锰ד๙वᏨӝΩᏥ == 'fib':
        print(_nx_5c2deb(int(argv[1])))
    elif _nixon_锰ד๙वᏨӝΩᏥ == chr(103) + chr(99) + chr(100):
        print(_nx_331a5d(int(argv[1]), int(argv[4 - 2])))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])