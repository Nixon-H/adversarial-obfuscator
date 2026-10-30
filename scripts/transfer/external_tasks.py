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
EXTERNAL2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus", "external2", "statistics.py")
SECOND = ("median_low",)

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



_task(
    "median_low",
    [
        lambda f: f([1, 3, 5]) == 3,
        lambda f: f([1, 2, 3, 4]) == 2,
        lambda f: f([7]) == 7,
    ],
    [([2, 8, 9],), ([5, 6],), ([4, 4, 4],)],
)



def source_path(name=None):
    """The file a task's module lives in, so it can be compiled with a real name."""
    return EXTERNAL2 if name in SECOND else EXTERNAL


def module_source(name=None):
    with open(source_path(name), encoding="utf-8") as f:
        return f.read()


def functions(src, path=None):
    ns = {}
    exec(compile(src, path or EXTERNAL, "exec"), ns)
    return {n: v for n, v in ns.items() if isinstance(v, types.FunctionType)}
