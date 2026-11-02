"""Tasks specified from docstrings alone, by an author who had not read the
research programme.

This module exists as an instrument-validity control. Every other task in the
benchmark was specified by the same person who assembled the benchmark, so
"does a spec-derived property set identify the function" could be partly
self-consistency. Here the specifications were written from the functions'
own docstrings and doctests, without access to the framing documents.

Three third-party corpora are used, each vendored with its licence:

  * `corpus/external/recipes.py`   -- more-itertools (MIT)
  * `corpus/external2/statistics.py` -- CPython 3.13 (PSF)
  * `corpus/external3/strutils.py`  -- boltons (BSD-3)

Selection rules I applied, before running anything:

  1. module-level functions only;
  2. behaviour fully determined by the docstring plus inputs I invent, with a
     preference for functions whose docstring carries doctests;
  3. properties are executable predicates over a function object;
  4. evaluator inputs are chosen to separate the target from its siblings in
     the same module -- and, where I could foresee it, to avoid inputs on
     which two different statistics coincide (for example a sample covariance
     of 1.0 is also a Pearson correlation of 1.0).

Only value-returning functions were eligible: the harness compares the
original's return value with a candidate's by equality, so a function that
returns an iterator would compare as "no match" for reasons that have nothing
to do with the spec.

Nothing in this file was tuned against obfuscated output. The properties are
transcriptions of the docstrings' own examples plus the general rule the
docstring states.
"""

import os
import types

_HERE = os.path.dirname(os.path.abspath(__file__))

RECIPES = os.path.join(_HERE, "corpus", "external", "recipes.py")
STATISTICS = os.path.join(_HERE, "corpus", "external2", "statistics.py")
STRUTILS = os.path.join(_HERE, "corpus", "external3", "strutils.py")

# Which module each task's function lives in.
_WHERE = {
    "is_prime": RECIPES,
    "multinomial": RECIPES,
    "median_high": STATISTICS,
    "multimode": STATISTICS,
    "bytes2human": STRUTILS,
    "a10n": STRUTILS,
}

TASKS = {}


def _task(name, props, eval_inputs):
    TASKS[name] = {"target": name, "props": props, "eval_inputs": eval_inputs}


# --------------------------------------------------------------------------
# more-itertools recipes (MIT)
# --------------------------------------------------------------------------
# "Return True if n is prime and False otherwise." The docstring gives 37
# (prime), 3*13 (not), and 18_446_744_073_709_551_557 (prime), and states the
# function is exact below 10**24. 1 and 2 are not doctested but follow from
# the definition of primality.
_task(
    "is_prime",
    [
        lambda f: f(37) is True,
        lambda f: f(3 * 13) is False,
        lambda f: f(2) is True,
        lambda f: f(1) is False,
        lambda f: f(18_446_744_073_709_551_557) is True,
    ],
    [(37,), (39,), (2,)],
)

# "Number of distinct arrangements of a multiset." The docstring gives
# multinomial(3, 4, 2) == 1260, multinomial(5, 2, 2, 1, 1) == 83160 (the
# anagrams of "abracadabra"), multinomial(5, 7) == math.comb(12, 5), and the
# all-ones factorial case.
_task(
    "multinomial",
    [
        lambda f: f(3, 4, 2) == 1260,
        lambda f: f(5, 2, 2, 1, 1) == 83160,
        lambda f: f(5, 7) == 792,
        lambda f: f(1, 1, 1, 1, 1, 1, 1) == 5040,
    ],
    [(3, 4, 2), (5, 7), (2, 3)],
)

# --------------------------------------------------------------------------
# CPython statistics (PSF)
# --------------------------------------------------------------------------
# "When the number of data points is odd, the middle value is returned. When
# it is even, the larger of the two middle values is returned." Doctested on
# [1, 3, 5] -> 3 and [1, 3, 5, 7] -> 5. I use even-length data for two of the
# evaluator inputs precisely because `median` agrees with `median_high` on
# odd-length data, and a single odd input cannot separate the two.
_task(
    "median_high",
    [
        lambda f: f([1, 3, 5]) == 3,
        lambda f: f([1, 3, 5, 7]) == 5,
        lambda f: f([7]) == 7,
        lambda f: f([1, 2]) == 2,
    ],
    [([1, 3, 5, 7],), ([4, 1, 3, 2],), ([2, 4],)],
)

# "Return a list of the most frequently occurring values." Doctested: a
# single mode, three tied modes (in first-occurrence order), and the empty
# input. The evaluator inputs are deliberately multimodal, because on
# single-mode input `mode` returns the same value and would be
# indistinguishable from `multimode[0]`.
_task(
    "multimode",
    [
        lambda f: f("aabbbbbbbbcc") == ["b"],
        lambda f: f("aabbbbccddddeeffffgg") == ["b", "d", "f"],
        lambda f: f("") == [],
        lambda f: f([1, 2, 2, 3, 3]) == [2, 3],
    ],
    [("aabb",), ("",), ("aabbbbccddddeeffffgg",)],
)

# --------------------------------------------------------------------------
# boltons strutils (BSD-3)
# --------------------------------------------------------------------------
# The docstring gives five doctests: 128991 -> "126K", 100001221 -> "95M",
# 0 with ndigits=2 -> "0.00B", 1024 -> "1K", 1024**8 -> "1Y". The 1024-based
# step and the single-letter suffix are both pinned by those examples.
_task(
    "bytes2human",
    [
        lambda f: f(128991) == "126K",
        lambda f: f(100001221) == "95M",
        lambda f: f(0, 2) == "0.00B",
        lambda f: f(1024) == "1K",
        lambda f: f(1024 ** 8) == "1Y",
    ],
    [(128991,), (1024,), (0, 2)],
)

# Numeronym: first character, the number of characters between the first and
# the last, and the last character. Doctested on "abbreviation" -> "a10n",
# "internationalization" -> "i18n" and "" -> "". "localization" (12 letters,
# 10 between) is the one input I extrapolated rather than quoted; it is the
# general rule the two examples establish.
_task(
    "a10n",
    [
        lambda f: f("abbreviation") == "a10n",
        lambda f: f("internationalization") == "i18n",
        lambda f: f("") == "",
        lambda f: f("localization") == "l10n",
    ],
    [("internationalization",), ("abbreviation",), ("localization",)],
)


def source_path(name=None):
    """The file a task's module lives in, so it can be compiled with a real name."""
    if name in _WHERE:
        return _WHERE[name]
    raise KeyError(name)


def module_source(name=None):
    with open(source_path(name), encoding="utf-8") as f:
        return f.read()


def functions(src, path=None):
    ns = {}
    exec(compile(src, path or RECIPES, "exec"), ns)
    return {n: v for n, v in ns.items() if isinstance(v, types.FunctionType)}
