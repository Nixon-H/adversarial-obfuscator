# State After 134 Rounds

**Date:** 2026-10-30

Two independent checks disagree, and both are correct.

## Suite: green

```
4513 passed, 5 skipped, 0 failed   (21 minutes)
```

Eleven contract tests that had been failing since before round 125 now pass. Their
cause was **not** any of the five hypotheses the programme pursued: it was a stale
call to a reverted helper, left behind by an incomplete revert in round 123, with
the resulting `TypeError` swallowed by an `except` that returned the original
source. See `swallowed-exception-returns-original.md`.

## Gate: red

```
artefacts checked: 48
failures: 2
  bulk/iterutils seed=4242 k=0: NameError: _nx_f24f62
  bulk/iterutils seed=7    k=0: NameError: _nx_f24f62
```

The eighth defect is still open. The function table references a name that is
never defined, deterministically at build index 0 and seed-dependently at index 2.
Mechanism recorded in `table-key-folding-defect.md`; three fixes were attempted
and all three reverted.

## Why both are right

The suite tests **contracts** — that the renamer renames, that `__all__` is
preserved, that the seed changes the output. The gate tests **artefacts** — that
what the obfuscator emits compiles, imports and runs.

The stale-call defect was invisible to the gate (the output ran; it was the input)
and loud in the suite. The table defect is invisible to the suite (no contract
covers a 61 KB module) and loud in the gate.

**Neither check is sufficient, and the programme has now demonstrated that in both
directions.**

## The ledger

| | |
|---|---|
| defects fixed | nine |
| defects open | one (the function table) |
| retractions | nine |
| documents | 46 |
| sealed reports | 40 |
| commit | `86ccea5` |

## The most honest sentence available

Nine of the ten defects were found by **widening the corpus** or by **reading the
output**, not by reasoning about the code. Every fix that was reverted had been
derived from a hypothesis; every fix that held came from a measurement.

The eighth defect is still open because the last three attempts to fix it were
derived from hypotheses rather than from the reduction its document says is
missing.

## Round 157: one commit is unpushed, and why

Round 157 added a Research programme section to the root `README.md` so the work is
discoverable from the repository root rather than only from `docs/research/`. The
commit succeeded locally:

```
490d7ee Root README: point at the research programme and the four checks
```

`git push` fails:

```
git@github.com: Permission denied (publickey).
~/.ssh/id_ed25519.pub exists; ssh-add -l -> The agent has no identities.
```

The key is present but not loaded into the agent, and this session cannot add it
without a passphrase prompt. Every earlier push in this programme succeeded, so the
agent has lost its identities rather than the key having changed.

**Status: one commit ahead of origin.** Nothing is lost — the work is committed, the
tests pass against it, and the next session with a loaded key can push it.

## What this means for the record

The repository state and the published state have diverged by one commit. That is
worth recording explicitly rather than silently, because every other claim in this
directory has been verified against the **local** tree, and one commit's worth of
changes is not yet visible to anyone who clones.

The affected change is documentation only: a README section naming the four checks
and linking `docs/research/README.md`. No code, no test, no claim depends on it.
