import sys


def add(a, b):
    return a + b


def mul(a, b):
    return a * b


def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def _demo(argv):
    op = argv[0]
    if op == "add":
        print(add(int(argv[1]), int(argv[2])))
    elif op == "mul":
        print(mul(int(argv[1]), int(argv[2])))
    elif op == "fib":
        print(fib(int(argv[1])))
    elif op == "gcd":
        print(gcd(int(argv[1]), int(argv[2])))
    else:
        print("unknown op")


if __name__ == "__main__":
    _demo(sys.argv[1:])
