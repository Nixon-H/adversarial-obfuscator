# Final verdict on `docs/research/paper-draft.md`

**Auditor:** iceman (closing verdict, fifth task)
**Date:** 2026-11-02
**Baseline:** `master` at `987e85c`, clean before this file was added.
**Interpreter:** `/usr/bin/python3 3.13.5 (main, Aug 10 2026, 12:06:59) [GCC 14.2.0]`

I ran `scripts/transfer/reproduce.py`, the two research guard files, a direct
`table_singleton()` call, and the paper against its source scripts. I modified
nothing except adding this file.

---

## 1. `reproduce.py`: all ten tables

```
singleton            | 51
module-size          | {1: 2, 2: 3.4, 3: 5.8, 4: 8.6}
diversity            | {'A-vs-B': 0.33, 'A-vs-C': 0.33, 'B-vs-C': 0}
fixed-build          | [9, 9, 9, 9, 9]
fault-control        | {'correct': 9, 'fault': 11}
authoring            | {'properties': 38}
calibration          | [9, 11, 20, 20]
sibling-substitution | {'mean': 5.11, 'min': 3, 'max': 8}
diversity-sd         | {'per_task': [0.333], 'tasks': 17, 'sd': 0.0}
blind-baseline       | {1: 8, 2: 12, 3: 16, 4: 20}
```

**No numeric mismatch.** Every value matches the "documents claim" column and
the paper's prose.

Two qualifications on the singleton row: it prints only `51`, while the claim
is "51 cells, 0 non-singleton". A direct call returns
`('singleton', 51, 0, '51 cells, 0 non-singleton')`, but `main()` unpacks
`for name, got, _extra, claim` and drops the non-singleton count, so the printed
table does not exhibit the zero. The script also does not "flag any that differ"
as the paper's status line says: it prints two columns and leaves comparison to
a human.

## 2. Guard run

Before this file was added:

```
$ python3 -m pytest tests/test_research_docs_consistency.py tests/test_research_numbers_match_sources.py -q
......................                                                   [100%]
22 passed in 0.16s
```

After adding this required verdict file, the document-count test fails:

```
AssertionError: the paper says 68 research documents, the directory holds 69
1 failed, 21 passed
```

The guard counts every `*.md` in `docs/research/`, so any new audit document
invalidates the paper's `(68 files)` claim. This is a guard-design defect, not
just a stale number; it cannot be fixed without editing the paper or the test,
both forbidden here.

## 3. The eight prior contradictions

1. **§5.3 semantic/structural channel — fixed.** It now says "does **not**
   create a *semantic* channel" and points at the structural one in §5.1b.
2. **Defect count — only partly fixed.** The abstract now says "ten of which
   produce artefacts that compile and then fail", and the table supports ten
   (3 no-compile, 7 import-fail, 3 runtime/wrong-answer). But §6.1 still says:
   "Three of them produce artefacts that are syntactically valid, compile, and
   then fail"; two of its three bullets (dataclass, `match`) explicitly do not
   compile. The original contradiction survives in §6.1.
3. **"All/every defect" vs the expiry — fixed.** It now says twelve of thirteen
   and names the expiry exception.
4. **Order invariance — fixed.** Scoped to "the single task whose permutations
   were run".
5. **Vendored-package count — fixed.** "two vendored packages; 20 external
   artefacts in a 38-artefact gate".
6. **"Factor of two" — fixed semantically.** "a factor of four" is right for
   2.0 vs 8.0; the edit left a dangling word (see defect 6 below).
7. **"Both families" — fixed.** "Across all three families".
8. **Document count — fixed before this file.** 68, and the guard passed; the
   guard's fragility is a separate defect below.

Seven are adequately fixed; item 2 is not.

## 4. New or surviving defects

### 4.1 §7 denies the independent specification the title claims

§7 says the external sources

> "do **not** provide an independent **specification**, because the
> properties are still written by this paper's author." (lines 468–470)

§5.1b says

> "Six tasks were specified by an author who had not read this paper, from
> docstrings alone, over three third-party modules" (lines 282–284)

and the subtitle says "two of them specified by someone other than this paper's
author" (lines 3–4). The blind tasks use the same external modules
(`recipes.py`, `statistics.py`, `strutils.py`), so the blanket §7 sentence is
false. **This is the material defect**: the limitations section denies the
headline's independent component. It does not invalidate the data — the blind
task script exists and reports the result — but it must be rewritten to
distinguish the 20 gated artefacts from the six blind-specified tasks.

### 4.2 "eight tables" is stale

Lines 9 and 519 say "eight tables". `reproduce.py`'s `main()` prints ten, and
the same header calls the sibling-substitution table the "ninth" and the
per-task sd table the "tenth". Change both to ten.

### 4.3 §4.2 "four or five ... per task" is false for one corpus task

Line 167: "four or five executable assertions per task". `store_keys` has three
properties (`real_tasks.py`), and the corpus tasks range 3–5. Either scope the
sentence to the nine synthetic tasks (as the 38/9 sentence does) or say "three
to five across the 17".

### 4.4 Abstract's "same-arity siblings" is false for the corpus tasks

Line 32: "each a target function among same-arity siblings". In
`held_out/codec/prog.py`, `rle_encode(text)` sits beside `xor_bytes(data, key)`;
in `calibration/calc/prog.py`, `gcd(a, b)` sits beside `fib(n)`. §4.1 correctly
says "the siblings are the other functions in the module". The abstract should
not say "same-arity".

### 4.5 §6.1's "Three of them" (same as prior item 2)

See §3.2. Quote: "Three of them produce artefacts that are syntactically valid,
compile, and then fail" (lines 379–380). Two of the three bullets that follow
say the output does not compile ("an empty class body is not valid Python";
"`SyntaxError: alternative patterns bind different names`"). This is a
self-contradicting paragraph in a section whose own table lists 3 no-compile,
7 import-fail, and 3 runtime defects.

### 4.6 Dangling "sizes"

Line 324: "a factor of four (the ratio narrows as candidates are added) sizes,
and the advantage erodes..." The word "sizes," is a remnant of the deleted
"at small sizes" clause. Copy-edit.

### 4.7 The document-count guard is self-invalidating

After this file, the guard is red at 68 vs 69. A guard that any new research
document breaks cannot guard a growing document set. Exclude audit files, or
derive the count from a manifest.

### 4.8 §4.3's build spread is not reproducible from the repository

The arithmetic is right: the eight sizes' mean is 31,288.75 bytes, spread
5,596 bytes, 17.9%; the named source `scripts/transfer/corpus/pkg/urllib3/_collections.py`
is 17,762 bytes. But the paper gives no seed set or command, and
`build-nondeterminism.md` still records the withdrawn 314-byte (0.08%) figure.
I could not reproduce the listed 30,424 ... 34,208 sizes from `generate_variant`
with the obvious seed sets. The eight "9" probe counts likewise have no script.
This does not affect the central result, but the paper's status line says the
build spread is checkable by "the measurement described in §4.3"; a description
is not a reproduction. Either add the seeds/command or label the numbers as a
reported observation.

## 5. The claim, in one sentence

On 11 load-bearing tasks — 7 hand-written, 2 independently specified, 2 prior
external — with module-level callable counts held constant, a
specification-derived probe counter shows exactly 0.00 difference between the
three transform families; the uncontrolled +0.33/0.00 was a callable-count
artefact, and the counter does respond to module size and semantic faults.

The evidence supports **exactly that sentence**, with the paper's own
qualifications (10 of 17 forced, inert pads, only 2 independent tasks, one-probe
resolution). It does not support the unqualified title as a general claim; the
subtitle's scope is the defensible one.

## 6. Verdict

**SUBMIT WITH NAMED CAVEATS.**

The core result is reproducible: all ten tables match, the guards pass before
this file, the confound and the matched zero are supported, and the external
replication is real. The blockers are textual, not empirical:

1. Rewrite §7 so it does not deny the independent specification of §5.1b and
   the subtitle. **If this is left as written, the paper's headline and its
   limitations contradict; that is the one blocker.**
2. Change "eight tables" to ten in both places.
3. Fix §4.2's "four or five", the abstract's "same-arity", and §6.1's "Three".
4. Repair or scope the document-count guard so the audit file does not turn it
   red.
5. Provide the §4.3 seeds/command, or downgrade the build-spread sentence to a
   reported observation.

Nothing found on the core arithmetic: the 0.00, the +0.33, the 51 cells, the
5.11, the 9/11/20/20, the 2.0/8.6 and the blind baseline all held.
