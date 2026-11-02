# Final audit of `docs/research/paper-draft.md`

**Auditor:** iceman (closing audit, third task)
**Date:** 2026-11-02
**Baseline:** `master` at `a463f44`, clean before this file was added.
**Interpreter:** `/usr/bin/python3 3.13.5 (main, Aug 10 2026, 12:06:59) [GCC 14.2.0]`

**What I ran, not just read:** `python3 -m pytest
tests/test_research_docs_consistency.py tests/test_research_numbers_match_sources.py -q`;
`python3 scripts/transfer/matched_families.py`; `python3 scripts/transfer/reproduce.py`;
a direct count of `docs/research/*.md` and of `artefact_gate._modules()`; and a
`table_singleton()` call that returns the non-singleton count the printed table
omits. No existing file was modified. This file is new.

---

## 1. Is the retitled claim supported by the artefacts?

### 1.1 What the artefacts actually say

`matched_families.py` reproduces the claim exactly. I ran it independently and got:

| check | result |
|---|---|
| callable counts before equalisation | A = 4 or 5, B = C = 5 or 6; A one fewer on all 17 tasks |
| A-vs-B, before / counts matched | **+0.33 / +0.00** |
| A-vs-C, before / counts matched | **+0.33 / +0.00** |
| B-vs-C, before / counts matched | **0.00 / +0.00** |
| matched probe counts A = B = C | **51 / 51 task-seed cells** |
| pad additivity (0,1,2,3 pads) | **459 measurements, 0 deviations** |
| source-side pre-padding (2 pads) | **0 / 153 count, 0 / 153 probe differences** |
| symmetric padding to max+2 | **+0.00 on all three pairings** |
| full survival trajectory | **0 mismatches in 51 cells** |

`reproduce.py` independently gives: singleton 51; module-size
`{1: 2.0, 2: 3.4, 3: 5.8, 4: 8.6}`; diversity
`{A-vs-B: 0.33, A-vs-C: 0.33, B-vs-C: 0}`; fixed-build `[9,9,9,9,9]`;
fault-control 9 → 11; authoring 38; calibration `[9,11,20,20]`;
blind baseline `{1: 8.0, 2: 12.0, 3: 16.0, 4: 20.0}`.

The confound is confirmed and the controlled result is real. **The two headline
sentences are supported as written:**

> "Transform-family diversification adds no measurable cost once the number of
> callables each family inserts is held constant." (abstract, lines 36–37)

> "Equalise the counts and the difference is **exactly 0.00 on all three
> pairings and all 17 tasks**, with matched probe counts identical across
> families in all 51 task/seed cells." (abstract, lines 46–48)

### 1.2 Verdict: supported as a metric-specific null; overclaimed as a title

The abstract and conclusion are careful. The **title** is not. The evidence
supports "no measurable difference on this probe counter, on these 17 tasks,
with counts matched"; it does not support "diversification adds nothing beyond
the callables it inserts" as a general statement. The paper's own evidence
document says so:

> "The null is mostly forced. On 10 of 17 tasks `probes = k` exactly, so
> matching counts *cannot* leave a difference under this counter. Only the 7
> tasks with `c > 0` could have shown a second channel. That is a small basis,
> and it is the honest scope of the evidence." (`matched-count-experiment.md`,
> lines 208–210)

> "A family effect smaller than one probe could not be resolved." (ibid., line
> 225)

> "That equality is partly forced by the counter (on 10 of 17 tasks probes
> equal the callable count), and it is evidence about this metric, not about
> attacker effort in general." (ibid., lines 244–246)

> "Padding up, not stripping down. … the matched artefact is 'A's own four
> candidates plus a foreign no-op', not a natural five-callable A." (ibid.,
> lines 217–221)

The paper carries two of these caveats in §5.1b (10/17 arithmetic; inert
pads), but the abstract's "the one-callable gap accounted for the whole effect"
and the title carry none of them. The conclusion explicitly disclaims the
general reading:

> "We do not claim the families are equally hard. We claim that a specification
> applied unchanged to every build is insensitive to the family that produced
> it …" (lines 455–457)

That is the defensible claim. The title says something else.

### 1.3 Exactly where the claim is stronger than the evidence

1. **"Adds Nothing" vs "no measurable cost".** The measured claim is
   resolution-limited: one probe per task, and the diff statistic quantises to
   multiples of 1/3. The doc says a family effect smaller than one probe could
   not be resolved (line 225). The title has no resolution qualifier.
2. **"Diversification" vs "transform-family diversification".** The paper
   tested three transform families (A/B/C), one build index (4), three seeds,
   Python source, function identification. The title generalises all of that
   away.
3. **"Beyond the callables it inserts" vs "beyond callable count".** The
   experiment pads A with a foreign no-op; it does not remove B's or C's extra
   string-decoding helper. The doc calls this "padding up, not stripping down"
   and says the matched artefact is not a natural five-callable A. The evidence
   supports "the count difference explains the mean difference"; it does not
   support "the *specific* inserted callables are the only channel" in general.
4. **"The whole effect" without the 10/17 caveat.** On 10 of 17 tasks
   `probes = k`, so the matched equality is partly arithmetic; only 7 tasks are
   load-bearing. The abstract states the result without that qualifier; §5.1b
   states it honestly. The title/abstract should not be stronger than §5.1b.
5. **One crossed observation per task.** The statistic crosses families only
   at seed 22; each task contributes one crossed comparison. "All 17 tasks"
   is 17 tasks, not 17 independent replications of a family effect. The doc
   says this (lines 222–225); the abstract does not.

---

## 2. Remaining internal contradictions

I found eight that survive the rewrite, plus two smaller ones. The abstract and
conclusion do **not** contradict each other; the contradictions are between the
abstract/title and the body, and within §5 and §6.

### 2.1 The channel: §5.3 still says the paper does not claim one

**Side A** — §5.1b heading and text (lines 208, 216–218):

> "### 5.1b The channel is structural, and it was measured"
>
> "Since §5.2 shows the counter tracks module size, **the family comparison
> measures callable-count difference, not family diversity**"

**Side B** — §5.3 (lines 302–304):

> "It shows the counter responds to semantics; it does not create a channel
> from transform family to probe count, and **the paper does not claim one**."

The first sentence's "it" can be read as the calibration, but the final clause
is unqualified and false: §5.1b and §5.2 claim exactly that channel. The
sentence should be restricted to "the calibration creates no channel", not "the
paper does not claim one."

### 2.2 The defect count: "four", "three", and the table disagree

**Side A** — abstract (lines 67–69):

> "**thirteen correctness defects** in the obfuscator that the benchmark found
> — **four of which produce artefacts that compile and then fail**"

**Side B** — §6.1 (lines 336–337):

> "**Three of them** produce artefacts that are syntactically valid, compile,
> and then fail — at import or at first call."

**Side C** — the table (lines 320–332) has a different split: **3 defects that
do not compile** (`#3`, `#5`, `#7`), **7 that fail at import** (`#4`, `#6`,
`#8`, `#10`, `#11`, `#12`, `#13`), and **3 runtime/wrong-answer/logic defects**
(`#1`, `#2`, `#9`). Neither "four" nor "three" matches the table. Worse, two of
the three bullets under §6.1 (dataclass, `match`) are explicitly "does not
compile" in the table and in the prose itself ("an empty class body is not
valid Python"; "`SyntaxError`"), so they are not "syntactically valid, compile,
and then fail."

This is the exact class of prose-count defect the guard tests were written to
catch; they do not catch it because they only check "N defects" phrases, not
"four of which" or "three of them."

### 2.3 "All/every defect" vs the 30-day expiry

**Side A** — §6.3 (lines 369–371) and §6.5 (lines 409–412):

> "**All of them** are visible to one that compiles **and imports** the output
> over real modules."
>
> "… and **it would have caught every defect above**."

**Side B** — §6.2 (lines 355–358), table row 1 (line 320), and the attached
defect document:

> "At pack time that window is zero; at run time it is recomputed from the
> wall clock, so it becomes 1 after thirty days and the key no longer
> matches. Every artefact stopped decrypting a month after it was built."

> "| 1 | 30-day expiry | artefact stops decrypting a month after build |
> reading the key derivation |"

`dataclass-body-strip.md` is explicit: "Compiling and importing every generated
artefact … would have caught 3 and 4 immediately and 2 the first time a function
was called." It does **not** include 1, the expiry. A compile-and-import gate at
build time cannot see a fuse that fires thirty days later. The same overclaim
covers row 13: importing the emitted `_cmp` module alone succeeds; the failure is
in `attr/__init__.py`, the importer, which the recommendation does not say to
import. The table's own "found by" column says row 1 was found by "reading the
key derivation", not by a gate.

### 2.4 Order invariance: §5.2 and the abstract vs §7

**Side A** — §5.2 (lines 273–275) and abstract (lines 63–65):

> "Permuting sibling order leaves the endpoint unchanged (**every permutation
> ends at 9**) while the path moves, so the endpoint is order-invariant and
> sibling-dependent."

> "… monotonically in nine of nine tasks and **invariant to the order the
> functions appear in**."

**Side B** — §7 (lines 434–435):

> "**Order invariance** was established on one task's permutations, not all."

The underlying evidence is `sumselected` only (`cost-is-build-independent.md`,
six permutations; the earlier review checked all 24). The paper's §5.2 does not
say "on `sumselected`", and the abstract generalises it to all nine module-size
tasks. Either scope the sentence to `sumselected`, or say "one task".

### 2.5 The external-package count: "two" vs "one"

**Side A** — abstract (lines 30–31):

> "A further five external sources (**three single-file libraries and two
> vendored packages**, 38 artefacts) are gated for execution"

**Side B** — §7 (lines 420–422):

> "plus five external sources gated for execution (**three single-file
> libraries and one vendored packages**, 38 artefacts)."

"Three plus one" is four, not five; the grammar is also broken ("one vendored
packages"). The gate has **two** vendored packages: `pkg/more_itertools` and
`pkg/attr` (14 package modules total). The abstract's "two" is right; §7's
"one" is stale. This is a surviving count defect, not a stylistic choice.

### 2.6 "A factor of two" vs the same sentence's 25%

**Side A** — §5.2 (lines 280–283):

> "a specification buys **roughly a factor of two at small sizes**, and the
> advantage erodes as modules grow (**25% of the blind cost at one candidate**,
> 43% at four)."

**Side B** — the table (lines 268–271): 2.0 vs 8.0 at one candidate; 8.6 vs 20.0
at four.

25% of the blind cost means the specification costs **one quarter**, i.e. a 4×
advantage at one candidate; at four it is 2.3×. "Factor of two at small sizes"
is wrong for the smallest size and is contradicted by the parenthetical in the
same sentence. The earlier review asked for "2.3× at four, 4× at one"; the
sentence was not fixed.

### 2.7 "No source-level analogue exists" vs "a bounded statement and nothing stronger"

**Side A** — §2 (lines 95–96):

> "It is not a systematic review — eight queries over two sessions, fifteen
> sources screened — so it **supports a bounded statement and nothing
> stronger**."

**Side B** — §2 (lines 110–112):

> "CoDiver's partition diversity denies analysis-knowledge transfer in
> virtualised code … **No source-level analogue exists**."

A universal negative ("exists") is stronger than a bounded statement. Either
say "none was found in the screen" (the honest form) or drop the sentence. This
is the same finding as the earlier review's item 13; it survives.

### 2.8 "Both families" vs three families

**Side A** — §5.4 (line 308):

> "Across **both families** at three build indices: **51 cells, zero
> non-singleton**."

**Side B** — §5.1b (line 232) and §7 (lines 428–429):

> "exactly 0.00 on **all three pairings**"
>
> "**Family space.** **Three families**, two shown equally hard."

"Both families" cannot mean the transform families: there are three. It means
the two task provenances (synthetic and real corpus), as
`sibling-separation-audit.md` uses "both families". But the paper never defines
that usage, and §7 uses "families" for transform families. This is the
terminology collision the earlier review flagged; it survives. The 51 cells are
17 tasks × 3 build indices, not a family count.

### 2.9 "Real programs" and "same-arity siblings"

**Side A** — abstract (lines 27–28):

> "We build 17 tasks — nine hand-written and **eight drawn from real
> programs** — each a target function **among same-arity siblings**"

**Side B** — §4.1 (lines 143–146):

> "Nine hand-written … eight drawn from **this repository's own corpus** …
> where **the siblings are the other functions in the module**."

The eight are in-repo `prog.py` demo modules, not third-party real programs, and
their siblings are not all same-arity: `held_out/codec/prog.py` has
`rle_encode(text)` (1 arg) beside `xor_bytes(data, key)` (2 args); target
`gcd(a, b)` (2) sits beside `fib(n)` (1). The body says "the other functions in
the module", which is accurate. The abstract's "real programs" and "same-arity"
are both stronger than the artefact. This is the earlier review's item 3,
partly fixed in the body and not fixed in the abstract.

### 2.10 "Each was measured against the existing suite"

**Side A** — §6.4 (lines 390–391):

> "The three possible exits are all product decisions rather than fixes, and
> **each was measured against the existing suite**"

**Side B** — §6.4 (lines 395–397):

> "**The first was implemented and reverted**; the other two are bounded by the
> architecture and by usability respectively."

Only the first exit has a suite result (`test_no_all_unchanged_behavior` fails).
Exit 2 is a whole-program redesign; exit 3 is a usability judgement. "Each was
measured against the existing suite" is false for two of the three. The attached
document says the same over-strong thing ("measured rather than assumed"), but
the table only supports the first.

### 2.11 Smaller residuals (not counted above)

- **§6 intro vs its table.** "All of them were found because the benchmark
  demanded something the project's own tests did not" (lines 314–316) vs table
  row 1 "found by reading the key derivation" and row 9 "found by suite".
- **"one per defect" in the artefacts table.** The paper lists ten defect
  documents for thirteen defects (lines 474–475); `dataclass-body-strip.md`
  (which covers the expiry, dataclass, and unbound-import defects) is not in
  the list. "One per defect, all cited here" is false.
- **§6.5 "thirteen silent failure modes"** is loose: the compile/import
  failures are loud once the output is compiled, not silent. The paper's own
  §6.1 calls them "code that does not run." A wording fix, not a data error.

---

## 3. Numbers I could not verify from an attached artefact

I did **not** try to fix any of these.

### 3.1 Stale or contradicted

| claim | where | status |
|---|---|---|
| "`docs/research/` (60 files)" | artefacts table, line 474 | **Stale.** At audit time there were **66 `.md`** files at `docs/research/` and **67** regular files (before adding this audit). The header admits the document count is not regenerated; it is also out of date. |
| "four of which produce artefacts that compile and then fail" | abstract, lines 68–69 | **Contradicted.** The table has 3 no-compile, 7 import-fail, 3 runtime/wrong-answer defects; §6.1 says "three". No artefact says "four". |
| "38 artefacts" attached to the five external sources | abstract, lines 30–31; §7, line 422 | **Misattributed.** `gate-count.json` says 38, and `_modules()` confirms 38; but 38 is the **whole gate**: 9 synthetic + 8 corpus + 1 stress + 20 external. The external count is **20**, not 38. No artefact says the five external sources produce 38 artefacts. |
| "five external sources" | abstract, line 30; §7, line 420 | **Not enumerable from the artefacts.** The gate has 20 external modules from four upstream libraries (boltons, `more_itertools`, `attrs`, cpython) — or five if boltons' `strutils` and `iterutils` are counted separately. §7's own enumeration is 3 + 1 = 4. |
| "four or five executable assertions per task" | §4.2, line 165 | **Overbroad if read across all 17.** The nine synthetic tasks are 4–5; the eight corpus tasks are 3–5 (`store_keys` has 3). The "38 properties across nine tasks" sentence correctly scopes the 38/9, but "per task" is unqualified. |
| "one per defect" | artefacts table, line 475 | **False.** Ten documents are listed for thirteen defects; `dataclass-body-strip.md` (the document for the expiry, dataclass, and unbound-import defects) is absent. |
| `external module 1/2/4/5/6` labels | defect table, lines 322–332 | **Undefined.** The paper never maps these labels to modules; `external module 3` is absent. A reader cannot verify which external module found which defect. |

### 3.2 Printed but not attested

| claim | where | note |
|---|---|---|
| the §5.1 standard-deviation column (0.00, 0.00, 0.00) | lines 186–190 | `reproduce.py` prints the mean differences, not the sd. The header admits the sd column is transcribed. The sd is derivable from the 17 per-task +0.33 diffs in `matched-count-experiment.md` (they are all identical, so sd = 0), but no attached output prints it. |

### 3.3 Verified (for balance)

These numbers are attested by the artefacts and/or by my run:

- 17 tasks = 9 synthetic + 8 corpus (`tasks.py`, `real_tasks.py`).
- 38 properties across nine tasks (38; `reproduce.py` authoring table, `tasks.py`).
- 5 tests in `tests/test_artifact_only_attack.py` (five test functions).
- median 0.007 s CPU (`cost-curve-n8.md`).
- 314 bytes / 0.08% / 8 distinct ASTs (`build-nondeterminism.md`; 414,988–415,302 bytes).
- 38 gate artefacts (`gate-count.json`; `_modules()` = 38).
- 13 defects (table rows 1–13).
- +0.33 / +0.33 / 0.00, matched 0.00 (`matched_families.py`, `reproduce.py`).
- 51 cells / 0 non-singleton (`table_singleton()` returns `(51, 0)`; the printed table shows only 51).
- 459 pad measurements / 0 deviations; 0/153 prepadding (`matched_families.py`).
- 10/17 tasks with `probes = k`; 7 with `c > 0` (`matched_families.py`).
- 2.0 / 3.4 / 5.8 / 8.6 and 8 / 12 / 16 / 20 (`reproduce.py`).
- 25% / 43% (2.0/8.0, 8.6/20.0).
- 9 / 11 / 20 / 20 and 5.11 (3–8 per task) (`dose-response.md`, `reproduce.py`).
- 9 of 9 monotone (`cost-is-build-independent.md`).
- 12 predicate builders; 2 false; 200/200; one in twelve; zero in forty (`transforms.py`, `tests/test_opaque_predicates_are_true.py`, `task-validity.md`, `retraction-cost-curve.md`).
- 24 permutations of `sumselected` (previous review; the paper only claims "every permutation ends at 9" for one task).

---

## 4. Does the title overclaim?

**Yes.** "Diversification Adds Nothing Beyond the Callables It Inserts" is
stronger than 17 tasks and 51 cells support in four ways:

1. **Scope.** It says "diversification", not "transform-family
   diversification"; the paper tests three transform families, one build
   index, three seeds, Python source, function identification.
2. **Outcome.** It says "adds nothing", not "adds no measurable cost on this
   instrument". The paper's own abstract says "no measurable cost" and "we
   claim that this instrument cannot tell"; the matching document says the
   result is "evidence about this metric, not about attacker effort in
   general."
3. **Mechanism.** It says "beyond the callables it inserts"; the experiment
   equalises **count** with a foreign inert pad, not the **identity/behaviour**
   of the inserted callables. The doc's own caveat: "padding up, not stripping
   down"; "pads are the easiest possible candidates".
4. **Resolution.** The diff statistic quantises to 1/3 of a probe; a family
   effect smaller than one probe could not be resolved. "Nothing" is stronger
   than "nothing at this resolution."

A defensible title would keep the measured qualifiers, e.g.:

> **On This Instrument, Transform-Family Diversification Adds Nothing Beyond
> Callable Count**

or

> **A Specification-Derived Probe Counter Cannot See Transform-Family
> Diversity Beyond Callable Count**

The abstract's "adds no measurable cost once the number of callables each
family inserts is held constant" is the sentence the data support. The title
should not be stronger than the abstract.

---

## 5. Guard run, verbatim

```
$ python3 -m pytest tests/test_research_docs_consistency.py tests/test_research_numbers_match_sources.py -q
.....................                                                    [100%]
21 passed in 0.11s
```

(A first run of the same command gave the same 21 passes in 0.19 s; the
pass/fail result is stable, only the wall time varies.)

**What this does and does not mean.** The guards pass, and they do check some
real things: defect-table contiguity, README/HANDOFF defect counts, the
`gate-count.json` artefact total, and the authoring count. They do **not** check
the title, the abstract's "four of which", §6.1's "three", §5.3's "the paper
does not claim one", the order-invariance scope, the "both families"
terminology, or the "60 files" count. A green run is a floor, not a clean bill
of health. The surviving contradictions are precisely in the prose the guards
do not parse.

---

## 6. Bottom line

- **The central result is sound.** The confound was real, the matched-count
  experiment was run, and I reproduced it independently: exactly 0.00 on all
  three pairings and all 17 tasks, with 51 identical task/seed cells and zero
  pad deviations. The paper's core data do not need to change.
- **The paper is not yet internally consistent.** Eight contradictions survive,
  including one that denies the paper's own central structural-channel claim
  (§5.3 vs §5.1b), one on the defect count the rewrite was supposed to fix
  ("four" vs "three" vs the table), and one on the "all/every defect" claim
  that the 30-day expiry refutes.
- **The title overclaims.** The abstract and conclusion are properly qualified;
  the title is not. Fix the title and the eight contradictions, and the paper
  is defensible as a methods note. The data are already there.
- **Nothing found on the core arithmetic.** I tried to break the 0.00, the
  callable counts, the pad additivity, the 51 cells, the 5.11, the 314/0.08,
  the 2.0/8.6 and the 9/11/20/20; all held. The remaining problems are prose,
  scope, and two stale counts, not the experiment.
