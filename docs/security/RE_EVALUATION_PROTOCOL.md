# Reverse-engineering evaluation protocol

Review register, P1 row *independent payload semantic review*, and §6 of the
register: "Measure whether an analyst can recover program behaviour, not
simply whether recognizable strings or identifiers remain absent."

**Status: NOT RUN.** This is the protocol and the scoring key. No independent
analyst has performed the evaluation. The maintainers' own sampling
(`docs/research/pydeobsbench-2026-11-18.md` §5u, §6c, §6d) is preparation
material, not independent verification, and the register treats it that way.

## 1. What this measures, and what it does not

It measures **semantic recovery cost**: given a built artefact and a fixed
budget, how much of the program's behaviour can a competent analyst recover?

It does NOT measure:

* whether the obfuscation is "unbreakable" — nothing is, and that is not the
  claim;
* whether strings or identifiers survive — that is a weaker, easier question
  and the register explicitly deprecates it;
* anything about the cryptographic layer, which has its own package
  (`CRYPTO_REVIEW_PACKAGE.md`).

## 2. The subject

`tests/fixtures/re_subject.py` — 60 lines, integer arithmetic, no imports
beyond `sys`. Chosen so the semantics are FINITE and CHECKABLE: an analyst
either recovers a specific formula or does not, and the score is not a matter
of impression.

The subject is built twice:

| arm | build | given to analyst |
|---|---|---|
| **obfuscated** | full protection stack, `--package native`, section split | yes |
| **control** | same source, obfuscation disabled | yes, as the baseline |

The analyst receives BOTH artefacts and is told which is which. The control
establishes their personal cost floor: if they take 20 hours on the control
and 22 on the obfuscated build, the obfuscation bought 10%, and that is a
finding worth recording rather than hiding.

The analyst is NOT given the source, the build tree, or this document's §4.

## 3. Budget and conditions

* **40 analyst-hours**, self-reported with timestamps. Tools unrestricted
  (Ghidra, gdb, strace, pycdc, custom scripts — whatever they choose); every
  tool recorded.
* Single analyst, or a pair who report jointly. The register's external
  review should be one person's output, not a committee's, so the cost figure
  is interpretable.
* The analyst may RUN the artefact as many times as they like. Observing
  behaviour is expected and is part of the measurement.
* The analyst must preserve raw notes, command history and any scripts they
  wrote. Those are the evidence, not a summary.

## 4. Scoring key — DO NOT GIVE THIS SECTION TO THE ANALYST

Four objectives, each scored 0 / 1 / 2.

**O1 — entry function.** Is the entry point identified?

| score | criterion |
|---|---|
| 0 | no entry point identified |
| 1 | a function that is called at startup is named/described, but not shown to be the entry |
| 2 | the entry function is identified and shown (by call graph, tracing, or behaviour) to be the one that drives the output |

**O2 — the numeric algorithm.** The ground truth:

```
balance = ( Σ_i  amount_i × max(1, 1000 − 7·i) ) // 1000
if balance > 50000:  balance −= penalty;  verdict = "settled"
else:                verdict = "rejected"
```

| score | criterion |
|---|---|
| 0 | no arithmetic recovered |
| 1 | the loop-and-accumulate shape recovered, or the decay recovered, but not both; OR the formula recovered with the wrong constant |
| 2 | the formula recovered with the correct decay (7), the correct divisor (1000), and the correct threshold (50000) |

Partial credit is deliberately coarse. An analyst who recovers "it's a
weighted sum with a decaying weight" but not the constants has recovered the
SHAPE and not the SEMANTICS, which is the distinction the register asks to
measure.

**O3 — string surface.**

| score | criterion |
|---|---|
| 0 | no string constants recovered |
| 1 | some recovered (`settled` / `rejected` / `audit`) but not all three |
| 2 | all three recovered, with their roles described (verdict values vs. audit prefix) |

**O4 — integrity-check semantics.**

| score | criterion |
|---|---|
| 0 | no awareness that tampering is detected |
| 1 | observed that modification prevents execution, without explaining the mechanism |
| 2 | explained that the artefact verifies its own bytes (or its provenance) and that failure is silent with exit 137 |

**Total: 0–8 per arm.** Report both arms and the DELTA. The headline number
for the register is `obfuscated_total − control_total` and
`obfuscated_hours − control_hours`.

## 5. Behavioural equivalence (a separate gate)

Independently of the scores, the analyst must answer: do the two arms
produce the same output for the same input? They should
(`RE-SUBJECT-OUTCOME 38664 rejected` then `audit:rejected`). If the analyst
finds a behavioural difference, that is a **build correctness defect**, not an
obfuscation result, and it outranks every score in this protocol.

## 6. Deliverables the analyst returns

1. Filled scoring table for both arms (O1–O4, 0–2 each).
2. Hours and tool inventory per arm.
3. Raw notes, scripts and command history.
4. A short narrative: what was easy, what was the wall, what would have
   made it easier.
5. Their own statement of the recovered algorithm, in their words.

## 7. What the maintainers must NOT do

* Must not coach, hint, or answer questions about the subject during the
  evaluation.
* Must not score the analyst's work themselves — the analyst fills the table,
  and the independent reviewer of the *evaluation* checks it against §4.
* Must not report a favourable arm alone. Both arms and the delta, always.
* Must not describe a high score as a failure of the product without saying
  what the control scored on the same objectives.

## 8. Known limitations of this design

* **One subject, 60 lines.** A single small program cannot characterise a
  large codebase. It measures whether obfuscation changes recovery cost AT
  ALL, not by how much across a real product.
* **The scoring is coarse.** 0/1/2 hides a lot. It is chosen so two
  independent scorers would agree; a finer scale would not be reproducible.
* **Analyst skill dominates.** A stronger analyst may score 8/8 on both arms
  in fewer hours. The delta is the interpretable number, not the raw score.
* **40 hours may be too short** to reach the wall on a good build, or too
  long for a weak one. If the analyst finishes the obfuscated arm in under 4
  hours, the budget was not the binding constraint and the result says more
  about the subject's size than about the protection.
* **This is one measurement, not a certification.** A good result here does
  not license a claim that the product resists reverse engineering in
  general.

## 9. Why the package exists

The register's P1 row cannot be closed by maintainers. What can be closed is
the protocol: a subject with checkable semantics, two arms, a fixed budget, a
scoring key that does not depend on the scorer's taste, and an explicit list
of what the measurement cannot support. When an analyst returns results, they
join this register as a measured row like any other.
