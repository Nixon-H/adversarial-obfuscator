# Trying to Automate Stale-Count Detection, and Why It Failed

**Date:** 2026-10-30, round 173.

Rounds 155, 163, 172 each found prose describing an older version of the work. Round
164's guard checks the four numbers that can be derived mechanically. This round
tried to go further: flag **conflicting "N of M" claims** across documents.

## The attempt

Scan every research document for `N of M`, group by `M`, and fail when two live
claims disagree. Lines containing "superseded", "historical", "Updated in round" or
"was **11" are treated as deliberately historical and skipped.

It failed immediately:

```
AssertionError: conflicting '9'-of-9 claims:
  {'9 of 9': ['cost-is-build-independent.md:140', 'cost-is-build-independent.md:241'],
   '8 of 9': ['external-tasks-evaluated.md:36']}
```

**"9 of 9" is tasks where the module-size curve is monotone. "8 of 9" was external
cells that were unique.** Different quantities, same shape `N of M`, and the guard
cannot tell them apart.

## Why it cannot work as written

`N of M` is not a claim with a fixed referent. The same pattern appears for
monotonicity, validity, permutation agreement and singleton audit. To compare them
the guard would need to know **what each `M` counts** — which is the semantic
understanding the guard exists to avoid depending on.

A narrower version would check only `of 12` (external cells) and only in the two
documents that discuss them. That is one rule per quantity, and the previous rounds
show each rule catches only the drift it was written for.

## What was reverted

The test. Shipping a guard that fires on unrelated counts would train the next
reader to ignore it — the same failure as a test skip, in a different costume.

## What stands instead

- The round 164 guard, which checks four derivable numbers.
- The 163 audit, recorded.
- A rule in `HANDOFF.md`: **when a fix changes a number, grep for the old one.**

The last is the honest state: stale-count detection is a **search**, not a check,
and no test written this round improved on searching.
