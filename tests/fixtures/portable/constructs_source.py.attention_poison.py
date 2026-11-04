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
    _nx_opaque = 22700 % 2 == 0
    if _nx_opaque == False:
        _nx_d0_0 = 124
        store = {}
        _nx_c0_0 = 1
        _nx_d0_1 = 59

        @functools.wraps(fn)
        def wrapper(*args):
            _nx_opaque = 4048 % 2 == 0
            if _nx_opaque == False:
                _nx_d0_0 = 110
                if args not in store:
                    store[args] = fn(*args)
                _nx_c0_0 = 1
            if _nx_opaque == False:
                _nx_d1_0 = 69
                if args not in store:
                    store[args] = fn(*args)
                _nx_c1_0 = 1
            if not _nx_opaque:
                pass
            else:
                if args not in store:
                    store[args] = fn(*args)
                return store[args]
        _nx_c0_1 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 241
        store = {}
        _nx_c1_0 = 1
        _nx_d1_1 = 253

        @functools.wraps(fn)
        def wrapper(*args):
            _nx_opaque = 4048 % 2 == 0
            if _nx_opaque == False:
                _nx_d0_0 = 110
                if args not in store:
                    store[args] = fn(*args)
                _nx_c0_0 = 1
            if _nx_opaque == False:
                _nx_d1_0 = 69
                if args not in store:
                    store[args] = fn(*args)
                _nx_c1_0 = 1
            if not _nx_opaque:
                pass
            else:
                if args not in store:
                    store[args] = fn(*args)
                return store[args]
        _nx_c1_1 = 1
    if not _nx_opaque:
        pass
    else:
        store = {}

        @functools.wraps(fn)
        def wrapper(*args):
            _nx_opaque = 4048 % 2 == 0
            if _nx_opaque == False:
                _nx_d0_0 = 110
                if args not in store:
                    store[args] = fn(*args)
                _nx_c0_0 = 1
            if _nx_opaque == False:
                _nx_d1_0 = 69
                if args not in store:
                    store[args] = fn(*args)
                _nx_c1_0 = 1
            if not _nx_opaque:
                pass
            else:
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
            return 'origin'
        case Point(x=0):
            return 'on-y'
        case Point(y=0):
            return 'on-x'
        case Point():
            return 'somewhere'
        case _:
            return 'other'

def walrus_count(values):
    _nx_opaque = 9159 % 2 == 1
    if _nx_opaque == False:
        _nx_d0_0 = 243
        n = 0
        _nx_c0_0 = 1
        _nx_d0_1 = 198
        while (chunk := values[n:n + 2]) != []:
            n += 2
        _nx_c0_1 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 246
        n = 0
        _nx_c1_0 = 1
        _nx_d1_1 = 29
        while (chunk := values[n:n + 2]) != []:
            n += 2
        _nx_c1_1 = 1
    if not _nx_opaque:
        pass
    else:
        n = 0
        while (chunk := values[n:n + 2]) != []:
            n += 2
        return n

def eg_sum(values):
    _nx_opaque = 6165 % 2 == 1
    if _nx_opaque == False:
        _nx_d0_0 = 38
        result = 0
        _nx_c0_0 = 1
        _nx_d0_1 = 130
        try:
            if not values:
                raise ValueError('empty')
            result = sum(values)
        except* ValueError:
            result = 0
        _nx_c0_1 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 20
        result = 0
        _nx_c1_0 = 1
        _nx_d1_1 = 241
        try:
            if not values:
                raise ValueError('empty')
            result = sum(values)
        except* ValueError:
            result = 0
        _nx_c1_1 = 1
    if not _nx_opaque:
        pass
    else:
        result = 0
        try:
            if not values:
                raise ValueError('empty')
            result = sum(values)
        except* ValueError:
            result = 0
        return result

def make_counter():
    _nx_opaque = 20271 % 2 == 1
    if _nx_opaque == False:
        _nx_d0_0 = 32
        count = 0
        _nx_c0_0 = 1
        _nx_d0_1 = 230

        def bump():
            _nx_opaque = 7119 % 2 == 1
            if _nx_opaque == False:
                _nx_d0_0 = 196
                nonlocal count
                _nx_c0_0 = 1
                _nx_d0_1 = 232
                count += 1
                _nx_c0_1 = 1
            if _nx_opaque == False:
                _nx_d1_0 = 206
                nonlocal count
                _nx_c1_0 = 1
                _nx_d1_1 = 131
                count += 1
                _nx_c1_1 = 1
            if not _nx_opaque:
                pass
            else:
                nonlocal count
                count += 1
                return count
        _nx_c0_1 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 190
        count = 0
        _nx_c1_0 = 1
        _nx_d1_1 = 107

        def bump():
            _nx_opaque = 7119 % 2 == 1
            if _nx_opaque == False:
                _nx_d0_0 = 196
                nonlocal count
                _nx_c0_0 = 1
                _nx_d0_1 = 232
                count += 1
                _nx_c0_1 = 1
            if _nx_opaque == False:
                _nx_d1_0 = 206
                nonlocal count
                _nx_c1_0 = 1
                _nx_d1_1 = 131
                count += 1
                _nx_c1_1 = 1
            if not _nx_opaque:
                pass
            else:
                nonlocal count
                count += 1
                return count
        _nx_c1_1 = 1
    if not _nx_opaque:
        pass
    else:
        count = 0

        def bump():
            _nx_opaque = 7119 % 2 == 1
            if _nx_opaque == False:
                _nx_d0_0 = 196
                nonlocal count
                _nx_c0_0 = 1
                _nx_d0_1 = 232
                count += 1
                _nx_c0_1 = 1
            if _nx_opaque == False:
                _nx_d1_0 = 206
                nonlocal count
                _nx_c1_0 = 1
                _nx_d1_1 = 131
                count += 1
                _nx_c1_1 = 1
            if not _nx_opaque:
                pass
            else:
                nonlocal count
                count += 1
                return count
        return bump

async def deliver(values):
    await asyncio.sleep(0)
    return sorted(values, reverse=True)

def main():
    _nx_opaque = 9614 % 2 == 0
    if _nx_opaque == False:
        _nx_d0_0 = 175
        holder = Holder()
        _nx_c0_0 = 1
        _nx_d0_1 = 220
        holder.slot = 7
        _nx_c0_1 = 1
        _nx_d0_2 = 141
        print('descriptor:', holder.slot)
        _nx_c0_2 = 1
        _nx_d0_3 = 96
        print('squares:', [slow_square(n) for n in range(5)])
        _nx_c0_3 = 1
        _nx_d0_4 = 87
        print('evens:', list(evens(9)))
        _nx_c0_4 = 1
        _nx_d0_5 = 197
        print('match:', [classify(p) for p in (Point(0, 0), Point(0, 3), Point(4, 0), Point(2, 2))])
        _nx_c0_5 = 1
        _nx_d0_6 = 84
        print('walrus:', walrus_count([1, 2, 3, 4, 5]))
        _nx_c0_6 = 1
        _nx_d0_7 = 222
        print('except-star:', eg_sum([1, 2, 3]), eg_sum([]))
        _nx_c0_7 = 1
        _nx_d0_8 = 166
        bump = make_counter()
        _nx_c0_8 = 1
        _nx_d0_9 = 236
        bump()
        _nx_c0_9 = 1
        _nx_d0_10 = 15
        bump()
        _nx_c0_10 = 1
        _nx_d0_11 = 230
        print('closure:', bump())
        _nx_c0_11 = 1
        _nx_d0_12 = 72
        print('dataclass:', Point(3, 4).norm())
        _nx_c0_12 = 1
        _nx_d0_13 = 150
        print('async:', asyncio.run(deliver([3, 1, 2])))
        _nx_c0_13 = 1
        _nx_d0_14 = 71
        print('OK')
        _nx_c0_14 = 1
    if _nx_opaque == False:
        _nx_d1_0 = 121
        holder = Holder()
        _nx_c1_0 = 1
        _nx_d1_1 = 109
        holder.slot = 7
        _nx_c1_1 = 1
        _nx_d1_2 = 102
        print('descriptor:', holder.slot)
        _nx_c1_2 = 1
        _nx_d1_3 = 20
        print('squares:', [slow_square(n) for n in range(5)])
        _nx_c1_3 = 1
        _nx_d1_4 = 120
        print('evens:', list(evens(9)))
        _nx_c1_4 = 1
        _nx_d1_5 = 27
        print('match:', [classify(p) for p in (Point(0, 0), Point(0, 3), Point(4, 0), Point(2, 2))])
        _nx_c1_5 = 1
        _nx_d1_6 = 41
        print('walrus:', walrus_count([1, 2, 3, 4, 5]))
        _nx_c1_6 = 1
        _nx_d1_7 = 137
        print('except-star:', eg_sum([1, 2, 3]), eg_sum([]))
        _nx_c1_7 = 1
        _nx_d1_8 = 135
        bump = make_counter()
        _nx_c1_8 = 1
        _nx_d1_9 = 64
        bump()
        _nx_c1_9 = 1
        _nx_d1_10 = 97
        bump()
        _nx_c1_10 = 1
        _nx_d1_11 = 33
        print('closure:', bump())
        _nx_c1_11 = 1
        _nx_d1_12 = 97
        print('dataclass:', Point(3, 4).norm())
        _nx_c1_12 = 1
        _nx_d1_13 = 26
        print('async:', asyncio.run(deliver([3, 1, 2])))
        _nx_c1_13 = 1
        _nx_d1_14 = 41
        print('OK')
        _nx_c1_14 = 1
    if not _nx_opaque:
        pass
    else:
        holder = Holder()
        holder.slot = 7
        print('descriptor:', holder.slot)
        print('squares:', [slow_square(n) for n in range(5)])
        print('evens:', list(evens(9)))
        print('match:', [classify(p) for p in (Point(0, 0), Point(0, 3), Point(4, 0), Point(2, 2))])
        print('walrus:', walrus_count([1, 2, 3, 4, 5]))
        print('except-star:', eg_sum([1, 2, 3]), eg_sum([]))
        bump = make_counter()
        bump()
        bump()
        print('closure:', bump())
        print('dataclass:', Point(3, 4).norm())
        print('async:', asyncio.run(deliver([3, 1, 2])))
        print('OK')
main()