# Blind-Property Baseline: Information Matters, But Less as Modules Grow

**Date:** 2026-10-30
**Trigger:** a review of the paper noted that growth in probe count with
candidate count is "near-definitional without a random-property baseline". This
is that baseline.

## The control

The same attacker, the same builds, and the same candidate counts, but the
property set is replaced by **blind** properties — four assertions that always
return true and therefore carry no information about which candidate is the
target. A blind attacker must evaluate every candidate with every property.

## Result

| candidates | specification properties | blind properties |
|---|---|---|
| 1 | **2.0** probes | 8.0 |
| 2 | **3.4** | 12.0 |
| 3 | **5.8** | 16.0 |
| 4 | **8.6** | 20.0 |

## What it shows

1. **Information matters.** The specification set costs less than the blind set
   at every size — 2.0 versus 8.0 at one candidate, 8.6 versus 20.0 at four.
   The module-size effect is not pure search-space arithmetic; a specification
   buys roughly a factor of two at small sizes.
2. **The advantage shrinks with size.** Blind properties grow linearly (+4
   probes per candidate), specification properties super-linearly (2.0, 3.4,
   5.8, 8.6). By four candidates the specification set costs 43% of the blind
   set, against 25% at one candidate.

That second observation is the more interesting one for a deployer: adding
same-shaped siblings penalises the informed attacker faster than the uninformed
one, so the *relative* value of a good specification erodes as a module grows.

## What it does not show

- **That the module-size effect is inherent.** This is one benchmark with one
  obfuscation configuration; a different family mix could change the shape.
- **Anything about the diversity null.** The baseline is about candidate count,
  not about transform families; it neither supports nor undermines §5.1.
- **That blind properties are a realistic attacker.** They are a control, not a
  model of one.

## Where this belongs in the paper

§5.2 currently reports the monotone curve without a baseline. It should report
this table beside it, with the sentence: *an attacker with no information spends
8.0 probes at one candidate and 20.0 at four, against 2.0 and 8.6 for one with a
specification, so the growth is not merely the size of the search space.*
