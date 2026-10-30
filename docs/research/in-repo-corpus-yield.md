# In-Repo Corpus Yield: 220 Candidates, 82 Statable

**Date:** 2026-10-30
**Method:** static scan of `obfuscator/` for small pure functions — no
decorators, ≤12 statements, 1–3 arguments, no I/O or runtime-module references
in the body.

## Result

| quantity | value |
|---|---|
| eligible small pure functions | **220** |
| with a substantive docstring (>30 chars) | **82** |
| ratio | 37% |

The 63% without documentation are not unusable in principle, but their
contracts could only be written by reading the body — which makes the
"specification" a restatement of the implementation, and turns the task into
"find the function whose code matches this code." That is the opposite of the
attacker model the study needs.

## What this establishes

**The corpus gap cannot be closed from inside this repository, and the reason
is specification, not code volume.** There are plenty of candidate functions;
there are not enough *documented* ones whose behaviour can be asserted without
reading them.

That matters because it is the same constraint the acquisition plan states for
external projects: eligibility is dominated by whether a specification can be
written from documentation, not by how much code is available. The in-repo scan
is a cheap measurement of that constraint, and it comes out at 1 in 3.

## What it does not establish

- That 82 is the true yield. The scan is syntactic: a docstring can be
  uninformative and an undocumented function can have an obvious contract
  (`len(x)`, `x + 1`).
- That those 82 are suitable. Many will take domain objects that cannot be
  called in isolation, which the scan does not check.
- That in-repo tasks would be *independent*. They share one author, one
  style, and one review process — the opposite of what the reviewer's
  "≥12 external projects" requirement is protecting against.

## Consequence

Adding in-repo tasks would raise the cell count without addressing the
objection, because the objection is about independence and specification
provenance. The honest move is to keep the in-repo corpus as a second
benchmark family (it already has eight tasks) and report the yield measurement
as evidence that the gap is real rather than an oversight.

This is recorded as a negative result: an obvious way to get more data was
available, was measured, and does not solve the problem.
