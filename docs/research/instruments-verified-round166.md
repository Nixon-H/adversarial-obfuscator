# All Four Instruments, One Round

**Date:** 2026-10-30, round 166.

Every instrument in the programme, run in one pass:

| instrument | result |
|---|---|
| task validity (internal) | **27 cells, 27 unique, 27 hit, 0 unnameable** |
| task validity (external) | **12 cells, 11 unique, 12 singleton** (superseded in round 171: 12 unique) |
| artefact gate | **26 checked, 0 failures** |
| reproduction | **8 of 8 tables** |
| test suite | **4521 passed, 4 skipped, 0 failed** |

## The one number that is not perfect

External validity was **11 of 12** unique at the time of this run. The failing cell
was `dotproduct` at build index 0, failing since round 91.

**Round 171 resolved it and the diagnosis above was wrong.** The evaluator's inputs
were fine; its candidate list counted classes and private aliases as functions.
`IndexError([1,2],[3,4])` constructs without raising, and `_sumprod` is bound to the
same implementation as the public `dotproduct`. Excluding both gives 12 of 12.

The paragraph below is kept as written because it records what I believed for
twelve rounds and why it was expensive: every attempt to "fix" the cell by widening
the inputs would have hidden a measurement bug behind a task change.

It is *reported* rather than pooled, which is why the count is 11 and not 12. A
benchmark that dropped the cell, or widened the evaluator inputs until it passed,
would report 12 and mean less.

## What each instrument can and cannot see

| instrument | catches | blind to |
|---|---|---|
| suite | code drifting from its contract | prose, artefact behaviour |
| gate | output that will not compile, import, run | contracts, prose |
| task validity | unscoreable cells | whether the task is interesting |
| reproduction | prose drifting from measurement | prose drifting from its own tables |
| numeric guard | table/count drift | every other number |

Five instruments, five different blind spots, and the last two exist only because
the first three were green while the documents said things that were no longer
true.

## What is still not measured

- **An independent specification.** All 38 properties are written by this
  programme's author. The external sources validate that artefacts run; they do not
  supply anyone else's reading of what a function should do.
- **Analyst time.** Probes are a resolution unit, not minutes. No human has been
  timed.
- **Comprehension.** Identification is not understanding; nothing here measures
  whether an analyst could explain or modify a recovered function.

These three are stated in the paper's limitations and none of them is reachable
from inside this repository.
