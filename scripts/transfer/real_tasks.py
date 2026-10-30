"""Tasks built from real corpus functions, not hand-written fixtures.

The synthetic benchmark (`tasks.py`) was chosen to avoid memorisation. Its
cost is that the functions are toy-sized and the siblings were designed by the
same person who wrote the specs. This module takes the opposite trade: real
programs already in the repository (`scripts/transfer/corpus/`), with their
own functions as siblings.

That is the closest this repository gets to the review's "real corpus"
requirement without scraping public projects, and it keeps the memorisation
property because these programs are repository-local.

Each task names a module (for siblings) and a target function, with a property
set written from what the function is documented to do.
"""

import os
import types

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")


def _module_source(rel):
    with open(os.path.join(CORPUS, rel), encoding="utf-8") as f:
        return f.read()


TASKS = {}


def _task(name, module_rel, target, props, eval_inputs):
    TASKS[name] = {
        "module": module_rel,
        "target": target,
        "props": props,
        "eval_inputs": eval_inputs,
    }


_task(
    "rle_encode",
    "held_out/codec/prog.py",
    "rle_encode",
    [
        lambda f: f("aaa") == "a3",
        lambda f: f("") == "",
        lambda f: f("ab") == "a1b1",
        lambda f: f("aaab") == "a3b1",
        lambda f: f("aaaaaaaaaa") == "a9a1",   # count caps at 9
    ],
    [("aab",), ("",), ("abcabc",)],
)

_task(
    "rle_decode",
    "held_out/codec/prog.py",
    "rle_decode",
    [
        lambda f: f("a3") == "aaa",
        lambda f: f("") == "",
        lambda f: f("a1b1") == "ab",
        lambda f: f("a3b1") == "aaab",
    ],
    [("a2b2",), ("",), ("z1",)],
)

_task(
    "slugify",
    "calibration/parser/prog.py",
    "slugify",
    [
        lambda f: f("Hello World") == "hello-world",
        lambda f: f("") == "",
        lambda f: f("a  b") == "a-b",
        lambda f: f("ABC") == "abc",
    ],
    [("X Y",), ("",), ("Lead and trail",)],
)

_task(
    "gcd",
    "calibration/calc/prog.py",
    "gcd",
    [
        lambda f: f(12, 18) == 6,
        lambda f: f(7, 13) == 1,
        lambda f: f(0, 5) == 5,
        lambda f: f(5, 0) == 5,
    ],
    [(8, 12), (9, 6), (17, 5)],
)


_task(
    "priority_pick",
    "held_out/sched/prog.py",
    "priority_pick",
    [
        lambda f: f([("a", 1), ("b", 5), ("c", 3)]) == "b",
        lambda f: f([]) == "",
        lambda f: f([("x", 2)]) == "x",
        lambda f: f([("p", 1), ("q", 1)]) == "p",
    ],
    [([("m", 3), ("n", 9)],), ([],), ([("z", 7)],)],
)

_task(
    "rotate_list",
    "held_out/sched/prog.py",
    "rotate_list",
    [
        lambda f: f([1, 2, 3], 1) == [2, 3, 1],
        lambda f: f([], 3) == [],
        lambda f: f([1, 2, 3], 0) == [1, 2, 3],
        lambda f: f([1, 2, 3], 3) == [1, 2, 3],
    ],
    [([4, 5, 6], 2), ([], 1), ([7], 5)],
)

_task(
    "store_get",
    "development/store/prog.py",
    "store_get",
    [
        lambda f: f({"a": 1}, "a", 0) == 1,
        lambda f: f({}, "a", 0) == 0,
        lambda f: f({"a": None}, "a", 9) is None,
        lambda f: f({}, "z", "d") == "d",
    ],
    [({"b": 2}, "b", -1), ({}, "q", 0), ({"c": 5}, "c", -1)],
)

_task(
    "store_keys",
    "development/store/prog.py",
    "store_keys",
    [
        lambda f: f({"a": 1, "b": 2}) == ["a", "b"],
        lambda f: f({}) == [],
        lambda f: f({"z": 1}) == ["z"],
    ],
    [({"m": 0, "n": 1},), ({},), ({"q": 9},)],
)

def module_source(task_name):
    """The target module's source plus nothing else: siblings are its own."""
    return _module_source(TASKS[task_name]["module"])


def functions(src):
    ns = {}
    exec(src, ns)
    return {n: v for n, v in ns.items() if isinstance(v, types.FunctionType)}
