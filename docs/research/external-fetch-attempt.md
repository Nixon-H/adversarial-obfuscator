# Attempting an External Corpus: One Module, Zero Tasks

**Date:** 2026-10-30
**Attempt:** fetch a permissively licensed external module and extract
specification-testable functions, to begin closing the corpus gap.

## What was done

`six.py` (MIT, 34,702 bytes, `github.com/benjaminp/six`) was fetched and scanned
with the same criteria used on the in-repo corpus: top-level functions, no
decorators, ≤12 statements, 1–2 arguments, no I/O references in the body, and a
docstring longer than 25 characters.

## Result

| quantity | value |
|---|---|
| bytes fetched | 34,702 |
| documented pure functions | **4** |
| of those, usable as tasks | **0** |

The four candidates are `_add_doc`, `remove_move`, `add_metaclass` and
`python_2_unicode_compatible`. Three are **decorators**, which take a function
or class and return a modified one — their contract is a transformation of a
callable, not a value, and a property set would have to construct functions to
test them. The fourth mutates a module attribute.

None has a contract that can be asserted from its documentation with simple
inputs, which is what the benchmark requires.

## What this establishes

**The corpus gap is a specification problem, not a fetching problem.** Getting
code is trivial; the yield of *tasks* is the constraint, and on this module it
was zero.

That is consistent with the in-repo scan, where 37% of eligible pure functions
had a substantive docstring, and it is stronger: even among the documented ones
here, the contracts were not expressible as assertions over inputs.

## What it does not establish

- That external corpora are infeasible. One module is one sample, and `six.py`
  is compatibility plumbing rather than application logic. A repository of
  numerical or parsing code would yield a normal rate; this one has almost no
  value-returning documented functions.
- That the criterion is right. Requiring a docstring and simple inputs may be
  too strict; the alternative is writing specifications by reading bodies, which
  is the error the acquisition plan rules out.

## Consequence

The acquisition plan's eligibility criteria stand, and its estimate — roughly
five to ten eligible functions per thousand lines — is **optimistic** for
utility libraries and may hold only for application code with documented APIs.
The plan should say that, and it now does.

This is recorded as a negative attempt rather than omitted, because "we tried to
get a corpus and could not" is the honest status and it is more useful to the
next attempt than silence.
