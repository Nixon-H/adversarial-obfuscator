"""A small multi-task benchmark: targets with siblings and executable specs.

The calibration so far is n=1 task. That is the binding limit on every claim
it can make, and one task cannot produce a variance estimate. This module
adds tasks, not projects: each task is a function with same-shaped siblings
and a property set written from its specification.

Why hand-written rather than scraped from public repositories: the review
warned that a public corpus lets a model-based attacker recall source, which
inflates recovery. Hand-written tasks cannot be recalled, so a favourable
result cannot be explained by memorisation. The cost is that they are
synthetic; that cost is recorded in the limits, not hidden.

Every task follows the same contract:
  name, target source, siblings (list of sources), properties (list of
  callables taking the candidate and returning True if it conforms).

The properties are the attacker's asset and contain no reference outputs.
"""

TASKS = {}


def _task(name, target, siblings, props):
    TASKS[name] = {"target": target, "siblings": siblings, "props": props}


_task(
    "sumselected",
    "def sumselected(values, lo, hi):\n"
    "    total = 0\n"
    "    for v in values:\n"
    "        if lo <= v < hi:\n"
    "            total += v\n"
    "    return total\n",
    [
        "def sa(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v * 2\n"
        "    return total\n",
        "def sb(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo < v <= hi:\n"
        "            total += v\n"
        "    return total\n",
        "def sc(values, lo, hi):\n"
        "    total = 1\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v\n"
        "    return total\n",
    ],
    [
        lambda f: f([1, 2, 3], 0, 10) == 6,
        lambda f: f([], 0, 10) == 0,
        lambda f: f([5], 0, 5) == 0,   # hi exclusive
        lambda f: f([5], 5, 6) == 5,   # lo inclusive
    ],
)

_task(
    "countchars",
    "def countchars(text, ch):\n"
    "    return sum(1 for c in text if c == ch)\n",
    [
        "def ca(text, ch):\n"
        "    return sum(1 for c in text if c != ch)\n",
        "def cb(text, ch):\n"
        "    return len(text)\n",
        "def cc(text, ch):\n"
        "    return text.count(ch) + 1\n",
    ],
    [
        lambda f: f("banana", "a") == 3,
        lambda f: f("banana", "z") == 0,
        lambda f: f("", "a") == 0,
        lambda f: f("aa", "a") == 2,
    ],
)

_task(
    "clamp01",
    "def clamp01(x):\n"
    "    if x < 0:\n"
    "        return 0\n"
    "    if x > 1:\n"
    "        return 1\n"
    "    return x\n",
    [
        "def c1(x):\n"
        "    if x < 0:\n"
        "        return 0\n"
        "    return x\n",
        "def c2(x):\n"
        "    if x > 1:\n"
        "        return 1\n"
        "    return x\n",
        # c3 used to be `x + 0.0`, which is semantically identical to the
        # target -- so the task had two correct answers and no attacker could
        # be scored. A decoy must actually differ.
        # c3 must differ from the target in at least one observed case. The
        # clamp high bound is 2 here instead of 1, so x > 1 separates them.
        "def c3(x):\n"
        "    return min(max(x, 0), 2)\n",
    ],
    [
        lambda f: f(-5) == 0,
        lambda f: f(5) == 1,
        lambda f: f(0.5) == 0.5,
        lambda f: f(0) == 0,
        lambda f: f(1) == 1,
    ],
)

_task(
    "is_even",
    "def is_even(n):\n"
    "    return n % 2 == 0\n",
    [
        "def e1(n):\n    return n % 2 == 1\n",
        "def e2(n):\n    return n % 4 == 0\n",
        "def e3(n):\n    return n > 0\n",
    ],
    [
        lambda f: f(2) is True,
        lambda f: f(3) is False,
        lambda f: f(0) is True,
        lambda f: f(-2) is True,
    ],
)

_task(
    "maxlen",
    "def maxlen(words):\n"
    "    best = 0\n"
    "    for w in words:\n"
    "        if len(w) > best:\n"
    "            best = len(w)\n"
    "    return best\n",
    [
        "def m1(words):\n"
        "    best = 0\n"
        "    for w in words:\n"
        "        if len(w) < best or best == 0:\n"
        "            best = len(w)\n"
        "    return best\n",
        "def m2(words):\n"
        "    return len(words)\n",
        "def m3(words):\n"
        "    best = 1\n"
        "    for w in words:\n"
        "        if len(w) > best:\n"
        "            best = len(w)\n"
        "    return best\n",
    ],
    [
        lambda f: f(["a", "bbb", "cc"]) == 3,
        lambda f: f([]) == 0,
        lambda f: f([""]) == 0,
        lambda f: f(["x"]) == 1,
    ],
)

_task(
    "running_total",
    "def running_total(xs):\n"
    "    out = []\n"
    "    total = 0\n"
    "    for x in xs:\n"
    "        total += x\n"
    "        out.append(total)\n"
    "    return out\n",
    [
        "def r1(xs):\n"
        "    out = []\n"
        "    for x in xs:\n"
        "        out.append(x)\n"
        "    return out\n",
        "def r2(xs):\n"
        "    out = []\n"
        "    total = 0\n"
        "    for x in xs:\n"
        "        total += x\n"
        "        out.append(total * 2)\n"
        "    return out\n",
        "def r3(xs):\n"
        "    out = [0]\n"
        "    total = 0\n"
        "    for x in xs:\n"
        "        total += x\n"
        "        out.append(total)\n"
        "    return out\n",
    ],
    [
        lambda f: f([1, 2, 3]) == [1, 3, 6],
        lambda f: f([]) == [],
        lambda f: f([0]) == [0],
        lambda f: f([-1, 1]) == [-1, 0],
    ],
)

_task(
    "signdiff",
    "def signdiff(a, b):\n"
    "    return (a > 0) != (b > 0)\n",
    [
        "def s1(a, b):\n    return (a > 0) == (b > 0)\n",
        "def s2(a, b):\n    return a > b\n",
        "def s3(a, b):\n    return (a >= 0) != (b > 0)\n",
    ],
    [
        lambda f: f(1, -1) is True,
        lambda f: f(-1, 1) is True,
        lambda f: f(1, 1) is False,
        lambda f: f(-1, -1) is False,
    ],
)

_task(
    "first_negative",
    "def first_negative(xs):\n"
    "    for i, x in enumerate(xs):\n"
    "        if x < 0:\n"
    "            return i\n"
    "    return -1\n",
    [
        "def fn1(xs):\n"
        "    for i, x in enumerate(xs):\n"
        "        if x > 0:\n"
        "            return i\n"
        "    return -1\n",
        "def fn2(xs):\n"
        "    for i, x in enumerate(xs):\n"
        "        if x < 0:\n"
        "            return i\n"
        "    return 0\n",
        "def fn3(xs):\n"
        "    for i, x in enumerate(xs):\n"
        "        if x <= 0:\n"
        "            return i\n"
        "    return -1\n",
    ],
    [
        lambda f: f([1, -2, 3]) == 1,
        lambda f: f([1, 2]) == -1,
        lambda f: f([-1]) == 0,
        lambda f: f([0, -1]) == 1,   # zero is not negative
    ],
)

_task(
    "count_above",
    "def count_above(values, limit):\n"
    "    n = 0\n"
    "    for v in values:\n"
    "        if v > limit:\n"
    "            n += 1\n"
    "    return n\n",
    [
        "def ca1(values, limit):\n"
        "    n = 0\n"
        "    for v in values:\n"
        "        if v >= limit:\n"
        "            n += 1\n"
        "    return n\n",
        "def ca2(values, limit):\n"
        "    n = 0\n"
        "    for v in values:\n"
        "        if v < limit:\n"
        "            n += 1\n"
        "    return n\n",
        "def ca3(values, limit):\n"
        "    return len(values)\n",
    ],
    [
        lambda f: f([1, 2, 3], 1) == 2,
        lambda f: f([], 5) == 0,
        lambda f: f([5], 5) == 0,      # strict comparison
        lambda f: f([6], 5) == 1,
    ],
)
