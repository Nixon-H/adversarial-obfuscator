# CI Was Red for Twenty-Eight Rounds and Nobody Looked

**Date:** 2026-10-30
**Corrects:** the round-41 claim that "a CI run would have caught it".

## What actually happened

Round 41 found that `test_h0_matches_legacy_seed_control` had been failing
since round 2, when `"vm"` was removed from H0's pass set. My conclusion was
that a CI run would have caught it immediately and I had simply not run the
full suite.

That was wrong in the most uncomfortable way. **CI ran. CI failed. I did not
check.**

The last five completed runs, from the commits that added the real-corpus
tasks and the pilot, all failed:

| commit | conclusion |
|---|---|
| 8334829 | failure |
| b1fa1b2 | failure |
| 4055a4f | failure |
| 3750858 | failure |
| 7cb1aad | failure |

The failure on 8334829 is the same assertion: the H0 pass set no longer ends
with `"vm"`.

## Why the feedback was missed

- I ran targeted test subsets and read their output.
- I checked `gh run list` a few times and saw `queued` or `in_progress`, and
  treated that as "verification pending" rather than "verification absent".
- Nothing in the workflow required a green run before continuing, and no
  summary step surfaced the red state.

There are currently 24 queued runs and 2 in progress, so the queue has been
backed up for a long time. A backlog is easy to mistake for a pending green
run; it is not the same thing, and treating it that way is what allowed a
month-equivalent of red CI to go unread.

## What the fix changes

The round-41 fix (`45731b9`) corrects the test, so the affected runs should
pass once the queue clears. But the process lesson is separate from the fix:

**Before claiming a state is verified, read the verdict rather than the queue.**
"Queued" and "in progress" are not evidence, and neither is a targeted subset
of tests. Only a completed run with `success` is.

## What is still unknown

- Why the queue is backed up. It could be runner capacity, billing, or a
  workflow configuration. This session has not diagnosed it and should not
  guess.
- Whether any *other* failure is hiding behind the 26 non-completed runs. The
  five most recent completed runs all failed on this same test, which suggests
  one cause, but the earlier queued commits have not been checked.

## Round 43: the queue is a runner problem, not only a concurrency one

A concurrency group was added (`.github/workflows/ci.yml`) so superseded runs
are cancelled and the newest commit gets the runner. That is correct and will
help once runners are available.

It does not explain the current state. After the change, new runs are still
`queued`, as are the older ones — nothing is being picked up at all. That
points at runner availability (capacity, billing, or a disabled runner), not at
queue depth, and this session cannot diagnose or fix it from here.

**So the honest statement is two-part:**

1. the workflow now has the concurrency control it lacked, so a backlog cannot
   silently accumulate again in the same way;
2. CI feedback is currently unavailable for reasons outside this repository's
   configuration, and the local suite is the only verification in effect.

Anything claiming "CI is green" while runs sit queued is unsupported. The
verification that counts today is the local run.
