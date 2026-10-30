"""Tasks from a real third-party library, with its licence.

Every earlier task came from this repository: hand-written, or corpus functions
whose specifications the same author wrote. This module takes functions from
`more-itertools` (MIT), vendored at `corpus/external/recipes.py` with the
licence retained in the file.

The functions are value-returning helpers with doctested contracts, which is why
this module yielded 49 documented candidates where `six.py` yielded none. The
siblings are the library's own other functions.
"""

import os
import types

EXTERNAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus", "external", "recipes.py")

TASKS = {}


def _task(name, props, eval_inputs):
    TASKS[name] = {"target": name, "props": props, "eval_inputs": eval_inputs}


_task(
    "all_equal",
    [
        lambda f: f("aaaa") is True,
        lambda f: f("aaab") is False,
        lambda f: f([1, 1, 1]) is True,
        lambda f: f([]) is True,
        lambda f: f([1, 2]) is False,
    ],
    [("bbbb",), ("ab",), ([2, 2],)],
)

_task(
    "dotproduct",
    [
        lambda f: f([10, 15, 12], [0.65, 0.80, 1.25]) == 33.5,
        lambda f: f([1, 2], [3, 4]) == 11,
        lambda f: f([], []) == 0,
        lambda f: f([2], [3]) == 6,
    ],
    [([1, 1], [2, 2]), ([], []), ([5], [0])],
)

_task(
    "take",
    [
        lambda f: f(3, range(10)) == [0, 1, 2],
        lambda f: f(10, range(3)) == [0, 1, 2],
        lambda f: f(0, range(5)) == [],
        lambda f: f(2, [7, 8, 9]) == [7, 8],
    ],
    [(1, [4, 5]), (5, [1]), (0, [1, 2])],
)


def module_source():
    with open(EXTERNAL, encoding="utf-8") as f:
        return f.read()


def functions(src):
    ns = {}
    exec(compile(src, EXTERNAL, "exec"), ns)
    return {n: v for n, v in ns.items() if isinstance(v, types.FunctionType)}
