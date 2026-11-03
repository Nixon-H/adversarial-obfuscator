"""Payload covering the constructs the demo does not: async, generators, dataclasses,
match, decorators with arguments, walrus, except*, descriptors, closures, comprehensions.

Prints a deterministic result so a build can be compared against its source.
"""
import asyncio
import dataclasses
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


@dataclasses.dataclass
class Point:
    x: int
    y: int

    def norm(self):
        return (self.x * self.x + self.y * self.y) ** 0.5


def cached(fn):
    store = {}

    @functools.wraps(fn)
    def wrapper(*args):
        if args not in store:
            store[args] = fn(*args)
        return store[args]

    return wrapper


@cached
def slow_square(n):
    return n * n


def evens(limit):
    for n in range(limit):
        if n % 2 == 0:
            yield n


def classify(point):
    match point:
        case Point(x=0, y=0):
            return "origin"
        case Point(x=0):
            return "on-y"
        case Point(y=0):
            return "on-x"
        case Point():
            return "somewhere"
        case _:
            return "other"


def walrus_count(values):
    n = 0
    while (chunk := values[n:n + 2]) != []:
        n += 2
    return n


def eg_sum(values):
    result = 0
    try:
        if not values:
            raise ValueError("empty")
        result = sum(values)
    except* ValueError:
        result = 0
    return result


def make_counter():
    count = 0

    def bump():
        nonlocal count
        count += 1
        return count

    return bump


async def deliver(values):
    await asyncio.sleep(0)
    return sorted(values, reverse=True)


def main():
    holder = Holder()
    holder.slot = 7
    print("descriptor:", holder.slot)
    print("squares:", [slow_square(n) for n in range(5)])
    print("evens:", list(evens(9)))
    print("match:", [classify(p) for p in (Point(0, 0), Point(0, 3), Point(4, 0), Point(2, 2))])
    print("walrus:", walrus_count([1, 2, 3, 4, 5]))
    print("except-star:", eg_sum([1, 2, 3]), eg_sum([]))
    bump = make_counter()
    bump(); bump()
    print("closure:", bump())
    print("dataclass:", Point(3, 4).norm())
    print("async:", asyncio.run(deliver([3, 1, 2])))
    print("OK")


main()
