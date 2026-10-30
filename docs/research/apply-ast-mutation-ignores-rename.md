# RETRACTED: `apply_ast_mutation` does honour `symbol_rename`

**Retracted in round 132, three rounds after it was reported.**

## What I claimed

That `apply_ast_mutation` accepts `symbol_rename` and never reads it, silently
returning unrenamed code, as a ninth product defect.

## What was actually true

My evidence was:

```
sed -n '331,460p' sources.py | grep -c symbol_rename   -> 0
```

The function runs from line **331 to 727**. The renaming block is at line
**463** — three lines past the end of the range I searched. Counting across the
real range gives:

```
awk 'NR>=331 && NR<=727' sources.py | grep -c symbol_rename   -> 1
```

So the entry point does apply the renamer. **There is no ninth defect.** The
"silent ignore" was an artefact of a range literal I wrote and did not check.

## Why this one is worse than the others

The eight retractions so far were experiments with a broken instrument. This one
was **a grep with a bound I guessed**, and the conclusion drawn from it — that a
public API silently discards its central option — is the most alarming claim in
the programme. It was wrong, and it was written up as a finding with a severity
paragraph about "the most damaging failure mode available".

Two rounds were then spent specifying fixes for it, and one was implemented and
measured before the range was ever checked.

## What survives

- The **eleven failing tests are real** and their cause is still unknown. They
  were failing before round 125, they fail now, and the renamer does run.
- The **round 125 control** — that those eleven predate my fix — remains valid
  and was measured correctly.
- The **measurement discipline** from round 130 still works: fix B was rejected
  on a number, not an argument.

## The rule

**A grep proves nothing until you have checked that the range you searched
contains the thing.** Every "the code does not mention X" claim in this document
needs the line count of the searched region printed next to it.

That is the same error class as the invalid fixture in round 102: the instrument
was wrong, its output looked like an answer, and the answer was alarming enough
that it was not checked.
