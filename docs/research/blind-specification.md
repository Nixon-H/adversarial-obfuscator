# Blind specification: six tasks written from docstrings alone

**Author:** an agent ("iceman") with no access to the research programme, the
benchmark tasks, the defect documents, the paper, or the handoff. Only
`scripts/transfer/external_tasks.py` and `scripts/transfer/evaluate_external.py`
were read, for the data shape; their property choices were not copied.

**Specification file:** `scripts/transfer/blind_tasks.py`
**SHA-256:** `3cb7f06a22806f2f2ddab4a475f022819b064a03425201bde65d579516387489`
**Sealed at:** 2026-11-02T01:50:23Z (2026-11-02 07:20:23 +0530, IST)
**Size:** 6,715 bytes

The hash was taken after the file was written and before any obfuscated output
was generated. It was re-checked after the evaluation run and still matches, so
every number below was produced by the file above.

## Interpreter

`/usr/bin/python3` 3.13.5 (GCC 14.2.0), `pytest 9.0.3`. This is the `python3`
that `python3 -m pytest` resolves to; the machine has a second Python
installation with a different `cryptography` version and it was not used.

## How the six were chosen

Eligibility, applied against the docstrings before running anything:

1. module-level function, not a method or a class;
2. behaviour fully determined by the docstring plus inputs I invent, preferring
   doctested functions;
3. value-returning: the harness compares the original's return value against a
   candidate's with `==`, so a function returning an iterator would compare as
   "no match" for reasons unrelated to the spec. This excluded most of the
   more-itertools recipes (`take`, `flatten`, `triplewise`, `pairwise`,
   `sieve`, `matmul`, `convolve`, `subslices`, `reshape`, `factor`, ...), which
   are generators here;
4. evaluator inputs chosen to separate the target from siblings *in the same
   module*, including inputs where two different statistics coincide (a sample
   covariance of 1.0 is also a Pearson correlation of 1.0, so covariance was
   not used).

Result: two functions from each corpus, six in total.

| Function | Corpus | Module |
|---|---|---|
| `is_prime` | more-itertools (MIT) | `scripts/transfer/corpus/external/recipes.py` |
| `multinomial` | more-itertools (MIT) | `scripts/transfer/corpus/external/recipes.py` |
| `median_high` | CPython 3.13 (PSF) | `scripts/transfer/corpus/external2/statistics.py` |
| `multimode` | CPython 3.13 (PSF) | `scripts/transfer/corpus/external2/statistics.py` |
| `bytes2human` | boltons (BSD-3) | `scripts/transfer/corpus/external3/strutils.py` |
| `a10n` | boltons (BSD-3) | `scripts/transfer/corpus/external3/strutils.py` |

All 26 properties were checked against the *original* functions before the
seal; all held. That check is a transcription check (did I copy the doctest
correctly), not a tuning step: no property was changed in response to it.

## The specifications

Each block quotes the docstring verbatim (dedented), then the properties, then
why I believe they pin the function.

### 1. `is_prime`

Docstring:

> Return ``True`` if *n* is prime and ``False`` otherwise.
>
> Basic examples:
>
>     >>> is_prime(37)
>     True
>     >>> is_prime(3 * 13)
>     False
>     >>> is_prime(18_446_744_073_709_551_557)
>     True
>
> Find the next prime over one billion:
>
>     >>> next(filter(is_prime, count(10**9)))
>     1000000007
>
> Generate random primes up to 200 bits and up to 60 decimal digits:
>
>     >>> from random import seed, randrange, getrandbits
>     >>> seed(18675309)
>
>     >>> next(filter(is_prime, map(getrandbits, repeat(200))))
>     893303929355758292373272075469392561129886005037663238028407
>
>     >>> next(filter(is_prime, map(randrange, repeat(10**60))))
>     269638077304026462407872868003560484232362454342414618963649
>
> This function is exact for values of *n* below 10**24.  For larger inputs,
> the probabilistic Miller-Rabin primality test has a less than 1 in 2**128
> chance of a false positive.

Properties:

```python
lambda f: f(37) is True
lambda f: f(3 * 13) is False
lambda f: f(2) is True
lambda f: f(1) is False
lambda f: f(18_446_744_073_709_551_557) is True
```

Why they pin it: `is`-comparison rules out a truthy integer (which `==` would
not). Two primes, one composite, one prime witness far outside trial-division
range (the function is asserted exact there), plus the two boundary values that
primality's definition fixes. A function that merely answers "is n odd" fails
on 2 and on 3*13; one that answers "is n > 1" fails on 39; a naive trial
division that is too slow on the 19-digit witness still returns the right
answer, so this spec does not pin the *algorithm*, only the *function*.

Evaluator inputs: `(37,)`, `(39,)`, `(2,)`. Chosen to give `True/False/True`
with the composite not equal to any obvious sibling output.

### 2. `multinomial`

Docstring:

> Number of distinct arrangements of a multiset.
>
> The expression ``multinomial(3, 4, 2)`` has several equivalent
> interpretations:
>
> * In the expansion of ``(a + b + c)⁹``, the coefficient of the
>   ``a³b⁴c²`` term is 1260.
>
> * There are 1260 distinct ways to arrange 9 balls consisting of 3 reds, 4
>   greens, and 2 blues.
>
> * There are 1260 unique ways to place 9 distinct objects into three bins
>   with sizes 3, 4, and 2.
>
> The :func:`multinomial` function computes the length of
> :func:`distinct_permutations`.  For example, there are 83,160 distinct
> anagrams of the word "abracadabra":
>
>     >>> from more_itertools import distinct_permutations, ilen
>     >>> ilen(distinct_permutations('abracadabra'))
>     83160
>
> This can be computed directly from the letter counts, 5a 2b 2r 1c 1d:
>
>     >>> from collections import Counter
>     >>> list(Counter('abracadabra').values())
>     [5, 2, 2, 1, 1]
>     >>> multinomial(5, 2, 2, 1, 1)
>     83160
>
> A binomial coefficient is a special case of multinomial where there are
> only two categories.  For example, the number of ways to arrange 12 balls
> with 5 reds and 7 blues is ``multinomial(5, 7)`` or ``math.comb(12, 5)``.
>
> Likewise, factorial is a special case of multinomial where
> the multiplicities are all just 1 so that
> ``multinomial(1, 1, 1, 1, 1, 1, 1) == math.factorial(7)``.
>
> Reference:  https://en.wikipedia.org/wiki/Multinomial_theorem

Properties:

```python
lambda f: f(3, 4, 2) == 1260
lambda f: f(5, 2, 2, 1, 1) == 83160
lambda f: f(5, 7) == 792
lambda f: f(1, 1, 1, 1, 1, 1, 1) == 5040
```

Why they pin it: four different arities (3, 5, 2, 7), all documented, including
the binomial case whose value follows from `math.comb(12, 5)`. A wrong
off-by-one in the factorial division, a swapped argument order, or a
"sum of counts" implementation fails at least one. It does not pin behaviour
on zero or negative counts, which the docstring does not define.

Evaluator inputs: `(3, 4, 2)`, `(5, 7)`, `(2, 3)` → 1260, 792, 10. Varied
arity, all distinct from sibling outputs.

### 3. `median_high`

Docstring:

> Return the high median of data.
>
> When the number of data points is odd, the middle value is returned.
> When it is even, the larger of the two middle values is returned.
>
> >>> median_high([1, 3, 5])
> 3
> >>> median_high([1, 3, 5, 7])
> 5

Properties:

```python
lambda f: f([1, 3, 5]) == 3
lambda f: f([1, 3, 5, 7]) == 5
lambda f: f([7]) == 7
lambda f: f([1, 2]) == 2
```

Why they pin it: the docstring defines the function completely, not just by
example — odd length takes the middle, even length takes the larger middle.
`median` agrees on every odd-length input, so two of the four properties are
even-length; `median_low` differs on both even-length cases. `[1, 2]` is the
smallest even case and separates "larger middle" from "lower middle" and from
"mean of middles" (1.5). The spec does not pin behaviour on unordered or
non-numeric input beyond what `median` also does.

Evaluator inputs: `([1, 3, 5, 7],)`, `([4, 1, 3, 2],)`, `([2, 4],)`. All
even-length, and two are unordered, so an implementation that assumes sorted
input is distinguishable from one that sorts.

### 4. `multimode`

Docstring:

> Return a list of the most frequently occurring values.
>
> Will return more than one result if there are multiple modes
> or an empty list if *data* is empty.
>
> >>> multimode('aabbbbbbbbcc')
> ['b']
> >>> multimode('aabbbbccddddeeffffgg')
> ['b', 'd', 'f']
> >>> multimode('')
> []

Properties:

```python
lambda f: f("aabbbbbbbbcc") == ["b"]
lambda f: f("aabbbbccddddeeffffgg") == ["b", "d", "f"]
lambda f: f("") == []
lambda f: f([1, 2, 2, 3, 3]) == [2, 3]
```

Why they pin it: the docstring states both the multi-mode result *and* its
order (the doctest's `['b', 'd', 'f']` fixes first-occurrence order, not
sorted order). The empty case is explicit. The list-of-ints case checks that
the function is not string-specific. A `mode`-like implementation returns a
scalar and fails; a Counter-ordered implementation that sorts would return
`['b', 'd', 'f']` here too, so sortedness against first-occurrence order is
only weakly separated — the int case `[2, 3]` happens to be both.

Evaluator inputs: `("aabb",)`, `("",)`, `("aabbbbccddddeeffffgg",)`. All
multi-modal or empty, deliberately: on single-mode input `mode` returns the
same value as `multimode[0]` and the two cannot be separated.

### 5. `bytes2human`

Docstring:

> Turns an integer value of *nbytes* into a human readable format. Set
> *ndigits* to control how many digits after the decimal point
> should be shown (default ``0``).
>
> >>> bytes2human(128991)
> '126K'
> >>> bytes2human(100001221)
> '95M'
> >>> bytes2human(0, 2)
> '0.00B'
> >>> bytes2human(1024)
> '1K'
> >>> bytes2human(1024 ** 8)
> '1Y'

Properties:

```python
lambda f: f(128991) == "126K"
lambda f: f(100001221) == "95M"
lambda f: f(0, 2) == "0.00B"
lambda f: f(1024) == "1K"
lambda f: f(1024 ** 8) == "1Y"
```

Why they pin it: five doctests covering the default precision, an explicit
`ndigits`, the zero case, the exact unit boundary (1024 → `1K`, i.e. binary not
decimal divisors), and the largest suffix (`Y`). 128991 → `126K` pins rounding
(125.97 → 126, nearest) rather than truncation. I did *not* add properties for
values just below a boundary (e.g. 1023), because the docstring does not state
the boundary rule explicitly and I did not want to guess a rounding convention.

Evaluator inputs: `(128991,)`, `(1024,)`, `(0, 2)`. Three different return
strings and two different arities.

### 6. `a10n`

Docstring:

> That thing where "internationalization" becomes "i18n", what's it
> called? Abbreviation? Oh wait, no: ``a10n``. (It's actually a form
> of `numeronym`_.)
>
> >>> a10n('abbreviation')
> 'a10n'
> >>> a10n('internationalization')
> 'i18n'
> >>> a10n('')
> ''
>
> .. _numeronym: http://en.wikipedia.org/wiki/Numeronym

Properties:

```python
lambda f: f("abbreviation") == "a10n"
lambda f: f("internationalization") == "i18n"
lambda f: f("") == ""
lambda f: f("localization") == "l10n"
```

Why they pin it: the two words are 12 and 20 letters and their numeronyms keep
the first and last letter with the count of the letters between them; that
generalises to any word. `""` is explicit. `localization` (12 letters) is the
one input I extrapolated rather than quoted — it is the rule the two examples
establish, not a new rule. A function that counts total length, or that trims
rather than elides, fails. The spec does not pin behaviour for 2- and 3-letter
words, which the docstring never shows and on which "count between" has no
room for a number.

Evaluator inputs: `("internationalization",)`, `("abbreviation",)`,
`("localization",)`. Only one sibling (`slugify("")`) coincides on the empty
string, and the empty string is not an evaluator input; the other two inputs
separate `a10n` from every string helper in the module.

## Evaluation

Command: `python3 scripts/transfer/evaluate_blind.py`
(`generate_variant(src, k, {"master_seed": 4242})`, `k ∈ {0, 2, 4}`; the
candidate collector excludes classes and underscore-prefixed names exactly as
`evaluate_external.py` does.)

```
task          module          k  cand  matches  pass unique
is_prime      recipes.py      0  75    1        1    True
is_prime      recipes.py      2  75    1        1    True
is_prime      recipes.py      4  75    1        1    True
multinomial   recipes.py      0  75    1        1    True
multinomial   recipes.py      2  75    1        1    True
multinomial   recipes.py      4  75    1        1    True
median_high   statistics.py   0  41    1        1    True
median_high   statistics.py   2  41    1        1    True
median_high   statistics.py   4  41    1        1    True
multimode     statistics.py   0  41    1        1    True
multimode     statistics.py   2  41    1        1    True
multimode     statistics.py   4  41    1        1    True
bytes2human   strutils.py     0  34    1        1    True
bytes2human   strutils.py     2  34    1        1    True
bytes2human   strutils.py     4  34    1        1    True
a10n          strutils.py     0  34    1        1    True
a10n          strutils.py     2  34    1        1    True
a10n          strutils.py     4  34    1        1    True

cells 18  evaluator-unique 18  attacker-singleton 18

is_prime      evaluator-unique 3/3  attacker-singleton 3/3
multinomial   evaluator-unique 3/3  attacker-singleton 3/3
median_high   evaluator-unique 3/3  attacker-singleton 3/3
multimode     evaluator-unique 3/3  attacker-singleton 3/3
bytes2human   evaluator-unique 3/3  attacker-singleton 3/3
a10n          evaluator-unique 3/3  attacker-singleton 3/3
```

`matches` is the number of candidates in the obfuscated module whose return
values equal the original's on the evaluator inputs; `pass` is the number that
pass the property set. Every cell is exactly 1 and 1.

The generator emits "potential scope issues" warnings on stdout for all three
modules (e.g. `take: ['islice', 'iterable', 'n', 'list']`). They are
diagnostics about free names, they appear for the unmodified pipeline too, and
they did not prevent generation or execution: every variant compiled and ran.

## Honest confidence assessment

**Least confident: `bytes2human` boundaries and `multinomial` edge
cases.** Concretely: `bytes2human` — the five doctests pin the examples but not
the boundary rule at 1023/1024 or the rounding mode at an exact .5, so a
correct implementation that differs from this one only at boundaries would
still pass my spec. `multinomial` — the docstring never defines behaviour for
zero counts or negative counts; I deliberately did not specify them, and a
candidate that mishandles them would be invisible to my property set.
`a10n('localization')` is the single property I extrapolated rather than read;
it held on the original, but it is my inference from two examples, not a quoted
doctest. `is_prime(1)` and `is_prime(2)` are definitional rather than
doctested — I judge that safe, but it is an inference.

**Strongest:** `median_high` and `multimode`. Both docstrings state the rule,
not only examples, and the property sets separate them from their nearest
siblings (`median`, `median_low`, `mode`) by construction.

**What a different author would have written differently.** Someone with the
same docstrings and a different temperament would almost certainly: (a) add
error-behaviour properties (`StatisticsError` on empty data for the statistics
functions, `ValueError` for a negative `r` in `nth_combination`), which the
docstrings do state for some functions — I did not use any such function
because I restricted myself to value-returning ones, but an author who allowed
`pytest.raises` specs would have a different, stricter benchmark; (b) use
floating-point functions (`geometric_mean`, `covariance`, `correlation`) with
`round(...)`, which I avoided because the docstrings explicitly disclaim exact
results, and an author more comfortable with approximate equality would pick
them; (c) write more properties (8–10 rather than 3–5), especially boundary
values; (d) include a function with keyword-only arguments, which none of mine
has except `human_readable_list`-style specs I skipped as under-documented.
So the six are a *conservative* sample: documented, doctested, value-returning
functions. A less conservative author would have produced harder specs and
probably a lower pass rate; my 18/18 should be read as "conservative specs
still identify their functions", not as an upper bound on spec difficulty.

## What I did not know

While writing `blind_tasks.py` I had not read any file in `docs/research/`,
the paper draft, the benchmark's own tasks, the defect documents, or the
handoff. I did not know: what the programme's central claim is; what a
"semantic" property set means in this context; what the expected result of the
attacker-singleton gate was; which transforms the pipeline applies or which of
them are supposed to preserve which behaviours; that thirteen correctness
defects had been found, or what they were; the phrase "channel" as the paper
uses it; and whether the six functions I picked overlapped with any existing
task (I verified after sealing that none of the six names appears in
`external_tasks.py`: that file specifies `all_equal`, `dotproduct`, `take` and
`median_low`).

What I did know, because the task statement said so: the repository is a
Python obfuscator; there is a benchmark with these two gates; and the concern
is that specs written by the benchmark's author might be self-consistent rather
than identifying. That framing is the experimental condition, not a leak: it
tells me *that* uniqueness matters, not *what the answer will be*.

One consequence worth stating plainly: I read the three corpus modules'
function list, signatures and docstrings, but not their bodies (except the
import header implicitly, and `evaluate_external.py`'s comments about private
aliases). So these specs are docstring-derived in the strict sense — if an
implementation contradicts its own docstring, my property set follows the
docstring, and the original function would fail its own spec. That did not
happen in any of the 26 properties, which is itself a small consistency result
about the corpora.
