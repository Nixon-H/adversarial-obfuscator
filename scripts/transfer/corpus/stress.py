"""Constructs the current corpus does not use: async, generators,
descriptors, except*, walrus, match with classes, decorators with arguments."""

import asyncio
import functools


class Descriptor:
    def __init__(self):
        self._value = 0

    def __get__(self, obj, objtype=None):
        return self._value

    def __set__(self, obj, value):
        self._value = value


class Holder:
    slot = Descriptor()


def cached(fn):
    cache = {}

    @functools.wraps(fn)
    def wrapper(*args):
        if args not in cache:
            cache[args] = fn(*args)
        return cache[args]

    return wrapper


@cached
def slow_square(n):
    return n * n


def squares(n):
    for i in range(n):
        yield i * i


def running_sum(values):
    total = 0
    for v in values:
        total += v
        yield total


async def gather_two(a, b):
    async def one(x):
        return x * 2

    return await one(a) + await one(b)


def grouped(values):
    # NOTE: `except*` forbids return/break/continue in its body, so the handler
    # assigns and the function returns after the try/except. An earlier version
    # of this module put `return 0` inside the handler, which made the FILE
    # invalid Python -- and the obfuscator's SyntaxError was then correct
    # behaviour reported as a defect.
    result = 0
    try:
        if not values:
            raise ValueError("empty")
        result = sum(values)
    except* ValueError:
        result = 0
    return result


def walrus_count(values):
    n = 0
    while (chunk := values[n:n + 2]) != []:
        n += 2
    return n
